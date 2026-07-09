"""Subscriptions / library / briefings / approvals / audit / settings / dashboard — a collection of lightweight CRUD endpoints."""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import current_user, require_admin
from ..connectors.export import markdown_to_pdf_bytes, to_bibtex
from ..connectors.notify import notify_all
from ..connectors.zotero import paper_to_zotero_item, push_papers
from ..core.budget.guard import today_spend
from ..core.router import cascade
from ..core.settings_store import DEFAULTS, SECRET_KEYS, all_settings, get_setting, set_setting
from ..db import get_db
from ..models import (Approval, AuditLog, Briefing, Paper, Subscription, Summary, Task, User)

router = APIRouter(prefix="/api", tags=["misc"])


# ---------- Subscriptions ----------
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


# ---------- Library ----------
@router.get("/library")
def library(q: str = "", limit: int = 50,
            user: User = Depends(current_user), db: Session = Depends(get_db)):
    stmt = select(Paper).order_by(Paper.created_at.desc()).limit(limit)
    if user.role != "admin":
        stmt = stmt.where(Paper.owner_id == user.id)  # AFR: permission filtering before retrieval
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


# ---------- Briefings ----------
@router.get("/briefings")
def briefings(limit: int = 14, user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(Briefing).order_by(Briefing.created_at.desc()).limit(limit)
    if user.role != "admin":
        q = q.where(Briefing.owner_id == user.id)
    return [{"id": b.id, "date": b.date, "content_md": b.content_md}
            for b in db.execute(q).scalars()]


# ---------- Approvals (HITL) ----------
@router.get("/approvals")
def approvals(user: User = Depends(current_user), db: Session = Depends(get_db)):
    # Only list pending approvals for the user's own tasks (admin sees all): an approval decision restarts the task, so it must not act across users
    q = (select(Approval).join(Task, Approval.task_id == Task.id)
         .where(Approval.status == "pending").order_by(Approval.created_at.desc()))
    if user.role != "admin":
        q = q.where(Task.owner_id == user.id)
    rows = db.execute(q).scalars().all()
    return [{"id": a.id, "task_id": a.task_id, "action_desc": a.action_desc,
             "risk_level": a.risk_level, "created_at": a.created_at} for a in rows]


@router.post("/approvals/{approval_id}/{decision}")
def decide(approval_id: str, decision: str,
           user: User = Depends(current_user), db: Session = Depends(get_db)):
    if decision not in ("approve", "reject"):
        raise HTTPException(400, "decision must be approve/reject")
    a = db.execute(select(Approval).where(Approval.id == approval_id)).scalar_one_or_none()
    if not a or a.status != "pending":
        raise HTTPException(404, "Approval item not found or already handled")
    task = db.execute(select(Task).where(Task.id == a.task_id)).scalar_one_or_none()
    if user.role != "admin" and (task is None or task.owner_id != user.id):
        raise HTTPException(403, "Cannot decide on another user's approval")
    a.status = "approved" if decision == "approve" else "rejected"
    a.decided_by = user.id
    if task and task.status == "WAITING_APPROVAL":
        task.status = "QUEUED"  # seamlessly resume from the checkpoint (the reject case is handled by require_approval raising TaskFailed)
    return {"ok": True, "status": a.status}


# ---------- Audit ----------
@router.get("/audit")
def audit(task_id: str = "", limit: int = 100,
          user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(AuditLog).order_by(AuditLog.ts.desc()).limit(limit)
    if task_id:
        # Specific task: a non-admin must own the task, otherwise its audit is not returned (prompt/output digests are sensitive)
        if user.role != "admin":
            owned = db.execute(select(Task.id).where(
                Task.id == task_id, Task.owner_id == user.id)).first()
            if owned is None:
                raise HTTPException(403, "Not allowed to view this task's audit log")
        q = q.where(AuditLog.task_id == task_id)
    elif user.role != "admin":
        # No task specified: a non-admin can only see audit records from their own tasks (system-level task_id="" records are admin-only)
        q = q.where(AuditLog.task_id.in_(select(Task.id).where(Task.owner_id == user.id)))
    return [{"id": r.id, "task_id": r.task_id, "step": r.step, "model": r.model,
             "tokens_in": r.tokens_in, "tokens_out": r.tokens_out,
             "cost_usd": round(r.cost_usd, 6), "cached": bool(r.cached),
             "simulated": bool(r.simulated), "ts": r.ts,
             "input_digest": r.input_digest, "output_digest": r.output_digest}
            for r in db.execute(q).scalars()]


# ---------- Settings ----------
@router.get("/settings")
def read_settings(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return all_settings(db, mask_secrets=True)


class SettingsIn(BaseModel):
    values: dict


@router.put("/settings")
def write_settings(body: SettingsIn, user: User = Depends(require_admin),
                   db: Session = Depends(get_db)):
    unknown = [k for k in body.values if k not in DEFAULTS]
    if unknown:
        raise HTTPException(400, f"Unknown settings: {unknown}")
    for k, v in body.values.items():
        if k in SECRET_KEYS and not str(v).strip():
            continue  # an empty secret field = leave the existing value unchanged
        set_setting(db, k, v)
    return {"ok": True}


@router.get("/telegram/bot")
def telegram_bot_info(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Bot configuration status and username needed for the QR code on the /connect page."""
    from ..connectors.telegram_bot import bot_info
    return bot_info(db)


@router.post("/settings/test-notify")
def test_notify(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    results = notify_all(db, "JarvisQwen test push", "If you can read this, push notifications are configured correctly ✅")
    if not results:
        raise HTTPException(400, "No push channel enabled")
    return {"results": results}


# ---------- Export ----------
@router.get("/briefings/{briefing_id}/export")
def export_briefing(briefing_id: str, fmt: str = "md",
                    user: User = Depends(current_user), db: Session = Depends(get_db)):
    b = db.execute(select(Briefing).where(Briefing.id == briefing_id)).scalar_one_or_none()
    if not b:
        raise HTTPException(404, "Briefing not found")
    if fmt == "md":
        return Response(b.content_md, media_type="text/markdown",
                        headers={"Content-Disposition": f'attachment; filename="briefing_{b.date}.md"'})
    if fmt == "pdf":
        try:
            pdf = markdown_to_pdf_bytes(f"JarvisQwen briefing {b.date}", b.content_md)
        except ImportError:
            raise HTTPException(501, "PDF export dependency missing on server (pip install reportlab)")
        return Response(pdf, media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="briefing_{b.date}.pdf"'})
    raise HTTPException(400, "fmt must be md or pdf")


@router.get("/library/export")
def export_library(fmt: str = "bibtex", user: User = Depends(current_user), db: Session = Depends(get_db)):
    stmt = select(Paper).order_by(Paper.created_at.desc())
    if user.role != "admin":
        stmt = stmt.where(Paper.owner_id == user.id)
    papers = db.execute(stmt).scalars().all()
    if fmt == "bibtex":
        text = to_bibtex([{"arxiv_id": p.arxiv_id, "title": p.title, "authors": p.authors,
                           "published_at": p.published_at, "url": p.url} for p in papers])
        return Response(text, media_type="application/x-bibtex",
                        headers={"Content-Disposition": 'attachment; filename="aaos_library.bib"'})
    raise HTTPException(400, "Only fmt=bibtex is supported for now")


# ---------- Zotero sync ----------
@router.post("/library/{paper_id}/zotero-sync")
def zotero_sync_one(paper_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.execute(select(Paper).where(Paper.id == paper_id)).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Paper not found")
    item = paper_to_zotero_item(p.title, p.authors, p.abstract, p.url, p.published_at, p.arxiv_id)
    ok, msg = push_papers(db, [item])
    if not ok:
        raise HTTPException(400, msg)
    return {"ok": True, "message": msg}


# ---------- Cross-library QA (library_qa, a lightweight implementation of the paper-qa idea) ----------
class QaIn(BaseModel):
    question: str


@router.post("/library/qa")
def library_qa(body: QaIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not body.question.strip():
        raise HTTPException(400, "Question cannot be empty")
    stmt = select(Paper).order_by(Paper.created_at.desc()).limit(200)
    if user.role != "admin":
        stmt = stmt.where(Paper.owner_id == user.id)  # AFR: filter first, then retrieve
    papers = db.execute(stmt).scalars().all()
    if not papers:
        return {"answer": "The library is empty — no papers to search yet.", "cited": [], "escalated": False}

    terms = [t for t in body.question.lower().split() if len(t) > 1]
    scored = []
    for p in papers:
        s = db.execute(select(Summary).where(Summary.paper_id == p.id)
                       .order_by(Summary.created_at.desc())).scalars().first()
        haystack = f"{p.title} {p.abstract} {s.content_md if s else ''}".lower()
        score = sum(1 for t in terms if t in haystack)
        if score > 0:
            scored.append((score, p, s))
    scored.sort(key=lambda x: -x[0])
    top = scored[:6]
    if not top:
        return {"answer": "No relevant papers found in the library. Try different keywords, or run a topic watch first.",
                "cited": [], "escalated": False}

    evidence = "\n\n".join(
        f"[{i+1}] \"{p.title}\": {(s.content_md if s else p.abstract)[:600]}"
        for i, (_, p, s) in enumerate(top)
    )
    prompt = (
        f"Answer the question using ONLY the paper evidence from my library below. "
        f"Cite sources as [number]; do not invent anything not present in the evidence.\n\n"
        f"Question: {body.question}\n\nEvidence:\n{evidence}"
    )
    result, escalated = cascade.complete_cascade(db, prompt, step="library_qa", max_tokens=1200)
    return {"answer": result.text, "escalated": escalated,
            "cited": [{"id": p.id, "title": p.title, "url": p.url} for _, p, _ in top]}


# ---------- Cost analysis ----------
@router.get("/dashboard/costs")
def dashboard_costs(days: int = 7, user: User = Depends(current_user), db: Session = Depends(get_db)):
    days = max(1, min(days, 30))
    since = time.time() - days * 86400
    rows = db.execute(select(AuditLog).where(AuditLog.ts >= since)).scalars().all()
    daily: dict[str, float] = {}
    by_model: dict[str, float] = {}
    for r in rows:
        day = time.strftime("%m-%d", time.localtime(r.ts))
        daily[day] = daily.get(day, 0) + r.cost_usd
        model_key = r.model.split("::")[-1] if r.model else "(other)"
        by_model[model_key] = by_model.get(model_key, 0) + r.cost_usd
    # Fill in days with no spend so the chart stays continuous
    ordered_days = []
    for i in range(days - 1, -1, -1):
        day = time.strftime("%m-%d", time.localtime(time.time() - i * 86400))
        ordered_days.append({"date": day, "cost_usd": round(daily.get(day, 0), 4)})
    model_breakdown = sorted(
        [{"model": k, "cost_usd": round(v, 4)} for k, v in by_model.items()],
        key=lambda x: -x["cost_usd"],
    )
    return {"daily": ordered_days, "by_model": model_breakdown}


# ---------- Dashboard ----------
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
