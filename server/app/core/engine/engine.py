"""轻量任务引擎：顺序步骤 + 检查点续跑 + ETA + Artifacts + 人类在环中断。

V1 用自研引擎（零额外依赖、行为完全可控）；接口与 LangGraph 对齐，
V2 若需要分支/并行图可平滑迁移（见《项目代码架构.md》）。

关键语义：
- 每步执行后立即写 Checkpoint（状态快照），崩溃/重启后从最后检查点恢复，已付费的 LLM 结果不重做。
- 步骤耗时写入 step_stats（EMA），驱动进度条与 ETA。
- 步骤可抛 NeedApproval（高危操作 → 审批队列挂起）、引擎捕获 BudgetExceeded（→ 挂起）。
- state["artifacts"] 是"验证伪影"：既是 Web 流水线视图的进度证据，也是重跑核验点。

会话纪律：引擎不再持有贯穿任务的长会话。所有引擎簿记（状态/进度/检查点）
各自开短会话即写即提交；步骤函数通过 ctx.session() 开短会话，且必须保证
任何网络调用（LLM/下载/推送）都发生在会话之外——SQLite 单写者模型下，
跨网络调用持有的写锁会堵死全站写操作（这是本项目曾全站瘫痪的根因）。
"""
from __future__ import annotations

import json
import time
import traceback
from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db import session as db_session
from ...models import Approval, Checkpoint, StepStat, Task
from ..budget.guard import BudgetExceeded
from ..bus import bus
from ..router.llm import RedactionBlocked


class NeedApproval(Exception):
    def __init__(self, desc: str, risk: str = "high") -> None:
        super().__init__(desc)
        self.desc = desc
        self.risk = risk


class TaskFailed(Exception):
    pass


@dataclass
class StepDef:
    name: str
    fn: Callable[["TaskContext", dict], dict]
    default_duration: float = 20.0  # 无历史数据时的耗时假设（秒）


@dataclass
class TaskContext:
    task: Task  # 分离态快照：属性只读可用（id/type/owner_id/params_json...）；写库走 ctx.session()
    state: dict = field(default_factory=dict)

    def session(self):
        """短会话工厂：with ctx.session() as db: ...（退出即提交关闭，不得跨网络调用）。"""
        return db_session()

    def artifact(self, name: str, content: str) -> None:
        """产出一个验证伪影（清单/摘要/文件列表），流水线视图可见。"""
        self.state.setdefault("artifacts", []).append(
            {"step": self.state.get("_current_step", ""), "name": name,
             "content": content[:8000], "ts": time.time()}
        )

    def publish(self, **data) -> None:
        bus.publish("task_progress", {"task_id": self.task.id, **data})

    def require_approval(self, desc: str, risk: str = "high") -> None:
        """高危操作前调用：已批准则通过，否则挂起进审批队列。"""
        approval_id = self.state.get("_approval_ids", {}).get(desc)
        if approval_id:
            with db_session() as db:
                row = db.execute(select(Approval).where(Approval.id == approval_id)).scalar_one_or_none()
                status = row.status if row else ""
            if status == "approved":
                return
            if status == "rejected":
                raise TaskFailed(f"Action rejected: {desc}")
        raise NeedApproval(desc, risk)


# ---- 任务图注册表 ----
REGISTRY: dict[str, list[StepDef]] = {}


def register(task_type: str, steps: list[StepDef]) -> None:
    REGISTRY[task_type] = steps


# ---- step_stats（EMA）与 ETA ----
def _stat_id(task_type: str, step: str) -> str:
    return f"{task_type}:{step}"


def _record_duration(db: Session, task_type: str, step: str, seconds: float) -> None:
    sid = _stat_id(task_type, step)
    row = db.execute(select(StepStat).where(StepStat.id == sid)).scalar_one_or_none()
    if row is None:
        db.add(StepStat(id=sid, duration_p50=seconds, duration_p90=seconds * 1.5, sample_count=1))
    else:  # 指数移动平均近似分位数
        row.duration_p50 = 0.7 * row.duration_p50 + 0.3 * seconds
        row.duration_p90 = max(0.8 * row.duration_p90, seconds)
        row.sample_count += 1


def step_durations(db: Session, task_type: str, steps: list[StepDef]) -> list[float]:
    out = []
    for s in steps:
        row = db.execute(select(StepStat).where(StepStat.id == _stat_id(task_type, s.name))).scalar_one_or_none()
        out.append(row.duration_p50 if row and row.duration_p50 > 0 else s.default_duration)
    return out


