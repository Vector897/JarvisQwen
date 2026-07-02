"""语义缓存 V1：归一化精确匹配 + TTL。

升级路径（V2）：embedding + 向量相似度（Qdrant），见架构文档 3.1。
接口已按语义缓存设计（lookup/store 以完整 prompt 为键），换实现不动调用方。
"""
from __future__ import annotations

import hashlib
import re
import time

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ...models import LlmCache
from ..settings_store import get_setting


def _normalize(prompt: str) -> str:
    return re.sub(r"\s+", " ", prompt).strip().lower()


def _key(model_tier: str, prompt: str) -> str:
    return hashlib.sha256(f"{model_tier}|{_normalize(prompt)}".encode()).hexdigest()


def lookup(db: Session, tier: str, prompt: str) -> str | None:
    if not get_setting(db, "cache_enabled"):
        return None
    row = db.execute(select(LlmCache).where(LlmCache.id == _key(tier, prompt))).scalar_one_or_none()
    if row is None or row.expires_at < time.time():
        return None
    row.hit_count += 1
    return row.response


def store(db: Session, tier: str, prompt: str, response: str, model: str) -> None:
    if not get_setting(db, "cache_enabled"):
        return
    ttl = float(get_setting(db, "cache_ttl_hours")) * 3600
    key = _key(tier, prompt)
    row = db.execute(select(LlmCache).where(LlmCache.id == key)).scalar_one_or_none()
    if row is None:
        db.add(LlmCache(id=key, response=response, model=model, expires_at=time.time() + ttl))
    else:
        row.response = response
        row.model = model
        row.expires_at = time.time() + ttl


def evict_expired(db: Session) -> int:
    result = db.execute(delete(LlmCache).where(LlmCache.expires_at < time.time()))
    return result.rowcount or 0
