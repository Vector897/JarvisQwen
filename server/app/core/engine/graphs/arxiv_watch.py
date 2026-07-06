"""学术工作流主图：轮询 → 去重 → 初筛 → 下载归档 → 逐篇总结 → 写记忆。

对应架构文档 3.7 学术工作流。params: {"query": "...", "max_results": 15}
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


MAX_DEEP = 6  # 单次任务最多深度总结的条目数（控成本与时长）


def fingerprint(title: str, arxiv_id: str) -> str:
    return hashlib.sha256(f"{arxiv_id}|{title.lower().strip()}".encode()).hexdigest()[:32]


def _route_source(ctx: TaskContext, query: str) -> str:
    """判定查询该走 'arxiv' 还是 'news'。

    优先用轻量层 LLM 分类——关键词允许列表判不准非学术查询（名人/产品名会误入
    arXiv：如 "Taylor Swift" 会命中泰勒展开类论文）。dry-run（无 Key，返回 simulated）
    或分类失败时回退到启发式 is_news_query。分类结果走语义缓存，重复查询 0 成本。"""
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
    except Exception:  # noqa: BLE001  分类失败不阻断，落到启发式
        pass
    return "news" if news.is_news_query(query) else "arxiv"


def step_fetch(ctx: TaskContext, state: dict) -> dict:
    """抓取候选条目。LLM 判定学术/新闻后走对应源；所选源为空时反向兜底，
    保证"任意查询都有结果"且不会把名人/产品查询错配成无关论文。"""
    params = state["params"]
    query = params.get("query", "LLM agents")
    n = int(params.get("max_results", 15))
    source = _route_source(ctx, query)
    if source == "news":
        found = news.search(query, n)
        if not found:  # 新闻空 → 反向退学术
            found, source = arxiv.search(query, n), "arxiv"
    else:
        found = arxiv.search(query, n)
        if not found:  # 学术空 → 退回新闻
            found, source = news.search(query, n), "news"
    state["found"] = found
    state["source"] = source
    unit = "papers" if source == "arxiv" else "news articles"
    body = "\n".join(f"- {p['title']} ({p['published_at']})" for p in found) or "(no results)"
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
    """轻量层初筛：按用户研究方向给相关度打分。"""
    fresh = state["fresh"]
    if not fresh:
        state["selected"] = []
        return state
    # 新闻按"查询词"判相关（命中查询的文章都相关）；论文按用户研究画像判相关。
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
    except Exception:  # noqa: BLE001  解析失败（或 dry-run）→ 全部通过，宁多勿漏
        scores = {i: 1.0 for i in range(len(fresh))}
    # 过阈值后按分数降序，最多深度总结 MAX_DEEP 篇（控成本/时长：新闻常全部命中）
    passing = sorted((i for i in range(len(fresh)) if scores.get(i, 0) >= threshold),
                     key=lambda i: scores.get(i, 0), reverse=True)
    selected = [fresh[i] for i in passing[:MAX_DEEP]]
    state["selected"] = selected
    ctx.artifact("Triage scores", "\n".join(
        f"- [{scores.get(i, 0):.2f}] {p['title']}" for i, p in enumerate(fresh)) or "(none)")
    return state


def step_ingest(ctx: TaskContext, state: dict) -> dict:
    """下载 PDF 并入库（纯代码，0 token）。"""
    stored_ids = []
    for p in state["selected"]:
        # 逐篇提交后崩溃重跑的幂等兜底：该指纹已入库则复用，不重复下载/插入
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
        ctx.db.commit()  # 逐篇提交而非 flush：flush 拿到的写锁会横跨下一篇的 PDF 下载（网络）
        stored_ids.append(paper.id)
    state["paper_ids"] = stored_ids
    ctx.artifact("Archive manifest", f"Archived {len(stored_ids)} papers (PDF + metadata)")
    return state


def step_summarize(ctx: TaskContext, state: dict) -> dict:
    """前沿层逐篇总结。断点友好：逐篇记录进度，重跑跳过已完成。"""
    done: list[str] = state.setdefault("summarized", [])
    ids = state.get("paper_ids", [])
    for idx, pid in enumerate(ids):
        if pid in done:
            continue
        # 上次运行已总结并提交过 → 幂等跳过，不重复付费（逐篇提交后崩溃重跑的兜底）。
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
        # 逐篇上报步内进度：这是唯一足够长的步骤（多次 ~120s 调用），不上报进度条会冻结。
        # report_progress 内部 commit——同时完成"逐篇提交释放写锁"，两个目的合一。
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
