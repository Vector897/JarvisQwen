"""Lightweight task engine: sequential steps + checkpoint resume + ETA + Artifacts + human-in-the-loop interruption.

V1 uses a home-grown engine (zero extra dependencies, fully controllable behavior); the interface is aligned with LangGraph,
so V2 can migrate smoothly if branching/parallel graphs are needed (see "Project Code Architecture.md").

Key semantics:
- After each step, a Checkpoint (state snapshot) is written immediately; after a crash/restart, execution resumes from the last checkpoint and already-paid-for LLM results are not redone.
- Step durations are written to step_stats (EMA), driving the progress bar and ETA.
- A step may raise NeedApproval (high-risk operation → suspend into the approval queue); the engine catches BudgetExceeded (→ suspend).
- state["artifacts"] is a "verification artifact": it serves both as progress evidence for the Web pipeline view and as a re-run verification point.
"""
from __future__ import annotations

import json
import time
import traceback
from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

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
    default_duration: float = 20.0  # assumed duration when there is no historical data (seconds)


@dataclass
class TaskContext:
    db: Session
    task: Task
    state: dict = field(default_factory=dict)
    # Intra-step progress interpolation baseline (written by the engine at the start of each step): overall progress = base + span * this step's completion fraction
    _prog_base: float = 0.0        # overall progress at the start of this step (0..1)
    _prog_span: float = 0.0        # this step's share of overall progress (0..1)
    _prog_step_dur: float = 0.0    # estimated duration of this step (seconds), used for intra-step ETA countdown
    _prog_after: float = 0.0       # sum of estimated durations of all steps after this one (seconds)

    def artifact(self, name: str, content: str) -> None:
        """Produce a verification artifact (manifest/summary/file list), visible in the pipeline view."""
        self.state.setdefault("artifacts", []).append(
            {"step": self.state.get("_current_step", ""), "name": name,
             "content": content[:8000], "ts": time.time()}
        )

    def report_progress(self, fraction: float, **extra) -> None:
        """Report the completion fraction (0..1) from inside a step, driving the progress bar to advance smoothly within long steps (e.g. per-item summarization).

        If a long step doesn't report, the progress bar freezes for its entire execution; here we compute overall progress
        from the interpolation baseline and persist it (a short commit releases the write lock), so the front-end list page uses events directly and the detail page reads the latest value on refetch."""
        fraction = max(0.0, min(1.0, fraction))
        overall = round(self._prog_base + self._prog_span * fraction, 4)
        self.task.progress = overall
        self.task.eta_ts = time.time() + (1.0 - fraction) * self._prog_step_dur + self._prog_after
        self.db.commit()  # persist and release the write lock; honors the "no lock held across network calls" convention
        bus.publish("task_progress", {"task_id": self.task.id, "progress": overall,
                                      "eta_ts": self.task.eta_ts, **extra})

    def publish(self, **data) -> None:
        bus.publish("task_progress", {"task_id": self.task.id, **data})

    def require_approval(self, desc: str, risk: str = "high") -> None:
        """Call before a high-risk operation: pass if already approved, otherwise suspend into the approval queue."""
        approval_id = self.state.get("_approval_ids", {}).get(desc)
        if approval_id:
            row = self.db.execute(select(Approval).where(Approval.id == approval_id)).scalar_one_or_none()
            if row and row.status == "approved":
                return
            if row and row.status == "rejected":
                raise TaskFailed(f"Action rejected: {desc}")
        raise NeedApproval(desc, risk)


# ---- Task graph registry ----
REGISTRY: dict[str, list[StepDef]] = {}


def register(task_type: str, steps: list[StepDef]) -> None:
    REGISTRY[task_type] = steps


# ---- step_stats (EMA) and ETA ----
def _stat_id(task_type: str, step: str) -> str:
    return f"{task_type}:{step}"


def _record_duration(db: Session, task_type: str, step: str, seconds: float) -> None:
    sid = _stat_id(task_type, step)
    row = db.execute(select(StepStat).where(StepStat.id == sid)).scalar_one_or_none()
    if row is None:
        db.add(StepStat(id=sid, duration_p50=seconds, duration_p90=seconds * 1.5, sample_count=1))
    else:  # exponential moving average approximating quantiles
        row.duration_p50 = 0.7 * row.duration_p50 + 0.3 * seconds
        row.duration_p90 = max(0.8 * row.duration_p90, seconds)
        row.sample_count += 1


def step_durations(db: Session, task_type: str, steps: list[StepDef]) -> list[float]:
    out = []
    for s in steps:
        row = db.execute(select(StepStat).where(StepStat.id == _stat_id(task_type, s.name))).scalar_one_or_none()
        out.append(row.duration_p50 if row and row.duration_p50 > 0 else s.default_duration)
    return out


