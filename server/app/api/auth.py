from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import LoginIn, UserOut
from app.security import create_access_token, new_csrf_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserOut)
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)) -> User:
    user = db.scalar(select(User).where(User.username == payload.username))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    settings = get_settings()
    secure = settings.environment == "production"
    response.set_cookie(
        "access_token",
        create_access_token(user.id),
        httponly=True,
        secure=secure,
        samesite="strict",
        max_age=settings.access_token_minutes * 60,
    )
    csrf_token = new_csrf_token()
    response.set_cookie("csrf_token", csrf_token, httponly=False, secure=secure, samesite="strict")
    record_event(db, action="auth.login", resource_type="user", resource_id=user.id, actor=user)
    db.commit()
    return user


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    record_event(db, action="auth.logout", resource_type="user", resource_id=user.id, actor=user)
    db.commit()
    response.delete_cookie("access_token")
    response.delete_cookie("csrf_token")
