from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import create_access_token
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.customer_account_service import get_or_create_primary_account_for_user
from app.models import (
    AuditLog,
    AuthChallenge,
    BillingCustomer,
    Budget,
    BudgetLineItem,
    BudgetProposal,
    AccountEntitlement,
    EntitlementDefinition,
    CustomerAccount,
    CustomerAccountMember,
    CustomerSubscription,
    Contribution,
    GuestInvite,
    Invite,
    Meeting,
    MeetingRsvp,
    MarketingAccessToken,
    MarketingAccessTokenRedemption,
    Notification,
    NotificationPreference,
    PackageEntitlementGrant,
    PackagePlan,
    PackagePrice,
    PaymentEvent,
    PaymentTransaction,
    Participant,
    Project,
    ProjectLink,
    ProjectMember,
    ProjectSettings,
    StaffMember,
    Task,
    Testimonial,
    User,
    Vendor,
    VendorBooking,
    VendorPayment,
    VendorPortfolioItem,
    VendorProfile,
)


@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(type_, compiler, **kw):
    return "JSON"


@pytest.fixture(autouse=True)
def isolated_test_settings(monkeypatch):
    monkeypatch.setattr(settings, "auth_provider", "local")
    monkeypatch.setattr(settings, "supabase_url", None)
    monkeypatch.setattr(settings, "supabase_anon_key", None)
    monkeypatch.setattr(settings, "database_url", None)
    monkeypatch.setattr(settings, "database_pooler_url", None)
    monkeypatch.setattr(settings, "postgres_prisma_url", None)
    monkeypatch.setattr(settings, "postgres_url", None)
    monkeypatch.setattr(settings, "postgres_url_non_pooling", None)
    monkeypatch.setattr(settings, "supabase_db_url", None)
    monkeypatch.setattr(settings, "environment", "test")
    yield


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_user(db: Session, *, name: str = "Test User", phone: str | None = None, email: str | None = None) -> User:
    unique = uuid4().hex[:8]
    user = User(name=name, phone=phone or f"+256700{unique[:6]}", email=email or f"user-{unique}@example.com")
    db.add(user)
    db.flush()
    return user


def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def create_project_with_member(
    db: Session,
    user: User,
    *,
    title: str = "QA Wedding",
    role: str = "OWNER",
    budget_visibility_mode: str = "FULL_ACCESS",
) -> Project:
    account = get_or_create_primary_account_for_user(db, user)
    project = Project(type="wedding", title=title, customer_account_id=account.id, owner_user_id=user.id)
    db.add(project)
    db.flush()
    db.add(
        ProjectMember(
            project_id=project.id,
            user_id=user.id,
            role=role,
            permissions_level="admin" if role in {"OWNER", "PARTNER", "COMMITTEE_CHAIR"} else None,
            budget_visibility_mode=budget_visibility_mode,
        )
    )
    db.add(ProjectSettings(project_id=project.id))
    db.flush()
    return project
