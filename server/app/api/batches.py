from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.database import get_db
from app.dependencies import enforce_batch_visibility, get_current_user, require_roles, role_codes
from app.enums import BatchStatus, BusinessType, RoleCode
from app.models import ProcessingBatch, User
from app.schemas import BatchOut
from app.services.batches import get_batch_or_404, submit_for_approval, validate_batch_records
from app.services.import_export import import_batch_file
from app.storage import store_upload
from app.tasks import import_and_validate_batch

router = APIRouter(prefix="/batches", tags=["batches"])


@router.get("", response_model=list[BatchOut])
def list_batches(
    business_type: BusinessType | None = None,
    batch_status: BatchStatus | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ProcessingBatch]:
    statement = select(ProcessingBatch).order_by(ProcessingBatch.created_at.desc())
    if business_type:
        statement = statement.where(ProcessingBatch.business_type == business_type)
    if batch_status:
        statement = statement.where(ProcessingBatch.status == batch_status)
    if RoleCode.VIEWER.value in role_codes(user):
        statement = statement.where(ProcessingBatch.status.in_([BatchStatus.APPROVED, BatchStatus.EXPORTED]))
    return list(db.scalars(statement))


@router.get("/{batch_id}", response_model=BatchOut)
def get_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProcessingBatch:
    batch = get_batch_or_404(db, batch_id)
    enforce_batch_visibility(batch, user)
    return batch


@router.post("/import", response_model=BatchOut, status_code=status.HTTP_202_ACCEPTED)
async def import_batch(
    name: str = Form(min_length=2, max_length=160),
    business_type: BusinessType = Form(),
    source_sheet: str | None = Form(default=None, max_length=160),
    file: UploadFile = File(),
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(RoleCode.ADMIN, RoleCode.OPERATOR)),
) -> ProcessingBatch:
    stored_file = await store_upload(file, actor)
    db.add(stored_file)
    db.flush()
    batch = ProcessingBatch(
        name=name,
        business_type=business_type,
        source_file_id=stored_file.id,
        source_sheet=source_sheet.strip() if source_sheet else None,
        created_by_id=actor.id,
    )
    db.add(batch)
    db.flush()
    record_event(
        db,
        action="batch.import_queued",
        resource_type="batch",
        resource_id=batch.id,
        actor=actor,
        details={"business_type": business_type.value, "file_id": stored_file.id},
    )
    db.commit()
    import_and_validate_batch.delay(batch.id)
    return batch


@router.post("/{batch_id}/validate", response_model=BatchOut)
def validate_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(RoleCode.ADMIN, RoleCode.OPERATOR)),
) -> ProcessingBatch:
    batch = get_batch_or_404(db, batch_id)
    if batch.status not in {BatchStatus.DRAFT, BatchStatus.VALIDATION_FAILED, BatchStatus.TASK_FAILED}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前状态不能重新校验")
    if batch.row_count == 0 and batch.source_file:
        import_batch_file(db, batch)
    validate_batch_records(db, batch)
    record_event(db, action="batch.validate", resource_type="batch", resource_id=batch.id, actor=actor)
    db.commit()
    db.refresh(batch)
    return batch


@router.post("/{batch_id}/submit", response_model=BatchOut)
def submit_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(RoleCode.ADMIN, RoleCode.OPERATOR)),
) -> ProcessingBatch:
    batch = submit_for_approval(db, get_batch_or_404(db, batch_id))
    record_event(db, action="batch.submit", resource_type="batch", resource_id=batch.id, actor=actor)
    db.commit()
    db.refresh(batch)
    return batch
