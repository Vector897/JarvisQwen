"""晨间简报图：聚合近 24h 总结 → 轻量层撰写 → 入库推送。

会话纪律：DB 读写在短会话内；LLM 撰写与外部推送（Telegram/SMTP）在会话外。
"""
from __future__ import annotations

import time

from sqlalchemy import select

from ....connectors.notify import notify_all
from ....models import Briefing, Paper, Summary
from ...bus import bus
from ...router import llm, policy
from ..engine import StepDef, TaskContext, register


def step_gather(ctx: TaskContext, state: dict) -> dict:
    cutoff = time.time() - 86400
    with ctx.session() as db:
        rows = db.execute(
            select(Summary, Paper).join(Paper, Summary.paper_id == Paper.id)
            .where(Summary.created_at >= cutoff, Paper.owner_id == ctx.task.owner_id)
            .order_by(Summary.created_at.desc())
        ).all()
        state["items"] = [
            {"title": p.title, "url": p.url, "summary": s.content_md[:1200]} for s, p in rows
        ]
    ctx.artifact("Source material", f"{len(state['items'])} summaries from the last 24h")
    return state


def step_compose(ctx: TaskContext, state: dict) -> dict:
    items = state["items"]
    if not items:
        state["briefing_md"] = "## Today's briefing\n\nNo new papers in the last 24 hours."
        return state
    material = "\n\n---\n\n".join(f"### {it['title']}\n{it['summary']}" for it in items[:20])
    prompt = (
        "You are a research assistant. From the paper summaries below, write a morning "
        "briefing in Markdown: open with 2-3 sentences on today's key takeaways, then for "
        "each paper give 2-3 sentences of highlights plus one line on why it's worth reading. "
        "Concise, information-dense, no filler.\n\n" + material
    )
    result = llm.complete(prompt, tier=policy.TIER_LIGHT, task_id=ctx.task.id,
                          step="compose", max_tokens=2000)  # 网络，无会话
    # 简报末尾附原文链接（本地拼接，0 token）
    links = "\n".join(f"- [{it['title']}]({it['url']})" for it in items)
    state["briefing_md"] = result.text + "\n\n## Links\n" + links
    return state


def step_save(ctx: TaskContext, state: dict) -> dict:
    date = time.strftime("%Y-%m-%d")
    with ctx.session() as db:
        db.add(Briefing(date=date, content_md=state["briefing_md"], owner_id=ctx.task.owner_id))
    ctx.artifact("Briefing", state["briefing_md"][:2000])
    # 会话已提交关闭，再做外部推送（Telegram+SMTP 最长 ~30s，期间不得持有会话/写锁）
    bus.publish("briefing_ready", {"date": date, "task_id": ctx.task.id})
    notify_all(f"JarvisQwen briefing {date}", state["briefing_md"][:3500])
    return state


register("briefing", [
    StepDef("gather", step_gather, default_duration=2),
    StepDef("compose", step_compose, default_duration=20),
    StepDef("save", step_save, default_duration=1),
])
