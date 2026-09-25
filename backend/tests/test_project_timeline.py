from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.project_member import ProjectMember
from app.models.timeline import ProjectTimelineItem
from conftest import auth_headers, create_project_with_member, create_user


def iso(dt: datetime) -> str:
    return dt.isoformat()


def make_payload(start: datetime, end: datetime, **overrides):
    payload = {
        "title": "Introduction ceremony",
        "description": "Formal family introduction",
        "category": "CEREMONY",
        "start_at": iso(start),
        "end_at": iso(end),
        "location": "Introduction venue",
        "status": "UPCOMING",
        "notes": "Keep elders seated near the front.",
        "sort_order": 10,
    }
    payload.update(overrides)
    return payload


def test_timeline_crud_filters_and_summary(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    assignee = create_user(db_session, name="Grace", email="grace@example.com")
    project = create_project_with_member(db_session, owner, title="Timeline Wedding")
    db_session.add(ProjectMember(project_id=project.id, user_id=assignee.id, role="COMMITTEE_MEMBER", permissions_level=None, budget_visibility_mode="NO_ACCESS"))
    db_session.commit()
    start = datetime.now(timezone.utc) + timedelta(days=1, hours=2)
    end = start + timedelta(hours=1)
    headers = auth_headers(owner)

    created = client.post(f"/projects/{project.id}/timeline", headers=headers, json=make_payload(start, end, assignee_user_id=str(assignee.id)))
    assert created.status_code == 200
    item = created.json()
    assert item["title"] == "Introduction ceremony"
    assert item["assignee_name"] == "Grace"
    assert item["duration_minutes"] == 60

    filtered = client.get(f"/projects/{project.id}/timeline?search=family&category=CEREMONY&status=UPCOMING&assignee={assignee.id}&date={start.date().isoformat()}&upcoming=true", headers=headers)
    assert filtered.status_code == 200
    assert [row["id"] for row in filtered.json()] == [item["id"]]

    detail = client.get(f"/projects/{project.id}/timeline/{item['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["location"] == "Introduction venue"

    updated = client.patch(f"/projects/{project.id}/timeline/{item['id']}", headers=headers, json={"status": "COMPLETED", "location": "Reception venue"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "COMPLETED"
    assert updated.json()["location"] == "Reception venue"

    summary = client.get(f"/projects/{project.id}/timeline/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["total"] == 1
    assert summary.json()["completed"] == 1
    assert summary.json()["cancelled"] == 0

    deleted = client.delete(f"/projects/{project.id}/timeline/{item['id']}", headers=headers)
    assert deleted.status_code == 200
    assert db_session.query(ProjectTimelineItem).filter_by(id=UUID(item["id"])).first() is None


def test_timeline_validation_rejects_bad_time_and_bad_assignee(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    outsider = create_user(db_session, name="Outsider")
    project = create_project_with_member(db_session, owner, title="Validation Timeline")
    db_session.commit()
    start = datetime.now(timezone.utc) + timedelta(days=1)
    headers = auth_headers(owner)

    missing_title = client.post(f"/projects/{project.id}/timeline", headers=headers, json=make_payload(start, start + timedelta(hours=1), title=""))
    bad_range = client.post(f"/projects/{project.id}/timeline", headers=headers, json=make_payload(start, start - timedelta(minutes=1)))
    bad_assignee = client.post(f"/projects/{project.id}/timeline", headers=headers, json=make_payload(start, start + timedelta(hours=1), assignee_user_id=str(outsider.id)))

    assert missing_title.status_code == 422
    assert bad_range.status_code == 422
    assert bad_assignee.status_code == 422


def test_timeline_permissions_and_cross_project_access(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    viewer = create_user(db_session, name="Viewer")
    other_owner = create_user(db_session, name="Other Owner")
    committee = create_user(db_session, name="Committee")
    project = create_project_with_member(db_session, owner, title="Permission Timeline")
    other_project = create_project_with_member(db_session, other_owner, title="Other Timeline")
    start = datetime.now(timezone.utc) + timedelta(days=2)
    item = ProjectTimelineItem(project_id=project.id, title="Private schedule", category="PROGRAM", start_at=start, end_at=start + timedelta(hours=1), status="UPCOMING")
    db_session.add(item)
    db_session.add(ProjectMember(project_id=project.id, user_id=viewer.id, role="FAMILY_VIEWER", budget_visibility_mode="NO_ACCESS"))
    db_session.add(ProjectMember(project_id=project.id, user_id=committee.id, role="COMMITTEE_MEMBER", permissions_json={"permissions": ["tasks.manage"]}, budget_visibility_mode="NO_ACCESS"))
    db_session.commit()

    view = client.get(f"/projects/{project.id}/timeline", headers=auth_headers(viewer))
    denied_mutation = client.post(f"/projects/{project.id}/timeline", headers=auth_headers(viewer), json=make_payload(start, start + timedelta(hours=1), title="Viewer edit"))
    allowed_mutation = client.post(f"/projects/{project.id}/timeline", headers=auth_headers(committee), json=make_payload(start + timedelta(hours=2), start + timedelta(hours=3), title="Committee schedule"))
    wrong_project = client.patch(f"/projects/{other_project.id}/timeline/{item.id}", headers=auth_headers(other_owner), json={"title": "Tampered"})
    outsider_delete = client.delete(f"/projects/{project.id}/timeline/{item.id}", headers=auth_headers(other_owner))

    assert view.status_code == 200
    assert denied_mutation.status_code == 403
    assert allowed_mutation.status_code == 200
    assert wrong_project.status_code == 404
    assert outsider_delete.status_code == 403


def test_timeline_conflict_detection_overlaps_touching_and_cancelled_items(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner, title="Conflict Timeline")
    base = datetime.now(timezone.utc) + timedelta(days=3)
    db_session.add_all(
        [
            ProjectTimelineItem(project_id=project.id, title="A", category="PROGRAM", start_at=base, end_at=base + timedelta(hours=1), status="UPCOMING"),
            ProjectTimelineItem(project_id=project.id, title="B", category="PROGRAM", start_at=base + timedelta(minutes=30), end_at=base + timedelta(hours=2), status="UPCOMING"),
            ProjectTimelineItem(project_id=project.id, title="C", category="PROGRAM", start_at=base + timedelta(hours=2), end_at=base + timedelta(hours=3), status="UPCOMING"),
            ProjectTimelineItem(project_id=project.id, title="Cancelled", category="PROGRAM", start_at=base, end_at=base + timedelta(hours=2), status="CANCELLED"),
        ]
    )
    db_session.commit()

    headers = auth_headers(owner)
    rows = client.get(f"/projects/{project.id}/timeline", headers=headers).json()
    conflict_rows = client.get(f"/projects/{project.id}/timeline?conflicts=true", headers=headers).json()
    summary = client.get(f"/projects/{project.id}/timeline/summary", headers=headers).json()

    conflicts_by_title = {row["title"]: row["has_conflict"] for row in rows}
    assert conflicts_by_title["A"] is True
    assert conflicts_by_title["B"] is True
    assert conflicts_by_title["C"] is False
    assert conflicts_by_title["Cancelled"] is False
    assert {row["title"] for row in conflict_rows} == {"A", "B"}
    assert summary["conflicts"] == 2


def test_timeline_today_and_current_summary(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner, title="Today Timeline")
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            ProjectTimelineItem(project_id=project.id, title="Current item", category="PROGRAM", start_at=now - timedelta(minutes=10), end_at=now + timedelta(minutes=50), status="UPCOMING"),
            ProjectTimelineItem(project_id=project.id, title="Next item", category="PROGRAM", start_at=now + timedelta(hours=2), end_at=now + timedelta(hours=3), status="UPCOMING"),
        ]
    )
    db_session.commit()

    response = client.get(f"/projects/{project.id}/timeline/summary", headers=auth_headers(owner))

    assert response.status_code == 200
    payload = response.json()
    assert payload["today"] >= 2
    assert payload["in_progress"] == 1
    assert payload["current_item"]["title"] == "Current item"
    assert payload["next_item"]["title"] == "Next item"
