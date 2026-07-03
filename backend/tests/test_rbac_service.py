from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.dependencies import CurrentUser, get_project_membership
from app.core.permissions import ProjectRole
from app.models.user import User
from app.models.project_member import ProjectMember
from app.services import rbac_service


class CountQuery:
    def __init__(self, owner_count: int):
        self.owner_count = owner_count

    def filter(self, *args):
        return self

    def count(self):
        return self.owner_count


class FakeDb:
    def __init__(self, owner_count: int):
        self.owner_count = owner_count

    def query(self, model):
        return CountQuery(self.owner_count)


def make_member(role: ProjectRole) -> ProjectMember:
    return ProjectMember(project_id=uuid4(), user_id=uuid4(), role=role.value, budget_visibility_mode="FULL_ACCESS")


def test_last_owner_cannot_be_demoted():
    member = make_member(ProjectRole.OWNER)
    with pytest.raises(HTTPException) as exc_info:
        rbac_service.ensure_not_last_owner_change(FakeDb(owner_count=1), member, next_role=ProjectRole.PARTNER)
    assert exc_info.value.status_code == 409


def test_owner_can_be_demoted_when_another_owner_exists():
    member = make_member(ProjectRole.OWNER)
    rbac_service.ensure_not_last_owner_change(FakeDb(owner_count=2), member, next_role=ProjectRole.PARTNER)


def test_non_owner_delete_does_not_trigger_owner_lockout():
    member = make_member(ProjectRole.COMMITTEE_MEMBER)
    rbac_service.ensure_not_last_owner_change(FakeDb(owner_count=1), member)


class EmptyMembershipQuery:
    def filter(self, *args):
        return self

    def first(self):
        return None


class EmptyMembershipDb:
    def query(self, model):
        return EmptyMembershipQuery()


def test_project_membership_denies_non_member_access():
    user = User(id=uuid4(), phone="+256700000999")
    with pytest.raises(HTTPException) as exc_info:
        get_project_membership(project_id=uuid4(), current_user=CurrentUser(user), db=EmptyMembershipDb())
    assert exc_info.value.status_code == 403
