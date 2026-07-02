"""记忆系统：情节记忆写入、夜间整合为语义记忆、两层检索、热度衰减驱逐。

对应调研报告《大模型记忆管理》：以任务执行为天然情节边界；
整合（Consolidation）在低峰定时执行；检索先 SQL 标签过滤再文本匹配（V2 换向量）。
"""
from __future__ import annotations

import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import Memory
from ..router import llm, policy


def write_episodic(db: Session, owner_id: str, content: str, tags: str = "") -> None:
    db.add(Memory(kind="episodic", content=content[:4000], tags=tags, owner_id=owner_id))


def retrieve(db: Session, owner_id: str, query_terms: list[str], limit: int = 10) -> list[Memory]:
    """两层检索：标签/关键词过滤 → 按热度与新近度排序。命中的记忆热度+1。"""
    rows = db.execute(
        select(Memory).where(Memory.owner_id == owner_id, Memory.archived == 0)
    ).scalars().all()
    scored: list[tuple[float, Memory]] = []
    for m in rows:
        text = (m.content + " " + m.tags).lower()
        score = sum(1.0 for t in query_terms if t.lower() in text)
        if score > 0:
            scored.append((score + m.heat * 0.1, m))
    scored.sort(key=lambda x: (-x[0], -x[1].ts))
    hits = [m for _, m in scored[:limit]]
    for m in hits:
        m.heat += 1.0
    return hits


def consolidate(db: Session, owner_id: str) -> int:
    """夜间整合：把近 24h 情节记忆交给轻量层提炼为语义记忆。"""
    cutoff = time.time() - 86400
    episodes = db.execute(
        select(Memory).where(
            Memory.kind == "episodic", Memory.owner_id == owner_id,
            Memory.ts >= cutoff, Memory.archived == 0,
        )
    ).scalars().all()
    if len(episodes) < 3:
        return 0
    joined = "\n---\n".join(e.content[:500] for e in episodes[:40])
    prompt = (
        "以下是一个科研助理系统过去 24 小时的工作记录片段。"
        "请提炼出 1-5 条值得长期记住的事实或模式（如用户关注的方向、反复出现的主题、明确的偏好），"
        "每条一行，直接输出结论，不要编号以外的多余文字：\n\n" + joined
    )
    result = llm.complete(db, prompt, tier=policy.TIER_LIGHT, step="memory_consolidate", max_tokens=512)
    count = 0
    for line in result.text.splitlines():
        line = line.strip().lstrip("0123456789.、- ")
        if len(line) >= 8:
            db.add(Memory(kind="semantic", content=line, tags="consolidated", owner_id=owner_id))
            count += 1
    return count


def decay_heat(db: Session, factor: float = 0.95, archive_below: float = 0.05) -> int:
    """遗忘曲线：热度衰减，过低者移出检索索引（归档不删除）。"""
    rows = db.execute(select(Memory).where(Memory.archived == 0)).scalars().all()
    archived = 0
    for m in rows:
        m.heat *= factor
        if m.heat < archive_below and m.kind == "episodic":
            m.archived = 1
            archived += 1
    return archived