def _update_progress(db: Session, task: Task, steps: list[StepDef], next_index: int,
                     ctx: "TaskContext | None" = None) -> None:
    durations = step_durations(db, task.type, steps)
    total = sum(durations) or 1.0
    done = sum(durations[:next_index])
    task.progress = round(done / total, 4)
    remaining = sum(durations[next_index:])
    task.eta_ts = time.time() + remaining if next_index < len(steps) else 0
    if ctx is not None and next_index < len(steps):  # record the intra-step progress interpolation baseline
        ctx._prog_base = task.progress
        ctx._prog_span = durations[next_index] / total
        ctx._prog_step_dur = durations[next_index]
        ctx._prog_after = sum(durations[next_index + 1:])
    bus.publish("task_progress", {
        "task_id": task.id, "status": task.status, "progress": task.progress,
        "eta_ts": task.eta_ts, "step_index": next_index, "total_steps": len(steps),
        "step_name": steps[next_index].name if next_index < len(steps) else "done",
    })


def latest_checkpoint(db: Session, task_id: str) -> Checkpoint | None:
    """Get the latest snapshot: the same step_index may have several (e.g. state saved on a failed retry); the most recent one wins."""
    return db.execute(
        select(Checkpoint).where(Checkpoint.task_id == task_id)
        .order_by(Checkpoint.step_index.desc(), Checkpoint.created_at.desc())
    ).scalars().first()


def run_task(db: Session, task: Task) -> None:
    """Execute a task: resume from the last checkpoint. Called by the scheduler worker thread."""
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

    ctx = TaskContext(db=db, task=task, state=state)
    task.status = "RUNNING"

    for i in range(start_index, len(steps)):
        step = steps[i]
        state["_current_step"] = step.name
        _update_progress(db, task, steps, i, ctx)  # also records the intra-step progress interpolation baseline
        db.commit()  # persist progress first: (1) leave no dirty data for an intra-step autoflush to grab the lock (2) make the progress bar immediately visible to the API
        t0 = time.time()
        try:
            new_state = step.fn(ctx, state)
            state = new_state if new_state is not None else state
            ctx.state = state
        except NeedApproval as e:
            approval = Approval(task_id=task.id, action_desc=e.desc, risk_level=e.risk)
            db.add(approval)
            db.flush()
            state.setdefault("_approval_ids", {})[e.desc] = approval.id
            _save_checkpoint(db, task, i - 1, state)  # after approval, re-run from this step
            task.status = "WAITING_APPROVAL"
            bus.publish("approval_needed", {"task_id": task.id, "desc": e.desc, "approval_id": approval.id})
            return
        except BudgetExceeded as e:
            _save_checkpoint(db, task, i - 1, state)
            task.status = "SUSPENDED"
            task.error = str(e)
            bus.publish("task_suspended", {"task_id": task.id, "reason": str(e)})
            return
        except (RedactionBlocked, TaskFailed) as e:
            task.status = "FAILED"
            task.error = str(e)
            task.finished_at = time.time()
            bus.publish("task_failed", {"task_id": task.id, "error": str(e)})
            return
        except Exception as e:  # noqa: BLE001  unknown error: keep the checkpoint, mark as failed and re-runnable
            _save_checkpoint(db, task, i - 1, state)
            task.status = "FAILED"
            task.error = f"{type(e).__name__}: {e}\n{traceback.format_exc()[-1500:]}"
            task.finished_at = time.time()
            bus.publish("task_failed", {"task_id": task.id, "error": str(e)})
            return

        _record_duration(db, task.type, step.name, time.time() - t0)
        _save_checkpoint(db, task, i, state)
        db.commit()  # commit per step: release the SQLite write lock so the next step's LLM/network calls don't hold it;
        #             also make artifacts/audit/checkpoints immediately visible to the API read connection (WAL snapshot).

    task.status = "DONE"
    task.progress = 1.0
    task.eta_ts = 0
    task.finished_at = time.time()
    _update_progress(db, task, steps, len(steps))
    bus.publish("task_done", {"task_id": task.id})


def _save_checkpoint(db: Session, task: Task, step_index: int, state: dict) -> None:
    if step_index < 0:
        step_index = -1  # no step completed yet, but we still need to save state such as approvals
    steps = REGISTRY[task.type]
    name = steps[step_index].name if 0 <= step_index < len(steps) else "(init)"
    db.add(Checkpoint(task_id=task.id, step_index=step_index, step_name=name,
                      state_json=json.dumps(state, ensure_ascii=False)))
    db.flush()
