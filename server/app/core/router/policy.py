"""三级路由决策：规则层（纯代码，0 成本）/ 轻量层 / 前沿层。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..settings_store import get_setting

TIER_RULE = "rule"  # 不调模型
TIER_LIGHT = "light"  # 便宜 API：解析、初筛、简报
TIER_FRONTIER = "frontier"  # 前沿模型：总结、综述


def models_for_tier(db: Session, tier: str) -> list[str]:
    """返回该层的 fallback 链（主模型在前）。"""
    if tier == TIER_LIGHT:
        chain = [get_setting(db, "model_light"), *get_setting(db, "model_light_fallbacks")]
    elif tier == TIER_FRONTIER:
        chain = [get_setting(db, "model_frontier"), *get_setting(db, "model_frontier_fallbacks")]
        # 前沿层全挂时降级到轻量层兜底（断路器思想：降级维持基础能力）
        chain += [get_setting(db, "model_light")]
    else:
        raise ValueError(f"tier '{tier}' 不需要模型")
    seen: set[str] = set()
    return [m for m in chain if m and not (m in seen or seen.add(m))]


def estimate_cost(tier: str, prompt_chars: int) -> float:
    """出境前的粗略成本预估（供预算检查用），按字符数近似 token。"""
    tokens = prompt_chars / 3
    per_mtok = {TIER_LIGHT: 0.9, TIER_FRONTIER: 5.0}.get(tier, 0.9)
    return tokens / 1_000_000 * per_mtok * 2  # 输入+输出粗估


# Qwen Cloud 官方定价（USD / 1M tokens，≤256K 档，来源 docs.qwencloud.com pricing）
QWEN_PRICING: dict[str, tuple[float, float]] = {
    "qwen3.7-max": (2.50, 7.50),
    "qwen3.7-plus": (0.40, 1.60),
    "qwen3.6-flash": (0.25, 1.50),
}


def exact_cost(model: str, tokens_in: int, tokens_out: int) -> float | None:
    """按官方价目表精确计价；未收录的模型返回 None（回退到 LiteLLM 或粗估）。"""
    name = model.split("/", 1)[-1]
    price = QWEN_PRICING.get(name)
    if price is None:
        return None
    return tokens_in / 1_000_000 * price[0] + tokens_out / 1_000_000 * price[1]
