import pytest
from sqlalchemy.orm import Session

from app.models import EntitlementDefinition, PackageEntitlementGrant, PackagePlan, PackagePrice, StaffMember
from app.models.customer_account import AccountEntitlement

from conftest import auth_headers, create_project_with_member, create_user


def create_staff(db: Session, *, role: str = "SUPER_ADMIN", permissions: list[str] | None = None):
    user = create_user(db, name="Catalog Admin")
    db.add(StaffMember(user_id=user.id, role=role, status="active", permissions_json={"permissions": permissions or []}))
    db.flush()
    return user


def seed_entitlement_definitions(db: Session):
    definitions = [
        EntitlementDefinition(key="events", name="Events", description="Event workspaces", value_type="QUANTITY", scope="ACCOUNT", is_usage_tracked=True),
        EntitlementDefinition(key="guests_per_event", name="Guests per event", description="Guest capacity per event", value_type="QUANTITY", scope="EVENT", is_usage_tracked=True),
        EntitlementDefinition(key="budget_management", name="Budget management", description="Budget tools", value_type="BOOLEAN", scope="ACCOUNT", is_usage_tracked=False),
    ]
    db.add_all(definitions)
    db.flush()


def create_package(db: Session, *, code: str, status: str = "ACTIVE", is_public: bool = True) -> PackagePlan:
    package = PackagePlan(code=code, name=code.replace("-", " ").title(), description="Package description", status=status, is_public=is_public, is_add_on=False)
    db.add(package)
    db.flush()
    return package


def add_grant(db: Session, package: PackagePlan, key: str = "events", *, quantity: int | None = 1, value_type: str = "QUANTITY", scope: str = "ACCOUNT") -> PackageEntitlementGrant:
    grant = PackageEntitlementGrant(package_plan_id=package.id, entitlement_key=key, quantity=quantity, value_type=value_type, scope=scope)
    db.add(grant)
    db.flush()
    return grant


def test_public_users_see_only_public_active_packages(client, db_session: Session):
    seed_entitlement_definitions(db_session)
    visible = create_package(db_session, code="visible")
    draft = create_package(db_session, code="draft", status="DRAFT")
    inactive = create_package(db_session, code="inactive", status="INACTIVE")
    internal = create_package(db_session, code="internal", is_public=False)
    for package in [visible, draft, inactive, internal]:
        add_grant(db_session, package)
    db_session.commit()

    response = client.get("/catalog/packages")

    assert response.status_code == 200
    assert [package["code"] for package in response.json()] == ["visible"]


def test_package_detail_respects_visibility_and_status(client, db_session: Session):
    seed_entitlement_definitions(db_session)
    visible = create_package(db_session, code="visible")
    hidden = create_package(db_session, code="hidden", is_public=False)
    add_grant(db_session, visible)
    add_grant(db_session, hidden)
    db_session.commit()

    visible_response = client.get("/catalog/packages/visible")
    hidden_response = client.get("/catalog/packages/hidden")

    assert visible_response.status_code == 200
    assert visible_response.json()["code"] == "visible"
    assert hidden_response.status_code == 404


def test_active_prices_are_public_only_when_package_is_public_and_active(client, db_session: Session):
    seed_entitlement_definitions(db_session)
    package = create_package(db_session, code="priced")
    db_session.add(PackagePrice(package_plan_id=package.id, currency="UGX", amount_minor=250000, billing_interval="ONE_TIME", status="ACTIVE"))
    add_grant(db_session, package)
    db_session.commit()

    visible = client.get("/catalog/packages/priced")
    package.status = "INACTIVE"
    db_session.commit()
    hidden = client.get("/catalog/packages/priced")

    assert visible.status_code == 200
    assert visible.json()["prices"][0]["amount_minor"] == 250000
    assert isinstance(visible.json()["prices"][0]["amount_minor"], int)
    assert hidden.status_code == 404


def test_admin_can_manage_catalog_and_prices(client, db_session: Session):
    seed_entitlement_definitions(db_session)
    admin = create_staff(db_session)
    db_session.commit()

    create_response = client.post(
        "/admin/catalog/packages",
        headers=auth_headers(admin),
        json={"code": "admin-plan", "name": "Admin Plan", "description": "Managed by admin", "status": "ACTIVE", "is_public": True},
    )
    package_id = create_response.json()["id"]
    price_response = client.post(
        f"/admin/catalog/packages/{package_id}/prices",
        headers=auth_headers(admin),
        json={"currency": "UGX", "amount_minor": 120000, "billing_interval": "ONE_TIME", "status": "ACTIVE"},
    )
    grant_response = client.post(
        f"/admin/catalog/packages/{package_id}/grants",
        headers=auth_headers(admin),
        json={"entitlement_key": "events", "scope": "ACCOUNT", "value_type": "QUANTITY", "quantity": 1},
    )

    assert create_response.status_code == 200
    assert price_response.status_code == 200
    assert price_response.json()["amount_minor"] == 120000
    assert grant_response.status_code == 200
    assert grant_response.json()["entitlement_key"] == "events"


