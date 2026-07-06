from urllib.parse import quote

from app.core.config import settings


def clean_whatsapp_contact(contact: str) -> str:
    return contact.replace("+", "").replace(" ", "")


def build_whatsapp_invite_url(contact: str, invite_link: str) -> str:
    message = quote(f"You have been invited to coordinate an Ellenor event. Open: {invite_link}")
    return f"https://wa.me/{clean_whatsapp_contact(contact)}?text={message}"


def build_whatsapp_manual_url(contact: str | None, message: str) -> str | None:
    if not contact:
        return None
    return f"https://wa.me/{clean_whatsapp_contact(contact)}?text={quote(message)}"


def build_whatsapp_cloud_payload(contact: str | None, message: str) -> dict[str, str | None]:
    return {
        "provider": "whatsapp_cloud_api",
        "phone_number_id": settings.whatsapp_phone_number_id,
        "to": clean_whatsapp_contact(contact) if contact else None,
        "type": "text",
        "body": message,
    }
