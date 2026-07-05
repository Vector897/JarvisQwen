from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import (SESSION_COOKIE, current_user, hash_password, make_session_token,
                    verify_password)
from ..db import get_db
from ..models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str


@router.post("/login")
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.name == body.username)).scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid username or password")
    response.set_cookie(SESSION_COOKIE, make_session_token(user.id),
                        httponly=True, samesite="lax", max_age=7 * 86400)
    return {"id": user.id, "name": user.name, "role": user.role}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "name": user.name, "role": user.role}


@router.post("/change-password")
def change_password(body: ChangePasswordIn, user: User = Depends(current_user),
                    db: Session = Depends(get_db)):
    row = db.execute(select(User).where(User.id == user.id)).scalar_one()
    if not verify_password(body.old_password, row.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(400, "New password must be at least 8 characters")
    row.password_hash = hash_password(body.new_password)
    return {"ok": True}
