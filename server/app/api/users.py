from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.database import get_db
from app.dependencies import require_roles
from app.enums import RoleCode
from app.models import Role, User
from app.schemas import RoleOut, UserCreate, UserOut
from app.security import hash_password

router = APIRouter(tags=["users"])


@router.get("/roles", response_model=list[RoleOut])
def list_roles(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleCode.ADMIN)),
) -> list[Role]:
    return list(db.scalars(select(Role).order_by(Role.code)))


@router.get("/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleCode.ADMIN)),
) -> list[User]:
    return list(db.scalars(select(User).order_by(User.username)))


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(RoleCode.ADMIN)),
) -> User:
    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")
    roles = list(db.scalars(select(Role).where(Role.code.in_(payload.role_codes))))
    if len(roles) != len(set(payload.role_codes)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="包含无效角色")
    user = User(
        username=payload.username,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        roles=roles,
    )
    db.add(user)
    db.flush()
    record_event(db, action="user.create", resource_type="user", resource_id=user.id, actor=actor)
    db.commit()
    db.refresh(user)
    return user
