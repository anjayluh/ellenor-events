from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.customer_account import CustomerAccount, CustomerAccountMember
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.project_settings import ProjectSettings
from app.models.user import User
from app.schemas.project import ProjectCreate
from app.services.entitlement_service import EVENTS_ENTITLEMENT_KEY, assert_entitlement_allows_usage, consume_entitlement_usage


def account_display_name(user: User) -> str:
    base = user.name or user.email or user.phone or "Ellenor Events Customer"
    return f"{base} Account"


def create_customer_account(db: Session, *, owner_user: User, name: str | None = None, status_value: str = "ACTIVE") -> CustomerAccount:
    account = CustomerAccount(name=name or account_display_name(owner_user), status=status_value)
    db.add(account)
    db.flush()
    add_account_member(db, account.id, owner_user.id, role="OWNER")
    return account


def add_account_member(db: Session, customer_account_id: UUID, user_id: UUID, *, role: str = "MEMBER", status_value: str = "ACTIVE") -> CustomerAccountMember:
    existing = (
        db.query(CustomerAccountMember)
        .filter(CustomerAccountMember.customer_account_id == customer_account_id, CustomerAccountMember.user_id == user_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already belongs to this customer account")
    member = CustomerAccountMember(customer_account_id=customer_account_id, user_id=user_id, role=role, status=status_value)
    db.add(member)
    db.flush()
    return member


def active_account_membership(db: Session, customer_account_id: UUID, user_id: UUID) -> CustomerAccountMember | None:
    return (
        db.query(CustomerAccountMember)
        .filter(
            CustomerAccountMember.customer_account_id == customer_account_id,
            CustomerAccountMember.user_id == user_id,
            CustomerAccountMember.status == "ACTIVE",
        )
        .first()
    )


def require_account_member(db: Session, customer_account_id: UUID, user_id: UUID) -> CustomerAccountMember:
    membership = active_account_membership(db, customer_account_id, user_id)
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer account access required")
    return membership


def list_user_account_memberships(db: Session, user_id: UUID) -> list[tuple[CustomerAccount, CustomerAccountMember]]:
    return (
        db.query(CustomerAccount, CustomerAccountMember)
        .join(CustomerAccountMember, CustomerAccountMember.customer_account_id == CustomerAccount.id)
        .filter(CustomerAccountMember.user_id == user_id, CustomerAccountMember.status == "ACTIVE")
        .order_by(CustomerAccount.created_at.asc())
        .all()
    )


def get_or_create_primary_account_for_user(db: Session, user: User) -> CustomerAccount:
    rows = list_user_account_memberships(db, user.id)
    owner_accounts = [account for account, membership in rows if membership.role == "OWNER" and account.status in {"LEAD", "ACTIVE"}]
    if owner_accounts:
        return owner_accounts[0]
    return create_customer_account(db, owner_user=user)


def list_account_projects(db: Session, customer_account_id: UUID) -> list[Project]:
    return db.query(Project).filter(Project.customer_account_id == customer_account_id).order_by(Project.created_at.desc()).all()


def create_project_for_account(db: Session, *, owner: User, payload: ProjectCreate) -> tuple[Project, ProjectMember]:
    account = get_or_create_primary_account_for_user(db, owner)
    entitlement = assert_entitlement_allows_usage(db, account.id, EVENTS_ENTITLEMENT_KEY)
    project = Project(**payload.model_dump(), customer_account_id=account.id, owner_user_id=owner.id)
    db.add(project)
    db.flush()
    membership = ProjectMember(
        project_id=project.id,
        user_id=owner.id,
        role="OWNER",
        permissions_level="admin",
        budget_visibility_mode="FULL_ACCESS",
    )
    db.add(membership)
    db.add(ProjectSettings(project_id=project.id))
    consume_entitlement_usage(db, entitlement)
    db.flush()
    return project, membership
