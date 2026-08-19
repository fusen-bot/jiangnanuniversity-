from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, ForeignKey, Numeric, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import BatchStatus, BusinessType, IssueStatus, TaskStatus


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


def enum_type(enum_class: type) -> Enum:
    return Enum(enum_class, native_enum=False, values_callable=lambda members: [member.value for member in members])


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    users: Mapped[list[User]] = relationship(secondary=user_roles, back_populates="roles")


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    roles: Mapped[list[Role]] = relationship(secondary=user_roles, back_populates="users")


class StoredFile(TimestampMixin, Base):
    __tablename__ = "stored_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    media_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="source")
    uploaded_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)


class ProcessingBatch(TimestampMixin, Base):
    __tablename__ = "processing_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    business_type: Mapped[BusinessType] = mapped_column(enum_type(BusinessType), nullable=False)
    status: Mapped[BatchStatus] = mapped_column(
        enum_type(BatchStatus), default=BatchStatus.DRAFT, nullable=False, index=True
    )
    row_count: Mapped[int] = mapped_column(default=0, nullable=False)
    issue_count: Mapped[int] = mapped_column(default=0, nullable=False)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    source_file_id: Mapped[str | None] = mapped_column(ForeignKey("stored_files.id"))
    source_sheet: Mapped[str | None] = mapped_column(String(160))
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    source_file: Mapped[StoredFile | None] = relationship()
    issues: Mapped[list[ValidationIssue]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class ReviewFee(TimestampMixin, Base):
    __tablename__ = "review_fees"
    __table_args__ = (UniqueConstraint("batch_id", "manuscript_no", "reviewer_name", name="uq_review_record"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    batch_id: Mapped[str] = mapped_column(ForeignKey("processing_batches.id", ondelete="CASCADE"), index=True)
    manuscript_no: Mapped[str] = mapped_column(String(80), nullable=False)
    reviewer_name: Mapped[str] = mapped_column(String(80), nullable=False)
    review_type: Mapped[str | None] = mapped_column(String(40))
    manuscript_title: Mapped[str | None] = mapped_column(String(500))
    employee_no: Mapped[str | None] = mapped_column(String(80))
    id_card: Mapped[str | None] = mapped_column(String(40))
    institution: Mapped[str | None] = mapped_column(String(255))
    department: Mapped[str | None] = mapped_column(String(160))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(40))
    bank_name: Mapped[str | None] = mapped_column(String(255))
    bank_account_name: Mapped[str | None] = mapped_column(String(160))
    bank_account: Mapped[str | None] = mapped_column(String(80))
    clearing_no: Mapped[str | None] = mapped_column(String(40))
    source_sheet: Mapped[str | None] = mapped_column(String(160))
    source_row: Mapped[int | None] = mapped_column()
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    revision: Mapped[int] = mapped_column(default=1, nullable=False)


class PageFee(TimestampMixin, Base):
    __tablename__ = "page_fees"
    __table_args__ = (UniqueConstraint("batch_id", "manuscript_no", name="uq_page_fee_record"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    batch_id: Mapped[str] = mapped_column(ForeignKey("processing_batches.id", ondelete="CASCADE"), index=True)
    manuscript_no: Mapped[str] = mapped_column(String(80), nullable=False)
    accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    invoiced: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reimbursement_no: Mapped[str | None] = mapped_column(String(80))
    voucher_no: Mapped[str | None] = mapped_column(String(80))
    tax_no: Mapped[str | None] = mapped_column(String(64))
    invoice_title: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(40))
    source_sheet: Mapped[str | None] = mapped_column(String(160))
    source_row: Mapped[int | None] = mapped_column()
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    revision: Mapped[int] = mapped_column(default=1, nullable=False)


class Royalty(TimestampMixin, Base):
    __tablename__ = "royalties"
    __table_args__ = (UniqueConstraint("batch_id", "manuscript_no", "author_name", name="uq_royalty_record"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    batch_id: Mapped[str] = mapped_column(ForeignKey("processing_batches.id", ondelete="CASCADE"), index=True)
    manuscript_no: Mapped[str] = mapped_column(String(80), nullable=False)
    article_title: Mapped[str | None] = mapped_column(String(500))
    author_name: Mapped[str] = mapped_column(String(80), nullable=False)
    institution: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(40))
    id_card: Mapped[str | None] = mapped_column(String(40))
    bank_name: Mapped[str | None] = mapped_column(String(255))
    bank_account_name: Mapped[str | None] = mapped_column(String(160))
    bank_account: Mapped[str | None] = mapped_column(String(80))
    clearing_no: Mapped[str | None] = mapped_column(String(40))
    employee_no: Mapped[str | None] = mapped_column(String(80))
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    source_sheet: Mapped[str | None] = mapped_column(String(160))
    source_row: Mapped[int | None] = mapped_column()
    revision: Mapped[int] = mapped_column(default=1, nullable=False)


class ValidationIssue(TimestampMixin, Base):
    __tablename__ = "validation_issues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    batch_id: Mapped[str] = mapped_column(ForeignKey("processing_batches.id", ondelete="CASCADE"), index=True)
    record_type: Mapped[str] = mapped_column(String(32), nullable=False)
    record_id: Mapped[str | None] = mapped_column(String(36))
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="warning", nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[IssueStatus] = mapped_column(enum_type(IssueStatus), default=IssueStatus.OPEN, nullable=False)
    resolution: Mapped[str | None] = mapped_column(String(500))
    resolved_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    batch: Mapped[ProcessingBatch] = relationship(back_populates="issues")


class Approval(TimestampMixin, Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    batch_id: Mapped[str] = mapped_column(ForeignKey("processing_batches.id", ondelete="CASCADE"), index=True)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    comment: Mapped[str] = mapped_column(String(500), nullable=False)
    decided_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)


class ExportRecord(TimestampMixin, Base):
    __tablename__ = "export_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    batch_id: Mapped[str] = mapped_column(ForeignKey("processing_batches.id", ondelete="CASCADE"), index=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("stored_files.id"), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)


class WorkflowTask(TimestampMixin, Base):
    __tablename__ = "workflow_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(enum_type(TaskStatus), default=TaskStatus.TODO, nullable=False)
    batch_id: Mapped[str | None] = mapped_column(ForeignKey("processing_batches.id"))
    issue_id: Mapped[str | None] = mapped_column(ForeignKey("validation_issues.id"))
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)


class Comment(TimestampMixin, Base):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    batch_id: Mapped[str] = mapped_column(ForeignKey("processing_batches.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)


class KnowledgeDocument(TimestampMixin, Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)


class AIInteraction(TimestampMixin, Base):
    __tablename__ = "ai_interactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    proposed_action: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(default=0, nullable=False)


class ToolCall(TimestampMixin, Base):
    __tablename__ = "tool_calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    interaction_id: Mapped[str] = mapped_column(ForeignKey("ai_interactions.id", ondelete="CASCADE"), index=True)
    tool_name: Mapped[str] = mapped_column(String(80), nullable=False)
    arguments: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    result_summary: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(36))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(36), index=True)
