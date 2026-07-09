"""Morning briefing graph: aggregate the last 24h of summaries → compose with the light tier → store and push."""
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
    rows = ctx.db.execute(
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
    result = llm.complete(ctx.db, prompt, tier=policy.TIER_LIGHT, task=ctx.task,
                          step="compose", max_tokens=2000)
    # append source links at the end of the briefing (assembled locally, 0 tokens)
    links = "\n".join(f"- [{it['title']}]({it['url']})" for it in items)
    state["briefing_md"] = result.text + "\n\n## Links\n" + links
    return state


def step_save(ctx: TaskContext, state: dict) -> dict:
    date = time.strftime("%Y-%m-%d")
    ctx.db.add(Briefing(date=date, content_md=state["briefing_md"], owner_id=ctx.task.owner_id))
    ctx.artifact("Briefing", state["briefing_md"][:2000])
    ctx.db.commit()  # persist and release the write lock first, then do the external push — Telegram+SMTP takes up to ~30s,
    #                  and holding the write lock during that would deadlock all site-wide POSTs (a settings SELECT would autoflush dirty objects)
    bus.publish("briefing_ready", {"date": date, "task_id": ctx.task.id})
    notify_all(ctx.db, f"JarvisQwen briefing {date}", state["briefing_md"][:3500])
    return state


register("briefing", [
    StepDef("gather", step_gather, default_duration=2),
    StepDef("compose", step_compose, default_duration=20),
    StepDef("save", step_save, default_duration=1),
])
