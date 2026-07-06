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
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import (
    AuditLog,
    AuthChallenge,
    Budget,
    BudgetLineItem,
    BudgetProposal,
    Contribution,
    Invite,
    Meeting,
    MeetingRsvp,
    Notification,
    NotificationPreference,
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
)


@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(type_, compiler, **kw):
    return "JSON"


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
    project = Project(type="wedding", title=title, owner_user_id=user.id)
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
