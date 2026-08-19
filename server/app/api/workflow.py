from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.config import get_settings
from app.database import get_db
from app.dependencies import enforce_batch_visibility, get_current_user, require_roles
from app.enums import ApprovalDecision, BatchStatus, IssueStatus, RoleCode
from app.models import Approval, Comment, ExportRecord, ProcessingBatch, User, ValidationIssue, WorkflowTask
from app.schemas import (
    ApprovalIn,
    ApprovalOut,
    BatchOut,
    CommentIn,
    CommentOut,
    IssueOut,
    IssueResolve,
    TaskIn,
    TaskOut,
    TaskUpdate,
)
from app.services.batches import get_batch_or_404
from app.services.import_export import export_batch
from app.state_machine import transition

router = APIRouter(tags=["workflow"])


@router.get("/validation-issues", response_model=list[IssueOut])
def list_issues(
    batch_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ValidationIssue]:
    enforce_batch_visibility(get_batch_or_404(db, batch_id), user)
    return list(
        db.scalars(
            select(ValidationIssue)
            .where(ValidationIssue.batch_id == batch_id)
            .order_by(ValidationIssue.created_at.desc())
        )
    )


@router.patch("/validation-issues/{issue_id}", response_model=IssueOut)
def resolve_issue(
    issue_id: str,
    payload: IssueResolve,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(RoleCode.ADMIN, RoleCode.OPERATOR)),
) -> ValidationIssue:
    issue = db.get(ValidationIssue, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="异常不存在")
    if payload.status == IssueStatus.OPEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="复核结果不能仍为未处理")
    issue.status = payload.status
    issue.resolution = payload.resolution
    issue.resolved_by_id = actor.id
    record_event(db, action="issue.resolve", resource_type="validation_issue", resource_id=issue.id, actor=actor)
    db.commit()
    db.refresh(issue)
    return issue


@router.post("/approvals/{batch_id}", response_model=BatchOut)
def decide_batch(
    batch_id: str,
    payload: ApprovalIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(RoleCode.ADMIN, RoleCode.APPROVER)),
) -> ProcessingBatch:
    batch = get_batch_or_404(db, batch_id)
    if batch.created_by_id == actor.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="经办人与审批人必须职责分离")
    target = BatchStatus.APPROVED if payload.decision == ApprovalDecision.APPROVE else BatchStatus.REJECTED
    batch.status = transition(batch.status, target)
    batch.version += 1
    db.add(
        Approval(
            batch_id=batch.id,
            decision=payload.decision.value,
            comment=payload.comment,
            decided_by_id=actor.id,
        )
    )
    record_event(
        db,
        action=f"approval.{payload.decision.value}",
        resource_type="batch",
        resource_id=batch.id,
        actor=actor,
        details={"comment": payload.comment},
    )
    db.commit()
    db.refresh(batch)
    return batch


@router.get("/approvals", response_model=list[ApprovalOut])
def list_approvals(
    batch_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Approval]:
    enforce_batch_visibility(get_batch_or_404(db, batch_id), user)
    return list(db.scalars(select(Approval).where(Approval.batch_id == batch_id).order_by(Approval.created_at)))


@router.post("/exports/{batch_id}", response_model=BatchOut)
def create_export(
    batch_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(RoleCode.ADMIN, RoleCode.OPERATOR)),
) -> ProcessingBatch:
    batch = get_batch_or_404(db, batch_id)
    if batch.status != BatchStatus.APPROVED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="只有已批准批次可以导出")
    stored_file = export_batch(db, batch, actor, get_settings().storage_dir)
    db.add(stored_file)
    db.flush()
    db.add(ExportRecord(batch_id=batch.id, file_id=stored_file.id, version=batch.version, created_by_id=actor.id))
    batch.status = transition(batch.status, BatchStatus.EXPORTED)
    record_event(
        db,
        action="batch.export",
        resource_type="batch",
        resource_id=batch.id,
        actor=actor,
        details={"file_id": stored_file.id},
    )
    db.commit()
    db.refresh(batch)
    return batch


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(
    batch_id: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleCode.ADMIN, RoleCode.OPERATOR, RoleCode.APPROVER)),
) -> list[WorkflowTask]:
    statement = select(WorkflowTask).order_by(WorkflowTask.created_at.desc())
    if batch_id:
        statement = statement.where(WorkflowTask.batch_id == batch_id)
    return list(db.scalars(statement))


@router.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(RoleCode.ADMIN, RoleCode.OPERATOR, RoleCode.APPROVER)),
) -> WorkflowTask:
    task = WorkflowTask(**payload.model_dump(), created_by_id=actor.id)
    db.add(task)
    db.flush()
    record_event(db, action="task.create", resource_type="task", resource_id=task.id, actor=actor)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: str,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(RoleCode.ADMIN, RoleCode.OPERATOR, RoleCode.APPROVER)),
) -> WorkflowTask:
    task = db.get(WorkflowTask, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    task.status = payload.status
    record_event(db, action="task.update", resource_type="task", resource_id=task.id, actor=actor)
    db.commit()
    db.refresh(task)
    return task


@router.get("/comments/{batch_id}", response_model=list[CommentOut])
def list_comments(
    batch_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Comment]:
    enforce_batch_visibility(get_batch_or_404(db, batch_id), user)
    return list(db.scalars(select(Comment).where(Comment.batch_id == batch_id).order_by(Comment.created_at)))


@router.post("/comments/{batch_id}", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(
    batch_id: str,
    payload: CommentIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(RoleCode.ADMIN, RoleCode.OPERATOR, RoleCode.APPROVER)),
) -> Comment:
    get_batch_or_404(db, batch_id)
    comment = Comment(batch_id=batch_id, content=payload.content, created_by_id=actor.id)
    db.add(comment)
    db.flush()
    record_event(db, action="comment.create", resource_type="batch", resource_id=batch_id, actor=actor)
    db.commit()
    db.refresh(comment)
    return comment
