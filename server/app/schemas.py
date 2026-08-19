from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.enums import ApprovalDecision, BatchStatus, BusinessType, IssueStatus, TaskStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RoleOut(ORMModel):
    id: str
    code: str
    name: str


class UserOut(ORMModel):
    id: str
    username: str
    display_name: str
    is_active: bool
    roles: list[RoleOut]


class LoginIn(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class UserCreate(LoginIn):
    display_name: str = Field(min_length=2, max_length=64)
    role_codes: list[str] = Field(min_length=1)


class BatchOut(ORMModel):
    id: str
    name: str
    business_type: BusinessType
    status: BatchStatus
    row_count: int
    issue_count: int
    version: int
    source_file_id: str | None
    source_sheet: str | None = None
    created_by_id: str
    created_at: datetime
    updated_at: datetime


class BatchCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    business_type: BusinessType


class ReviewFeeIn(BaseModel):
    manuscript_no: str = Field(min_length=1, max_length=80)
    reviewer_name: str = Field(min_length=1, max_length=80)
    review_type: str | None = Field(default=None, max_length=40)
    manuscript_title: str | None = Field(default=None, max_length=500)
    employee_no: str | None = Field(default=None, max_length=80)
    id_card: str | None = Field(default=None, max_length=40)
    institution: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=160)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    bank_name: str | None = Field(default=None, max_length=255)
    bank_account_name: str | None = Field(default=None, max_length=160)
    bank_account: str | None = Field(default=None, max_length=80)
    clearing_no: str | None = Field(default=None, max_length=40)
    is_internal: bool = False
    amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)


class ReviewFeeOut(ReviewFeeIn, ORMModel):
    id: str
    batch_id: str
    revision: int
    source_sheet: str | None = None
    source_row: int | None = None


class ReviewFeeUpdate(ReviewFeeIn):
    revision: int = Field(ge=1)


class PageFeeIn(BaseModel):
    manuscript_no: str = Field(min_length=1, max_length=80)
    accepted: bool = False
    invoiced: bool = False
    paid: bool = False
    reimbursement_no: str | None = Field(default=None, max_length=80)
    voucher_no: str | None = Field(default=None, max_length=80)
    tax_no: str | None = Field(default=None, max_length=64)
    invoice_title: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)


class PageFeeOut(PageFeeIn, ORMModel):
    id: str
    batch_id: str
    revision: int
    source_sheet: str | None = None
    source_row: int | None = None


class PageFeeUpdate(PageFeeIn):
    revision: int = Field(ge=1)


class RoyaltyIn(BaseModel):
    manuscript_no: str = Field(min_length=1, max_length=80)
    article_title: str | None = Field(default=None, max_length=500)
    author_name: str = Field(min_length=1, max_length=80)
    institution: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    id_card: str | None = Field(default=None, max_length=40)
    bank_name: str | None = Field(default=None, max_length=255)
    bank_account_name: str | None = Field(default=None, max_length=160)
    bank_account: str | None = Field(default=None, max_length=80)
    clearing_no: str | None = Field(default=None, max_length=40)
    employee_no: str | None = Field(default=None, max_length=80)
    is_internal: bool = False
    eligible: bool = True
    amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)


class RoyaltyOut(RoyaltyIn, ORMModel):
    id: str
    batch_id: str
    revision: int
    source_sheet: str | None = None
    source_row: int | None = None


class RoyaltyUpdate(RoyaltyIn):
    revision: int = Field(ge=1)


class ScrapeRequest(BaseModel):
    year: int = Field(ge=2000, le=2100)
    issue: int = Field(ge=1, le=24)


class IssueOut(ORMModel):
    id: str
    batch_id: str
    record_type: str
    record_id: str | None
    code: str
    severity: str
    message: str
    status: IssueStatus
    resolution: str | None
    resolved_by_id: str | None
    created_at: datetime


class IssueResolve(BaseModel):
    status: IssueStatus
    resolution: str = Field(min_length=2, max_length=500)


class ApprovalIn(BaseModel):
    decision: ApprovalDecision
    comment: str = Field(min_length=2, max_length=500)


class ApprovalOut(ORMModel):
    id: str
    batch_id: str
    decision: str
    comment: str
    decided_by_id: str
    created_at: datetime


class TaskIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    batch_id: str | None = None
    issue_id: str | None = None
    assignee_id: str | None = None


class TaskUpdate(BaseModel):
    status: TaskStatus


class TaskOut(TaskIn, ORMModel):
    id: str
    status: TaskStatus
    created_by_id: str
    created_at: datetime


class CommentIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class CommentOut(CommentIn, ORMModel):
    id: str
    batch_id: str
    created_by_id: str
    created_at: datetime


class KnowledgeIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=10, max_length=100_000)
    source: str = Field(min_length=2, max_length=255)


class KnowledgeOut(KnowledgeIn, ORMModel):
    id: str
    is_active: bool
    created_at: datetime


class AssistantQuery(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    batch_id: str | None = None


class AssistantResponse(BaseModel):
    interaction_id: str
    answer: str
    sources: list[dict[str, Any]]
    proposed_action: dict[str, Any] | None = None
    warning: str | None = None


class ActionConfirm(BaseModel):
    interaction_id: str


class AuditOut(ORMModel):
    id: str
    occurred_at: datetime
    actor_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    details: dict[str, Any]
    request_id: str | None


class FileOut(ORMModel):
    id: str
    original_name: str
    media_type: str
    size_bytes: int
    sha256: str
    category: str
    uploaded_by_id: str
    created_at: datetime


class SearchResult(BaseModel):
    type: str
    id: str
    title: str
    subtitle: str
    batch_id: str | None = None
