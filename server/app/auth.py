"""Login authentication: PBKDF2 password hashing + HMAC-signed session cookie + RBAC dependencies."""
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
    """No-login fallback. In local single-machine mode (no access code) it falls back
    to admin, preserving the zero-config experience; in public demo mode (access code
    set) it falls back to a restricted demo member — passing the access-code gate only
    means "allowed to try it out", not that you hold admin rights (changing
    budget/model/keys/users requires logging in as admin)."""
    if config.access_code:
        demo = db.execute(select(User).where(User.name == "demo")).scalar_one_or_none()
        if demo is None:
            try:
                demo = User(name="demo", role="member",
                            password_hash=hash_password(secrets.token_urlsafe(24)))
                db.add(demo)
                db.flush()
            except Exception:  # noqa: BLE001  concurrent first-access hits the name unique constraint → fetch the one already created
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
    # Use a valid session if present; otherwise fall back to the default local account ("quick try" works without login).
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
    """On first startup, create admin; write the password to data/admin_password.txt and print it to the log."""
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
