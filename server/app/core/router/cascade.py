"""Model cascade (AutoMix idea): the light tier answers first → heuristic self-assessed confidence → escalate to the frontier tier only if it falls short.

Compared to "blindly always use the frontier tier", this keeps the router from
overspending when the light tier is already good enough; compared to "blindly always
use the light tier", it ensures hard cases don't get low-quality answers.
Self-assessment uses a zero-cost heuristic (no extra model call), avoiding the paradox
of "spending an extra call in order to save money".
"""
from __future__ import annotations

import re

from sqlalchemy.orm import Session

from ...models import Task
from . import llm, policy

HEDGE_PATTERNS = re.compile(
    r"不确定|不清楚|无法判断|难以确定|可能是|也许|不太好说|"
    r"not sure|uncertain|unclear|cannot determine|i don't know|hard to tell",
    re.IGNORECASE,
)


def _confidence_heuristic(text: str, min_len: int = 20) -> float:
    """Zero-cost confidence estimate: too short, hedging words, or obvious truncation → low confidence."""
    if not text or len(text.strip()) < min_len:
        return 0.2
    score = 1.0
    if HEDGE_PATTERNS.search(text):
        score -= 0.4
    if text.rstrip().endswith(("...", "…")):
        score -= 0.2
    if len(text) < min_len * 2:
        score -= 0.15
    return max(0.0, score)


def complete_cascade(
    db: Session,
    prompt: str,
    *,
    task: Task | None = None,
    step: str = "",
    max_tokens: int = 2048,
    confidence_threshold: float = 0.6,
) -> tuple[llm.LlmResult, bool]:
    """Answer with the light tier first; if confidence is insufficient, escalate to the frontier tier and redo. Returns (result, whether an escalation occurred)."""
    light_result = llm.complete(db, prompt, tier=policy.TIER_LIGHT, task=task,
                                step=f"{step}_light", max_tokens=max_tokens)
    if light_result.cached or light_result.simulated:
        return light_result, False  # cache hit / dry-run does not participate in cascade evaluation

    confidence = _confidence_heuristic(light_result.text)
    if confidence >= confidence_threshold:
        return light_result, False

    frontier_result = llm.complete(db, prompt, tier=policy.TIER_FRONTIER, task=task,
                                   step=f"{step}_escalated", max_tokens=max_tokens)
    return frontier_result, True
