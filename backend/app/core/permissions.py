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
PROJECT_ADMIN_ROLES = {ProjectRole.OWNER, ProjectRole.PARTNER, ProjectRole.COMMITTEE_CHAIR}
PROJECT_OWNER_ROLES = {ProjectRole.OWNER, ProjectRole.PARTNER}
MEMBER_DELETE_ROLES = {ProjectRole.OWNER, ProjectRole.PARTNER}


def require_role(actual: ProjectRole, allowed: set[ProjectRole]) -> None:
    if actual not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient project permissions")


def require_budget_read(visibility: BudgetVisibilityMode) -> None:
    if visibility not in BUDGET_READ_LEVELS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Budget is not visible for this project role")
