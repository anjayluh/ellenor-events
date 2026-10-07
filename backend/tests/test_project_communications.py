from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.communication import ProjectCommunication, ProjectCommunicationRead, ProjectCommunicationRecipient
from app.models.project_member import ProjectMember
from conftest import auth_headers, create_project_with_member, create_user


def add_member(db: Session, project_id, user, role="COMMITTEE_MEMBER") -> ProjectMember:
    member = ProjectMember(project_id=project_id, user_id=user.id, role=role, budget_visibility_mode="NO_ACCESS")
    db.add(member)
    db.flush()
    return member


def create_payload(**overrides):
    payload = {
        "title": "Family meeting update",
        "body": "The family planning meeting will begin at 6pm.",
        "communication_type": "ANNOUNCEMENT",
        "priority": "IMPORTANT",
        "audience_mode": "ALL_MEMBERS",
        "recipient_user_ids": [],
    }
    payload.update(overrides)
    return payload


def test_communications_create_list_summary_read_and_archive(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    member = create_user(db_session, name="Committee Member")
    family_viewer = create_user(db_session, name="Family Viewer")
    guest_viewer = create_user(db_session, name="Guest Viewer")
    project = create_project_with_member(db_session, owner, title="Communications Wedding")
    add_member(db_session, project.id, member)
    add_member(db_session, project.id, family_viewer, role="FAMILY_VIEWER")
    add_member(db_session, project.id, guest_viewer, role="GUEST_VIEWER")
    db_session.commit()

    created = client.post(f"/projects/{project.id}/communications", headers=auth_headers(owner), json=create_payload())
    assert created.status_code == 200
    communication = created.json()
    assert communication["is_read"] is False
    assert communication["author_name"] == "Owner"
    assert communication["recipient_count"] == 3
    assert communication["read_recipient_count"] == 0

    listed = client.get(f"/projects/{project.id}/communications", headers=auth_headers(member))
    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()] == [communication["id"]]

    guest_list = client.get(f"/projects/{project.id}/communications", headers=auth_headers(guest_viewer))
    assert guest_list.status_code == 200
    assert guest_list.json() == []

    summary = client.get(f"/projects/{project.id}/communications/summary", headers=auth_headers(member))
    assert summary.status_code == 200
    assert summary.json()["unread_count"] == 1
    assert summary.json()["total_active"] == 1

    marked = client.post(f"/projects/{project.id}/communications/{communication['id']}/read", headers=auth_headers(member), json={})
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True

    member_summary = client.get(f"/projects/{project.id}/communications/summary", headers=auth_headers(member))
    owner_summary = client.get(f"/projects/{project.id}/communications/summary", headers=auth_headers(owner))
    assert member_summary.json()["unread_count"] == 0
    assert owner_summary.json()["unread_count"] == 1
    assert db_session.query(ProjectCommunicationRead).filter_by(user_id=member.id).count() == 1

    owner_detail = client.get(f"/projects/{project.id}/communications/{communication['id']}", headers=auth_headers(owner))
    assert owner_detail.status_code == 200
    assert owner_detail.json()["read_recipient_count"] == 1
    marked_unread = client.delete(f"/projects/{project.id}/communications/{communication['id']}/read", headers=auth_headers(member))
    assert marked_unread.status_code == 200
    assert marked_unread.json()["is_read"] is False

    archived = client.post(f"/projects/{project.id}/communications/{communication['id']}/archive", headers=auth_headers(owner), json={})
    assert archived.status_code == 200
    assert archived.json()["is_archived"] is True
    edit_archived = client.patch(f"/projects/{project.id}/communications/{communication['id']}", headers=auth_headers(owner), json={"title": "Changed"})
    assert edit_archived.status_code == 409
    history = client.get(f"/projects/{project.id}/communications?status=ARCHIVED", headers=auth_headers(owner))
    assert history.status_code == 200
    assert history.json()[0]["id"] == communication["id"]
    restored = client.post(f"/projects/{project.id}/communications/{communication['id']}/unarchive", headers=auth_headers(owner), json={})
    assert restored.status_code == 200
    assert restored.json()["is_archived"] is False


