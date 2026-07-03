from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def write_audit_log(
    db: Session,
    action: str,
    actor_user_id: UUID | None = None,
    project_id: UUID | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor_user_id,
        project_id=project_id,
        action=action,
        metadata_json=metadata or {},
    )
    db.add(entry)
    return entry
