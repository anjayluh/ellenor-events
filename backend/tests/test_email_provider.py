from uuid import uuid4

import httpx

from app.core.config import settings
from app.services.email_provider import EmailDeliveryError, ResendEmailProvider, get_email_provider
from app.services.email_service import text_to_html


def test_email_html_escapes_content_and_links_public_urls():
    rendered = text_to_html("Hello <script>alert(1)</script>\n\nhttps://ellenor-events.vercel.app/guest-rsvp/test")

    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
    assert 'href="https://ellenor-events.vercel.app/guest-rsvp/test"' in rendered
    assert "Ellenor Events" in rendered


def test_mock_email_provider_is_available_outside_production():
    provider = get_email_provider("mock")

    result = provider.send(
        notification_id=uuid4(),
        recipient="qa@example.com",
        subject="QA",
        text_body="Hello",
        html_body="<p>Hello</p>",
    )

    assert result.accepted is True
    assert result.provider_message_id.startswith("mock-")


def test_mock_email_provider_is_rejected_in_production(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")

    try:
        get_email_provider("mock")
    except EmailDeliveryError as exc:
        assert "not allowed" in str(exc)
    else:
        raise AssertionError("production must reject mock email delivery")


def test_resend_provider_sends_branded_payload_with_idempotency(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "test-key")
    captured: dict[str, object] = {}

    def fake_post(url, *, headers, json, timeout):
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        return httpx.Response(200, json={"id": "re_123"}, request=httpx.Request("POST", url))

    monkeypatch.setattr("app.services.email_provider.httpx.post", fake_post)
    notification_id = uuid4()
    result = ResendEmailProvider().send(
        notification_id=notification_id,
        recipient="qa@example.com",
        subject="Invitation",
        text_body="Hello",
        html_body="<p>Hello</p>",
    )

    assert result.accepted is True
    assert result.provider_message_id == "re_123"
    assert captured["headers"]["Idempotency-Key"] == str(notification_id)
    assert captured["json"]["to"] == ["qa@example.com"]


def test_resend_provider_fails_closed_without_key():
    settings.resend_api_key = None

    try:
        ResendEmailProvider().send(
            notification_id=uuid4(),
            recipient="qa@example.com",
            subject="Invitation",
            text_body="Hello",
            html_body="<p>Hello</p>",
        )
    except EmailDeliveryError as exc:
        assert "not configured" in str(exc)
    else:
        raise AssertionError("Resend delivery must require an API key")
