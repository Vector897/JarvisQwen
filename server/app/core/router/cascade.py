"""模型级联（AutoMix 思想）：轻量层先答 → 启发式自评置信度 → 不达标才升级前沿层。

比起「无脑总是用前沿层」，这让路由层在轻量层已经够用的情况下不多花钱；
比起「无脑总是用轻量层」，又保证了疑难案例不会给出低质量答案。
自评用零成本启发式（不额外调用模型），避免「为了省钱又多花一次钱」的悖论。
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
    """零成本置信度估计：过短、含糊词、明显截断 → 低置信度。"""
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
    """先用轻量层回答；置信度不足则升级前沿层重做。返回 (结果, 是否发生了升级)。"""
    light_result = llm.complete(db, prompt, tier=policy.TIER_LIGHT, task=task,
                                step=f"{step}_light", max_tokens=max_tokens)
    if light_result.cached or light_result.simulated:
        return light_result, False  # 缓存命中/dry-run 不参与级联判断

    confidence = _confidence_heuristic(light_result.text)
    if confidence >= confidence_threshold:
        return light_result, False

    frontier_result = llm.complete(db, prompt, tier=policy.TIER_FRONTIER, task=task,
                                   step=f"{step}_escalated", max_tokens=max_tokens)
    return frontier_result, True
