import httpx
import pytest
from fastapi import HTTPException

from app.schemas.auth import RegisterRequest
from app.services.auth_service import register_with_supabase_password


class ErrorResponse:
    status_code = 400

    def __init__(self, payload: dict[str, str]):
        self.payload = payload

    def json(self):
        return self.payload


class RejectedResponse(ErrorResponse):
    def raise_for_status(self):
        raise httpx.HTTPStatusError("rejected", request=httpx.Request("POST", "https://example.com"), response=self)


@pytest.mark.parametrize(
    ("payload", "expected_status", "expected_detail"),
    [
        (
            {"msg": "User already registered"},
            409,
            "An account already exists for this email. Please sign in instead.",
        ),
        (
            {"msg": "Email not confirmed"},
            403,
            "This account is not confirmed. Check the email address used to sign up for the confirmation link, then return here to sign in.",
        ),
    ],
)
def test_registration_explains_existing_account_state(
    db_session,
    monkeypatch,
    payload: dict[str, str],
    expected_status: int,
    expected_detail: str,
):
    from app.core.config import settings

    monkeypatch.setattr(settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(settings, "supabase_anon_key", "anon-key")
    monkeypatch.setattr(
        "app.services.auth_service.httpx.post",
        lambda *args, **kwargs: RejectedResponse(payload),
    )

    with pytest.raises(HTTPException) as exc_info:
        register_with_supabase_password(
            db_session,
            RegisterRequest(email="person@example.com", password="password123", name="Person"),
        )

    assert exc_info.value.status_code == expected_status
    assert exc_info.value.detail == expected_detail


def test_registration_uses_configured_frontend_confirmation_url(db_session, monkeypatch):
    from app.core.config import settings

    captured_url = ""

    def post(*args, **kwargs):
        nonlocal captured_url
        captured_url = args[0]
        return RejectedResponse({"msg": "User already registered"})

    monkeypatch.setattr(settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(settings, "supabase_anon_key", "anon-key")
    monkeypatch.setattr(settings, "frontend_url", "https://ellenor-events.vercel.app")
    monkeypatch.setattr(settings, "auth_confirmation_redirect_url", None)
    monkeypatch.setattr("app.services.auth_service.httpx.post", post)

    with pytest.raises(HTTPException):
        register_with_supabase_password(
            db_session,
            RegisterRequest(email="person@example.com", password="password123", name="Person"),
        )

    assert captured_url == "https://example.supabase.co/auth/v1/signup?redirect_to=https%3A%2F%2Fellenor-events.vercel.app%2Flogin"
