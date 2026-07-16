from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification import Notification, NotificationPreference
from app.services.audit_service import write_audit_log
from app.services.email_service import build_resend_email_payload
from app.services.whatsapp_service import build_whatsapp_cloud_payload, build_whatsapp_manual_url


@dataclass
class PreparedNotification:
    id: UUID
    project_id: UUID
    channel: str
    provider: str


def get_or_create_notification_preferences(db: Session, project_id: UUID) -> NotificationPreference:
    preferences = db.query(NotificationPreference).filter(NotificationPreference.project_id == project_id).first()
    if preferences:
        return preferences
    preferences = NotificationPreference(project_id=project_id)
    db.add(preferences)
    db.flush()
    return preferences


def build_provider_payload(channel: str, recipient_contact: str | None, subject: str | None, body: str) -> tuple[str, dict]:
    if channel == "email":
        return "resend", build_resend_email_payload(recipient_contact, subject or "Ellenor Events update", body)

    if settings.whatsapp_mode == "cloud_api":
        return "whatsapp_cloud_api", build_whatsapp_cloud_payload(recipient_contact, body)

    return "manual_whatsapp", {"provider": "manual_whatsapp", "url": build_whatsapp_manual_url(recipient_contact, body), "body": body}


def create_notification(
    db: Session,
    project_id: UUID,
    channel: str,
    body: str,
    recipient_contact: str | None = None,
    recipient_user_id: UUID | None = None,
    subject: str | None = None,
    actor_user_id: UUID | None = None,
    metadata: dict | None = None,
) -> Notification | PreparedNotification:
    provider, provider_payload = build_provider_payload(channel, recipient_contact, subject, body)
    if settings.uses_remote_supabase_auth:
        notification_id = db.execute(
            text(
                """
                select public.create_notification(
                    :project_id,
                    :recipient_user_id,
                    :recipient_contact,
                    :channel,
                    :provider,
                    :subject,
                    :body,
                    cast(:provider_payload as jsonb),
                    :max_attempts
                )
                """
            ),
            {
                "project_id": str(project_id),
                "recipient_user_id": str(recipient_user_id) if recipient_user_id else None,
                "recipient_contact": recipient_contact,
                "channel": channel,
                "provider": provider,
                "subject": subject,
                "body": body,
                "provider_payload": json.dumps(provider_payload),
                "max_attempts": settings.notification_max_attempts,
            },
        ).scalar_one()
        write_audit_log(
            db,
            "notification.prepared",
            actor_user_id=actor_user_id,
            project_id=project_id,
            metadata={"notification_id": str(notification_id), "channel": channel, "provider": provider, **(metadata or {})},
        )
        return PreparedNotification(id=notification_id, project_id=project_id, channel=channel, provider=provider)

    notification = Notification(
        project_id=project_id,
        recipient_user_id=recipient_user_id,
        recipient_contact=recipient_contact,
        channel=channel,
        provider=provider,
        subject=subject,
        body=body,
        status="prepared",
        provider_payload=provider_payload,
        max_attempts=settings.notification_max_attempts,
    )
    db.add(notification)
    db.flush()
    write_audit_log(
        db,
        "notification.prepared",
        actor_user_id=actor_user_id,
        project_id=project_id,
        metadata={"notification_id": str(notification.id), "channel": channel, "provider": provider, **(metadata or {})},
    )
    return notification


def queue_project_notification(
    db: Session,
    project_id: UUID,
    action: str,
    title: str,
    message: str,
    actor_user_id: UUID | None = None,
    metadata: dict | None = None,
) -> Notification:
    notification = create_notification(
        db,
        project_id=project_id,
        channel="email",
        subject=title,
        body=message,
        actor_user_id=actor_user_id,
        metadata=metadata,
    )
    write_audit_log(
        db,
        action,
        actor_user_id=actor_user_id,
        project_id=project_id,
        metadata={"title": title, "message": message, "notification_id": str(notification.id), **(metadata or {})},
    )
    return notification


def mark_notification_failed(notification: Notification, error: str) -> Notification:
    notification.attempts = (notification.attempts or 0) + 1
    notification.last_error = error
    if notification.attempts >= notification.max_attempts:
        notification.status = "failed"
        notification.next_retry_at = None
    else:
        notification.status = "retry_scheduled"
        notification.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=5 * notification.attempts)
    return notification


def mark_notification_sent(notification: Notification) -> Notification:
    notification.attempts = (notification.attempts or 0) + 1
    notification.status = "sent"
    notification.sent_at = datetime.now(timezone.utc)
    notification.last_error = None
    notification.next_retry_at = None
    return notification
