import hashlib
import re
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.config import get_settings
from app.models import StoredFile, User, new_id

ALLOWED_UPLOADS: dict[str, set[str]] = {
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/octet-stream"},
    ".xls": {"application/vnd.ms-excel", "application/octet-stream"},
    ".csv": {"text/csv", "application/vnd.ms-excel", "application/octet-stream"},
    ".pdf": {"application/pdf", "application/octet-stream"},
    ".txt": {"text/plain", "application/octet-stream"},
    ".md": {"text/markdown", "text/plain", "application/octet-stream"},
}


def safe_download_name(name: str) -> str:
    cleaned = re.sub(r"[\r\n\"\\/]", "_", Path(name).name)
    return cleaned[:200] or "download"


async def store_upload(file: UploadFile, user: User, category: str = "source") -> StoredFile:
    settings = get_settings()
    original_name = safe_download_name(file.filename or "upload")
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_UPLOADS or file.content_type not in ALLOWED_UPLOADS[suffix]:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="不支持的文件类型")

    content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="文件超过大小限制")
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件为空")

    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    storage_name = f"{new_id()}{suffix}"
    destination = settings.storage_dir / storage_name
    destination.write_bytes(content)
    return StoredFile(
        original_name=original_name,
        storage_name=storage_name,
        media_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        category=category,
        uploaded_by_id=user.id,
    )


def resolve_stored_file(stored_file: StoredFile) -> Path:
    root = get_settings().storage_dir.resolve()
    candidate = (root / stored_file.storage_name).resolve()
    if candidate.parent != root:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="非法文件路径")
    return candidate
