from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.dependencies import get_current_user
from app.core.security import create_access_token, decode_access_token


def test_access_token_round_trip():
    user_id = uuid4()
    token = create_access_token(user_id)
    assert decode_access_token(token) == user_id


def test_access_token_rejects_invalid_token():
    with pytest.raises(ValueError):
        decode_access_token("not-a-real-token")


def test_access_token_rejects_expired_token():
    token = create_access_token(uuid4(), expires_delta=timedelta(minutes=-1))
    with pytest.raises(ValueError):
        decode_access_token(token)


def test_current_user_requires_token_when_dev_header_disabled():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(credentials=None, x_user_id=None, db=None)
    assert exc_info.value.status_code == 401


def test_allowed_cors_origins_deduplicates_frontend_and_extra_origins():
    from app.core.config import Settings

    settings = Settings(
        frontend_url="https://ellenor-events.vercel.app",
        cors_origins="https://preview.vercel.app, https://ellenor-events.vercel.app",
    )

    assert settings.allowed_cors_origins == [
        "https://ellenor-events.vercel.app",
        "https://preview.vercel.app",
    ]
