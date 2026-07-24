from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.models.staff_member import StaffMember
from app.models.vendor_portal import VendorProfile

from conftest import auth_headers, create_project_with_member, create_user


def create_super_admin(db_session: Session):
    user = create_user(db_session, name="Super Admin", email="anjayluh.wakabi@gmail.com")
    db_session.add(
        StaffMember(
            user_id=user.id,
            role="SUPER_ADMIN",
            permissions_json={"permissions": []},
            status="active",
        )
    )
    db_session.commit()
    return user


def test_super_admin_can_grant_staff_permissions_and_view_logs(client, db_session: Session):
    super_admin = create_super_admin(db_session)

    grant = client.post(
        "/admin/staff",
        headers=auth_headers(super_admin),
        json={
            "email": "ops@example.com",
            "role": "OPERATIONS_MANAGER",
            "permissions": ["admin.users.view", "admin.logs.view"],
            "status": "active",
        },
    )

    assert grant.status_code == 200
    assert grant.json()["email"] == "ops@example.com"
    assert grant.json()["permissions"] == ["admin.logs.view", "admin.users.view"]

    users = client.get("/admin/users", headers=auth_headers(super_admin))
    logs = client.get("/admin/logs", headers=auth_headers(super_admin))

    assert users.status_code == 200
    assert logs.status_code == 200
    assert any(log["action"] == "admin.staff_permissions_updated" for log in logs.json())


def test_guest_invites_are_event_rsvp_records_not_project_members(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner, title="Guest Invite Wedding")
    db_session.commit()

    created = client.post(
        f"/projects/{project.id}/guest-invites",
        headers=auth_headers(owner),
        json={
            "guest_name": "Auntie Rose",
            "email": "auntie.rose@example.com",
            "invitation_card_url": "https://example.com/card.png",
        },
    )
    assert created.status_code == 200
    token = created.json()["token"]

    sent = client.post(f"/projects/{project.id}/guest-invites/{created.json()['id']}/send", headers=auth_headers(owner))
    assert sent.status_code == 200
    assert sent.json()["sent_count"] == 1

    response = client.post(f"/guest-invites/{token}/respond", json={"attendance_status": "accepted"})
    assert response.status_code == 200
    assert response.json()["attendance_status"] == "accepted"

    summary = client.get(f"/projects/{project.id}/guest-invites/summary", headers=auth_headers(owner))
    assert summary.status_code == 200
    assert summary.json()["total"] == 1
    assert summary.json()["accepted"] == 1


def test_vendor_profile_marketplace_booking_and_payments(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    vendor = create_user(db_session, name="Vendor", email="vendor@example.com")
    project = create_project_with_member(db_session, owner, title="Vendor Wedding")
    db_session.commit()

    profile = client.put(
        "/vendors/portal/profile",
        headers=auth_headers(vendor),
        json={
            "business_name": "Pearl Decor",
            "category": "decor",
            "contact_email": "hello@pearldecor.example",
            "payment_details": "MTN MoMo +256700000000",
            "bio": "Wedding and introduction ceremony decor.",
        },
    )
    assert profile.status_code == 200

    portfolio = client.post(
        "/vendors/portal/portfolio",
        headers=auth_headers(vendor),
        json={"title": "Purple garden setup", "image_url": "https://example.com/work.jpg"},
    )
    assert portfolio.status_code == 200

    marketplace = client.get("/vendors/marketplace")
    assert marketplace.status_code == 200
    assert marketplace.json()[0]["business_name"] == "Pearl Decor"

    booking = client.post(
        f"/vendors/projects/{project.id}/bookings",
        headers=auth_headers(owner),
        json={
            "vendor_user_id": str(vendor.id),
            "meeting_requested_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
            "meeting_notes": "Discuss decor concept.",
        },
    )
    assert booking.status_code == 200

    payment = client.post(
        f"/vendors/portal/bookings/{booking.json()['id']}/payments",
        headers=auth_headers(vendor),
        json={"amount": 500000, "received_at": date.today().isoformat(), "payment_method": "mobile_money"},
    )
    assert payment.status_code == 200
    assert payment.json()["amount"] == 500000


def test_budget_line_items_expose_tabular_payment_totals(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner, title="Budget Table Wedding")
    db_session.add(Budget(project_id=project.id, total=0, spent=0))
    db_session.commit()

    item = client.post(
        f"/projects/{project.id}/budget/line-items",
        headers=auth_headers(owner),
        json={
            "category": "decor",
            "description": "Stage decor",
            "item_name": "Stage decor",
            "unit_cost": 1200000,
            "quantity": 2,
            "total_cost": 2400000,
            "deposited_amount": 1000000,
            "balance": 1400000,
            "next_deposit_date": date.today().isoformat(),
            "payment_details": "Airtel Money +256700111222",
            "estimated_amount": 2400000,
            "actual_amount": 1000000,
        },
    )
    assert item.status_code == 200
    assert item.json()["item_name"] == "Stage decor"

    budget = client.get(f"/projects/{project.id}/budget", headers=auth_headers(owner))
    assert budget.status_code == 200
    assert budget.json()["line_item_total_cost"] == 2400000
    assert budget.json()["line_item_deposited_total"] == 1000000
    assert budget.json()["line_item_balance_total"] == 1400000
