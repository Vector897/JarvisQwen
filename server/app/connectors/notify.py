"""外部推送：Telegram / 邮件（SMTP）。简报生成完成、预算熔断时触发。

失败静默降级（推送不是关键路径，不应让任务失败）。

会话纪律：本模块自管短会话——先短会话读配置并关闭，再做网络发送。
调用方不需要（也不应该）把自己的会话传进来。
"""
from __future__ import annotations

import smtplib
from email.mime.text import MIMEText

import httpx

from ..core.settings_store import get_setting
from ..db import session


def push_telegram(text: str) -> tuple[bool, str]:
    with session() as db:  # ① 短会话读配置
        token = str(get_setting(db, "telegram_bot_token") or "")
        chat_id = str(get_setting(db, "telegram_chat_id") or "")
    if not token or not chat_id:
        return False, "Telegram bot token / chat ID not configured"
    try:  # ② 网络发送（无会话）
        resp = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text[:4000], "parse_mode": "Markdown"},
            timeout=15,
        )
        if resp.status_code == 200:
            return True, "Pushed to Telegram"
        return False, f"Telegram push failed: {resp.text[:200]}"
    except Exception as e:  # noqa: BLE001
        return False, f"Telegram push error: {e}"


def push_email(subject: str, body: str) -> tuple[bool, str]:
    with session() as db:  # ① 短会话读配置
        host = str(get_setting(db, "smtp_host") or "")
        to_addr = str(get_setting(db, "smtp_to") or "")
        port = int(get_setting(db, "smtp_port") or 587)
        user = str(get_setting(db, "smtp_user") or "")
        password = str(get_setting(db, "smtp_password") or "")
        from_addr = str(get_setting(db, "smtp_from") or user)
    if not host or not to_addr:
        return False, "SMTP server / recipient not configured"
    try:  # ② 网络发送（无会话）
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_addr
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.starttls()
            if user:
                server.login(user, password)
            server.sendmail(from_addr, [to_addr], msg.as_string())
        return True, "Email sent"
    except Exception as e:  # noqa: BLE001
        return False, f"Email send error: {e}"


def notify_all(subject: str, text: str) -> list[str]:
    """按已启用的渠道推送，返回结果消息列表（供审计/调试）。"""
    with session() as db:
        tg_enabled = bool(get_setting(db, "notify_telegram_enabled"))
        email_enabled = bool(get_setting(db, "notify_email_enabled"))
    results = []
    if tg_enabled:
        ok, msg = push_telegram(f"*{subject}*\n\n{text}")
        results.append(msg)
    if email_enabled:
        ok, msg = push_email(subject, text)
        results.append(msg)
    return results
