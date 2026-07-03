from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.invite import Invite
from app.services.invite_service import ensure_invite_can_be_accepted, normalize_invite_contact


def make_invite(status: str = "pending", expires_delta: timedelta = timedelta(days=1)) -> Invite:
    return Invite(
        id=uuid4(),
        project_id=uuid4(),
        contact="+256700000000",
        role_assigned="COMMITTEE_MEMBER",
        token="token",
        status=status,
        expires_at=datetime.now(timezone.utc) + expires_delta,
    )


def test_pending_unexpired_invite_can_be_accepted():
    ensure_invite_can_be_accepted(make_invite())


def test_expired_invite_is_rejected_and_marked_expired():
    invite = make_invite(expires_delta=timedelta(minutes=-1))
    with pytest.raises(HTTPException) as exc_info:
        ensure_invite_can_be_accepted(invite)
    assert exc_info.value.status_code == 410
    assert invite.status == "expired"


def test_accepted_invite_cannot_be_reused():
    with pytest.raises(HTTPException) as exc_info:
        ensure_invite_can_be_accepted(make_invite(status="accepted"))
    assert exc_info.value.status_code == 409


def test_invite_contact_normalization():
    assert normalize_invite_contact(" +256 700 000000 ") == "+256700000000"
    assert normalize_invite_contact("USER@EXAMPLE.COM") == "user@example.com"
