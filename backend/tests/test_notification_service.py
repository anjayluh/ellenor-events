from uuid import uuid4

from app.models.notification import Notification
from app.services.notification_service import build_provider_payload, mark_notification_failed, mark_notification_sent
from app.services.whatsapp_service import build_whatsapp_manual_url


def test_manual_whatsapp_payload_contains_wa_link():
    provider, payload = build_provider_payload("whatsapp", "+256 700 000000", "Meeting", "Planning meeting moved")

    assert provider == "manual_whatsapp"
    assert payload["url"].startswith("https://wa.me/256700000000")
    assert "Planning" in payload["body"]


def test_resend_email_payload_is_prepared():
    provider, payload = build_provider_payload("email", "user@example.com", "Invite", "Open your invite")

    assert provider == "resend"
    assert payload["to"] == "user@example.com"
    assert payload["subject"] == "Invite"


def test_whatsapp_manual_url_handles_missing_contact():
    assert build_whatsapp_manual_url(None, "Hello") is None


def test_notification_failure_schedules_retry_until_max_attempts():
    notification = Notification(project_id=uuid4(), channel="email", provider="resend", body="Hello", max_attempts=2)

    mark_notification_failed(notification, "Provider timeout")

    assert notification.status == "retry_scheduled"
    assert notification.attempts == 1
    assert notification.next_retry_at is not None
    assert notification.last_error == "Provider timeout"


def test_notification_failure_marks_failed_at_max_attempts():
    notification = Notification(project_id=uuid4(), channel="email", provider="resend", body="Hello", max_attempts=1)

    mark_notification_failed(notification, "Provider timeout")

    assert notification.status == "failed"
    assert notification.next_retry_at is None


def test_notification_sent_clears_retry_state():
    notification = Notification(project_id=uuid4(), channel="email", provider="resend", body="Hello", attempts=1, last_error="timeout")

    mark_notification_sent(notification)

    assert notification.status == "sent"
    assert notification.sent_at is not None
    assert notification.last_error is None
