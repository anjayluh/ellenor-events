from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.customer_account import AccountEntitlement, CustomerAccount, CustomerAccountMember
from app.models.project_member import ProjectMember
from app.services.customer_account_service import add_account_member, create_customer_account, list_account_projects
from app.services.entitlement_service import active_entitlements, create_entitlement, entitlement_is_active

from conftest import auth_headers, create_project_with_member, create_user


def test_create_customer_account_adds_owner_without_paid_era_compatibility_entitlement(db_session: Session):
    owner = create_user(db_session, name="Customer Owner")

    account = create_customer_account(db_session, owner_user=owner, name="Nakasero Wedding Account")

    membership = db_session.query(CustomerAccountMember).filter_by(customer_account_id=account.id, user_id=owner.id).one()
    assert account.name == "Nakasero Wedding Account"
    assert account.status == "ACTIVE"
    assert membership.role == "OWNER"
    assert membership.status == "ACTIVE"
    assert db_session.query(AccountEntitlement).filter_by(customer_account_id=account.id, key="events").count() == 0


def test_add_account_members_and_prevent_duplicates(db_session: Session):
    owner = create_user(db_session, name="Owner")
    member = create_user(db_session, name="Planner")
    account = create_customer_account(db_session, owner_user=owner)

    account_member = add_account_member(db_session, account.id, member.id, role="MEMBER")

    assert account_member.role == "MEMBER"
    with pytest.raises(HTTPException) as exc:
        add_account_member(db_session, account.id, member.id, role="MEMBER")
    assert exc.value.status_code == 409


def test_projects_are_associated_with_customer_accounts(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner, title="Account Wedding")
    db_session.commit()

    accounts = client.get("/customer-accounts", headers=auth_headers(owner))

    assert accounts.status_code == 200
    payload = accounts.json()
    assert len(payload) == 1
    assert payload[0]["membership"]["role"] == "OWNER"
    assert payload[0]["projects"][0]["id"] == str(project.id)
    assert payload[0]["projects"][0]["customer_account_id"] == str(project.customer_account_id)


