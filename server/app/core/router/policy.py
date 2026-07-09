"""Three-tier routing decision: rule tier (pure code, zero cost) / light tier / frontier tier."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..settings_store import get_setting

TIER_RULE = "rule"  # no model call
TIER_LIGHT = "light"  # cheap API: parsing, initial screening, briefs
TIER_FRONTIER = "frontier"  # frontier model: summarization, synthesis


def models_for_tier(db: Session, tier: str) -> list[str]:
    """Return the fallback chain for this tier (primary model first)."""
    if tier == TIER_LIGHT:
        chain = [get_setting(db, "model_light"), *get_setting(db, "model_light_fallbacks")]
    elif tier == TIER_FRONTIER:
        chain = [get_setting(db, "model_frontier"), *get_setting(db, "model_frontier_fallbacks")]
        # When the entire frontier tier is down, degrade to the light tier as a fallback
        # (circuit-breaker principle: degrade to preserve baseline capability)
        chain += [get_setting(db, "model_light")]
    else:
        raise ValueError(f"tier '{tier}' does not require a model")
    seen: set[str] = set()
    return [m for m in chain if m and not (m in seen or seen.add(m))]


def estimate_cost(tier: str, prompt_chars: int) -> float:
    """Rough pre-egress cost estimate (for budget checks), approximating tokens by character count."""
    tokens = prompt_chars / 3
    per_mtok = {TIER_LIGHT: 0.9, TIER_FRONTIER: 5.0}.get(tier, 0.9)
    return tokens / 1_000_000 * per_mtok * 2  # rough estimate of input + output


# Qwen Cloud official pricing (USD / 1M tokens, ≤256K tier, source: docs.qwencloud.com pricing)
QWEN_PRICING: dict[str, tuple[float, float]] = {
    "qwen3.7-max": (2.50, 7.50),
    "qwen3.7-plus": (0.40, 1.60),
    "qwen3.6-flash": (0.25, 1.50),
}


def exact_cost(model: str, tokens_in: int, tokens_out: int) -> float | None:
    """Price exactly from the official price list; return None for unlisted models (falls back to LiteLLM or a rough estimate)."""
    name = model.split("/", 1)[-1]
    price = QWEN_PRICING.get(name)
    if price is None:
        return None
    return tokens_in / 1_000_000 * price[0] + tokens_out / 1_000_000 * price[1]
