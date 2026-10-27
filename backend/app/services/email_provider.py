from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import httpx

from app.core.config import settings


class EmailDeliveryError(RuntimeError):
    """Raised when an email provider cannot accept a message."""


@dataclass(frozen=True)
class EmailDeliveryResult:
    accepted: bool
    provider_message_id: str | None = None
    error: str | None = None


class EmailProvider(Protocol):
    name: str

    def send(
        self,
        *,
        notification_id: UUID,
        recipient: str,
        subject: str,
        text_body: str,
        html_body: str,
    ) -> EmailDeliveryResult:
        ...


class ResendEmailProvider:
    name = "resend"

    def send(
        self,
        *,
        notification_id: UUID,
        recipient: str,
        subject: str,
        text_body: str,
        html_body: str,
    ) -> EmailDeliveryResult:
        if not settings.resend_api_key:
            raise EmailDeliveryError("Email delivery is not configured")
        payload = {
            "from": settings.resend_from_email,
            "to": [recipient],
            "subject": subject,
            "text": text_body,
            "html": html_body,
        }
        try:
            response = httpx.post(
                f"{settings.resend_api_base_url.rstrip('/')}/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": str(notification_id),
                },
                json=payload,
                timeout=settings.email_delivery_timeout_seconds,
            )
            response.raise_for_status()
            response_data = response.json()
        except httpx.HTTPStatusError as exc:
            raise EmailDeliveryError("Email provider rejected the message") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise EmailDeliveryError("Email provider could not be reached") from exc

        provider_message_id = response_data.get("id")
        if not provider_message_id:
            raise EmailDeliveryError("Email provider returned an incomplete response")
        return EmailDeliveryResult(accepted=True, provider_message_id=str(provider_message_id))


class MockEmailProvider:
    name = "mock"

    def send(
        self,
        *,
        notification_id: UUID,
        recipient: str,
        subject: str,
        text_body: str,
        html_body: str,
    ) -> EmailDeliveryResult:
        return EmailDeliveryResult(accepted=True, provider_message_id=f"mock-{notification_id}")


def get_email_provider(provider: str | None = None) -> EmailProvider:
    provider_name = (provider or settings.email_provider).lower()
    if provider_name == "mock":
        if settings.is_production:
            raise EmailDeliveryError("Mock email delivery is not allowed in production")
        return MockEmailProvider()
    if provider_name == "resend":
        return ResendEmailProvider()
    raise EmailDeliveryError(f"Unsupported email provider: {provider_name}")
