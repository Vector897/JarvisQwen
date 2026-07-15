"""Academic workflow main graph: poll → dedupe → triage → download & archive → per-item summarize → write memory.

Corresponds to architecture doc 3.7 Academic Workflow. params: {"query": "...", "max_results": 15}
"""
from __future__ import annotations

import hashlib
import json

from sqlalchemy import select

from ....connectors import arxiv, news, pdf_ingest
from ....models import Paper, Summary
from ...bus import bus
from ...memory import memory
from ...router import llm, policy
from ...security.prompt_guard import wrap_external
from ...settings_store import get_setting
from ..engine import StepDef, TaskContext, register


MAX_DEEP = 6  # max number of items deep-summarized per task (controls cost and duration)


def fingerprint(title: str, arxiv_id: str) -> str:
    return hashlib.sha256(f"{arxiv_id}|{title.lower().strip()}".encode()).hexdigest()[:32]


def _route_source(ctx: TaskContext, query: str) -> str:
    """Decide whether a query should go to 'arxiv' or 'news'.

    Prefer classification by the light-tier LLM — a keyword allowlist can't reliably judge non-academic queries (celebrity/product names slip into
    arXiv: e.g. "Taylor Swift" would match Taylor-expansion papers). On dry-run (no Key, returns simulated)
    or classification failure, fall back to the heuristic is_news_query. Classification results go through the semantic cache, so repeated queries cost 0."""
    prompt = (
        "Classify this search query as exactly one word — 'academic' or 'news'.\n"
        "academic = scholarly research: papers, science, math, algorithms, ML/AI methods.\n"
        "news = people, companies, products, markets, politics, entertainment, current events.\n"
        f"Query: {query}\nAnswer:"
    )
    try:
        result = llm.complete(ctx.db, prompt, tier=policy.TIER_LIGHT, task=ctx.task,
                              step="route", max_tokens=8)
        if not result.simulated:
            ans = result.text.strip().lower()
            if "news" in ans:
                return "news"
            if "academic" in ans or "arxiv" in ans:
                return "arxiv"
    except Exception:  # noqa: BLE001  classification failure is non-blocking, fall through to the heuristic
        pass
    return "news" if news.is_news_query(query) else "arxiv"


def step_fetch(ctx: TaskContext, state: dict) -> dict:
    """Fetch candidate items. After the LLM decides academic/news, use the corresponding source; if the chosen source is empty, fall back to the other,
    guaranteeing "any query yields results" and that celebrity/product queries aren't mismatched to unrelated papers."""
    params = state["params"]
    query = params.get("query", "LLM agents")
    n = int(params.get("max_results", 15))
    source = _route_source(ctx, query)
    if source == "news":
        found = news.search(query, n)
        if not found:  # news empty → fall back to academic
            found, source = arxiv.search(query, n), "arxiv"
    else:
        found = arxiv.search(query, n)
        if not found:  # academic empty → fall back to news
            found, source = news.search(query, n), "news"
    state["found"] = found
    state["source"] = source
    unit = "papers" if source == "arxiv" else "news articles"
    body = "\n".join(
        (f"- [{p['title']} ({p['published_at']})]({p['url']})" if p.get("url")
         else f"- {p['title']} ({p['published_at']})")
        for p in found
    ) or "(no results)"
    ctx.artifact("Search results", f"[source: {source} · {len(found)} {unit}]\n{body}")
    return state


def step_dedupe(ctx: TaskContext, state: dict) -> dict:
    fresh = []
    for p in state["found"]:
        fp = fingerprint(p["title"], p["arxiv_id"])
        exists = ctx.db.execute(select(Paper).where(Paper.dedup_fingerprint == fp)).first()
        if not exists:
            p["fingerprint"] = fp
            fresh.append(p)
    state["fresh"] = fresh
    ctx.artifact("Dedupe result", f"{len(fresh)} new / {len(state['found'])} fetched")
    return state


def step_filter(ctx: TaskContext, state: dict) -> dict:
    """Light-tier triage: score relevance against the user's research focus."""
    fresh = state["fresh"]
    if not fresh:
        state["selected"] = []
        return state
    # News relevance is judged by the "query terms" (any article matching the query is relevant); papers are judged by the user's research profile.
    if state.get("source") == "news":
        profile = state["params"].get("query", "") or str(get_setting(ctx.db, "research_profile"))
    else:
        profile = str(get_setting(ctx.db, "research_profile")) or state["params"].get("query", "")
    listing = "\n".join(f"{i}. {p['title']} — {p['abstract'][:300]}" for i, p in enumerate(fresh))
    prompt = (
        f"My research focus: {profile}\n\nBelow are candidate papers. Score each for relevance (0-1). "
        f'Output ONLY a JSON array like [{{"i":0,"score":0.8}}]:\n\n{wrap_external(listing)}'
    )
    result = llm.complete(ctx.db, prompt, tier=policy.TIER_LIGHT, task=ctx.task, step="filter", max_tokens=1024)
    threshold = float(get_setting(ctx.db, "relevance_threshold"))
    scores: dict[int, float] = {}
    try:
        text = result.text
        start, end = text.find("["), text.rfind("]")
        for item in json.loads(text[start : end + 1]):
            scores[int(item["i"])] = float(item["score"])
    except Exception:  # noqa: BLE001  parse failure (or dry-run) → let everything through, better too many than miss any
        scores = {i: 1.0 for i in range(len(fresh))}
    # After passing the threshold, sort by score descending and deep-summarize at most MAX_DEEP items (controls cost/duration: news often all match)
    passing = sorted((i for i in range(len(fresh)) if scores.get(i, 0) >= threshold),
                     key=lambda i: scores.get(i, 0), reverse=True)
    selected = [fresh[i] for i in passing[:MAX_DEEP]]
    state["selected"] = selected
    ctx.artifact("Triage scores", "\n".join(
        f"- [{scores.get(i, 0):.2f}] {p['title']}" for i, p in enumerate(fresh)) or "(none)")
    return state


