"""Unified LLM call point: the single channel for all outbound requests.

Six-stage pipeline: redact → cache → budget → route → resilient call
(backoff / circuit breaker / fallback) → audit accounting.
No prompt can ever bypass security and accounting — this is the project's core
engineering constraint.

When no API key is configured, it enters dry-run mode: returns a simulated
response and marks it as simulated in the audit log, ensuring the system can run
the full pipeline end-to-end even without a key (for development/demo use).
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from ...models import Task
from ..budget import guard as budget_guard
from ..cache import semantic as cache
from ..security import audit_log
from ..security.redact import redact
from ..settings_store import get_setting
from . import policy, providers, resilience


@dataclass
class LlmResult:
    text: str
    model: str
    cost_usd: float
    cached: bool = False
    simulated: bool = False


class RedactionBlocked(Exception):
    pass


def _call_litellm(db: Session, model: str, prompt: str, max_tokens: int) -> tuple[str, float, int, int]:
    import litellm

    provider = providers.provider_of_model(model)
    key_row = providers.pick_key(db, provider)
    if key_row is None:
        raise resilience.AllModelsFailed(f"No usable API key for provider {provider}")
    kwargs: dict = {
        "api_key": providers.decrypt_key(key_row.encrypted_key),
        "max_tokens": max_tokens,
        "timeout": 120,
    }
    call_model, api_base = providers.litellm_route(model, key_row)
    if api_base:
        kwargs["api_base"] = api_base
    resp = litellm.completion(model=call_model, messages=[{"role": "user", "content": prompt}], **kwargs)
    text = resp.choices[0].message.content or ""
    usage = getattr(resp, "usage", None)
    tin = getattr(usage, "prompt_tokens", 0) or 0
    tout = getattr(usage, "completion_tokens", 0) or 0
    cost = policy.exact_cost(model, tin, tout)  # Qwen official price list takes precedence
    if cost is None:
        try:
            cost = float(litellm.completion_cost(completion_response=resp))
        except Exception:  # noqa: BLE001
            cost = policy.estimate_cost(policy.TIER_FRONTIER, len(prompt))
    return text, cost, tin, tout


def _has_any_key(db: Session) -> bool:
    from sqlalchemy import select

    from ...models import ApiKey

    return db.execute(select(ApiKey).where(ApiKey.status == "active")).first() is not None


def complete(
    db: Session,
    prompt: str,
    *,
    tier: str = policy.TIER_LIGHT,
    task: Task | None = None,
    step: str = "",
    max_tokens: int = 2048,
) -> LlmResult:
    task_id = task.id if task else ""

    # (1) Redaction (replace with placeholders, restore after the response returns)
    level = str(get_setting(db, "redact_level"))
    red = redact(prompt, level)
    if red.blocked:
        raise RedactionBlocked(red.reason)
    safe_prompt = red.text

    # (2) Semantic cache
    hit = cache.lookup(db, tier, safe_prompt)
    if hit is not None:
        audit_log.record(db, task_id=task_id, step=step, model="(cache)", input_text=safe_prompt,
                         output_text=hit, cached=True)
        return LlmResult(text=red.restore(hit), model="(cache)", cost_usd=0, cached=True)

    # (3) Budget check (raises BudgetExceeded when over limit → engine suspends the task)
    budget_guard.check(db, task, upcoming_estimate=policy.estimate_cost(tier, len(safe_prompt)))

    # dry-run: when no key exists, return a simulated response and keep the pipeline running
    if not _has_any_key(db):
        fake = f"[simulated/dry-run] tier={tier}, no API key configured. Prompt digest: {safe_prompt[:120]}"
        audit_log.record(db, task_id=task_id, step=step, model="(simulated)", input_text=safe_prompt,
                         output_text=fake, simulated=True)
        return LlmResult(text=fake, model="(simulated)", cost_usd=0, simulated=True)

    # (4)(5) Routing + resilient call (backoff / circuit breaker / fallback chain)
    # Commit first: flush the dirty writes produced by autoflush (progress, cache counters, etc.)
    # to the database and release the SQLite write lock; otherwise the write lock would be held
    # across the entire (up to 120s) network call, blocking every POST site-wide.
    db.commit()
    chain = policy.models_for_tier(db, tier)
    retries = int(get_setting(db, "max_retries"))

    def _do(model: str) -> tuple[str, float, int, int]:
        return _call_litellm(db, model, safe_prompt, max_tokens)

    model, (text, cost, tin, tout) = resilience.call_with_fallbacks(chain, _do, retries_per_model=retries)

    # (6) Audit accounting + cache backfill + accumulate task spend
    audit_log.record(db, task_id=task_id, step=step, model=model, tokens_in=tin, tokens_out=tout,
                     cost_usd=cost, input_text=safe_prompt, output_text=text)
    cache.store(db, tier, safe_prompt, text, model)
    if task is not None:
        task.cost_usd += cost

    return LlmResult(text=red.restore(text), model=model, cost_usd=cost)