def _update_progress(db: Session, task: Task, steps: list[StepDef], next_index: int) -> None:
    durations = step_durations(db, task.type, steps)
    total = sum(durations) or 1.0
    done = sum(durations[:next_index])
    task.progress = round(done / total, 4)
    remaining = sum(durations[next_index:])
    task.eta_ts = time.time() + remaining if next_index < len(steps) else 0
    bus.publish("task_progress", {
        "task_id": task.id, "status": task.status, "progress": task.progress,
        "eta_ts": task.eta_ts, "step_index": next_index, "total_steps": len(steps),
        "step_name": steps[next_index].name if next_index < len(steps) else "done",
    })


def latest_checkpoint(db: Session, task_id: str) -> Checkpoint | None:
    """取最新快照：同一 step_index 可能有多个（如失败重试保存的状态），以时间最新者为准。"""
    return db.execute(
        select(Checkpoint).where(Checkpoint.task_id == task_id)
        .order_by(Checkpoint.step_index.desc(), Checkpoint.created_at.desc())
    ).scalars().first()


def _fetch_task(db: Session, task_id: str) -> Task:
    return db.execute(select(Task).where(Task.id == task_id)).scalar_one()


def run_task(task_id: str) -> None:
    """执行任务：从最后一个检查点续跑。由调度器工作线程调用。

    引擎自管会话：每次簿记开短会话即写即提交，步骤执行期间（含其中的
    LLM/网络调用）不持有任何会话。
    """
    with db_session() as db:
        task = _fetch_task(db, task_id)
        steps = REGISTRY.get(task.type)
        if not steps:
            task.status = "FAILED"
            task.error = f"Unknown task type: {task.type}"
            return
        cp = latest_checkpoint(db, task.id)
        if cp is not None:
            state: dict = json.loads(cp.state_json)
            start_index = cp.step_index + 1
        else:
            state = {"params": json.loads(task.params_json)}
            start_index = 0
        task.status = "RUNNING"
    # 会话已提交关闭；task 是分离态快照（expire_on_commit=False，属性可读）

    ctx = TaskContext(task=task, state=state)

    for i in range(start_index, len(steps)):
        step = steps[i]
        state["_current_step"] = step.name
        with db_session() as db:  # 进度即写即提交：对 API 实时可见，且不留脏数据给步内查询 autoflush
            _update_progress(db, _fetch_task(db, task_id), steps, i)
        t0 = time.time()
        try:
            new_state = step.fn(ctx, state)
            state = new_state if new_state is not None else state
            ctx.state = state
        except NeedApproval as e:
            with db_session() as db:
                approval = Approval(task_id=task_id, action_desc=e.desc, risk_level=e.risk)
                db.add(approval)
                db.flush()
                state.setdefault("_approval_ids", {})[e.desc] = approval.id
                _save_checkpoint(db, task, i - 1, state)  # 审批通过后从本步重跑
                _fetch_task(db, task_id).status = "WAITING_APPROVAL"
                approval_id = approval.id
            bus.publish("approval_needed", {"task_id": task_id, "desc": e.desc, "approval_id": approval_id})
            return
        except BudgetExceeded as e:
            with db_session() as db:
                _save_checkpoint(db, task, i - 1, state)
                row = _fetch_task(db, task_id)
                row.status = "SUSPENDED"
                row.error = str(e)
            bus.publish("task_suspended", {"task_id": task_id, "reason": str(e)})
            return
        except (RedactionBlocked, TaskFailed) as e:
            with db_session() as db:
                row = _fetch_task(db, task_id)
                row.status = "FAILED"
                row.error = str(e)
                row.finished_at = time.time()
            bus.publish("task_failed", {"task_id": task_id, "error": str(e)})
            return
        except Exception as e:  # noqa: BLE001  未知错误：保留检查点，标记失败可重跑
            with db_session() as db:
                _save_checkpoint(db, task, i - 1, state)
                row = _fetch_task(db, task_id)
                row.status = "FAILED"
                row.error = f"{type(e).__name__}: {e}\n{traceback.format_exc()[-1500:]}"
                row.finished_at = time.time()
            bus.publish("task_failed", {"task_id": task_id, "error": str(e)})
            return

        with db_session() as db:
            _record_duration(db, task.type, step.name, time.time() - t0)
            _save_checkpoint(db, task, i, state)

    with db_session() as db:
        row = _fetch_task(db, task_id)
        row.status = "DONE"
        row.progress = 1.0
        row.eta_ts = 0
        row.finished_at = time.time()
        _update_progress(db, row, steps, len(steps))
    bus.publish("task_done", {"task_id": task_id})


def _save_checkpoint(db: Session, task: Task, step_index: int, state: dict) -> None:
    if step_index < 0:
        step_index = -1  # 尚未完成任何步骤，但需要保存审批等状态
    steps = REGISTRY[task.type]
    name = steps[step_index].name if 0 <= step_index < len(steps) else "(init)"
    db.add(Checkpoint(task_id=task.id, step_index=step_index, step_name=name,
                      state_json=json.dumps(state, ensure_ascii=False)))
    db.flush()
