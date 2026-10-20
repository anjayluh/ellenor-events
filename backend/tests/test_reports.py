from uuid import uuid4

from app.models.project_guest import ProjectGuest

from conftest import auth_headers, create_project_with_member, create_user


def test_report_summary_and_exports_are_project_scoped(client, db_session):
    user = create_user(db_session)
    project = create_project_with_member(db_session, user, title="Reportable Event")
    db_session.add(ProjectGuest(project_id=project.id, first_name="=SUM(A1)", last_name="Guest", display_name="=SUM(A1) Guest", email="guest@example.com"))
    db_session.commit()

    headers = auth_headers(user)
    summary = client.get(f"/projects/{project.id}/reports/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["title"] == "Reportable Event"
    assert summary.json()["guests"]["total"] == 1

    guests_csv = client.get(f"/projects/{project.id}/reports/exports/guests.csv", headers=headers)
    assert guests_csv.status_code == 200
    assert guests_csv.headers["content-type"].startswith("text/csv")
    assert "'=SUM(A1) Guest" in guests_csv.text

    report_pdf = client.get(f"/projects/{project.id}/reports/export.pdf", headers=headers)
    assert report_pdf.status_code == 200
    assert report_pdf.headers["content-type"].startswith("application/pdf")
    assert report_pdf.content.startswith(b"%PDF-1.4")


def test_empty_event_report_still_generates_a_valid_pdf(client, db_session):
    user = create_user(db_session)
    project = create_project_with_member(db_session, user, title="Empty Event")
    db_session.commit()

    response = client.get(f"/projects/{project.id}/reports/export.pdf", headers=auth_headers(user))

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-1.4")


def test_reports_require_authentication_and_project_membership(client, db_session):
    owner = create_user(db_session)
    outsider = create_user(db_session)
    project = create_project_with_member(db_session, owner)
    db_session.commit()

    assert client.get(f"/projects/{project.id}/reports/summary").status_code == 401
    assert client.get(f"/projects/{project.id}/reports/summary", headers=auth_headers(outsider)).status_code == 403


def test_report_dataset_rejects_unknown_export(client, db_session):
    user = create_user(db_session)
    project = create_project_with_member(db_session, user)
    db_session.commit()

    response = client.get(f"/projects/{project.id}/reports/exports/{uuid4()}.csv", headers=auth_headers(user))

    assert response.status_code == 404


def test_guest_export_uses_existing_guest_management_permission(client, db_session):
    owner = create_user(db_session)
    viewer = create_user(db_session)
    project = create_project_with_member(db_session, owner)
    from app.models.project_member import ProjectMember

    db_session.add(ProjectMember(project_id=project.id, user_id=viewer.id, role="FAMILY_VIEWER", budget_visibility_mode="NO_ACCESS"))
    db_session.commit()

    response = client.get(f"/projects/{project.id}/reports/exports/guests.csv", headers=auth_headers(viewer))

    assert response.status_code == 403
