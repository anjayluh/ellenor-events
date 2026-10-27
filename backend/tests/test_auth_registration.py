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
