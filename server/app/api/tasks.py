"""任务：创建（自然语言或结构化）、列表、详情（流水线+Artifacts+ETA）、重跑/取消。"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..core.engine.engine import REGISTRY, latest_checkpoint, step_durations
from ..core.engine.task_templates import TEMPLATES, apply_template
from ..db import get_db
from ..models import Task, User

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskIn(BaseModel):
    type: str = ""  # 留空 + 给 prompt = 自然语言解析
    prompt: str = ""
    params: dict = {}
    title: str = ""
    budget_limit_usd: float = 1.0
    priority: int = 5
    template_id: str = ""  # 优先级：template_id > type > prompt
    template_values: dict = {}


@router.get("/templates")
def list_templates():
    return TEMPLATES


def _parse_prompt(prompt: str) -> tuple[str, dict, str]:
    """自然语言 → 任务。V1 规则解析（0 token），V2 换轻量层模型解析。"""
    p = prompt.strip()
    lowered = p.lower()
    if any(k in lowered for k in ("简报", "briefing", "日报", "digest")):
        return "briefing", {}, "Morning briefing"
    # 默认视为文献跟踪/调研请求，提取主题
    for prefix in ("帮我调研", "调研", "跟踪", "检索", "查找", "搜索",
                   "research the latest progress on", "track new papers on", "track", "watch",
                   "research", "survey recent work on", "survey", "search", "find", "monitor"):
        if lowered.startswith(prefix):
            p = p[len(prefix):].strip("：: ，, ")
            break
    return "arxiv_watch", {"query": p or "LLM agents", "max_results": 15}, f"Watch: {p[:40]}"


@router.post("")
def create_task(body: TaskIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role == "viewer":
        raise HTTPException(403, "Viewers cannot create tasks")
    if body.template_id:
        try:
            ttype, params, title = apply_template(body.template_id, body.template_values)
        except ValueError as e:
            raise HTTPException(400, str(e))
    elif body.type:
        ttype, params, title = body.type, body.params, body.title or body.type
    elif body.prompt:
        ttype, params, title = _parse_prompt(body.prompt)
    else:
        raise HTTPException(400, "type, prompt, or template_id required")
    if ttype not in REGISTRY:
        raise HTTPException(400, f"Unknown task type: {ttype}; available: {list(REGISTRY)}")
    task = Task(type=ttype, title=title, params_json=json.dumps(params, ensure_ascii=False),
                owner_id=user.id, priority=body.priority, budget_limit_usd=body.budget_limit_usd)
    db.add(task)
    db.flush()
    return {"id": task.id, "type": ttype, "title": title, "status": task.status}


@router.get("")
def list_tasks(status: str = "", limit: int = 50,
               user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(Task).order_by(Task.created_at.desc()).limit(limit)
    if user.role != "admin":
        q = q.where(Task.owner_id == user.id)
    if status:
        q = q.where(Task.status == status)
    rows = db.execute(q).scalars().all()
    return [_brief(t) for t in rows]


def _brief(t: Task) -> dict:
    return {"id": t.id, "type": t.type, "title": t.title, "status": t.status,
            "progress": t.progress, "eta_ts": t.eta_ts, "cost_usd": round(t.cost_usd, 4),
            "created_at": t.created_at, "finished_at": t.finished_at, "error": t.error[:300]}


@router.get("/{task_id}")
def task_detail(task_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = db.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Task not found")
    if user.role != "admin" and t.owner_id != user.id:
        raise HTTPException(403, "Not allowed to view this task")
    steps = REGISTRY.get(t.type, [])
    cp = latest_checkpoint(db, t.id)
    done_index = cp.step_index if cp else -1
    state = json.loads(cp.state_json) if cp else {}
    durations = step_durations(db, t.type, steps) if steps else []
    pipeline = []
    for i, s in enumerate(steps):
        if t.status == "DONE" or i <= done_index:
            st = "done"
        elif i == done_index + 1 and t.status == "RUNNING":
            st = "running"
        elif i == done_index + 1 and t.status == "WAITING_APPROVAL":
            st = "waiting_approval"
        elif i == done_index + 1 and t.status in ("FAILED", "SUSPENDED"):
            st = "failed" if t.status == "FAILED" else "suspended"
        else:
            st = "pending"
        pipeline.append({"index": i, "name": s.name, "status": st,
                         "est_duration": round(durations[i], 1) if durations else 0})
    return {**_brief(t), "params": json.loads(t.params_json), "pipeline": pipeline,
            "artifacts": state.get("artifacts", [])}


@router.post("/{task_id}/rerun")
def rerun(task_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """从最后检查点重新排队（FAILED/SUSPENDED/DONE 均可）。"""
    t = db.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Task not found")
    if user.role != "admin" and t.owner_id != user.id:
        raise HTTPException(403, "Not allowed to operate on this task")
    t.status = "QUEUED"
    t.error = ""
    t.finished_at = 0
    return {"ok": True, "status": t.status}


@router.post("/{task_id}/cancel")
def cancel(task_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = db.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Task not found")
    if user.role != "admin" and t.owner_id != user.id:
        raise HTTPException(403, "Not allowed to operate on this task")
    if t.status in ("QUEUED", "SUSPENDED", "WAITING_APPROVAL"):
        t.status = "CANCELLED"
    return {"ok": True, "status": t.status}
