from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import BatchStatus, RoleCode
from app.models import ProcessingBatch, User
from app.security import decode_access_token


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    try:
        user_id = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期") from exc
    user = db.scalar(select(User).where(User.id == user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不可用")
    return user


def role_codes(user: User) -> set[str]:
    return {role.code for role in user.roles}


def enforce_batch_visibility(batch: ProcessingBatch, user: User) -> None:
    if RoleCode.VIEWER.value in role_codes(user) and batch.status not in {
        BatchStatus.APPROVED,
        BatchStatus.EXPORTED,
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只读角色只能查看已批准结果")


def require_roles(*allowed: RoleCode) -> Callable[..., User]:
    allowed_values = {role.value for role in allowed}

    def dependency(user: User = Depends(get_current_user)) -> User:
        if role_codes(user).isdisjoint(allowed_values):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
        return user

    return dependency
