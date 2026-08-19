import httpx

from app.celery_app import celery_app
from app.database import SessionLocal
from app.enums import BatchStatus
from app.models import Royalty
from app.services.batches import get_batch_or_404, validate_batch_records
from app.services.import_export import import_batch_file
from app.services.ingestion import JournalGateway, extract_authors_from_pdf
from app.storage import resolve_stored_file


@celery_app.task(bind=True, autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def import_and_validate_batch(self, batch_id: str) -> dict[str, int | str]:
    del self
    with SessionLocal() as db:
        batch = get_batch_or_404(db, batch_id)
        try:
            import_batch_file(db, batch)
            validate_batch_records(db, batch)
            db.commit()
            return {"batch_id": batch.id, "rows": batch.row_count, "issues": batch.issue_count}
        except Exception:
            db.rollback()
            failed_batch = get_batch_or_404(db, batch_id)
            failed_batch.status = BatchStatus.TASK_FAILED
            db.commit()
            raise


def _save_royalties(db, batch, records) -> None:
    for record in records:
        db.add(
            Royalty(
                batch_id=batch.id,
                manuscript_no=record.manuscript_no,
                article_title=record.article_title,
                author_name=record.author_name,
                institution=record.institution,
                email=record.email,
            )
        )


@celery_app.task(bind=True, autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def extract_pdf_authors(self, batch_id: str) -> dict[str, int | str]:
    del self
    with SessionLocal() as db:
        batch = get_batch_or_404(db, batch_id)
        try:
            if not batch.source_file:
                raise ValueError("Batch has no source PDF")
            records = extract_authors_from_pdf(resolve_stored_file(batch.source_file))
            _save_royalties(db, batch, records)
            validate_batch_records(db, batch)
            db.commit()
            return {"batch_id": batch.id, "rows": batch.row_count, "issues": batch.issue_count}
        except Exception:
            db.rollback()
            failed_batch = get_batch_or_404(db, batch_id)
            failed_batch.status = BatchStatus.TASK_FAILED
            db.commit()
            raise


@celery_app.task(bind=True, autoretry_for=(httpx.HTTPError,), retry_backoff=True, max_retries=3)
def scrape_journal_issue(self, batch_id: str, year: int, issue: int) -> dict[str, int | str]:
    del self
    with SessionLocal() as db:
        batch = get_batch_or_404(db, batch_id)
        try:
            records = JournalGateway().fetch_issue(year, issue)
            _save_royalties(db, batch, records)
            validate_batch_records(db, batch)
            db.commit()
            return {"batch_id": batch.id, "rows": batch.row_count, "issues": batch.issue_count}
        except Exception:
            db.rollback()
            failed_batch = get_batch_or_404(db, batch_id)
            failed_batch.status = BatchStatus.TASK_FAILED
            db.commit()
            raise
