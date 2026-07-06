from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.dependencies import CurrentUser
from app.api.staff import require_staff_user
from app.models.staff_member import StaffMember
from app.models.user import User
from app.services.staff_service import build_risk_alert, missing_vendor_categories, risk_level


class StaffQuery:
    def __init__(self, staff_member):
        self.staff_member = staff_member

    def filter(self, *args):
        return self

    def first(self):
        return self.staff_member


class FakeDb:
    def __init__(self, staff_member=None):
        self.staff_member = staff_member
        self.added = []

    def query(self, model):
        return StaffQuery(self.staff_member)

    def add(self, item):
        self.added.append(item)


def make_current_user():
    return CurrentUser(User(id=uuid4(), phone="+256700000101"))


def test_staff_access_denies_non_staff_user():
    with pytest.raises(HTTPException) as exc_info:
        require_staff_user(current_user=make_current_user(), db=FakeDb())
    assert exc_info.value.status_code == 403


def test_staff_access_allows_active_staff_user():
    user = make_current_user()
    staff_member = StaffMember(user_id=user.id, role="OPERATIONS_MANAGER", status="active")
    result = require_staff_user(current_user=user, db=FakeDb(staff_member))
    assert result is staff_member


def test_risk_level_prioritizes_high_risk_conditions():
    assert risk_level(overdue_task_count=3, missing_vendor_count=0, budget_variance=0) == "high"
    assert risk_level(overdue_task_count=0, missing_vendor_count=1, budget_variance=0) == "medium"
    assert risk_level(overdue_task_count=0, missing_vendor_count=0, budget_variance=0) == "low"


def test_missing_vendor_categories_requires_core_categories():
    assert missing_vendor_categories({"decor", "catering", "photography"}) == 0
    assert missing_vendor_categories({"decor"}) == 2


def test_build_risk_alert_includes_budget_variance_message():
    alerts = build_risk_alert(uuid4(), "Wedding", overdue_task_count=0, missing_vendor_count=0, budget_variance=0.25)
    assert alerts[0]["severity"] == "high"
    assert "Budget variance" in alerts[0]["message"]