def test_account_users_see_only_their_account_projects(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    member = create_user(db_session, name="Account Member")
    outsider = create_user(db_session, name="Outsider")
    account_project = create_project_with_member(db_session, owner, title="Visible Account Event")
    other_project = create_project_with_member(db_session, outsider, title="Other Customer Event")
    add_account_member(db_session, account_project.customer_account_id, member.id, role="MEMBER")
    db_session.commit()

    visible = client.get(f"/customer-accounts/{account_project.customer_account_id}/projects", headers=auth_headers(member))
    denied = client.get(f"/customer-accounts/{other_project.customer_account_id}/projects", headers=auth_headers(member))

    assert visible.status_code == 200
    assert [project["id"] for project in visible.json()] == [str(account_project.id)]
    assert denied.status_code == 403


def test_account_membership_does_not_replace_event_membership(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    account_member = create_user(db_session, name="Billing Helper")
    project = create_project_with_member(db_session, owner, title="Event Permission Wedding")
    add_account_member(db_session, project.customer_account_id, account_member.id, role="MEMBER")
    db_session.commit()

    account_projects = client.get(f"/customer-accounts/{project.customer_account_id}/projects", headers=auth_headers(account_member))
    event_detail = client.get(f"/projects/{project.id}", headers=auth_headers(account_member))

    assert account_projects.status_code == 200
    assert event_detail.status_code == 403


def test_entitlement_lookup_status_and_expiry_behavior(db_session: Session):
    owner = create_user(db_session, name="Owner")
    account = create_customer_account(db_session, owner_user=owner)
    now = datetime.now(timezone.utc)
    expired = create_entitlement(
        db_session,
        account.id,
        "advanced_insights",
        quantity=1,
        status_value="ACTIVE",
        starts_at=now - timedelta(days=10),
        expires_at=now - timedelta(days=1),
    )
    active = create_entitlement(
        db_session,
        account.id,
        "guests",
        quantity=100,
        used_quantity=25,
        status_value="ACTIVE",
        starts_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=30),
    )
    inactive = create_entitlement(db_session, account.id, "vendors", quantity=3, status_value="INACTIVE")

    assert not entitlement_is_active(expired, now=now)
    assert entitlement_is_active(active, now=now)
    assert not entitlement_is_active(inactive, now=now)
    assert active_entitlements(db_session, account.id, "guests", now=now) == [active]
    assert active_entitlements(db_session, account.id, "advanced_insights", now=now) == []


def test_new_account_without_paid_or_marketing_entitlement_cannot_create_event(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    db_session.commit()

    response = client.post(
        "/projects",
        headers=auth_headers(owner),
        json={"type": "wedding", "title": "Entitled Wedding", "event_date": None},
    )

    assert response.status_code == 402


def test_legacy_compatibility_account_can_create_event(client, db_session: Session):
    owner = create_user(db_session, name="Legacy Owner")
    account = create_customer_account(db_session, owner_user=owner)
    create_entitlement(db_session, account.id, "events", quantity=None, metadata={"source": "compatibility_foundation", "compatibility": True})
    db_session.commit()

    response = client.post(
        "/projects",
        headers=auth_headers(owner),
        json={"type": "wedding", "title": "Legacy Wedding", "event_date": None},
    )

    assert response.status_code == 200
    project = response.json()
    entitlement = db_session.query(AccountEntitlement).filter_by(customer_account_id=account.id, key="events").one()
    assert project["customer_account_id"] == str(account.id)
    assert entitlement.used_quantity == 1


def test_new_account_with_marketing_entitlement_can_create_event(client, db_session: Session):
    owner = create_user(db_session, name="Marketing Owner")
    account = create_customer_account(db_session, owner_user=owner)
    create_entitlement(db_session, account.id, "events", quantity=1, metadata={"source": "MARKETING", "subscription_id": "marketing-sub"})
    db_session.commit()

    response = client.post(
        "/projects",
        headers=auth_headers(owner),
        json={"type": "wedding", "title": "Marketing Wedding", "event_date": None},
    )

    assert response.status_code == 200
    entitlement = db_session.query(AccountEntitlement).filter_by(customer_account_id=account.id, key="events").one()
    assert entitlement.used_quantity == 1


def test_new_account_with_paid_entitlement_can_create_event(client, db_session: Session):
    owner = create_user(db_session, name="Paid Owner")
    account = create_customer_account(db_session, owner_user=owner)
    create_entitlement(db_session, account.id, "events", quantity=1, metadata={"source": "PAID", "subscription_id": "paid-sub"})
    db_session.commit()

    response = client.post(
        "/projects",
        headers=auth_headers(owner),
        json={"type": "wedding", "title": "Paid Wedding", "event_date": None},
    )

    assert response.status_code == 200
    entitlement = db_session.query(AccountEntitlement).filter_by(customer_account_id=account.id, key="events").one()
    assert entitlement.used_quantity == 1


def test_entitlement_precedence_prefers_paid_over_compatibility(db_session: Session):
    owner = create_user(db_session)
    account = create_customer_account(db_session, owner_user=owner)
    compatibility = create_entitlement(db_session, account.id, "events", quantity=None, metadata={"source": "compatibility_foundation", "compatibility": True})
    paid = create_entitlement(db_session, account.id, "events", quantity=1, metadata={"source": "PAID", "subscription_id": "paid-sub"})

    assert active_entitlements(db_session, account.id, "events")[0] == paid
    assert active_entitlements(db_session, account.id, "events")[-1] == compatibility


def test_entitlement_precedence_prefers_marketing_over_compatibility(db_session: Session):
    owner = create_user(db_session)
    account = create_customer_account(db_session, owner_user=owner)
    compatibility = create_entitlement(db_session, account.id, "events", quantity=None, metadata={"source": "compatibility_foundation", "compatibility": True})
    marketing = create_entitlement(db_session, account.id, "events", quantity=1, metadata={"source": "MARKETING", "subscription_id": "marketing-sub"})

    assert active_entitlements(db_session, account.id, "events")[0] == marketing
    assert active_entitlements(db_session, account.id, "events")[-1] == compatibility


def test_entitlement_precedence_prefers_paid_over_marketing(db_session: Session):
    owner = create_user(db_session)
    account = create_customer_account(db_session, owner_user=owner)
    marketing = create_entitlement(db_session, account.id, "events", quantity=1, metadata={"source": "MARKETING", "subscription_id": "marketing-sub"})
    paid = create_entitlement(db_session, account.id, "events", quantity=1, metadata={"source": "PAID", "subscription_id": "paid-sub"})

    assert active_entitlements(db_session, account.id, "events")[0] == paid
    assert active_entitlements(db_session, account.id, "events")[1] == marketing


def test_existing_event_permissions_continue_to_work(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    committee = create_user(db_session, name="Committee")
    project = create_project_with_member(db_session, owner, title="Committee Event")
    db_session.add(ProjectMember(project_id=project.id, user_id=committee.id, role="COMMITTEE_MEMBER", budget_visibility_mode="NO_ACCESS"))
    db_session.commit()

    response = client.get(f"/projects/{project.id}", headers=auth_headers(committee))

    assert response.status_code == 200
    assert response.json()["role"] == "COMMITTEE_MEMBER"
