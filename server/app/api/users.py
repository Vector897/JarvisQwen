"""用户管理（admin 专属）：创建成员账号、改角色、删除。"""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import hash_password, require_admin
from ..db import get_db
from ..models import User

router = APIRouter(prefix="/api/users", tags=["users"])

ROLES = ("admin", "member", "viewer")


@router.get("")
def list_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return [{"id": u.id, "name": u.name, "role": u.role, "created_at": u.created_at}
            for u in db.execute(select(User).order_by(User.created_at)).scalars()]


class UserIn(BaseModel):
    name: str
    role: str = "member"


@router.post("")
def create_user(body: UserIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if body.role not in ROLES:
        raise HTTPException(400, f"role 必须是 {ROLES}")
    if db.execute(select(User).where(User.name == body.name)).scalar_one_or_none():
        raise HTTPException(400, "用户名已存在")
    temp_password = secrets.token_urlsafe(9)
    user = User(name=body.name, role=body.role, password_hash=hash_password(temp_password))
    db.add(user)
    db.flush()
    return {"id": user.id, "name": user.name, "role": user.role,
            "temp_password": temp_password, "message": "请把临时密码告知该用户，首次登录后建议修改"}


class RoleIn(BaseModel):
    role: str


@router.put("/{user_id}/role")
def change_role(user_id: str, body: RoleIn, admin: User = Depends(require_admin),
                db: Session = Depends(get_db)):
    if body.role not in ROLES:
        raise HTTPException(400, f"role 必须是 {ROLES}")
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")
    if user.id == admin.id and body.role != "admin":
        raise HTTPException(400, "不能取消自己的管理员权限")
    user.role = body.role
    return {"ok": True}


@router.delete("/{user_id}")
def delete_user(user_id: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if user_id == admin.id:
        raise HTTPException(400, "不能删除自己")
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user:
        db.delete(user)
    return {"ok": True}
