"""Telegram 遥控：轮询 getUpdates，把授权 chat 发来的消息转成任务并回执。

- polling 而非 webhook：本地/内网部署零公网配置可用。
- 安全：只处理 settings.telegram_chat_id 配置的那一个 chat 的消息；
  其他人即使找到 bot 也无法指挥你的系统。
- 失败静默：遥控不是关键路径，网络抖动不产生副作用（offset 未推进会自然重试）。
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
    """给 /connect 页的二维码用：返回 bot 用户名与配置状态。"""
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
    """调度器定时调用：拉取新消息 → 建任务 → 回执。

    分四段执行，所有网络调用都在 DB 会话之外——会话内做网络会让
    autoflush 拿到的 SQLite 写锁横跨 15s 的 HTTP 请求，堵死全站写操作。
    """
    # ① 短会话读配置
    with session() as db:
        token = str(get_setting(db, "telegram_bot_token") or "")
        chat_id = str(get_setting(db, "telegram_chat_id") or "")
        offset = int(get_setting(db, "telegram_update_offset") or 0)
    if not token or not chat_id:
        return

    # ② 网络拉取（无会话）
    try:
        resp = httpx.get(f"https://api.telegram.org/bot{token}/getUpdates",
                         params={"offset": offset + 1, "timeout": 0}, timeout=15)
        updates = resp.json().get("result", [])
    except Exception:  # noqa: BLE001
        return
    if not updates:
        return

    # ③ 短会话建任务 + 推进游标（回执先攒着）
    from ..api.tasks import _parse_prompt  # 局部导入避免环形依赖

    replies: list[str] = []
    with session() as db:
        for u in updates:
            offset = max(offset, int(u.get("update_id", 0)))
            msg = u.get("message") or {}
            text = (msg.get("text") or "").strip()
            from_chat = str((msg.get("chat") or {}).get("id", ""))
            if not text or from_chat != chat_id:
                continue  # 非授权 chat 一律忽略
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

    # ④ 会话已提交关闭，再发回执（任务已持久化，回执语义也更准确）
    for text in replies:
        _reply(token, chat_id, text)
