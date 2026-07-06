from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_project_membership, membership_role
from app.core.permissions import PROJECT_ADMIN_ROLES, require_role
from app.db.session import get_db
from app.models.notification import Notification
from app.schemas.notification import NotificationPreferenceRead, NotificationPreferenceUpdate, NotificationRead, NotificationRetryRead
from app.services.audit_service import write_audit_log
from app.services.notification_service import get_or_create_notification_preferences, mark_notification_failed

router = APIRouter()


@router.get("", response_model=list[NotificationRead])
def list_notifications(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), PROJECT_ADMIN_ROLES)
    return db.query(Notification).filter(Notification.project_id == project_id).order_by(Notification.created_at.desc()).all()


@router.get("/preferences", response_model=NotificationPreferenceRead)
def get_preferences(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), PROJECT_ADMIN_ROLES)
    return get_or_create_notification_preferences(db, project_id)


@router.patch("/preferences", response_model=NotificationPreferenceRead)
def update_preferences(project_id: UUID, payload: NotificationPreferenceUpdate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), PROJECT_ADMIN_ROLES)
    preferences = get_or_create_notification_preferences(db, project_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(preferences, field, value)
    write_audit_log(db, "notification.preferences_updated", actor_user_id=membership.user_id, project_id=project_id)
    db.commit()
    db.refresh(preferences)
    return preferences


@router.post("/{notification_id}/retry", response_model=NotificationRetryRead)
def retry_notification(project_id: UUID, notification_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), PROJECT_ADMIN_ROLES)
    notification = db.query(Notification).filter(Notification.project_id == project_id, Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if notification.status == "sent":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sent notifications do not need retry")
    notification.status = "prepared"
    notification.next_retry_at = None
    mark_notification_failed(notification, "Manual retry queued for provider worker")
    write_audit_log(db, "notification.retry_queued", actor_user_id=membership.user_id, project_id=project_id, metadata={"notification_id": str(notification_id)})
    db.commit()
    db.refresh(notification)
    return NotificationRetryRead(id=notification.id, status=notification.status, attempts=notification.attempts, next_retry_at=notification.next_retry_at)
