from enum import StrEnum


class RoleCode(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"
    APPROVER = "approver"
    VIEWER = "viewer"


class BusinessType(StrEnum):
    REVIEW_FEE = "review_fee"
    PAGE_FEE = "page_fee"
    ROYALTY = "royalty"


class BatchStatus(StrEnum):
    DRAFT = "draft"
    VALIDATING = "validating"
    PENDING_REVIEW = "pending_review"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    EXPORTED = "exported"
    REJECTED = "rejected"
    VALIDATION_FAILED = "validation_failed"
    TASK_FAILED = "task_failed"


class IssueStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class ApprovalDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
