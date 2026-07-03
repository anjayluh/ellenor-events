from uuid import UUID

from sqlalchemy.orm import Session

from app.services.audit_service import write_audit_log


def queue_project_notification(
    db: Session,
    project_id: UUID,
    action: str,
    title: str,
    message: str,
    actor_user_id: UUID | None = None,
    metadata: dict | None = None,
) -> None:
    write_audit_log(
        db,
        action,
        actor_user_id=actor_user_id,
        project_id=project_id,
        metadata={"title": title, "message": message, **(metadata or {})},
    )
