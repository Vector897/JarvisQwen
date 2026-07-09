"""Read/write for business-level configuration (settings table); changes from the web UI take effect immediately (hot reload)."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import config
from ..models import Setting

DEFAULTS: dict[str, Any] = {
    "daily_budget_usd": config.daily_budget_usd,
    "redact_level": "medium",  # low/medium/high; high = validation mode, blocks outright
    "cache_enabled": True,
    "cache_ttl_hours": 72,
    "briefing_hour": 7,  # hour of day to generate the briefing
    "consolidate_hour": 3,  # memory consolidation time
    # Model selection for three-tier routing — defaults to the full Qwen lineup: rules tier $0 → flash first-pass screening → max deep summarization
    "model_light": "qwen/qwen3.6-flash",
    "model_light_fallbacks": ["qwen/qwen3.7-plus"],
    "model_frontier": "qwen/qwen3.7-max",
    "model_frontier_fallbacks": ["qwen/qwen3.7-plus"],
    "max_retries": 3,
    "relevance_threshold": 0.5,  # relevance threshold for first-pass paper screening
    "research_profile": "",  # description of the user's research direction, used as context for screening and summarization
    "cascade_enabled": True,
    "cascade_confidence_threshold": 0.6,
    # Push notifications
    "notify_telegram_enabled": False,
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "telegram_update_offset": 0,  # getUpdates cursor for remote-control polling
    "notify_email_enabled": False,
    "smtp_host": "",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_password": "",
    "smtp_from": "",
    "smtp_to": "",
    "notify_on_budget_cutoff": True,
    # Zotero sync
    "zotero_api_key": "",
    "zotero_library_id": "",
    "zotero_library_type": "user",
    # UI
    "ui_theme": "light",  # light/dark (also stored in localStorage; this copy provides cross-device persistence)
    "ui_lang": "en",  # en/zh
}

SECRET_KEYS = {  # these keys are masked in GET /api/settings to avoid leaking plaintext to the frontend
    "telegram_bot_token", "smtp_password", "zotero_api_key",
}


def get_setting(db: Session, key: str) -> Any:
    row = db.execute(select(Setting).where(Setting.key == key)).scalar_one_or_none()
    if row is None:
        return DEFAULTS.get(key)
    return json.loads(row.value_json)


def set_setting(db: Session, key: str, value: Any) -> None:
    row = db.execute(select(Setting).where(Setting.key == key)).scalar_one_or_none()
    if row is None:
        db.add(Setting(key=key, value_json=json.dumps(value, ensure_ascii=False)))
    else:
        row.value_json = json.dumps(value, ensure_ascii=False)


def all_settings(db: Session, mask_secrets: bool = False) -> dict[str, Any]:
    merged = dict(DEFAULTS)
    for row in db.execute(select(Setting)).scalars():
        try:
            merged[row.key] = json.loads(row.value_json)
        except json.JSONDecodeError:
            pass
    if mask_secrets:
        # Secret fields are not echoed in plaintext: cleared + accompanied by a "<key>_is_set" boolean flag.
        # Frontend: submitting a field left empty = leave the existing secret unchanged (PUT skips empty secret fields).
        for key in SECRET_KEYS:
            merged[f"{key}_is_set"] = bool(merged.get(key))
            merged[key] = ""
    return merged
