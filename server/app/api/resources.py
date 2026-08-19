from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.database import get_db
from app.dependencies import get_current_user, require_roles, role_codes
from app.enums import BatchStatus, RoleCode
from app.models import AuditEvent, PageFee, ProcessingBatch, ReviewFee, Royalty, StoredFile, User
from app.schemas import AuditOut, FileOut, SearchResult
from app.storage import resolve_stored_file, safe_download_name

router = APIRouter(tags=["resources"])


@router.get("/files", response_model=list[FileOut])
def list_files(
    category: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[StoredFile]:
    statement = select(StoredFile).order_by(StoredFile.created_at.desc())
    if category:
        statement = statement.where(StoredFile.category == category)
    if RoleCode.VIEWER.value in role_codes(user):
        statement = statement.where(StoredFile.category == "export")
    return list(db.scalars(statement))


@router.get("/files/{file_id}/download")
def download_file(
    file_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> FileResponse:
    stored_file = db.get(StoredFile, file_id)
    if not stored_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    if RoleCode.VIEWER.value in role_codes(actor) and stored_file.category != "export":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只读角色不能下载源文件")
    path = resolve_stored_file(stored_file)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件内容不存在")
    record_event(db, action="file.download", resource_type="file", resource_id=file_id, actor=actor)
    db.commit()
    return FileResponse(path, media_type=stored_file.media_type, filename=safe_download_name(stored_file.original_name))


@router.get("/audit-events", response_model=list[AuditOut])
def list_audit_events(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleCode.ADMIN, RoleCode.APPROVER)),
) -> list[AuditEvent]:
    return list(db.scalars(select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(limit)))


@router.get("/search", response_model=list[SearchResult])
def search(
    query: str = Query(min_length=2, max_length=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SearchResult]:
    results: list[SearchResult] = []
    viewer = RoleCode.VIEWER.value in role_codes(user)
    visible_statuses = [BatchStatus.APPROVED, BatchStatus.EXPORTED]
    batch_statement = select(ProcessingBatch).where(ProcessingBatch.name.contains(query))
    if viewer:
        batch_statement = batch_statement.where(ProcessingBatch.status.in_(visible_statuses))
    for batch in db.scalars(batch_statement.order_by(ProcessingBatch.created_at.desc()).limit(10)):
        results.append(
            SearchResult(type="batch", id=batch.id, title=batch.name, subtitle=batch.status.value, batch_id=batch.id)
        )
    review_statement = select(ReviewFee).where(
        or_(ReviewFee.manuscript_no.contains(query), ReviewFee.reviewer_name.contains(query))
    )
    page_statement = select(PageFee).where(
        or_(PageFee.manuscript_no.contains(query), PageFee.invoice_title.contains(query))
    )
    royalty_statement = select(Royalty).where(
        or_(Royalty.manuscript_no.contains(query), Royalty.author_name.contains(query))
    )
    if viewer:
        review_statement = review_statement.join(ProcessingBatch).where(ProcessingBatch.status.in_(visible_statuses))
        page_statement = page_statement.join(ProcessingBatch).where(ProcessingBatch.status.in_(visible_statuses))
        royalty_statement = royalty_statement.join(ProcessingBatch).where(ProcessingBatch.status.in_(visible_statuses))
    for review_record in db.scalars(review_statement.limit(10)):
        results.append(
            SearchResult(
                type="review_fee",
                id=review_record.id,
                title=review_record.manuscript_no,
                subtitle=review_record.reviewer_name,
                batch_id=review_record.batch_id,
            )
        )
    for page_record in db.scalars(page_statement.limit(10)):
        results.append(
            SearchResult(
                type="page_fee",
                id=page_record.id,
                title=page_record.manuscript_no,
                subtitle=page_record.invoice_title or "版面费",
                batch_id=page_record.batch_id,
            )
        )
    for royalty_record in db.scalars(royalty_statement.limit(10)):
        results.append(
            SearchResult(
                type="royalty",
                id=royalty_record.id,
                title=royalty_record.manuscript_no,
                subtitle=royalty_record.author_name,
                batch_id=royalty_record.batch_id,
            )
        )
    return results[:30]
