from app.core.config import settings


def build_email_invite_payload(contact: str, invite_link: str) -> dict[str, str | None]:
    return build_resend_email_payload(
        contact,
        "Your Ellenor Events invitation",
        f"You have been invited to coordinate an Ellenor event. Open: {invite_link}",
    )


def build_resend_email_payload(contact: str | None, subject: str, body: str) -> dict[str, str | None]:
    return {
        "provider": "resend",
        "from": settings.resend_from_email,
        "to": contact,
        "subject": subject,
        "body": body,
    }
