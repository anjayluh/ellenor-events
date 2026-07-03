from app.core.config import settings


def build_email_invite_payload(contact: str, invite_link: str) -> dict[str, str | None]:
    return {
        "provider": settings.email_provider,
        "to": contact,
        "subject": "Your Ellenor Events invitation",
        "body": f"You have been invited to coordinate an Ellenor event. Open: {invite_link}",
    }
