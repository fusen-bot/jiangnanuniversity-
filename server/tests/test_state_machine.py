import pytest
from fastapi import HTTPException

from app.enums import BatchStatus
from app.state_machine import transition


def test_happy_path_requires_every_workflow_stage():
    status = BatchStatus.DRAFT
    for target in (
        BatchStatus.VALIDATING,
        BatchStatus.PENDING_REVIEW,
        BatchStatus.PENDING_APPROVAL,
        BatchStatus.APPROVED,
        BatchStatus.EXPORTED,
    ):
        status = transition(status, target)
    assert status == BatchStatus.EXPORTED


def test_cannot_skip_review_and_approval():
    with pytest.raises(HTTPException) as exc:
        transition(BatchStatus.DRAFT, BatchStatus.APPROVED)
    assert exc.value.status_code == 409
