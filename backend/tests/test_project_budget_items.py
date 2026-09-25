from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.budget import ProjectBudgetItem
from app.models.project_member import ProjectMember
from app.models.vendor import Vendor
from conftest import auth_headers, create_project_with_member, create_user


def test_authorized_member_can_list_budget_items_and_outsider_is_denied(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    outsider = create_user(db_session, name="Outsider")
    project = create_project_with_member(db_session, owner, title="Budget Wedding")
    db_session.add(ProjectBudgetItem(project_id=project.id, name="Venue", category="Venue", planned_amount=1000000, committed_amount=800000, paid_amount=0, status="COMMITTED"))
    db_session.commit()

    visible = client.get(f"/projects/{project.id}/budget/items", headers=auth_headers(owner))
    hidden = client.get(f"/projects/{project.id}/budget/items", headers=auth_headers(outsider))

    assert visible.status_code == 200
    assert visible.json()[0]["name"] == "Venue"
    assert hidden.status_code == 403


def test_budget_item_crud_search_filter_vendor_link_and_summary(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner, title="Budget Flow Wedding")
    vendor = Vendor(project_id=project.id, name="Elegant Decor", category="Decor", status="confirmed", agreed_amount=1000000, amount_paid=300000, balance_amount=700000)
    db_session.add(vendor)
    db_session.commit()
    headers = auth_headers(owner)

    created = client.post(
        f"/projects/{project.id}/budget",
        headers=headers,
        json={
            "name": "Reception decor",
            "category": "Decor",
            "description": "Stage and reception flowers",
            "vendor_id": str(vendor.id),
            "planned_amount": "1200000",
            "committed_amount": "1000000",
            "paid_amount": "300000",
            "currency": "UGX",
            "due_date": (date.today() + timedelta(days=7)).isoformat(),
            "status": "PARTIALLY_PAID",
            "notes": "Final payment before setup",
        },
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["vendor_name"] == "Elegant Decor"
    assert payload["outstanding_amount"] == "700000.00"

    filtered = client.get(f"/projects/{project.id}/budget/items?search=flowers&category=Decor&status=PARTIALLY_PAID&vendor_id={vendor.id}&payment_filter=unpaid", headers=headers)
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()] == [payload["id"]]

    detail = client.get(f"/projects/{project.id}/budget/{payload['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["name"] == "Reception decor"

    updated = client.patch(
        f"/projects/{project.id}/budget/{payload['id']}",
        headers=headers,
        json={"paid_amount": "1000000", "status": "PAID"},
    )
    assert updated.status_code == 200
    assert updated.json()["outstanding_amount"] == "0.00"

    summary = client.get(f"/projects/{project.id}/budget/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["total_items"] == 1
    assert summary.json()["total_planned"] == "1200000.00"
    assert summary.json()["total_committed"] == "1000000.00"
    assert summary.json()["total_paid"] == "1000000.00"
    assert summary.json()["total_outstanding"] == "0.00"
    assert summary.json()["paid_items"] == 1
    assert summary.json()["paid_percentage"] == 100
    assert summary.json()["category_breakdown"][0]["category"] == "Decor"

    budget = client.get(f"/projects/{project.id}/budget", headers=headers)
    assert budget.status_code == 200
    assert budget.json()["summary"]["total_items"] == 1
    assert budget.json()["items"][0]["vendor_name"] == "Elegant Decor"

    deleted = client.delete(f"/projects/{project.id}/budget/{payload['id']}", headers=headers)
    assert deleted.status_code == 200
    assert db_session.query(ProjectBudgetItem).filter_by(id=UUID(payload["id"])).first() is None


def test_budget_item_financial_validation_rejects_negative_overpayment_and_invalid_status(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner, title="Budget Validation Wedding")
    db_session.commit()
    headers = auth_headers(owner)

    negative = client.post(
        f"/projects/{project.id}/budget",
        headers=headers,
        json={"name": "Cake", "category": "Cake", "planned_amount": "-1", "committed_amount": "0", "paid_amount": "0", "status": "PLANNED"},
    )
    overpaid = client.post(
        f"/projects/{project.id}/budget",
        headers=headers,
        json={"name": "Photo", "category": "Photography", "planned_amount": "100", "committed_amount": "100", "paid_amount": "200", "status": "PAID"},
    )
    inconsistent = client.post(
        f"/projects/{project.id}/budget",
        headers=headers,
        json={"name": "Venue", "category": "Venue", "planned_amount": "100", "committed_amount": "100", "paid_amount": "50", "status": "PAID"},
    )

    assert negative.status_code == 422
    assert overpaid.status_code == 422
    assert inconsistent.status_code == 422


def test_budget_item_rejects_vendor_from_another_project(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    other_owner = create_user(db_session, name="Other Owner")
    project = create_project_with_member(db_session, owner, title="Budget Vendor Wedding")
    other_project = create_project_with_member(db_session, other_owner, title="Other Vendor Wedding")
    vendor = Vendor(project_id=other_project.id, name="Hidden Vendor", category="Decor", status="confirmed")
    db_session.add(vendor)
    db_session.commit()

    response = client.post(
        f"/projects/{project.id}/budget",
        headers=auth_headers(owner),
        json={"name": "Decor", "category": "Decor", "vendor_id": str(vendor.id), "planned_amount": "100", "committed_amount": "0", "paid_amount": "0", "status": "PLANNED"},
    )

    assert response.status_code == 422


def test_cross_project_budget_item_access_is_rejected(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    other_owner = create_user(db_session, name="Other Owner")
    project = create_project_with_member(db_session, owner, title="Protected Budget")
    other_project = create_project_with_member(db_session, other_owner, title="Other Budget")
    item = ProjectBudgetItem(project_id=project.id, name="Hidden Cost", category="Venue", planned_amount=100, committed_amount=100, paid_amount=0, status="COMMITTED")
    db_session.add(item)
    db_session.commit()

    wrong_project = client.patch(
        f"/projects/{other_project.id}/budget/{item.id}",
        headers=auth_headers(other_owner),
        json={"name": "Tampered"},
    )
    outsider_delete = client.delete(f"/projects/{project.id}/budget/{item.id}", headers=auth_headers(other_owner))

    assert wrong_project.status_code == 404
    assert outsider_delete.status_code == 403


def test_committee_member_needs_budget_permission_for_mutation(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    committee = create_user(db_session, name="Committee")
    viewer = create_user(db_session, name="Viewer")
    project = create_project_with_member(db_session, owner, title="Permission Budget Wedding")
    db_session.add(ProjectMember(project_id=project.id, user_id=committee.id, role="COMMITTEE_MEMBER", permissions_level=None, permissions_json={"permissions": ["budget.edit"]}, budget_visibility_mode="FULL_ACCESS"))
    db_session.add(ProjectMember(project_id=project.id, user_id=viewer.id, role="FAMILY_VIEWER", budget_visibility_mode="SUMMARY_ACCESS"))
    db_session.commit()

    allowed = client.post(
        f"/projects/{project.id}/budget",
        headers=auth_headers(committee),
        json={"name": "Transport", "category": "Transport", "planned_amount": "100000", "committed_amount": "0", "paid_amount": "0", "status": "PLANNED"},
    )
    denied = client.post(
        f"/projects/{project.id}/budget",
        headers=auth_headers(viewer),
        json={"name": "Venue", "category": "Venue", "planned_amount": "100000", "committed_amount": "0", "paid_amount": "0", "status": "PLANNED"},
    )
    summary = client.get(f"/projects/{project.id}/budget/summary", headers=auth_headers(viewer))

    assert allowed.status_code == 200
    assert denied.status_code == 403
    assert summary.status_code == 200
