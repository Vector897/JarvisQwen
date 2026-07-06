"""统一 LLM 调用点：所有出境请求的唯一通道。

六道工序：脱敏 → 缓存 → 预算 → 路由 → 弹性调用（退避/断路器/fallback）→ 审计记账。
任何 prompt 都不可能绕过安全与记账——这是本项目的核心工程约束。

会话纪律（本模块是全项目的样板）：DB 会话只为一次交互而活，绝不跨网络调用。
执行分三段：
  ① 短会话：脱敏/缓存/预算/路由计划（连 API Key 都在此取好），提交即关闭
  ② 纯网络：litellm 调用（最长 120s），期间不持有任何会话或 SQLite 锁
  ③ 短会话：审计 + 缓存回填 + 任务花费累计
SQLite 单写者模型下，任何"开着事务做网络"的写法都会锁死全站写操作。

未配置任何 API Key 时进入 dry-run 模式：返回模拟响应并在审计中标记 simulated，
保证系统无 Key 也能完整跑通流程（开发/演示用）。
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from ...db import session
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


def _has_any_key(db) -> bool:
    from ...models import ApiKey

    return db.execute(select(ApiKey).where(ApiKey.status == "active")).first() is not None


def complete(
    prompt: str,
    *,
    tier: str = policy.TIER_LIGHT,
    task_id: str = "",
    step: str = "",
    max_tokens: int = 2048,
) -> LlmResult:
    # ---- ① 短会话：全部前置 DB 工作，返回前提交关闭 ----
    with session() as db:
        level = str(get_setting(db, "redact_level"))
        red = redact(prompt, level)
        if red.blocked:
            raise RedactionBlocked(red.reason)
        safe_prompt = red.text

        hit = cache.lookup(db, tier, safe_prompt)
        if hit is not None:
            audit_log.record(db, task_id=task_id, step=step, model="(cache)", input_text=safe_prompt,
                             output_text=hit, cached=True)
            return LlmResult(text=red.restore(hit), model="(cache)", cost_usd=0, cached=True)

        # 预算检查（超限抛 BudgetExceeded → 引擎将任务挂起）；任务行现查现用，不依赖外部 ORM 对象
        task_row = db.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none() if task_id else None
        budget_guard.check(db, task_row, upcoming_estimate=policy.estimate_cost(tier, len(safe_prompt)))

        # dry-run：没有任何 Key 时返回模拟响应，流程照走
        if not _has_any_key(db):
            fake = f"[simulated/dry-run] tier={tier}, no API key configured. Prompt digest: {safe_prompt[:120]}"
            audit_log.record(db, task_id=task_id, step=step, model="(simulated)", input_text=safe_prompt,
                             output_text=fake, simulated=True)
            return LlmResult(text=fake, model="(simulated)", cost_usd=0, simulated=True)

        # 路由计划：每个候选模型的调用名/Key/endpoint 都在会话内取好，网络阶段零 DB 依赖
        retries = int(get_setting(db, "max_retries"))
        plan: dict[str, tuple[str, str, str]] = {}  # model -> (call_model, api_key, api_base)
        for model in policy.models_for_tier(db, tier):
            key_row = providers.pick_key(db, providers.provider_of_model(model))
            if key_row is None:
                continue
            call_model, api_base = providers.litellm_route(model, key_row)
            plan[model] = (call_model, providers.decrypt_key(key_row.encrypted_key), api_base)

    chain = list(plan)
    if not chain:
        raise resilience.AllModelsFailed(f"No usable API key for any model in tier {tier}")

    # ---- ② 纯网络：不持有任何会话/写锁 ----
    def _do(model: str) -> tuple[str, float, int, int]:
        import litellm

        call_model, api_key, api_base = plan[model]
        kwargs: dict = {"api_key": api_key, "max_tokens": max_tokens, "timeout": 120}
        if api_base:
            kwargs["api_base"] = api_base
        resp = litellm.completion(model=call_model, messages=[{"role": "user", "content": safe_prompt}], **kwargs)
        text = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None)
        tin = getattr(usage, "prompt_tokens", 0) or 0
        tout = getattr(usage, "completion_tokens", 0) or 0
        cost = policy.exact_cost(model, tin, tout)  # Qwen 官方价目表优先
        if cost is None:
            try:
                cost = float(litellm.completion_cost(completion_response=resp))
            except Exception:  # noqa: BLE001
                cost = policy.estimate_cost(policy.TIER_FRONTIER, len(safe_prompt))
        return text, cost, tin, tout

    model, (text, cost, tin, tout) = resilience.call_with_fallbacks(chain, _do, retries_per_model=retries)

    # ---- ③ 短会话：审计记账 + 缓存回填 + 任务累计花费 ----
    with session() as db:
        audit_log.record(db, task_id=task_id, step=step, model=model, tokens_in=tin, tokens_out=tout,
                         cost_usd=cost, input_text=safe_prompt, output_text=text)
        cache.store(db, tier, safe_prompt, text, model)
        if task_id:
            task_row = db.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()
            if task_row is not None:
                task_row.cost_usd += cost

    return LlmResult(text=red.restore(text), model=model, cost_usd=cost)
