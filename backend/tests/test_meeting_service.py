from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.meeting import MeetingRsvp
from app.services.meeting_service import get_meeting_or_404, upsert_meeting_rsvp


class ExistingRsvpQuery:
    def __init__(self, rsvp):
        self.rsvp = rsvp

    def filter(self, *args):
        return self

    def first(self):
        return self.rsvp


class FakeRsvpDb:
    def __init__(self, rsvp=None):
        self.rsvp = rsvp
        self.added = []
        self.flushed = False

    def query(self, model):
        return ExistingRsvpQuery(self.rsvp)

    def add(self, item):
        self.added.append(item)

    def flush(self):
        self.flushed = True


class EmptyMeetingQuery:
    def filter(self, *args):
        return self

    def first(self):
        return None


class EmptyMeetingDb:
    def query(self, model):
        return EmptyMeetingQuery()


def test_upsert_meeting_rsvp_updates_existing_response():
    rsvp = MeetingRsvp(meeting_id=uuid4(), user_id=uuid4(), status="tentative", comment="Maybe")
    db = FakeRsvpDb(rsvp=rsvp)

    result = upsert_meeting_rsvp(db, rsvp.meeting_id, rsvp.user_id, "accepted", "I will attend")

    assert result is rsvp
    assert result.status == "accepted"
    assert result.comment == "I will attend"
    assert db.added == []


def test_upsert_meeting_rsvp_creates_new_response():
    db = FakeRsvpDb()
    meeting_id = uuid4()
    user_id = uuid4()

    result = upsert_meeting_rsvp(db, meeting_id, user_id, "declined", "Traveling")

    assert result.meeting_id == meeting_id
    assert result.user_id == user_id
    assert result.status == "declined"
    assert db.added == [result]
    assert db.flushed is True


def test_get_meeting_or_404_scopes_by_project():
    with pytest.raises(HTTPException) as exc_info:
        get_meeting_or_404(EmptyMeetingDb(), project_id=uuid4(), meeting_id=uuid4())
    assert exc_info.value.status_code == 404
