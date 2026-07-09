"""Memory system: episodic memory writes, nightly consolidation into semantic memory, two-layer retrieval, heat-decay eviction.

Corresponds to the research report "LLM Memory Management": task execution serves as a natural
episode boundary; consolidation runs on a schedule during off-peak hours; retrieval first filters by
SQL tags then matches text (V2 switches to vectors).
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
    """Two-layer retrieval: tag/keyword filtering → sort by heat and recency. Matched memories get heat +1."""
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


def _keyword_overlap(a: str, b: str) -> float:
    wa, wb = set(a.lower().split()), set(b.lower().split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _find_conflict(db: Session, owner_id: str, new_fact: str) -> Memory | None:
    """Coarse-grained conflict detection: find an existing semantic memory whose topic overlaps the new fact but whose content differs (a candidate for temporal arbitration)."""
    existing = db.execute(
        select(Memory).where(Memory.kind == "semantic", Memory.owner_id == owner_id, Memory.archived == 0)
    ).scalars().all()
    best, best_score = None, 0.0
    for m in existing:
        overlap = _keyword_overlap(new_fact, m.content)
        if overlap > best_score:
            best_score, best = overlap, m
    # Topic overlaps but it's not the same sentence → possibly old/new phrasings of the same topic, hand off to arbitration
    if best is not None and 0.35 <= best_score < 0.95:
        return best
    return None


def _arbitrate(db: Session, old: Memory, new_fact: str) -> str:
    """Temporal arbitration: produce a reconciling summary that preserves historical continuity, rather than a hard overwrite."""
    prompt = (
        "Below are two records on the same topic from different points in time; they may conflict. "
        "Write ONE sentence that reconciles them with explicit time sense "
        "(e.g. 'X was A before T1, updated to B since'):"
        f"\nOld record: {old.content}\nNew record: {new_fact}"
    )
    result = llm.complete(db, prompt, tier=policy.TIER_LIGHT, step="memory_arbitrate", max_tokens=200)
    return result.text.strip() or f"{old.content} (updated: {new_fact})"


def consolidate(db: Session, owner_id: str) -> int:
    """Nightly consolidation: hand the last 24h of episodic memories to the light tier to distill into semantic memory; on conflict, use temporal arbitration rather than a hard overwrite."""
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
        "Below are work-log fragments from a research-assistant system over the past 24 hours. "
        "Extract 1-5 facts or patterns worth remembering long-term (topics the user cares "
        "about, recurring themes, explicit preferences). One per line, conclusions only:\n\n" + joined
    )
    result = llm.complete(db, prompt, tier=policy.TIER_LIGHT, step="memory_consolidate", max_tokens=512)
    count = 0
    for line in result.text.splitlines():
        fact = line.strip().lstrip("0123456789.、- ")
        if len(fact) < 8:
            continue
        conflict = _find_conflict(db, owner_id, fact)
        if conflict is not None:
            reconciled = _arbitrate(db, conflict, fact)
            conflict.content = reconciled
            conflict.confidence = min(1.0, conflict.confidence + 0.1)
            conflict.ts = time.time()
            conflict.tags = (conflict.tags + ",reconciled").strip(",")
        else:
            db.add(Memory(kind="semantic", content=fact, tags="consolidated", owner_id=owner_id))
        count += 1
    return count


def decay_heat(db: Session, factor: float = 0.95, archive_below: float = 0.05) -> int:
    """Forgetting curve: heat decays, and entries too low are removed from the retrieval index (archived, not deleted)."""
    rows = db.execute(select(Memory).where(Memory.archived == 0)).scalars().all()
    archived = 0
    for m in rows:
        m.heat *= factor
        if m.heat < archive_below and m.kind == "episodic":
            m.archived = 1
            archived += 1
    return archived
