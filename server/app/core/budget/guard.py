"""预算帽：日预算 + 任务预算双重限制；80% 告警、100% 熔断。"""
from __future__ import annotations

import time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...models import AuditLog, Task
from ..bus import bus
from ..settings_store import get_setting


class BudgetExceeded(Exception):
    pass


def today_start_ts() -> float:
    lt = time.localtime()
    return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))


def today_spend(db: Session) -> float:
    v = db.execute(
        select(func.coalesce(func.sum(AuditLog.cost_usd), 0.0)).where(AuditLog.ts >= today_start_ts())
    ).scalar_one()
    return float(v)


def check(db: Session, task: Task | None = None, upcoming_estimate: float = 0.01) -> None:
    """在每次 LLM 出境调用前检查。超限抛 BudgetExceeded → 任务挂起而非死循环烧钱。"""
    daily_limit = float(get_setting(db, "daily_budget_usd"))
    spent = today_spend(db)
    if spent + upcoming_estimate >= daily_limit:
        bus.publish("budget_alert", {"level": "cutoff", "spent": spent, "limit": daily_limit})
        raise BudgetExceeded(f"日预算已用尽（${spent:.2f}/${daily_limit:.2f}）")
    if spent >= 0.8 * daily_limit:
        bus.publish("budget_alert", {"level": "warn", "spent": spent, "limit": daily_limit})
    if task is not None and task.budget_limit_usd > 0 and task.cost_usd >= task.budget_limit_usd:
        raise BudgetExceeded(f"任务预算已用尽（${task.cost_usd:.2f}/${task.budget_limit_usd:.2f}）")
