import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.enums import BatchStatus, BusinessType, IssueStatus
from app.models import ProcessingBatch, ReviewFee, User
from app.services.batches import get_batch_or_404, submit_for_approval, validate_batch_records


def test_validation_creates_issues_and_requires_resolution(db: Session, users: dict[str, User]):
    batch = ProcessingBatch(
        name="审稿费测试",
        business_type=BusinessType.REVIEW_FEE,
        created_by_id=users["operator"].id,
    )
    db.add(batch)
    db.flush()
    db.add(ReviewFee(batch_id=batch.id, manuscript_no="M-1", reviewer_name="张三", institution="外部机构"))
    db.flush()

    validate_batch_records(db, batch)
    assert batch.status == BatchStatus.PENDING_REVIEW
    assert batch.row_count == 1
    assert batch.issue_count == 2
    with pytest.raises(HTTPException):
        submit_for_approval(db, batch)

    for issue in batch.issues:
        issue.status = IssueStatus.RESOLVED
    submit_for_approval(db, batch)
    assert batch.status == BatchStatus.PENDING_APPROVAL


def test_missing_batch_returns_404(db: Session):
    with pytest.raises(HTTPException) as exc:
        get_batch_or_404(db, "missing")
    assert exc.value.status_code == 404
