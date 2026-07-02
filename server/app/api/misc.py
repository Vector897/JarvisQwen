"""订阅 / 知识库 / 简报 / 审批 / 审计 / 设置 / 仪表盘——轻量 CRUD 集合。"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import current_user, require_admin
from ..core.budget.guard import today_spend
from ..core.settings_store import DEFAULTS, all_settings, get_setting, set_setting
from ..db import get_db
from ..models import (Approval, AuditLog, Briefing, Paper, Subscription, Summary, Task, User)

router = APIRouter(prefix="/api", tags=["misc"])


# ---------- 订阅 ----------
class SubIn(BaseModel):
    query: str
    interval_minutes: int = 360


@router.post("/subscriptions")
def add_sub(body: SubIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    sub = Subscription(owner_id=user.id, query=body.query, interval_minutes=max(30, body.interval_minutes))
    db.add(sub)
    db.flush()
    return {"id": sub.id}


@router.get("/subscriptions")
def list_subs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(Subscription).order_by(Subscription.created_at.desc())
    if user.role != "admin":
        q = q.where(Subscription.owner_id == user.id)
    return [{"id": s.id, "query": s.query, "interval_minutes": s.interval_minutes,
             "enabled": bool(s.enabled), "last_run_at": s.last_run_at}
            for s in db.execute(q).scalars()]


@router.post("/subscriptions/{sub_id}/toggle")
def toggle_sub(sub_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = db.execute(select(Subscription).where(Subscription.id == sub_id)).scalar_one_or_none()
    if not s:
        raise HTTPException(404)
    s.enabled = 0 if s.enabled else 1
    return {"enabled": bool(s.enabled)}


@router.delete("/subscriptions/{sub_id}")
def delete_sub(sub_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = db.execute(select(Subscription).where(Subscription.id == sub_id)).scalar_one_or_none()
    if s:
        db.delete(s)
    return {"ok": True}


# ---------- 知识库 ----------
@router.get("/library")
def library(q: str = "", limit: int = 50,
            user: User = Depends(current_user), db: Session = Depends(get_db)):
    stmt = select(Paper).order_by(Paper.created_at.desc()).limit(limit)
    if user.role != "admin":
        stmt = stmt.where(Paper.owner_id == user.id)  # AFR：检索前权限过滤
    if q:
        stmt = stmt.where(Paper.title.like(f"%{q}%") | Paper.abstract.like(f"%{q}%"))
    papers = db.execute(stmt).scalars().all()
    out = []
    for p in papers:
        s = db.execute(select(Summary).where(Summary.paper_id == p.id)
                       .order_by(Summary.created_at.desc())).scalars().first()
        out.append({"id": p.id, "title": p.title, "authors": p.authors[:200],
                    "published_at": p.published_at, "url": p.url, "has_pdf": bool(p.pdf_path),
                    "summary_md": s.content_md if s else "", "abstract": p.abstract[:500]})
    return out


# ---------- 简报 ----------
@router.get("/briefings")
def briefings(limit: int = 14, user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(Briefing).order_by(Briefing.created_at.desc()).limit(limit)
    if user.role != "admin":
        q = q.where(Briefing.owner_id == user.id)
    return [{"id": b.id, "date": b.date, "content_md": b.content_md}
            for b in db.execute(q).scalars()]


# ---------- 审批（HITL）----------
@router.get("/approvals")
def approvals(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Approval).where(Approval.status == "pending")
                      .order_by(Approval.created_at.desc())).scalars().all()
    return [{"id": a.id, "task_id": a.task_id, "action_desc": a.action_desc,
             "risk_level": a.risk_level, "created_at": a.created_at} for a in rows]


@router.post("/approvals/{approval_id}/{decision}")
def decide(approval_id: str, decision: str,
           user: User = Depends(current_user), db: Session = Depends(get_db)):
    if decision not in ("approve", "reject"):
        raise HTTPException(400, "decision 必须是 approve/reject")
    a = db.execute(select(Approval).where(Approval.id == approval_id)).scalar_one_or_none()
    if not a or a.status != "pending":
        raise HTTPException(404, "审批项不存在或已处理")
    a.status = "approved" if decision == "approve" else "rejected"
    a.decided_by = user.id
    task = db.execute(select(Task).where(Task.id == a.task_id)).scalar_one_or_none()
    if task and task.status == "WAITING_APPROVAL":
        task.status = "QUEUED"  # 从检查点无缝继续（拒绝的情况由 require_approval 抛 TaskFailed）
    return {"ok": True, "status": a.status}


# ---------- 审计 ----------
@router.get("/audit")
def audit(task_id: str = "", limit: int = 100,
          user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(AuditLog).order_by(AuditLog.ts.desc()).limit(limit)
    if task_id:
        q = q.where(AuditLog.task_id == task_id)
    return [{"id": r.id, "task_id": r.task_id, "step": r.step, "model": r.model,
             "tokens_in": r.tokens_in, "tokens_out": r.tokens_out,
             "cost_usd": round(r.cost_usd, 6), "cached": bool(r.cached),
             "simulated": bool(r.simulated), "ts": r.ts,
             "input_digest": r.input_digest, "output_digest": r.output_digest}
            for r in db.execute(q).scalars()]


# ---------- 设置 ----------
@router.get("/settings")
def read_settings(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return all_settings(db)


class SettingsIn(BaseModel):
    values: dict


@router.put("/settings")
def write_settings(body: SettingsIn, user: User = Depends(require_admin),
                   db: Session = Depends(get_db)):
    unknown = [k for k in body.values if k not in DEFAULTS]
    if unknown:
        raise HTTPException(400, f"未知配置项：{unknown}")
    for k, v in body.values.items():
        set_setting(db, k, v)
    return {"ok": True}


# ---------- 仪表盘 ----------
@router.get("/dashboard")
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)):
    spent = today_spend(db)
    limit = float(get_setting(db, "daily_budget_usd"))
    counts = dict(db.execute(select(Task.status, func.count()).group_by(Task.status)).all())
    day_ago = time.time() - 86400
    calls_24h = db.execute(select(func.count()).select_from(AuditLog)
                           .where(AuditLog.ts >= day_ago)).scalar_one()
    cached_24h = db.execute(select(func.count()).select_from(AuditLog)
                            .where(AuditLog.ts >= day_ago, AuditLog.cached == 1)).scalar_one()
    papers_total = db.execute(select(func.count()).select_from(Paper)).scalar_one()
    return {"today_spend_usd": round(spent, 4), "daily_budget_usd": limit,
            "task_counts": counts, "llm_calls_24h": calls_24h,
            "cache_hits_24h": cached_24h, "papers_total": papers_total}
