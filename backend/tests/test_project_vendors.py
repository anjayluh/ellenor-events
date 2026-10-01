from uuid import UUID

from sqlalchemy.orm import Session

from app.models.budget import ProjectBudgetItem
from app.models.project_member import ProjectMember
from app.models.vendor import Vendor
from app.services.entitlement_service import create_entitlement

from conftest import auth_headers, create_project_with_member, create_user


def add_vendor_entitlement(db: Session, project, *, quantity: int | None = 20):
    return create_entitlement(db, project.customer_account_id, "vendors_per_event", quantity=quantity, metadata={"source": "MARKETING", "test": True})


def test_authorized_member_can_list_vendors_and_outsider_is_denied(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    outsider = create_user(db_session, name="Outsider")
    project = create_project_with_member(db_session, owner, title="Vendor Wedding")
    db_session.add(Vendor(project_id=project.id, name="Pearl Decor", category="DECOR", status="SHORTLISTED"))
    db_session.commit()

    visible = client.get(f"/projects/{project.id}/vendors", headers=auth_headers(owner))
    hidden = client.get(f"/projects/{project.id}/vendors", headers=auth_headers(outsider))

    assert visible.status_code == 200
    assert visible.json()[0]["name"] == "Pearl Decor"
    assert hidden.status_code == 403


def test_vendor_crud_search_filter_detail_and_budget_derived_summary(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner, title="Vendor Flow Wedding")
    add_vendor_entitlement(db_session, project, quantity=3)
    db_session.commit()
    headers = auth_headers(owner)

    created = client.post(
        f"/projects/{project.id}/vendors",
        headers=headers,
        json={
            "name": "Elegant Decor House",
            "category": "Decor",
            "contact_person": "Amina",
            "phone": "+256700111222",
            "email": "decor@example.com",
            "website": "https://decor.example.com",
            "service_description": "Stage, reception flowers, and backdrop.",
            "status": "contacted",
            "notes": "Purple and gold theme",
        },
    )
    assert created.status_code == 200
    vendor = created.json()
    assert vendor["category"] == "DECOR"
    assert vendor["status"] == "CONTACTED"
    assert vendor["financial_summary"]["outstanding_total"] == "0.00"

    db_session.add(
        ProjectBudgetItem(
            project_id=project.id,
            vendor_id=UUID(vendor["id"]),
            name="Decor package",
            category="Decor",
            planned_amount=1200000,
            committed_amount=1000000,
            actual_amount=900000,
            paid_amount=300000,
            status="PARTIALLY_PAID",
        )
    )
    db_session.commit()

    filtered = client.get(f"/projects/{project.id}/vendors?search=amina&category=Decor&status=CONTACTED&outstanding=true", headers=headers)
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()] == [vendor["id"]]
    assert filtered.json()[0]["financial_summary"]["outstanding_total"] == "600000.00"

    detail = client.get(f"/projects/{project.id}/vendors/{vendor['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["contact_person"] == "Amina"
    assert detail.json()["budget_items"][0]["name"] == "Decor package"

    updated = client.patch(
        f"/projects/{project.id}/vendors/{vendor['id']}",
        headers=headers,
        json={"status": "CONFIRMED", "address": "Kampala", "event_day_contact": "Amina setup lead"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "CONFIRMED"
    assert updated.json()["address"] == "Kampala"

    summary = client.get(f"/projects/{project.id}/vendors/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["total"] == 1
    assert summary.json()["confirmed"] == 1
    assert summary.json()["needs_attention"] == 0
    assert summary.json()["with_outstanding_balance"] == 1
    assert summary.json()["outstanding_balance"] == "600000.00"
    assert summary.json()["planned_total"] == "1200000.00"
    assert summary.json()["actual_total"] == "900000.00"
    assert summary.json()["vendor_usage"] == {"key": "vendors_per_event", "label": "Vendors", "used": 1, "limit": 3, "remaining": 2}

    blocked_delete = client.delete(f"/projects/{project.id}/vendors/{vendor['id']}", headers=headers)
    assert blocked_delete.status_code == 409

    budget_item = db_session.query(ProjectBudgetItem).filter_by(vendor_id=UUID(vendor["id"])).one()
    db_session.delete(budget_item)
    db_session.commit()
    deleted = client.delete(f"/projects/{project.id}/vendors/{vendor['id']}", headers=headers)
    assert deleted.status_code == 200
    assert db_session.query(Vendor).filter_by(id=UUID(vendor["id"])).first() is None


def test_vendor_creation_requires_vendor_entitlement(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner, title="No Vendor Package")
    db_session.commit()

    response = client.post(
        f"/projects/{project.id}/vendors",
        headers=auth_headers(owner),
        json={"name": "Sound Team", "category": "PA_SOUND"},
    )

    assert response.status_code == 402
    assert response.json()["detail"]["code"] == "VENDOR_ENTITLEMENT_REQUIRED"


def test_vendor_creation_rejects_exhausted_entitlement(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner, title="Limited Vendor Wedding")
    add_vendor_entitlement(db_session, project, quantity=1)
    db_session.add(Vendor(project_id=project.id, name="Existing Decor", category="DECOR", status="CONFIRMED"))
    db_session.commit()

    response = client.post(
        f"/projects/{project.id}/vendors",
        headers=auth_headers(owner),
        json={"name": "Second Decor", "category": "DECOR"},
    )

    assert response.status_code == 402
    assert response.json()["detail"]["code"] == "VENDOR_ENTITLEMENT_REQUIRED"


def test_vendor_validation_rejects_invalid_category_status_and_email(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner, title="Validation Vendor Wedding")
    add_vendor_entitlement(db_session, project)
    db_session.commit()
    headers = auth_headers(owner)

    invalid_category = client.post(f"/projects/{project.id}/vendors", headers=headers, json={"name": "Mystery Studio", "category": "Unknown Service"})
    invalid_status = client.post(f"/projects/{project.id}/vendors", headers=headers, json={"name": "Photo Studio", "category": "PHOTOGRAPHY", "status": "won"})
    invalid_email = client.post(f"/projects/{project.id}/vendors", headers=headers, json={"name": "Cake Studio", "category": "CAKE", "email": "not-email"})

    assert invalid_category.status_code == 422
    assert invalid_status.status_code == 422
    assert invalid_email.status_code == 422


def test_cross_project_vendor_access_is_rejected(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    other_owner = create_user(db_session, name="Other Owner")
    project = create_project_with_member(db_session, owner, title="Protected Vendors")
    other_project = create_project_with_member(db_session, other_owner, title="Other Vendors")
    add_vendor_entitlement(db_session, project)
    add_vendor_entitlement(db_session, other_project)
    vendor = Vendor(project_id=project.id, name="Hidden Caterer", category="CATERING", status="SHORTLISTED")
    db_session.add(vendor)
    db_session.commit()

    wrong_project = client.patch(
        f"/projects/{other_project.id}/vendors/{vendor.id}",
        headers=auth_headers(other_owner),
        json={"name": "Tampered"},
    )
    outsider_delete = client.delete(f"/projects/{project.id}/vendors/{vendor.id}", headers=auth_headers(other_owner))

    assert wrong_project.status_code == 404
    assert outsider_delete.status_code == 403


def test_committee_member_needs_vendor_permission_for_mutation(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    committee = create_user(db_session, name="Committee")
    project = create_project_with_member(db_session, owner, title="Permission Vendor Wedding")
    add_vendor_entitlement(db_session, project)
    db_session.add(ProjectMember(project_id=project.id, user_id=committee.id, role="COMMITTEE_MEMBER", permissions_level=None, permissions_json={"permissions": ["vendors.manage"]}))
    db_session.commit()

    response = client.post(
        f"/projects/{project.id}/vendors",
        headers=auth_headers(committee),
        json={"name": "Hair Studio", "category": "MAKEUP_BEAUTY"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Hair Studio"
