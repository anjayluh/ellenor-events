from enum import StrEnum

from fastapi import HTTPException, status


class ProjectRole(StrEnum):
    OWNER = "OWNER"
    PARTNER = "PARTNER"
    COMMITTEE_CHAIR = "COMMITTEE_CHAIR"
    COMMITTEE_MEMBER = "COMMITTEE_MEMBER"
    FAMILY_VIEWER = "FAMILY_VIEWER"
    GUEST_VIEWER = "GUEST_VIEWER"


class BudgetVisibilityMode(StrEnum):
    FULL_ACCESS = "FULL_ACCESS"
    SUMMARY_ACCESS = "SUMMARY_ACCESS"
    CONTRIBUTION_ONLY = "CONTRIBUTION_ONLY"
    NO_ACCESS = "NO_ACCESS"


BUDGET_READ_LEVELS = {
    BudgetVisibilityMode.FULL_ACCESS,
    BudgetVisibilityMode.SUMMARY_ACCESS,
    BudgetVisibilityMode.CONTRIBUTION_ONLY,
}

BUDGET_WRITE_ROLES = {ProjectRole.OWNER, ProjectRole.PARTNER}
EVENT_ADMIN_PERMISSION = "event.manage"
BUDGET_EDIT_PERMISSION = "budget.edit"
COMMITTEE_MANAGE_PERMISSION = "committee.manage"
GUEST_INVITES_MANAGE_PERMISSION = "guest_invites.manage"
VENDORS_MANAGE_PERMISSION = "vendors.manage"
MEETINGS_MANAGE_PERMISSION = "meetings.manage"
TASKS_MANAGE_PERMISSION = "tasks.manage"
EVENT_PERMISSION_OPTIONS = {
    EVENT_ADMIN_PERMISSION,
    BUDGET_EDIT_PERMISSION,
    COMMITTEE_MANAGE_PERMISSION,
    GUEST_INVITES_MANAGE_PERMISSION,
    VENDORS_MANAGE_PERMISSION,
    MEETINGS_MANAGE_PERMISSION,
    TASKS_MANAGE_PERMISSION,
}
PROJECT_ADMIN_ROLES = {ProjectRole.OWNER, ProjectRole.PARTNER, ProjectRole.COMMITTEE_CHAIR}
PROJECT_OWNER_ROLES = {ProjectRole.OWNER, ProjectRole.PARTNER}
MEMBER_DELETE_ROLES = {ProjectRole.OWNER, ProjectRole.PARTNER}


def require_role(actual: ProjectRole, allowed: set[ProjectRole]) -> None:
    if actual not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient project permissions")


def require_budget_read(visibility: BudgetVisibilityMode) -> None:
    if visibility not in BUDGET_READ_LEVELS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Budget is not visible for this project role")



def normalize_permissions(raw_permissions: dict | list | None) -> set[str]:
    if raw_permissions is None:
        return set()
    if isinstance(raw_permissions, list):
        values = raw_permissions
    else:
        values = raw_permissions.get("permissions", [])
    return {str(permission) for permission in values if str(permission) in EVENT_PERMISSION_OPTIONS}


def default_permissions_for_role(role: ProjectRole) -> set[str]:
    if role in {ProjectRole.OWNER, ProjectRole.PARTNER}:
        return set(EVENT_PERMISSION_OPTIONS)
    if role == ProjectRole.COMMITTEE_CHAIR:
        return {COMMITTEE_MANAGE_PERMISSION, GUEST_INVITES_MANAGE_PERMISSION, VENDORS_MANAGE_PERMISSION, MEETINGS_MANAGE_PERMISSION, TASKS_MANAGE_PERMISSION}
    if role == ProjectRole.COMMITTEE_MEMBER:
        return {MEETINGS_MANAGE_PERMISSION, TASKS_MANAGE_PERMISSION}
    return set()


def effective_permissions(role: ProjectRole, raw_permissions: dict | list | None) -> set[str]:
    return default_permissions_for_role(role) | normalize_permissions(raw_permissions)


def has_permission(role: ProjectRole, raw_permissions: dict | list | None, permission: str) -> bool:
    return permission in effective_permissions(role, raw_permissions)


def require_permission(actual: ProjectRole, raw_permissions: dict | list | None, allowed_roles: set[ProjectRole], permission: str) -> None:
    if actual in allowed_roles or has_permission(actual, raw_permissions, permission):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient event permissions")
