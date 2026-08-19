from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.enums import BatchStatus, BusinessType, IssueStatus
from app.models import PageFee, ProcessingBatch, ReviewFee, Royalty, ValidationIssue
from app.services.rules import (
    calculate_review_fee,
    calculate_royalty,
    is_internal,
    validate_page_fee,
    validate_review_fee,
    validate_royalty,
)
from app.state_machine import transition

RECORD_MODELS = {
    BusinessType.REVIEW_FEE: ReviewFee,
    BusinessType.PAGE_FEE: PageFee,
    BusinessType.ROYALTY: Royalty,
}


def get_batch_or_404(db: Session, batch_id: str) -> ProcessingBatch:
    batch = db.get(ProcessingBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批次不存在")
    return batch


def validate_batch_records(db: Session, batch: ProcessingBatch) -> ProcessingBatch:
    batch.status = transition(batch.status, BatchStatus.VALIDATING)
    db.flush()
    db.execute(delete(ValidationIssue).where(ValidationIssue.batch_id == batch.id))

    if batch.business_type == BusinessType.REVIEW_FEE:
        records: list[ReviewFee | PageFee | Royalty] = list(
            db.scalars(select(ReviewFee).where(ReviewFee.batch_id == batch.id))
        )
    elif batch.business_type == BusinessType.PAGE_FEE:
        records = list(db.scalars(select(PageFee).where(PageFee.batch_id == batch.id)))
    else:
        records = list(db.scalars(select(Royalty).where(Royalty.batch_id == batch.id)))

    for record in records:
        if isinstance(record, ReviewFee):
            record.is_internal = is_internal(record.institution)
            record.amount = calculate_review_fee(record)
        elif isinstance(record, Royalty):
            record.is_internal = is_internal(record.institution)
            record.amount = calculate_royalty(record)
        if isinstance(record, ReviewFee):
            record_issues = validate_review_fee(record)
        elif isinstance(record, PageFee):
            record_issues = validate_page_fee(record)
        else:
            record_issues = validate_royalty(record)
        for code, severity, message in record_issues:
            db.add(
                ValidationIssue(
                    batch_id=batch.id,
                    record_type=batch.business_type.value,
                    record_id=record.id,
                    code=code,
                    severity=severity,
                    message=message,
                )
            )

    batch.row_count = len(records)
    db.flush()
    batch.issue_count = (
        db.scalar(select(func.count()).select_from(ValidationIssue).where(ValidationIssue.batch_id == batch.id)) or 0
    )
    batch.status = transition(batch.status, BatchStatus.PENDING_REVIEW)
    batch.version += 1
    return batch


def submit_for_approval(db: Session, batch: ProcessingBatch) -> ProcessingBatch:
    open_issues = db.scalar(
        select(func.count())
        .select_from(ValidationIssue)
        .where(ValidationIssue.batch_id == batch.id, ValidationIssue.status == IssueStatus.OPEN)
    )
    if open_issues:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="仍有未处理异常，不能提交审批")
    batch.status = transition(batch.status, BatchStatus.PENDING_APPROVAL)
    batch.version += 1
    return batch
