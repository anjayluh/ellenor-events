from datetime import datetime, timedelta, timezone

from app.models.project_member import ProjectMember
from conftest import auth_headers, create_project_with_member, create_user


def future_window(days: int = 2):
    start = datetime.now(timezone.utc) + timedelta(days=days)
    return start, start + timedelta(hours=1)


def meeting_payload(title: str, start: datetime, end: datetime):
    return {
        "title": title,
        "category": "COMMITTEE",
        "start_at": start.isoformat(),
        "end_at": end.isoformat(),
        "description": "Coordinate the planning team",
        "location": "Family room",
    }


def test_meeting_collaboration_records_and_follow_up_task(client, db_session):
    owner = create_user(db_session, name="Meeting Owner")
    member = create_user(db_session, name="Committee Member")
    project = create_project_with_member(db_session, owner, title="Collaboration Wedding")
    db_session.add(ProjectMember(project_id=project.id, user_id=member.id, role="COMMITTEE_MEMBER"))
    db_session.commit()
    start, end = future_window()

    created = client.post(f"/projects/{project.id}/meetings", headers=auth_headers(owner), json=meeting_payload("Planning Circle", start, end))
    assert created.status_code == 200
    meeting_id = created.json()["id"]

    participant = client.post(f"/projects/{project.id}/meetings/{meeting_id}/participants", headers=auth_headers(owner), json={"user_id": str(member.id), "attendance_status": "INVITED"})
    assert participant.status_code == 201
    assert participant.json()["user_id"] == str(member.id)

    agenda = client.post(f"/projects/{project.id}/meetings/{meeting_id}/agenda", headers=auth_headers(owner), json={"title": "Confirm responsibilities"})
    assert agenda.status_code == 201

    decision = client.post(f"/projects/{project.id}/meetings/{meeting_id}/decisions", headers=auth_headers(owner), json={"decision_text": "Use the shared event checklist"})
    assert decision.status_code == 201

    notes = client.patch(f"/projects/{project.id}/meetings/{meeting_id}/notes", headers=auth_headers(owner), json={"notes": "Bring the latest supplier updates."})
    assert notes.status_code == 200

    task = client.post(f"/projects/{project.id}/meetings/{meeting_id}/tasks", headers=auth_headers(owner), json={"title": "Share supplier checklist", "category": "COMMITTEE"})
    assert task.status_code == 201
    assert task.json()["meeting_id"] == meeting_id

    detail = client.get(f"/projects/{project.id}/meetings/{meeting_id}", headers=auth_headers(owner))
    assert detail.status_code == 200
    assert len(detail.json()["participants"]) == 1
    assert detail.json()["agenda_items"][0]["title"] == "Confirm responsibilities"
    assert detail.json()["decisions"][0]["decision_text"] == "Use the shared event checklist"
    assert detail.json()["follow_up_tasks"][0]["title"] == "Share supplier checklist"


def test_meeting_rejects_invalid_time_and_cross_project_participant(client, db_session):
    owner = create_user(db_session, name="Meeting Owner")
    outside = create_user(db_session, name="Outside Member")
    project = create_project_with_member(db_session, owner, title="Scoped Wedding")
    other_project = create_project_with_member(db_session, outside, title="Other Wedding")
    db_session.commit()
    start, end = future_window()

    invalid = client.post(f"/projects/{project.id}/meetings", headers=auth_headers(owner), json=meeting_payload("Bad timing", end, start))
    assert invalid.status_code == 422

    valid = client.post(f"/projects/{project.id}/meetings", headers=auth_headers(owner), json=meeting_payload("Scoped meeting", start, end))
    assert valid.status_code == 200
    meeting_id = valid.json()["id"]
    rejected = client.post(f"/projects/{project.id}/meetings/{meeting_id}/participants", headers=auth_headers(owner), json={"user_id": str(outside.id)})
    assert rejected.status_code == 422
    assert other_project.id != project.id


def test_meeting_summary_reports_conflicts_and_touching_items_do_not_conflict(client, db_session):
    owner = create_user(db_session, name="Summary Owner")
    project = create_project_with_member(db_session, owner, title="Summary Wedding")
    db_session.commit()
    start, end = future_window()
    first = client.post(f"/projects/{project.id}/meetings", headers=auth_headers(owner), json=meeting_payload("First", start, end))
    assert first.status_code == 200
    touching = client.post(f"/projects/{project.id}/meetings", headers=auth_headers(owner), json=meeting_payload("Touching", end, end + timedelta(hours=1)))
    assert touching.status_code == 200
    overlap = client.post(f"/projects/{project.id}/meetings", headers=auth_headers(owner), json=meeting_payload("Overlap", start + timedelta(minutes=30), end + timedelta(minutes=30)))
    assert overlap.status_code == 200
    first_detail = client.get(f"/projects/{project.id}/meetings/{first.json()['id']}", headers=auth_headers(owner))
    touching_detail = client.get(f"/projects/{project.id}/meetings/{touching.json()['id']}", headers=auth_headers(owner))
    assert first_detail.json()["conflict_ids"] == [overlap.json()["id"]]
    assert touching_detail.json()["conflict_ids"] == [overlap.json()["id"]]
    summary = client.get(f"/projects/{project.id}/meetings/summary", headers=auth_headers(owner))
    assert summary.status_code == 200
    assert summary.json()["total"] == 3
    assert summary.json()["conflicts"] == 3
