from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.project_member import ProjectMember
from app.models.task import Task

from conftest import auth_headers, create_project_with_member, create_user


def create_task_record(db: Session, project, *, title="Existing Task", status="TODO", due_date=None, assigned_to=None, priority="MEDIUM", category="GENERAL") -> Task:
    task = Task(project_id=project.id, title=title, status=status, due_date=due_date, assigned_to=assigned_to, priority=priority, category=category)
    db.add(task)
    db.flush()
    return task


def test_authorized_user_creates_task_with_project_assignee(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    assignee = create_user(db_session, name="Committee", email="committee@example.com")
    project = create_project_with_member(db_session, owner, title="Task Wedding")
    db_session.add(ProjectMember(project_id=project.id, user_id=assignee.id, role="COMMITTEE_MEMBER", permissions_level=None, permissions_json={"permissions": []}))
    db_session.commit()

    response = client.post(
        f"/projects/{project.id}/tasks",
        headers=auth_headers(owner),
        json={
            "title": "Confirm family transport",
            "description": "Call both family transport leads.",
            "assigned_to": str(assignee.id),
            "priority": "HIGH",
            "category": "LOGISTICS",
            "due_date": str(date.today() + timedelta(days=2)),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "TODO"
    assert payload["priority"] == "HIGH"
    assert payload["category"] == "LOGISTICS"
    assert payload["assigned_to"] == str(assignee.id)
    assert payload["created_by_user_id"] == str(owner.id)


def test_task_create_rejects_invalid_project_and_invalid_assignee(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    outsider = create_user(db_session, name="Outsider")
    project = create_project_with_member(db_session, owner, title="Assignee Wedding")
    db_session.commit()

    invalid_assignee = client.post(
        f"/projects/{project.id}/tasks",
        headers=auth_headers(owner),
        json={"title": "Assign outsider", "assigned_to": str(outsider.id)},
    )
    invalid_project = client.post(
        f"/projects/{project.id}/tasks",
        headers=auth_headers(outsider),
        json={"title": "Hidden task"},
    )

    assert invalid_assignee.status_code == 422
    assert invalid_project.status_code == 403


def test_task_status_done_and_reopen_manage_completed_at(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner, title="Completion Wedding")
    task = create_task_record(db_session, project, title="Finish program")
    db_session.commit()
    headers = auth_headers(owner)

    done = client.patch(f"/projects/{project.id}/tasks/{task.id}", headers=headers, json={"status": "DONE"})
    assert done.status_code == 200
    assert done.json()["completed_at"] is not None

    reopened = client.patch(f"/projects/{project.id}/tasks/{task.id}", headers=headers, json={"status": "IN_PROGRESS"})
    assert reopened.status_code == 200
    assert reopened.json()["completed_at"] is None


def test_read_only_member_cannot_mutate_and_assignee_can_update_status(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    assignee = create_user(db_session, name="Assignee")
    viewer = create_user(db_session, name="Viewer")
    project = create_project_with_member(db_session, owner, title="Permission Wedding")
    db_session.add(ProjectMember(project_id=project.id, user_id=assignee.id, role="COMMITTEE_MEMBER", permissions_level=None, permissions_json={"permissions": []}))
    db_session.add(ProjectMember(project_id=project.id, user_id=viewer.id, role="FAMILY_VIEWER", permissions_level=None, budget_visibility_mode="SUMMARY_ACCESS", permissions_json={"permissions": []}))
    task = create_task_record(db_session, project, title="Assigned work", assigned_to=assignee.id)
    db_session.commit()

    viewer_update = client.patch(f"/projects/{project.id}/tasks/{task.id}", headers=auth_headers(viewer), json={"status": "DONE"})
    assignee_status = client.patch(f"/projects/{project.id}/tasks/{task.id}", headers=auth_headers(assignee), json={"status": "IN_PROGRESS"})
    viewer_assigned = create_task_record(db_session, project, title="Viewer assigned", assigned_to=viewer.id)
    db_session.commit()
    viewer_assigned_update = client.patch(f"/projects/{project.id}/tasks/{viewer_assigned.id}", headers=auth_headers(viewer), json={"status": "DONE"})

    assert viewer_update.status_code == 403
    assert viewer_assigned_update.status_code == 403
    assert assignee_status.status_code == 200


def test_cross_project_task_access_is_rejected(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    other_owner = create_user(db_session, name="Other")
    project = create_project_with_member(db_session, owner, title="Protected Task Event")
    other_project = create_project_with_member(db_session, other_owner, title="Other Task Event")
    task = create_task_record(db_session, project, title="Protected task")
    db_session.commit()

    wrong_project = client.get(f"/projects/{other_project.id}/tasks/{task.id}", headers=auth_headers(other_owner))
    outsider = client.get(f"/projects/{project.id}/tasks", headers=auth_headers(other_owner))

    assert wrong_project.status_code == 404
    assert outsider.status_code == 403


def test_task_filters_and_my_tasks(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    assignee = create_user(db_session, name="Assignee")
    project = create_project_with_member(db_session, owner, title="Filter Wedding")
    db_session.add(ProjectMember(project_id=project.id, user_id=assignee.id, role="COMMITTEE_MEMBER", permissions_level=None, permissions_json={"permissions": []}))
    matching = create_task_record(db_session, project, title="Call decorator", status="IN_PROGRESS", priority="URGENT", category="DECOR", assigned_to=assignee.id, due_date=date.today() + timedelta(days=1))
    create_task_record(db_session, project, title="Pay venue", status="TODO", priority="LOW", category="VENUE", due_date=date.today() - timedelta(days=1))
    db_session.commit()
    headers = auth_headers(assignee)

    filtered = client.get(
        f"/projects/{project.id}/tasks?search=decorator&status=IN_PROGRESS&priority=URGENT&category=DECOR&my_tasks=true&due_soon=true",
        headers=headers,
    )

    assert filtered.status_code == 200
    assert [task["id"] for task in filtered.json()] == [str(matching.id)]


def test_task_summary_counts(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner, title="Summary Wedding")
    create_task_record(db_session, project, title="Done", status="DONE", due_date=date.today() - timedelta(days=2))
    create_task_record(db_session, project, title="Late", status="TODO", due_date=date.today() - timedelta(days=1))
    create_task_record(db_session, project, title="Soon", status="IN_PROGRESS", due_date=date.today() + timedelta(days=3), assigned_to=owner.id)
    db_session.commit()

    summary = client.get(f"/projects/{project.id}/tasks/summary", headers=auth_headers(owner))

    assert summary.status_code == 200
    payload = summary.json()
    assert payload["total"] == 3
    assert payload["completed"] == 1
    assert payload["todo"] == 1
    assert payload["in_progress"] == 1
    assert payload["overdue"] == 1
    assert payload["due_soon"] == 1
    assert payload["completion_percentage"] == 33
    assert payload["my_tasks"] == 1


def test_authorized_deletion_and_read_only_rejection(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    viewer = create_user(db_session, name="Viewer")
    project = create_project_with_member(db_session, owner, title="Delete Wedding")
    db_session.add(ProjectMember(project_id=project.id, user_id=viewer.id, role="GUEST_VIEWER", permissions_level=None, permissions_json={"permissions": []}))
    task = create_task_record(db_session, project, title="Delete me")
    db_session.commit()

    denied = client.delete(f"/projects/{project.id}/tasks/{task.id}", headers=auth_headers(viewer))
    deleted = client.delete(f"/projects/{project.id}/tasks/{task.id}", headers=auth_headers(owner))

    assert denied.status_code == 403
    assert deleted.status_code == 200
    assert db_session.query(Task).filter_by(id=task.id).first() is None
