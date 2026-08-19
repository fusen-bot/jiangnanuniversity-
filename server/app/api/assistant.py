from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.enums import RoleCode
from app.models import AIInteraction, KnowledgeDocument, ToolCall, User, WorkflowTask
from app.schemas import ActionConfirm, AssistantQuery, AssistantResponse, KnowledgeIn, KnowledgeOut, TaskOut
from app.services.assistant import ask_assistant

router = APIRouter(tags=["assistant"])


@router.get("/knowledge", response_model=list[KnowledgeOut])
def list_knowledge(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[KnowledgeDocument]:
    return list(db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.is_active.is_(True))))


@router.post("/knowledge", response_model=KnowledgeOut, status_code=status.HTTP_201_CREATED)
def add_knowledge(
    payload: KnowledgeIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(RoleCode.ADMIN)),
) -> KnowledgeDocument:
    document = KnowledgeDocument(**payload.model_dump(), created_by_id=actor.id)
    db.add(document)
    db.flush()
    record_event(db, action="knowledge.create", resource_type="knowledge", resource_id=document.id, actor=actor)
    db.commit()
    db.refresh(document)
    return document


@router.post("/assistant/query", response_model=AssistantResponse)
def query_assistant(
    payload: AssistantQuery,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> AssistantResponse:
    result = ask_assistant(db, actor, payload.question, payload.batch_id)
    record_event(
        db,
        action="assistant.query",
        resource_type="ai_interaction",
        resource_id=result.interaction.id,
        actor=actor,
    )
    db.commit()
    return AssistantResponse(
        interaction_id=result.interaction.id,
        answer=result.interaction.answer,
        sources=result.interaction.sources,
        proposed_action=result.interaction.proposed_action,
        warning=result.warning,
    )


@router.post("/assistant/confirm", response_model=TaskOut)
def confirm_assistant_action(
    payload: ActionConfirm,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(RoleCode.ADMIN, RoleCode.OPERATOR, RoleCode.APPROVER)),
) -> WorkflowTask:
    interaction = db.get(AIInteraction, payload.interaction_id)
    if not interaction or interaction.user_id != actor.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="待确认建议不存在")
    action = interaction.proposed_action or {}
    if action.get("type") != "create_task":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该建议不包含可确认操作")
    existing = db.scalar(
        select(ToolCall).where(
            ToolCall.interaction_id == interaction.id,
            ToolCall.tool_name == "create_task",
            ToolCall.confirmed_by_id.is_not(None),
        )
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该建议已经确认")
    task = WorkflowTask(
        title=str(action["title"])[:200],
        batch_id=action.get("batch_id"),
        created_by_id=actor.id,
    )
    db.add(task)
    db.flush()
    db.add(
        ToolCall(
            interaction_id=interaction.id,
            tool_name="create_task",
            arguments=action,
            result_summary=f"created task {task.id}",
            confirmed_by_id=actor.id,
        )
    )
    record_event(db, action="assistant.action_confirm", resource_type="task", resource_id=task.id, actor=actor)
    db.commit()
    db.refresh(task)
    return task
