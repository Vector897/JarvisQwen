"""Telegram remote control: poll getUpdates, turn messages from the authorized chat into tasks and acknowledge them.

- Polling rather than webhook: works with zero public-network configuration for local/intranet deployment.
- Security: only processes messages from the single chat configured in settings.telegram_chat_id;
  others cannot command your system even if they find the bot.
- Silent failure: remote control is not on the critical path, and network jitter produces no side effects (an un-advanced offset naturally retries).
"""
from __future__ import annotations

import json

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.settings_store import get_setting, set_setting
from ..db import session
from ..models import Task, User

HELP_TEXT = (
    "🤖 *JarvisQwen at your service.*\n\n"
    "Just text me what you want, in plain language:\n"
    "· `Track new papers on LLM agent security`\n"
    "· `Research the latest progress on volatility forecasting`\n"
    "· `Generate today's briefing`\n\n"
    "I'll queue it, run the full pipeline, and your briefing/summaries "
    "will be waiting in the console."
)


def bot_info(db: Session) -> dict:
    """For the QR code on the /connect page: returns the bot username and configuration status."""
    token = str(get_setting(db, "telegram_bot_token") or "")
    chat_id = str(get_setting(db, "telegram_chat_id") or "")
    enabled = bool(get_setting(db, "notify_telegram_enabled"))
    if not token:
        return {"configured": False, "enabled": enabled, "chat_configured": bool(chat_id)}
    try:
        r = httpx.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10).json()
        username = (r.get("result") or {}).get("username", "")
    except Exception:  # noqa: BLE001
        username = ""
    return {"configured": bool(username), "enabled": enabled,
            "chat_configured": bool(chat_id), "username": username}


def _reply(token: str, chat_id: str, text: str) -> None:
    try:
        httpx.post(f"https://api.telegram.org/bot{token}/sendMessage",
                   json={"chat_id": chat_id, "text": text[:4000], "parse_mode": "Markdown"},
                   timeout=15)
    except Exception:  # noqa: BLE001
        pass


def poll_commands() -> None:
    """Called periodically by the scheduler: fetch new messages → create tasks → acknowledge.

    Executed in four stages, with all network calls kept outside the DB session — doing
    network work inside a session would let the SQLite write lock held by autoflush span
    a 15s HTTP request, blocking writes across the entire application.
    """
    # ① Short session to read configuration
    with session() as db:
        token = str(get_setting(db, "telegram_bot_token") or "")
        chat_id = str(get_setting(db, "telegram_chat_id") or "")
        offset = int(get_setting(db, "telegram_update_offset") or 0)
    if not token or not chat_id:
        return

    # ② Network fetch (no session)
    try:
        resp = httpx.get(f"https://api.telegram.org/bot{token}/getUpdates",
                         params={"offset": offset + 1, "timeout": 0}, timeout=15)
        updates = resp.json().get("result", [])
    except Exception:  # noqa: BLE001
        return
    if not updates:
        return

    # ③ Short session to create tasks + advance the cursor (acknowledgements batched for later)
    from ..api.tasks import _parse_prompt  # local import to avoid a circular dependency

    replies: list[str] = []
    with session() as db:
        for u in updates:
            offset = max(offset, int(u.get("update_id", 0)))
            msg = u.get("message") or {}
            text = (msg.get("text") or "").strip()
            from_chat = str((msg.get("chat") or {}).get("id", ""))
            if not text or from_chat != chat_id:
                continue  # ignore all unauthorized chats
            if text.startswith(("/start", "/help")):
                replies.append(HELP_TEXT)
                continue
            admin = db.execute(select(User).where(User.role == "admin")).scalars().first()
            if admin is None:
                continue
            ttype, params, title = _parse_prompt(text)
            db.add(Task(type=ttype, title=title,
                        params_json=json.dumps(params, ensure_ascii=False),
                        owner_id=admin.id, priority=4))
            replies.append(f"✅ Task queued: *{title}*\nI'm on it — results will be in your console and next briefing.")
        set_setting(db, "telegram_update_offset", offset)

    # ④ Session already committed and closed, then send acknowledgements (tasks are persisted, so the ack semantics are also more accurate)
    for text in replies:
        _reply(token, chat_id, text)
