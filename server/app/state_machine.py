from fastapi import HTTPException, status

from app.enums import BatchStatus

ALLOWED_TRANSITIONS: dict[BatchStatus, set[BatchStatus]] = {
    BatchStatus.DRAFT: {BatchStatus.VALIDATING},
    BatchStatus.VALIDATING: {BatchStatus.PENDING_REVIEW, BatchStatus.VALIDATION_FAILED, BatchStatus.TASK_FAILED},
    BatchStatus.PENDING_REVIEW: {BatchStatus.PENDING_APPROVAL, BatchStatus.TASK_FAILED},
    BatchStatus.PENDING_APPROVAL: {BatchStatus.APPROVED, BatchStatus.REJECTED},
    BatchStatus.REJECTED: {BatchStatus.PENDING_REVIEW},
    BatchStatus.APPROVED: {BatchStatus.EXPORTED, BatchStatus.TASK_FAILED},
    BatchStatus.TASK_FAILED: {BatchStatus.VALIDATING, BatchStatus.APPROVED},
    BatchStatus.VALIDATION_FAILED: {BatchStatus.VALIDATING},
    BatchStatus.EXPORTED: set(),
}


def transition(current: BatchStatus, target: BatchStatus) -> BatchStatus:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"不允许从 {current.value} 转换为 {target.value}",
        )
    return target
