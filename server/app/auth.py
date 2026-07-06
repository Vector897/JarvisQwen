"""登录鉴权：PBKDF2 口令哈希 + HMAC 签名会话 cookie + RBAC 依赖项。"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import config
from .db import get_db
from .models import User

SESSION_COOKIE = "aaos_session"
SESSION_TTL = 7 * 86400


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt), stored)


def _sign(payload: bytes) -> str:
    sig = hmac.new(config.secret_key.encode(), payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload).decode() + "." + base64.urlsafe_b64encode(sig).decode()


def make_session_token(user_id: str) -> str:
    payload = json.dumps({"uid": user_id, "exp": time.time() + SESSION_TTL}).encode()
    return _sign(payload)


def parse_session_token(token: str) -> str | None:
    try:
        payload_b64, sig_b64 = token.split(".", 1)
        payload = base64.urlsafe_b64decode(payload_b64)
        expect = hmac.new(config.secret_key.encode(), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(expect, base64.urlsafe_b64decode(sig_b64)):
            return None
        data = json.loads(payload)
        if data["exp"] < time.time():
            return None
        return data["uid"]
    except Exception:
        return None


def _default_user(db: Session) -> User | None:
    """免登录回退。本地单机模式（无访问码）回退到 admin，保持零配置体验；
    公网演示模式（设置了访问码）回退到受限的 demo member——过访问码闸门
    只代表"可以体验"，不代表拥有管理权限（改预算/模型/Key/用户须登录 admin）。"""
    if config.access_code:
        demo = db.execute(select(User).where(User.name == "demo")).scalar_one_or_none()
        if demo is None:
            try:
                demo = User(name="demo", role="member",
                            password_hash=hash_password(secrets.token_urlsafe(24)))
                db.add(demo)
                db.flush()
            except Exception:  # noqa: BLE001  并发首访撞 name 唯一约束 → 取已建的
                db.rollback()
                demo = db.execute(select(User).where(User.name == "demo")).scalar_one_or_none()
        return demo
    user = db.execute(select(User).where(User.name == "admin")).scalar_one_or_none()
    if user:
        return user
    return db.execute(select(User)).scalars().first()


def current_user(
    db: Session = Depends(get_db),
    aaos_session: str | None = Cookie(default=None),
) -> User:
    # 有有效会话则用之；否则退回默认本地账户（"快速尝试"免登录直接可用）。
    if aaos_session:
        uid = parse_session_token(aaos_session)
        if uid:
            user = db.execute(select(User).where(User.id == uid)).scalar_one_or_none()
            if user:
                return user
    user = _default_user(db)
    if not user:
        raise HTTPException(401, "No local user provisioned")
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Admin privileges required")
    return user


def ensure_admin_user() -> None:
    """首次启动创建 admin，密码写入 data/admin_password.txt 并打印到日志。"""
    from .db import session

    with session() as db:
        existing = db.execute(select(User).where(User.name == "admin")).scalar_one_or_none()
        if existing:
            return
        password = secrets.token_urlsafe(12)
        db.add(User(name="admin", role="admin", password_hash=hash_password(password)))
        pw_file = config.data_dir / "admin_password.txt"
        pw_file.write_text(password)
        print(f"[JarvisQwen] Admin account created; initial password in {pw_file} (change it after signing in)")
