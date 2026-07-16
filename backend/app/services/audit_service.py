from uuid import UUID
import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit_log import AuditLog


def write_audit_log(
    db: Session,
    action: str,
    actor_user_id: UUID | None = None,
    project_id: UUID | None = None,
    metadata: dict | None = None,
) -> AuditLog | UUID:
    metadata_json = metadata or {}
    if settings.uses_remote_supabase_auth:
        return db.execute(
            text(
                """
                select public.write_audit_log(
                    :actor_user_id,
                    :project_id,
                    :action,
                    cast(:metadata as jsonb)
                )
                """
            ),
            {
                "actor_user_id": str(actor_user_id) if actor_user_id else None,
                "project_id": str(project_id) if project_id else None,
                "action": action,
                "metadata": json.dumps(metadata_json),
            },
        ).scalar_one()

    entry = AuditLog(
        actor_user_id=actor_user_id,
        project_id=project_id,
        action=action,
        metadata_json=metadata_json,
    )
    db.add(entry)
    return entry