def test_targeted_communications_validate_recipients_and_isolate_visibility(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    recipient = create_user(db_session, name="Recipient")
    non_recipient = create_user(db_session, name="Non Recipient")
    outsider = create_user(db_session, name="Outsider")
    other_project = create_project_with_member(db_session, outsider, title="Other Event")
    project = create_project_with_member(db_session, owner, title="Targeted Wedding")
    add_member(db_session, project.id, recipient)
    add_member(db_session, project.id, non_recipient)
    db_session.commit()

    cross_event = client.post(
        f"/projects/{project.id}/communications",
        headers=auth_headers(owner),
        json=create_payload(audience_mode="SELECTED_MEMBERS", recipient_user_ids=[str(outsider.id)]),
    )
    assert cross_event.status_code == 422

    created = client.post(
        f"/projects/{project.id}/communications",
        headers=auth_headers(owner),
        json=create_payload(audience_mode="SELECTED_MEMBERS", recipient_user_ids=[str(recipient.id)]),
    )
    assert created.status_code == 200
    communication_id = created.json()["id"]
    assert db_session.query(ProjectCommunicationRecipient).filter_by(communication_id=UUID(communication_id)).count() == 1

    recipient_list = client.get(f"/projects/{project.id}/communications", headers=auth_headers(recipient))
    non_recipient_list = client.get(f"/projects/{project.id}/communications", headers=auth_headers(non_recipient))
    outsider_list = client.get(f"/projects/{other_project.id}/communications", headers=auth_headers(outsider))
    assert len(recipient_list.json()) == 1
    assert recipient_list.json()[0]["recipient_user_ids"] == []
    assert recipient_list.json()[0]["recipient_read_states"] == []
    assert non_recipient_list.json() == []
    assert outsider_list.json() == []

    hidden_detail = client.get(f"/projects/{project.id}/communications/{communication_id}", headers=auth_headers(non_recipient))
    assert hidden_detail.status_code == 404


def test_planning_notes_and_mutation_permissions(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    committee = create_user(db_session, name="Committee")
    family = create_user(db_session, name="Family")
    project = create_project_with_member(db_session, owner, title="Notes Wedding")
    add_member(db_session, project.id, committee)
    add_member(db_session, project.id, family, role="FAMILY_VIEWER")
    db_session.commit()

    note = client.post(
        f"/projects/{project.id}/communications",
        headers=auth_headers(owner),
        json=create_payload(communication_type="PLANNING_NOTE", audience_mode="ALL_MEMBERS"),
    )
    assert note.status_code == 200
    note_id = note.json()["id"]

    assert len(client.get(f"/projects/{project.id}/communications", headers=auth_headers(committee)).json()) == 1
    assert client.get(f"/projects/{project.id}/communications", headers=auth_headers(family)).json() == []

    denied = client.post(
        f"/projects/{project.id}/communications",
        headers=auth_headers(committee),
        json=create_payload(title="Committee draft"),
    )
    assert denied.status_code == 403
    pinned = client.post(f"/projects/{project.id}/communications/{note_id}/pin", headers=auth_headers(owner), json={})
    assert pinned.status_code == 200
    assert pinned.json()["is_pinned"] is True


def test_expired_communications_leave_regular_members_view_but_remain_manager_history(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    member = create_user(db_session, name="Member")
    project = create_project_with_member(db_session, owner, title="Expiry Wedding")
    add_member(db_session, project.id, member)
    db_session.commit()

    expired = client.post(
        f"/projects/{project.id}/communications",
        headers=auth_headers(owner),
        json=create_payload(expires_at=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()),
    )
    assert expired.status_code == 200
    communication_id = expired.json()["id"]

    assert client.get(f"/projects/{project.id}/communications", headers=auth_headers(member)).json() == []
    manager_history = client.get(f"/projects/{project.id}/communications?status=ALL", headers=auth_headers(owner))
    assert manager_history.status_code == 200
    assert manager_history.json()[0]["id"] == communication_id
