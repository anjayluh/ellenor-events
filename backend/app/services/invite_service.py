from app.core.config import settings


def build_invite_link(token: str) -> str:
    return f"{settings.frontend_url}/invite/{token}"
