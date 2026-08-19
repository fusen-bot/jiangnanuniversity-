from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditEvent, User


def record_event(
    db: Session,
    *,
    action: str,
    resource_type: str,
    resource_id: str | None,
    actor: User | None,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_id=actor.id if actor else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        request_id=request_id,
    )
    db.add(event)
    return event
