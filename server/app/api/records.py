from typing import Any, TypeVar

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.database import get_db
from app.dependencies import enforce_batch_visibility, get_current_user, require_roles, role_codes
from app.enums import BatchStatus, BusinessType, RoleCode
from app.models import PageFee, ProcessingBatch, ReviewFee, Royalty, User
from app.schemas import (
    PageFeeIn,
    PageFeeOut,
    PageFeeUpdate,
    ReviewFeeIn,
    ReviewFeeOut,
    ReviewFeeUpdate,
    RoyaltyIn,
    RoyaltyOut,
    RoyaltyUpdate,
)
from app.security import mask_email, mask_identifier
from app.services.batches import get_batch_or_404

router = APIRouter(tags=["financial-records"])
ModelT = TypeVar("ModelT", ReviewFee, PageFee, Royalty)


def _editable_batch(db: Session, batch_id: str, expected: BusinessType) -> ProcessingBatch:
    batch = get_batch_or_404(db, batch_id)
    if batch.business_type != expected:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="业务类型不匹配")
    if batch.status not in {BatchStatus.DRAFT, BatchStatus.PENDING_REVIEW, BatchStatus.REJECTED}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前状态不允许修改记录")
    return batch


def _create_record(
    db: Session,
    actor: User,
    batch_id: str,
    expected: BusinessType,
    model: type[ModelT],
    payload: BaseModel,
) -> ModelT:
    batch = _editable_batch(db, batch_id, expected)
    record = model(batch_id=batch.id, **payload.model_dump())
    db.add(record)
    db.flush()
    batch.row_count += 1
    batch.version += 1
    record_event(db, action="record.create", resource_type=expected.value, resource_id=record.id, actor=actor)
    db.commit()
    db.refresh(record)
    return record


def _update_record(
    db: Session,
    actor: User,
    record_id: str,
    expected: BusinessType,
    model: type[ModelT],
    payload: BaseModel,
) -> ModelT:
    record = db.get(model, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    batch = _editable_batch(db, record.batch_id, expected)
    values = payload.model_dump()
    expected_revision = values.pop("revision")
    if record.revision != expected_revision:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="记录已被他人修改，请刷新后重试")
    for key, value in values.items():
        setattr(record, key, value)
    record.revision += 1
    batch.version += 1
    record_event(db, action="record.update", resource_type=expected.value, resource_id=record.id, actor=actor)
    db.commit()
    db.refresh(record)
    return record


@router.get("/review-fees", response_model=list[ReviewFeeOut])
def review_fees(batch_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[Any]:
    enforce_batch_visibility(get_batch_or_404(db, batch_id), user)
    rows = list(db.scalars(select(ReviewFee).where(ReviewFee.batch_id == batch_id)))
    if RoleCode.VIEWER.value in role_codes(user):
        return [
            ReviewFeeOut.model_validate(row).model_copy(
                update={
                    "id_card": mask_identifier(row.id_card),
                    "email": mask_email(row.email),
                    "phone": mask_identifier(row.phone),
                    "bank_account": mask_identifier(row.bank_account),
                    "clearing_no": mask_identifier(row.clearing_no),
                }
            )
            for row in rows
        ]
    return rows


@router.post("/review-fees", response_model=ReviewFeeOut, status_code=status.HTTP_201_CREATED)
def create_review_fee(
    batch_id: str,
    payload: ReviewFeeIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(RoleCode.ADMIN, RoleCode.OPERATOR)),
) -> ReviewFee:
    return _create_record(db, actor, batch_id, BusinessType.REVIEW_FEE, ReviewFee, payload)


@router.patch("/review-fees/{record_id}", response_model=ReviewFeeOut)
def update_review_fee(
    record_id: str,
    payload: ReviewFeeUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(RoleCode.ADMIN, RoleCode.OPERATOR)),
) -> ReviewFee:
    return _update_record(db, actor, record_id, BusinessType.REVIEW_FEE, ReviewFee, payload)


@router.get("/page-fees", response_model=list[PageFeeOut])
def page_fees(batch_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[Any]:
    enforce_batch_visibility(get_batch_or_404(db, batch_id), user)
    rows = list(db.scalars(select(PageFee).where(PageFee.batch_id == batch_id)))
    if RoleCode.VIEWER.value in role_codes(user):
        return [
            PageFeeOut.model_validate(row).model_copy(
                update={"email": mask_email(row.email), "tax_no": mask_identifier(row.tax_no)}
            )
            for row in rows
        ]
    return rows


@router.post("/page-fees", response_model=PageFeeOut, status_code=status.HTTP_201_CREATED)
def create_page_fee(
    batch_id: str,
    payload: PageFeeIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(RoleCode.ADMIN, RoleCode.OPERATOR)),
) -> PageFee:
    return _create_record(db, actor, batch_id, BusinessType.PAGE_FEE, PageFee, payload)


@router.patch("/page-fees/{record_id}", response_model=PageFeeOut)
def update_page_fee(
    record_id: str,
    payload: PageFeeUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(RoleCode.ADMIN, RoleCode.OPERATOR)),
) -> PageFee:
    return _update_record(db, actor, record_id, BusinessType.PAGE_FEE, PageFee, payload)


@router.get("/royalties", response_model=list[RoyaltyOut])
def royalties(batch_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[Any]:
    enforce_batch_visibility(get_batch_or_404(db, batch_id), user)
    rows = list(db.scalars(select(Royalty).where(Royalty.batch_id == batch_id)))
    if RoleCode.VIEWER.value in role_codes(user):
        return [
            RoyaltyOut.model_validate(row).model_copy(
                update={
                    "email": mask_email(row.email),
                    "phone": mask_identifier(row.phone),
                    "id_card": mask_identifier(row.id_card),
                    "bank_account": mask_identifier(row.bank_account),
                    "clearing_no": mask_identifier(row.clearing_no),
                }
            )
            for row in rows
        ]
    return rows


@router.post("/royalties", response_model=RoyaltyOut, status_code=status.HTTP_201_CREATED)
def create_royalty(
    batch_id: str,
    payload: RoyaltyIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(RoleCode.ADMIN, RoleCode.OPERATOR)),
) -> Royalty:
    return _create_record(db, actor, batch_id, BusinessType.ROYALTY, Royalty, payload)


@router.patch("/royalties/{record_id}", response_model=RoyaltyOut)
def update_royalty(
    record_id: str,
    payload: RoyaltyUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(RoleCode.ADMIN, RoleCode.OPERATOR)),
) -> Royalty:
    return _update_record(db, actor, record_id, BusinessType.ROYALTY, Royalty, payload)