def test_catalog_view_admin_can_read_catalog_without_user_admin_permission(client, db_session: Session):
    seed_entitlement_definitions(db_session)
    package = create_package(db_session, code="catalog-viewer-plan")
    add_grant(db_session, package)
    admin = create_staff(db_session, role="SUPPORT_AGENT", permissions=["admin.catalog.view"])
    db_session.commit()

    me_response = client.get("/admin/me", headers=auth_headers(admin))
    catalog_response = client.get("/admin/catalog/packages", headers=auth_headers(admin))
    users_response = client.get("/admin/users", headers=auth_headers(admin))

    assert me_response.status_code == 200
    assert catalog_response.status_code == 200
    assert catalog_response.json()[0]["code"] == "catalog-viewer-plan"
    assert users_response.status_code == 403


def test_unauthorized_users_cannot_mutate_catalog(client, db_session: Session):
    user = create_user(db_session)
    db_session.commit()

    response = client.post(
        "/admin/catalog/packages",
        headers=auth_headers(user),
        json={"code": "blocked", "name": "Blocked", "description": "Should not save"},
    )

    assert response.status_code == 403


def test_package_prices_require_valid_package_and_billing_interval(client, db_session: Session):
    admin = create_staff(db_session)
    db_session.commit()

    missing_package = client.post(
        "/admin/catalog/packages/00000000-0000-0000-0000-000000000000/prices",
        headers=auth_headers(admin),
        json={"currency": "UGX", "amount_minor": 1000, "billing_interval": "ONE_TIME", "status": "ACTIVE"},
    )
    invalid_interval = client.post(
        "/admin/catalog/packages/00000000-0000-0000-0000-000000000000/prices",
        headers=auth_headers(admin),
        json={"currency": "UGX", "amount_minor": 1000, "billing_interval": "WEEKLY", "status": "ACTIVE"},
    )

    assert missing_package.status_code == 404
    assert invalid_interval.status_code == 422


def test_entitlement_grants_validate_definition_duplicates_and_quantities(client, db_session: Session):
    seed_entitlement_definitions(db_session)
    admin = create_staff(db_session)
    package = create_package(db_session, code="grant-plan")
    db_session.commit()

    valid = client.post(
        f"/admin/catalog/packages/{package.id}/grants",
        headers=auth_headers(admin),
        json={"entitlement_key": "events", "scope": "ACCOUNT", "value_type": "QUANTITY", "quantity": 1},
    )
    duplicate = client.post(
        f"/admin/catalog/packages/{package.id}/grants",
        headers=auth_headers(admin),
        json={"entitlement_key": "events", "scope": "ACCOUNT", "value_type": "QUANTITY", "quantity": 2},
    )
    invalid_quantity = client.post(
        f"/admin/catalog/packages/{package.id}/grants",
        headers=auth_headers(admin),
        json={"entitlement_key": "guests_per_event", "scope": "EVENT", "value_type": "QUANTITY", "quantity": 0},
    )
    invalid_boolean = client.post(
        f"/admin/catalog/packages/{package.id}/grants",
        headers=auth_headers(admin),
        json={"entitlement_key": "budget_management", "scope": "ACCOUNT", "value_type": "BOOLEAN", "quantity": 1},
    )
    missing_definition = client.post(
        f"/admin/catalog/packages/{package.id}/grants",
        headers=auth_headers(admin),
        json={"entitlement_key": "advanced_insights", "scope": "ACCOUNT", "value_type": "BOOLEAN"},
    )

    assert valid.status_code == 200
    assert duplicate.status_code == 409
    assert invalid_quantity.status_code == 422
    assert invalid_boolean.status_code == 422
    assert missing_definition.status_code == 404


def test_phase_one_project_and_compatibility_entitlement_still_work(client, db_session: Session):
    owner = create_user(db_session, name="Existing Owner")
    project = create_project_with_member(db_session, owner, title="Existing Event")
    db_session.add(AccountEntitlement(customer_account_id=project.customer_account_id, key="events", quantity=None, used_quantity=0, status="ACTIVE", metadata_json={"source": "compatibility_foundation", "compatibility": True}))
    db_session.flush()
    entitlement_before = db_session.query(AccountEntitlement).filter_by(customer_account_id=project.customer_account_id, key="events").one()
    db_session.commit()

    response = client.get("/projects", headers=auth_headers(owner))
    entitlement_after = db_session.query(AccountEntitlement).filter_by(customer_account_id=project.customer_account_id, key="events").one()

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(project.id)
    assert entitlement_before.quantity is None
    assert entitlement_after.quantity is None
