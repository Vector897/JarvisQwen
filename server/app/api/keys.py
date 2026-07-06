"""BYOK：Key 录入（自动格式修正+厂商识别+实时探活）、列表（掩码）、删除。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..core.router import providers
from ..db import get_db
from ..models import ApiKey, User

router = APIRouter(prefix="/api/keys", tags=["keys"])


class KeyIn(BaseModel):
    raw_key: str
    provider: str = ""  # 留空则自动识别
    base_url: str = ""
    label: str = ""
    skip_probe: bool = False


@router.post("")
def add_key(body: KeyIn, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    key = providers.normalize_key(body.raw_key)
    if not key or len(key) < 10:
        raise HTTPException(400, "Key is empty or too short - check what you pasted")
    provider = body.provider or providers.detect_provider(key, body.base_url)
    if not provider:
        return {"need_provider": True, "normalized": providers.mask(key),
                "message": "Could not auto-detect the provider (Qwen / OpenAI / DeepSeek share the sk- prefix) - pick one manually and retry",
                "options": providers.PROVIDERS}
    if provider not in providers.PROVIDERS:
        raise HTTPException(400, f"Unknown provider: {provider}")

    probe_msg = "Probe skipped"
    if not body.skip_probe:
        ok, probe_msg = providers.probe(provider, key, body.base_url)
        if not ok:
            raise HTTPException(400, probe_msg)

    row = ApiKey(provider=provider, encrypted_key=providers.encrypt_key(key),
                 base_url=body.base_url, label=body.label or provider, owner_id=user.id)
    db.add(row)
    db.flush()
    return {"id": row.id, "provider": provider, "masked": providers.mask(key), "message": probe_msg}


@router.get("")
def list_keys(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.execute(select(ApiKey).order_by(ApiKey.provider, ApiKey.priority)).scalars().all()
    return [{
        "id": r.id, "provider": r.provider, "label": r.label, "base_url": r.base_url,
        "status": r.status, "masked": providers.mask(providers.decrypt_key(r.encrypted_key)),
    } for r in rows]


@router.delete("/{key_id}")
def delete_key(key_id: str, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    row = db.execute(select(ApiKey).where(ApiKey.id == key_id)).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Key not found")
    if user.role != "admin" and row.owner_id != user.id:
        raise HTTPException(403, "Cannot delete another user's key")
    db.delete(row)
    return {"ok": True}


@router.post("/{key_id}/probe")
def reprobe(key_id: str, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    row = db.execute(select(ApiKey).where(ApiKey.id == key_id)).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Key not found")
    ok, msg = providers.probe(row.provider, providers.decrypt_key(row.encrypted_key), row.base_url)
    row.status = "active" if ok else "broken"
    return {"ok": ok, "message": msg, "status": row.status}
