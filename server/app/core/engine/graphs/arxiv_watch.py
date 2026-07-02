"""学术工作流主图：轮询 → 去重 → 初筛 → 下载归档 → 逐篇总结 → 写记忆。

对应架构文档 3.7 学术工作流。params: {"query": "...", "max_results": 15}
"""
from __future__ import annotations

import hashlib
import json

from sqlalchemy import select

from ....connectors import arxiv, pdf_ingest
from ....models import Paper, Summary
from ...bus import bus
from ...memory import memory
from ...router import llm, policy
from ...security.prompt_guard import wrap_external
from ...settings_store import get_setting
from ..engine import StepDef, TaskContext, register


def fingerprint(title: str, arxiv_id: str) -> str:
    return hashlib.sha256(f"{arxiv_id}|{title.lower().strip()}".encode()).hexdigest()[:32]


def step_fetch(ctx: TaskContext, state: dict) -> dict:
    params = state["params"]
    found = arxiv.search(params.get("query", "LLM agents"), int(params.get("max_results", 15)))
    state["found"] = found
    ctx.artifact("检索结果", "\n".join(f"- {p['title']} ({p['published_at']})" for p in found) or "(无结果)")
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
    ctx.artifact("去重结果", f"新论文 {len(fresh)} / 检索 {len(state['found'])} 篇")
    return state


def step_filter(ctx: TaskContext, state: dict) -> dict:
    """轻量层初筛：按用户研究方向给相关度打分。"""
    fresh = state["fresh"]
    if not fresh:
        state["selected"] = []
        return state
    profile = str(get_setting(ctx.db, "research_profile")) or state["params"].get("query", "")
    listing = "\n".join(f"{i}. {p['title']} — {p['abstract'][:300]}" for i, p in enumerate(fresh))
    prompt = (
        f"我的研究方向：{profile}\n\n以下是候选论文，请为每篇打相关度分（0-1），"
        f'只输出 JSON 数组，如 [{{"i":0,"score":0.8}}]：\n\n{wrap_external(listing)}'
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
    selected = [p for i, p in enumerate(fresh) if scores.get(i, 0) >= threshold]
    state["selected"] = selected
    ctx.artifact("初筛结果", "\n".join(
        f"- [{scores.get(i, 0):.2f}] {p['title']}" for i, p in enumerate(fresh)) or "(无)")
    return state


def step_ingest(ctx: TaskContext, state: dict) -> dict:
    """下载 PDF 并入库（纯代码，0 token）。"""
    stored_ids = []
    for p in state["selected"]:
        pdf_path = pdf_ingest.download_pdf(p.get("pdf_url", ""), p["arxiv_id"])
        paper = Paper(
            arxiv_id=p["arxiv_id"], title=p["title"], authors=p["authors"],
            abstract=p["abstract"], published_at=p["published_at"], url=p["url"],
            pdf_path=pdf_path, dedup_fingerprint=p["fingerprint"], owner_id=ctx.task.owner_id,
        )
        ctx.db.add(paper)
        ctx.db.flush()
        stored_ids.append(paper.id)
    state["paper_ids"] = stored_ids
    ctx.artifact("归档清单", f"已归档 {len(stored_ids)} 篇（PDF + 元数据）")
    return state


def step_summarize(ctx: TaskContext, state: dict) -> dict:
    """前沿层逐篇总结。断点友好：逐篇记录进度，重跑跳过已完成。"""
    done: list[str] = state.setdefault("summarized", [])
    ids = state.get("paper_ids", [])
    for idx, pid in enumerate(ids):
        if pid in done:
            continue
        paper = ctx.db.execute(select(Paper).where(Paper.id == pid)).scalar_one()
        fulltext = pdf_ingest.extract_text(paper.pdf_path, max_chars=40000)
        body = fulltext if fulltext else paper.abstract
        prompt = (
            "请总结这篇论文：核心贡献、方法、实验结论、与已有工作的差异，"
            "以及对科研人员的启示。用中文、Markdown 格式、400 字以内。\n\n"
            f"标题：{paper.title}\n\n{wrap_external(body)}"
        )
        result = llm.complete(ctx.db, prompt, tier=policy.TIER_FRONTIER, task=ctx.task,
                              step="summarize", max_tokens=1500)
        ctx.db.add(Summary(paper_id=pid, model=result.model, content_md=result.text,
                           cost_usd=result.cost_usd))
        done.append(pid)
        bus.publish("task_progress", {"task_id": ctx.task.id,
                                      "sub_progress": f"总结 {idx + 1}/{len(ids)}"})
    ctx.artifact("总结完成", f"共总结 {len(done)} 篇")
    return state


def step_memorize(ctx: TaskContext, state: dict) -> dict:
    n = len(state.get("summarized", []))
    q = state["params"].get("query", "")
    memory.write_episodic(ctx.db, ctx.task.owner_id,
                          f"执行文献跟踪「{q}」：检索 {len(state.get('found', []))} 篇，"
                          f"新增 {len(state.get('fresh', []))} 篇，总结 {n} 篇。",
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
