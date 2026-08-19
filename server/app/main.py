import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import assistant, auth, batches, ingestion, records, resources, users, workflow
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    if settings.environment == "production" and settings.secret_key == "development-only-secret-change-me":
        raise RuntimeError("Production requires a unique JFP_SECRET_KEY")
    yield


app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    description="单机构、多角色的期刊财务智能运营平台",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-ID"],
)


@app.middleware("http")
async def security_and_request_context(request: Request, call_next: Any):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))[:64]
    if request.method not in {"GET", "HEAD", "OPTIONS"} and request.url.path != "/api/v1/auth/login":
        csrf_cookie = request.cookies.get("csrf_token")
        csrf_header = request.headers.get("X-CSRF-Token")
        if not csrf_cookie or csrf_cookie != csrf_header:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF 校验失败", "request_id": request_id},
            )
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "version": "2.0.0"}


for api_router in (
    auth.router,
    users.router,
    batches.router,
    ingestion.router,
    records.router,
    workflow.router,
    resources.router,
    assistant.router,
):
    app.include_router(api_router, prefix="/api/v1")
