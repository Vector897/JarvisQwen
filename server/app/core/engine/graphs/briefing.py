"""晨间简报图：聚合近 24h 总结 → 轻量层撰写 → 入库推送。"""
from __future__ import annotations

import time

from sqlalchemy import select

from ....models import Briefing, Paper, Summary
from ...bus import bus
from ...router import llm, policy
from ..engine import StepDef, TaskContext, register


def step_gather(ctx: TaskContext, state: dict) -> dict:
    cutoff = time.time() - 86400
    rows = ctx.db.execute(
        select(Summary, Paper).join(Paper, Summary.paper_id == Paper.id)
        .where(Summary.created_at >= cutoff, Paper.owner_id == ctx.task.owner_id)
        .order_by(Summary.created_at.desc())
    ).all()
    state["items"] = [
        {"title": p.title, "url": p.url, "summary": s.content_md[:1200]} for s, p in rows
    ]
    ctx.artifact("素材清单", f"近 24 小时共 {len(state['items'])} 篇总结")
    return state


def step_compose(ctx: TaskContext, state: dict) -> dict:
    items = state["items"]
    if not items:
        state["briefing_md"] = "## 今日简报\n\n过去 24 小时没有新论文动态。"
        return state
    material = "\n\n---\n\n".join(f"### {it['title']}\n{it['summary']}" for it in items[:20])
    prompt = (
        "你是科研助理。根据以下论文总结素材，写一份中文晨间简报（Markdown）："
        "开头 2-3 句话概括今日要点；然后每篇论文 2-3 句话要点 + 一句'为什么值得看'。"
        "简明、信息密度高、不要空话。\n\n" + material
    )
    result = llm.complete(ctx.db, prompt, tier=policy.TIER_LIGHT, task=ctx.task,
                          step="compose", max_tokens=2000)
    # 简报末尾附原文链接（本地拼接，0 token）
    links = "\n".join(f"- [{it['title']}]({it['url']})" for it in items)
    state["briefing_md"] = result.text + "\n\n## 原文链接\n" + links
    return state


def step_save(ctx: TaskContext, state: dict) -> dict:
    date = time.strftime("%Y-%m-%d")
    ctx.db.add(Briefing(date=date, content_md=state["briefing_md"], owner_id=ctx.task.owner_id))
    bus.publish("briefing_ready", {"date": date, "task_id": ctx.task.id})
    ctx.artifact("简报", state["briefing_md"][:2000])
    return state


register("briefing", [
    StepDef("gather", step_gather, default_duration=2),
    StepDef("compose", step_compose, default_duration=20),
    StepDef("save", step_save, default_duration=1),
])
