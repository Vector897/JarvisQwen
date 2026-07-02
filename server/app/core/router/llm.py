"""统一 LLM 调用点：所有出境请求的唯一通道。

六道工序：脱敏 → 缓存 → 预算 → 路由 → 弹性调用（退避/断路器/fallback）→ 审计记账。
任何 prompt 都不可能绕过安全与记账——这是本项目的核心工程约束。

未配置任何 API Key 时进入 dry-run 模式：返回模拟响应并在审计中标记 simulated，
保证系统无 Key 也能完整跑通流程（开发/演示用）。
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
        raise resilience.AllModelsFailed(f"厂商 {provider} 没有可用的 API Key")
    kwargs: dict = {
        "api_key": providers.decrypt_key(key_row.encrypted_key),
        "max_tokens": max_tokens,
        "timeout": 120,
    }
    if key_row.base_url:
        kwargs["api_base"] = key_row.base_url
    resp = litellm.completion(model=model, messages=[{"role": "user", "content": prompt}], **kwargs)
    text = resp.choices[0].message.content or ""
    usage = getattr(resp, "usage", None)
    tin = getattr(usage, "prompt_tokens", 0) or 0
    tout = getattr(usage, "completion_tokens", 0) or 0
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

    # ① 脱敏（占位符替换，返回后还原）
    level = str(get_setting(db, "redact_level"))
    red = redact(prompt, level)
    if red.blocked:
        raise RedactionBlocked(red.reason)
    safe_prompt = red.text

    # ② 语义缓存
    hit = cache.lookup(db, tier, safe_prompt)
    if hit is not None:
        audit_log.record(db, task_id=task_id, step=step, model="(cache)", input_text=safe_prompt,
                         output_text=hit, cached=True)
        return LlmResult(text=red.restore(hit), model="(cache)", cost_usd=0, cached=True)

    # ③ 预算检查（超限抛 BudgetExceeded → 引擎将任务挂起）
    budget_guard.check(db, task, upcoming_estimate=policy.estimate_cost(tier, len(safe_prompt)))

    # dry-run：没有任何 Key 时返回模拟响应，流程照走
    if not _has_any_key(db):
        fake = f"[模拟响应/dry-run] tier={tier}，未配置 API Key。请求摘要：{safe_prompt[:120]}"
        audit_log.record(db, task_id=task_id, step=step, model="(simulated)", input_text=safe_prompt,
                         output_text=fake, simulated=True)
        return LlmResult(text=fake, model="(simulated)", cost_usd=0, simulated=True)

    # ④⑤ 路由 + 弹性调用（退避/断路器/fallback 链）
    chain = policy.models_for_tier(db, tier)
    retries = int(get_setting(db, "max_retries"))

    def _do(model: str) -> tuple[str, float, int, int]:
        return _call_litellm(db, model, safe_prompt, max_tokens)

    model, (text, cost, tin, tout) = resilience.call_with_fallbacks(chain, _do, retries_per_model=retries)

    # ⑥ 审计记账 + 缓存回填 + 任务累计花费
    audit_log.record(db, task_id=task_id, step=step, model=model, tokens_in=tin, tokens_out=tout,
                     cost_usd=cost, input_text=safe_prompt, output_text=text)
    cache.store(db, tier, safe_prompt, text, model)
    if task is not None:
        task.cost_usd += cost

    return LlmResult(text=red.restore(text), model=model, cost_usd=cost)
