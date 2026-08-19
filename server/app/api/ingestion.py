from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.audit import record_event
from app.database import get_db
from app.dependencies import require_roles
from app.enums import BusinessType, RoleCode
from app.models import ProcessingBatch, User
from app.schemas import BatchOut, ScrapeRequest
from app.storage import store_upload
from app.tasks import extract_pdf_authors, scrape_journal_issue

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/pdf-authors", response_model=BatchOut, status_code=status.HTTP_202_ACCEPTED)
async def queue_pdf_extraction(
    name: str = Form(min_length=2, max_length=160),
    file: UploadFile = File(),
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(RoleCode.ADMIN, RoleCode.OPERATOR)),
) -> ProcessingBatch:
    stored_file = await store_upload(file, actor)
    if not stored_file.original_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="作者提取只支持PDF")
    db.add(stored_file)
    db.flush()
    batch = ProcessingBatch(
        name=name,
        business_type=BusinessType.ROYALTY,
        source_file_id=stored_file.id,
        created_by_id=actor.id,
    )
    db.add(batch)
    db.flush()
    record_event(db, action="pdf.extract_queued", resource_type="batch", resource_id=batch.id, actor=actor)
    db.commit()
    extract_pdf_authors.delay(batch.id)
    return batch


@router.post("/journal-issue", response_model=BatchOut, status_code=status.HTTP_202_ACCEPTED)
def queue_journal_scrape(
    payload: ScrapeRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(RoleCode.ADMIN, RoleCode.OPERATOR)),
) -> ProcessingBatch:
    batch = ProcessingBatch(
        name=f"{payload.year}年第{payload.issue}期作者稿费",
        business_type=BusinessType.ROYALTY,
        created_by_id=actor.id,
    )
    db.add(batch)
    db.flush()
    record_event(
        db,
        action="journal.scrape_queued",
        resource_type="batch",
        resource_id=batch.id,
        actor=actor,
        details=payload.model_dump(),
    )
    db.commit()
    scrape_journal_issue.delay(batch.id, payload.year, payload.issue)
    return batch
