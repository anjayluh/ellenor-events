from urllib.parse import quote


def build_whatsapp_invite_url(contact: str, invite_link: str) -> str:
    message = quote(f"You have been invited to coordinate an Ellenor event. Open: {invite_link}")
    cleaned_contact = contact.replace("+", "").replace(" ", "")
    return f"https://wa.me/{cleaned_contact}?text={message}"