def step_ingest(ctx: TaskContext, state: dict) -> dict:
    """Download PDFs and store them (pure code, 0 tokens)."""
    stored_ids = []
    for p in state["selected"]:
        # idempotent fallback for crash-and-rerun after per-item commit: if this fingerprint is already stored, reuse it without re-downloading/re-inserting
        prev = ctx.db.execute(select(Paper).where(Paper.dedup_fingerprint == p["fingerprint"])).scalar_one_or_none()
        if prev is not None:
            stored_ids.append(prev.id)
            continue
        pdf_path = pdf_ingest.download_pdf(p.get("pdf_url", ""), p["arxiv_id"])
        paper = Paper(
            arxiv_id=p["arxiv_id"], title=p["title"], authors=p["authors"],
            abstract=p["abstract"], published_at=p["published_at"], url=p["url"],
            pdf_path=pdf_path, dedup_fingerprint=p["fingerprint"], owner_id=ctx.task.owner_id,
        )
        ctx.db.add(paper)
        ctx.db.commit()  # commit per item rather than flush: a write lock from flush would span the next item's PDF download (network)
        stored_ids.append(paper.id)
    state["paper_ids"] = stored_ids
    ctx.artifact("Archive manifest", f"Archived {len(stored_ids)} papers (PDF + metadata)")
    return state


def step_summarize(ctx: TaskContext, state: dict) -> dict:
    """Frontier-tier per-item summarization. Checkpoint-friendly: record progress per item, skip completed ones on rerun."""
    done: list[str] = state.setdefault("summarized", [])
    ids = state.get("paper_ids", [])
    for idx, pid in enumerate(ids):
        if pid in done:
            continue
        # already summarized and committed in a previous run → idempotently skip without paying again (fallback for crash-and-rerun after per-item commit).
        if ctx.db.execute(select(Summary).where(Summary.paper_id == pid)).first():
            done.append(pid)
            continue
        paper = ctx.db.execute(select(Paper).where(Paper.id == pid)).scalar_one()
        fulltext = pdf_ingest.extract_text(paper.pdf_path, max_chars=40000)
        body = fulltext if fulltext else paper.abstract
        if state.get("source") == "news":
            prompt = (
                "Summarize this news item for a busy reader: what happened, why it matters, "
                "the key numbers/quotes, and what to watch next. Markdown, under 200 words.\n\n"
                f"Headline: {paper.title}\nSource: {paper.authors}\n\n{wrap_external(body)}"
            )
        else:
            prompt = (
                "Summarize this paper: core contribution, method, experimental findings, "
                "how it differs from prior work, and takeaways for researchers. "
                "Markdown, under 300 words.\n\n"
                f"Title: {paper.title}\n\n{wrap_external(body)}"
            )
        result = llm.complete(ctx.db, prompt, tier=policy.TIER_FRONTIER, task=ctx.task,
                              step="summarize", max_tokens=1500)
        ctx.db.add(Summary(paper_id=pid, model=result.model, content_md=result.text,
                           cost_usd=result.cost_usd))
        done.append(pid)
        # report intra-step progress per item: this is the only step long enough (multiple ~120s calls); without reporting the progress bar freezes.
        # report_progress commits internally — also accomplishing "per-item commit releases the write lock", two goals in one.
        ctx.report_progress((idx + 1) / len(ids),
                            sub_progress=f"Summarizing {idx + 1}/{len(ids)}")
    ctx.artifact("Summaries done", f"Summarized {len(done)} papers")
    return state


def step_memorize(ctx: TaskContext, state: dict) -> dict:
    n = len(state.get("summarized", []))
    q = state["params"].get("query", "")
    memory.write_episodic(ctx.db, ctx.task.owner_id,
                          f"Ran literature watch '{q}': fetched {len(state.get('found', []))}, "
                          f"{len(state.get('fresh', []))} new, summarized {n}.",
                          tags=f"arxiv_watch,{q}")
    return state


register("arxiv_watch", [
    StepDef("fetch", step_fetch, default_duration=8),
    StepDef("dedupe", step_dedupe, default_duration=1),
    StepDef("filter", step_filter, default_duration=15),
    StepDef("ingest", step_ingest, default_duration=30),
    StepDef("summarize", step_summarize, default_duration=120),
    StepDef("memorize", step_memorize, default_duration=1),
])
