from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.budget import Budget, BudgetLineItem, Contribution
from app.models.invite import Invite
from app.models.meeting import Meeting
from app.models.project_member import ProjectMember
from app.services.invite_service import generate_invite_token

from conftest import auth_headers, create_project_with_member, create_user


def test_auth_rejects_missing_and_tampered_bearer_tokens(client):
    unauthenticated = client.get("/projects")
    assert unauthenticated.status_code == 401

    tampered = client.get("/projects", headers={"Authorization": "Bearer not-a-real-token"})
    assert tampered.status_code == 401


def test_project_list_is_scoped_to_current_membership(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    outsider = create_user(db_session, name="Outsider")
    visible_project = create_project_with_member(db_session, owner, title="Visible Wedding")
    create_project_with_member(db_session, outsider, title="Hidden Introduction")
    db_session.commit()

    response = client.get("/projects", headers=auth_headers(owner))

    assert response.status_code == 200
    projects = response.json()
    assert [project["id"] for project in projects] == [str(visible_project.id)]
    assert projects[0]["title"] == "Visible Wedding"


def test_cross_project_member_meeting_and_budget_access_is_denied(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    outsider = create_user(db_session, name="Outsider")
    protected_project = create_project_with_member(db_session, owner, title="Protected Wedding")
    create_project_with_member(db_session, outsider, title="Outsider Event")
    meeting = Meeting(
        project_id=protected_project.id,
        created_by=owner.id,
        type="committee",
        title="Private Committee Meeting",
        scheduled_time=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(meeting)
    db_session.add(Budget(project_id=protected_project.id, total=25_000_000, spent=5_000_000))
    db_session.commit()

    headers = auth_headers(outsider)

    assert client.get(f"/projects/{protected_project.id}", headers=headers).status_code == 403
    assert client.get(f"/projects/{protected_project.id}/members", headers=headers).status_code == 403
    assert client.get(f"/projects/{protected_project.id}/meetings", headers=headers).status_code == 403
    assert client.get(f"/projects/{protected_project.id}/budget", headers=headers).status_code == 403
    assert client.get(f"/projects/{protected_project.id}/meetings/{meeting.id}", headers=headers).status_code == 403


def test_budget_visibility_modes_do_not_leak_sensitive_fields(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    summary_user = create_user(db_session, name="Summary Viewer")
    contribution_user = create_user(db_session, name="Contribution Viewer")
    no_access_user = create_user(db_session, name="No Access Viewer")
    project = create_project_with_member(db_session, owner, title="Budget Wedding")
    db_session.add_all(
        [
            ProjectMember(
                project_id=project.id,
                user_id=summary_user.id,
                role="FAMILY_VIEWER",
                budget_visibility_mode="SUMMARY_ACCESS",
            ),
            ProjectMember(
                project_id=project.id,
                user_id=contribution_user.id,
                role="GUEST_VIEWER",
                budget_visibility_mode="CONTRIBUTION_ONLY",
            ),
            ProjectMember(
                project_id=project.id,
                user_id=no_access_user.id,
                role="GUEST_VIEWER",
                budget_visibility_mode="NO_ACCESS",
            ),
            Budget(project_id=project.id, total=42_000_000, spent=7_500_000),
            BudgetLineItem(
                project_id=project.id,
                category="Catering",
                description="Reception catering",
                estimated_amount=16_000_000,
                actual_amount=4_500_000,
                status="approved",
            ),
            Contribution(project_id=project.id, contributor="Committee", pledged=12_000_000, paid=4_500_000),
        ]
    )
    db_session.commit()

    full = client.get(f"/projects/{project.id}/budget", headers=auth_headers(owner)).json()
    summary = client.get(f"/projects/{project.id}/budget", headers=auth_headers(summary_user)).json()
    contribution = client.get(f"/projects/{project.id}/budget", headers=auth_headers(contribution_user)).json()
    no_access = client.get(f"/projects/{project.id}/budget", headers=auth_headers(no_access_user))

    assert full["total"] == 42_000_000
    assert full["spent"] == 7_500_000
    assert len(full["line_items"]) == 1
    assert len(full["contributions"]) == 1

    assert summary["total"] == 42_000_000
    assert summary["contribution_progress"] == 4_500_000
    assert summary["spent"] is None
    assert summary["remaining"] is None
    assert summary["line_items"] is None
    assert summary["contributions"] is None

    assert contribution["total"] is None
    assert contribution["spent"] is None
    assert contribution["remaining"] is None
    assert contribution["contribution_progress"] == 4_500_000
    assert contribution["line_items"] is None
    assert contribution["contributions"] is None

    assert no_access.status_code == 403


def test_invite_create_open_accept_and_reuse_protection(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner, title="Invite Wedding")
    db_session.commit()

    create_response = client.post(
        "/invites",
        headers=auth_headers(owner),
        json={
            "project_id": str(project.id),
            "contact": "+256700123456",
            "role_assigned": "COMMITTEE_MEMBER",
            "delivery_channel": "whatsapp",
        },
    )
    assert create_response.status_code == 200
    invite_payload = create_response.json()
    token = invite_payload["invite_link"].rsplit("/", 1)[-1]

    opened = client.get(f"/invites/{token}")
    assert opened.status_code == 200
    assert opened.json()["opened_count"] == 1

    accepted = client.post(
        "/invites/accept",
        json={"token": token, "name": "Committee Member", "phone": "+256700123456"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["role"] == "COMMITTEE_MEMBER"

    reused = client.post(
        "/invites/accept",
        json={"token": token, "name": "Replay", "phone": "+256700123456"},
    )
    assert reused.status_code == 409


def test_expired_invite_cannot_be_accepted(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner, title="Expired Invite Wedding")
    token = generate_invite_token()
    db_session.add(
        Invite(
            project_id=project.id,
            contact="+256700654321",
            role_assigned="COMMITTEE_MEMBER",
            token=token,
            status="pending",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
    )
    db_session.commit()

    response = client.post(
        "/invites/accept",
        json={"token": token, "name": "Late Guest", "phone": "+256700654321"},
    )

    assert response.status_code == 410


def test_meeting_create_list_rsvp_flow(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner, title="Meeting Wedding")
    db_session.commit()
    scheduled_time = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()

    created = client.post(
        f"/projects/{project.id}/meetings",
        headers=auth_headers(owner),
        json={
            "type": "committee",
            "title": "Budget Alignment",
            "agenda": "Review supplier payments",
            "scheduled_time": scheduled_time,
        },
    )
    assert created.status_code == 200
    meeting_id = created.json()["id"]

    listed = client.get(f"/projects/{project.id}/meetings", headers=auth_headers(owner))
    assert listed.status_code == 200
    assert [meeting["id"] for meeting in listed.json()] == [meeting_id]

    rsvp = client.post(
        f"/projects/{project.id}/meetings/{meeting_id}/rsvp",
        headers=auth_headers(owner),
        json={"status": "attending", "comment": "I will bring notes"},
    )
    assert rsvp.status_code == 200
    assert rsvp.json()["status"] == "attending"


def test_member_role_changes_protect_last_owner(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner, title="Owner Lockout Wedding")
    member = db_session.query(ProjectMember).filter_by(project_id=project.id, user_id=owner.id).one()
    db_session.commit()

    response = client.patch(
        f"/projects/{project.id}/members/{member.id}",
        headers=auth_headers(owner),
        json={"role": "COMMITTEE_CHAIR"},
    )

    assert response.status_code == 409
