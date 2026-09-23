from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.api.dependencies import trusted_backend_write
from app.models import (
    AccountEntitlement,
    CustomerSubscription,
    EntitlementDefinition,
    MarketingAccessToken,
    PackageEntitlementGrant,
    PackagePlan,
    PackagePrice,
    PaymentTransaction,
    StaffMember,
)
from app.services.billing_service import cancel_subscription, renew_subscription
from app.services.customer_account_service import add_account_member
from app.services.entitlement_service import active_entitlements, entitlement_is_active
from app.services.payment_provider import get_payment_provider

from conftest import auth_headers, create_project_with_member, create_user


def create_staff(db: Session, *, permissions: list[str] | None = None):
    user = create_user(db, name="Billing Admin")
    db.add(StaffMember(user_id=user.id, role="SUPPORT_AGENT", status="active", permissions_json={"permissions": permissions or []}))
    db.flush()
    return user


def seed_billing_catalog(db: Session, *, package_status: str = "ACTIVE", price_status: str = "ACTIVE"):
    definitions = [
        EntitlementDefinition(key="events", name="Events", description="Events", value_type="QUANTITY", scope="ACCOUNT", is_usage_tracked=True),
        EntitlementDefinition(key="guests_per_event", name="Guests", description="Guests per event", value_type="QUANTITY", scope="EVENT", is_usage_tracked=True),
        EntitlementDefinition(key="budget_management", name="Budget", description="Budget tools", value_type="BOOLEAN", scope="ACCOUNT", is_usage_tracked=False),
    ]
    db.add_all(definitions)
    package = PackagePlan(code="event", name="Event", description="Event package", status=package_status, is_public=True, display_order=1)
    db.add(package)
    db.flush()
    price = PackagePrice(package_plan_id=package.id, currency="UGX", amount_minor=30000, billing_interval="MONTHLY", status=price_status, starts_at=datetime.now(timezone.utc) - timedelta(days=1))
    db.add(price)
    db.flush()
    db.add_all(
        [
            PackageEntitlementGrant(package_plan_id=package.id, entitlement_key="events", scope="ACCOUNT", value_type="QUANTITY", quantity=1),
            PackageEntitlementGrant(package_plan_id=package.id, entitlement_key="guests_per_event", scope="EVENT", value_type="QUANTITY", quantity=300),
            PackageEntitlementGrant(package_plan_id=package.id, entitlement_key="budget_management", scope="ACCOUNT", value_type="BOOLEAN", quantity=None),
        ]
    )
    db.flush()
    return package, price


@pytest.fixture(autouse=True)
def mock_payment_provider(monkeypatch):
    monkeypatch.setattr(settings, "payment_provider", "mock")


def test_authenticated_owner_can_start_checkout_and_server_controls_amount(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    package, price = seed_billing_catalog(db_session)
    db_session.commit()

    response = client.post(
        "/billing/checkout",
        headers=auth_headers(owner),
        json={"package_price_id": str(price.id), "amount_minor": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["amount_minor"] == 30000
    assert payload["package_price_id"] == str(price.id)
    assert payload["checkout_url"].startswith("https://payments.example.test/checkout/")
    transaction = db_session.query(PaymentTransaction).one()
    subscription = db_session.query(CustomerSubscription).one()
    assert transaction.status == "INITIATED"
    assert subscription.status == "INCOMPLETE"
    assert subscription.package_plan_id == package.id


def test_checkout_cannot_target_another_customer_account(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    outsider = create_user(db_session, name="Outsider")
    project = create_project_with_member(db_session, owner)
    _package, price = seed_billing_catalog(db_session)
    db_session.commit()

    response = client.post(
        "/billing/checkout",
        headers=auth_headers(outsider),
        json={"package_price_id": str(price.id), "customer_account_id": str(project.customer_account_id)},
    )

    assert response.status_code == 403


def test_account_member_cannot_checkout_for_account_they_do_not_own(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    member = create_user(db_session, name="Member")
    project = create_project_with_member(db_session, owner)
    add_account_member(db_session, project.customer_account_id, member.id, role="MEMBER")
    _package, price = seed_billing_catalog(db_session)
    db_session.commit()

    response = client.post(
        "/billing/checkout",
        headers=auth_headers(member),
        json={"package_price_id": str(price.id), "customer_account_id": str(project.customer_account_id)},
    )

    assert response.status_code == 403


def test_inactive_package_or_price_is_rejected(client, db_session: Session):
    owner = create_user(db_session)
    _package, inactive_price = seed_billing_catalog(db_session, price_status="INACTIVE")
    db_session.commit()

    response = client.post("/billing/checkout", headers=auth_headers(owner), json={"package_price_id": str(inactive_price.id)})

    assert response.status_code == 409


def test_successful_payment_webhook_activates_subscription_and_entitlements(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner)
    _package, price = seed_billing_catalog(db_session)
    db_session.commit()
    checkout = client.post("/billing/checkout", headers=auth_headers(owner), json={"package_price_id": str(price.id)}).json()

    response = client.post(
        "/billing/webhooks/flutterwave",
        headers={"x-mock-payment-secret": "test-webhook-secret"},
        json={"event_id": "evt-success-1", "data": {"id": "tx-1", "tx_ref": checkout["provider_reference"], "status": "SUCCESSFUL", "amount_minor": 30000, "currency": "UGX"}},
    )
    duplicate = client.post(
        "/billing/webhooks/flutterwave",
        headers={"x-mock-payment-secret": "test-webhook-secret"},
        json={"event_id": "evt-success-1", "data": {"id": "tx-1", "tx_ref": checkout["provider_reference"], "status": "SUCCESSFUL", "amount_minor": 30000, "currency": "UGX"}},
    )

    assert response.status_code == 200
    assert duplicate.status_code == 200
    subscription = db_session.query(CustomerSubscription).one()
    transaction = db_session.query(PaymentTransaction).one()
    paid_entitlements = [entitlement for entitlement in db_session.query(AccountEntitlement).filter_by(customer_account_id=project.customer_account_id, key="events").all() if (entitlement.metadata_json or {}).get("source") == "PAID"]
    assert subscription.status == "ACTIVE"
    assert transaction.status == "SUCCESSFUL"
    assert len(paid_entitlements) == 1
    assert paid_entitlements[0].quantity == 1
    assert active_entitlements(db_session, project.customer_account_id, "events")[0].metadata_json["source"] == "PAID"


def test_failed_and_pending_payment_do_not_activate_paid_access(client, db_session: Session):
    owner = create_user(db_session)
    _package, price = seed_billing_catalog(db_session)
    db_session.commit()
    checkout = client.post("/billing/checkout", headers=auth_headers(owner), json={"package_price_id": str(price.id)}).json()

    pending = client.post(
        "/billing/webhooks/flutterwave",
        headers={"x-mock-payment-secret": "test-webhook-secret"},
        json={"event_id": "evt-pending", "data": {"id": "tx-pending", "tx_ref": checkout["provider_reference"], "status": "PENDING", "amount_minor": 30000, "currency": "UGX"}},
    )
    failed = client.post(
        "/billing/webhooks/flutterwave",
        headers={"x-mock-payment-secret": "test-webhook-secret"},
        json={"event_id": "evt-failed", "data": {"id": "tx-failed", "tx_ref": checkout["provider_reference"], "status": "FAILED", "amount_minor": 30000, "currency": "UGX"}},
    )

    assert pending.status_code == 200
    assert failed.status_code == 200
    subscription = db_session.query(CustomerSubscription).one()
    assert subscription.status == "FAILED"
    assert db_session.query(AccountEntitlement).filter(AccountEntitlement.metadata_json["source"].as_string() == "PAID").count() == 0


def test_invalid_webhook_and_amount_mismatch_are_rejected(client, db_session: Session):
    owner = create_user(db_session)
    _package, price = seed_billing_catalog(db_session)
    db_session.commit()
    checkout = client.post("/billing/checkout", headers=auth_headers(owner), json={"package_price_id": str(price.id)}).json()

    invalid_signature = client.post("/billing/webhooks/flutterwave", json={"event_id": "evt-invalid", "data": {"tx_ref": checkout["provider_reference"], "status": "SUCCESSFUL"}})
    amount_mismatch = client.post(
        "/billing/webhooks/flutterwave",
        headers={"x-mock-payment-secret": "test-webhook-secret"},
        json={"event_id": "evt-mismatch", "data": {"id": "tx-mismatch", "tx_ref": checkout["provider_reference"], "status": "SUCCESSFUL", "amount_minor": 1, "currency": "UGX"}},
    )

    assert invalid_signature.status_code == 401
    assert amount_mismatch.status_code == 409


def test_verified_payment_requires_amount_currency_and_matching_reference(client, db_session: Session):
    owner = create_user(db_session)
    _package, price = seed_billing_catalog(db_session)
    db_session.commit()
    checkout = client.post("/billing/checkout", headers=auth_headers(owner), json={"package_price_id": str(price.id)}).json()

    missing_amount = client.post(
        "/billing/webhooks/flutterwave",
        headers={"x-mock-payment-secret": "test-webhook-secret"},
        json={"event_id": "evt-missing-amount", "data": {"id": "tx-missing-amount", "tx_ref": checkout["provider_reference"], "status": "SUCCESSFUL", "currency": "UGX"}},
    )
    missing_currency = client.post(
        "/billing/webhooks/flutterwave",
        headers={"x-mock-payment-secret": "test-webhook-secret"},
        json={"event_id": "evt-missing-currency", "data": {"id": "tx-missing-currency", "tx_ref": checkout["provider_reference"], "status": "SUCCESSFUL", "amount_minor": 30000}},
    )
    wrong_currency = client.post(
        "/billing/webhooks/flutterwave",
        headers={"x-mock-payment-secret": "test-webhook-secret"},
        json={"event_id": "evt-wrong-currency", "data": {"id": "tx-wrong-currency", "tx_ref": checkout["provider_reference"], "status": "SUCCESSFUL", "amount_minor": 30000, "currency": "USD"}},
    )

    assert missing_amount.status_code == 422
    assert missing_currency.status_code == 422
    assert wrong_currency.status_code == 409
    assert db_session.query(AccountEntitlement).filter(AccountEntitlement.metadata_json["source"].as_string() == "PAID").count() == 0


def test_duplicate_transaction_reference_is_prevented(db_session: Session):
    owner = create_user(db_session)
    project = create_project_with_member(db_session, owner)
    _package, price = seed_billing_catalog(db_session)
    subscription = CustomerSubscription(customer_account_id=project.customer_account_id, package_plan_id=price.package_plan_id, package_price_id=price.id)
    db_session.add(subscription)
    db_session.flush()
    db_session.add(PaymentTransaction(customer_account_id=project.customer_account_id, subscription_id=subscription.id, package_price_id=price.id, amount_minor=30000, currency="UGX", provider="mock", provider_reference="same-ref"))
    db_session.add(PaymentTransaction(customer_account_id=project.customer_account_id, subscription_id=subscription.id, package_price_id=price.id, amount_minor=30000, currency="UGX", provider="mock", provider_reference="same-ref"))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_subscription_cancellation_renewal_and_expiry_are_represented(db_session: Session):
    owner = create_user(db_session)
    project = create_project_with_member(db_session, owner)
    _package, price = seed_billing_catalog(db_session)
    subscription = CustomerSubscription(customer_account_id=project.customer_account_id, package_plan_id=price.package_plan_id, package_price_id=price.id, status="ACTIVE", currency="UGX", amount_minor=30000, billing_interval="MONTHLY", current_period_start=datetime.now(timezone.utc), current_period_end=datetime.now(timezone.utc) + timedelta(days=30))
    db_session.add(subscription)
    db_session.flush()

    cancel_subscription(db_session, subscription, cancel_at_period_end=True)
    previous_end = subscription.current_period_end
    renew_subscription(db_session, subscription)

    assert subscription.cancel_at_period_end is True
    assert subscription.status == "ACTIVE"
    assert subscription.current_period_start == previous_end
    expired = AccountEntitlement(customer_account_id=project.customer_account_id, key="events", quantity=1, status="ACTIVE", starts_at=datetime.now(timezone.utc) - timedelta(days=60), expires_at=datetime.now(timezone.utc) - timedelta(days=1), metadata_json={"source": "PAID"})
    assert not entitlement_is_active(expired)


def test_immediate_cancellation_deactivates_only_subscription_entitlements(db_session: Session):
    owner = create_user(db_session)
    project = create_project_with_member(db_session, owner)
    _package, price = seed_billing_catalog(db_session)
    subscription = CustomerSubscription(
        customer_account_id=project.customer_account_id,
        package_plan_id=price.package_plan_id,
        package_price_id=price.id,
        status="ACTIVE",
        access_source="PAID",
        currency="UGX",
        amount_minor=30000,
        billing_interval="MONTHLY",
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(subscription)
    db_session.flush()
    paid_entitlement = AccountEntitlement(customer_account_id=project.customer_account_id, key="events", quantity=1, status="ACTIVE", metadata_json={"source": "PAID", "subscription_id": str(subscription.id)})
    marketing_entitlement = AccountEntitlement(customer_account_id=project.customer_account_id, key="events", quantity=1, status="ACTIVE", metadata_json={"source": "MARKETING", "subscription_id": "other-subscription"})
    compatibility_entitlement = AccountEntitlement(customer_account_id=project.customer_account_id, key="events", quantity=None, status="ACTIVE", metadata_json={"source": "compatibility_foundation", "compatibility": True})
    db_session.add_all([paid_entitlement, marketing_entitlement, compatibility_entitlement])
    db_session.flush()

    cancel_subscription(db_session, subscription, cancel_at_period_end=False)

    assert subscription.status == "CANCELLED"
    assert paid_entitlement.status == "INACTIVE"
    assert not entitlement_is_active(paid_entitlement)
    assert marketing_entitlement.status == "ACTIVE"
    assert compatibility_entitlement.status == "ACTIVE"


def test_marketing_access_token_redemption_and_duplicate_handling(client, db_session: Session):
    owner = create_user(db_session, email="owner@example.com")
    project = create_project_with_member(db_session, owner)
    package, _price = seed_billing_catalog(db_session)
    admin = create_staff(db_session, permissions=["admin.billing.manage", "admin.billing.view"])
    db_session.commit()
    token_response = client.post(
        "/admin/billing/access-tokens",
        headers=auth_headers(admin),
        json={"code": "ELLENOR-FREE-2026", "package_plan_id": str(package.id), "duration_days": 90, "max_redemptions": 20, "assigned_email": "owner@example.com"},
    )

    redeem = client.post("/billing/access-tokens/redeem", headers=auth_headers(owner), json={"code": "ELLENOR-FREE-2026", "customer_account_id": str(project.customer_account_id)})
    duplicate = client.post("/billing/access-tokens/redeem", headers=auth_headers(owner), json={"code": "ELLENOR-FREE-2026", "customer_account_id": str(project.customer_account_id)})

    assert token_response.status_code == 200
    assert redeem.status_code == 200
    assert redeem.json()["access_source"] == "MARKETING"
    assert duplicate.status_code == 409
    token = db_session.query(MarketingAccessToken).filter_by(code="ELLENOR-FREE-2026").one()
    assert token.redemption_count == 1


def test_marketing_access_token_db_limit_is_not_exceeded(client, db_session: Session):
    owner = create_user(db_session, email="owner-limit@example.com")
    second_owner = create_user(db_session, email="second-limit@example.com")
    first_project = create_project_with_member(db_session, owner)
    second_project = create_project_with_member(db_session, second_owner)
    package, _price = seed_billing_catalog(db_session)
    admin = create_staff(db_session, permissions=["admin.billing.manage", "admin.billing.view"])
    db_session.commit()
    create_response = client.post(
        "/admin/billing/access-tokens",
        headers=auth_headers(admin),
        json={"code": "ONE-USE", "package_plan_id": str(package.id), "duration_days": 30, "max_redemptions": 1},
    )
    first = client.post("/billing/access-tokens/redeem", headers=auth_headers(owner), json={"code": "ONE-USE", "customer_account_id": str(first_project.customer_account_id)})
    second = client.post("/billing/access-tokens/redeem", headers=auth_headers(second_owner), json={"code": "ONE-USE", "customer_account_id": str(second_project.customer_account_id)})

    assert create_response.status_code == 200
    assert first.status_code == 200
    assert second.status_code == 409
    token = db_session.query(MarketingAccessToken).filter_by(code="ONE-USE").one()
    assert token.redemption_count == 1


def test_marketing_access_token_rejects_expired_exhausted_and_wrong_email(client, db_session: Session):
    owner = create_user(db_session, email="owner@example.com")
    wrong_user = create_user(db_session, email="wrong@example.com")
    project = create_project_with_member(db_session, owner)
    package, _price = seed_billing_catalog(db_session)
    expired = MarketingAccessToken(code="EXPIRED", package_plan_id=package.id, duration_days=30, expires_at=datetime.now(timezone.utc) - timedelta(days=1), status="ACTIVE")
    exhausted = MarketingAccessToken(code="EXHAUSTED", package_plan_id=package.id, duration_days=30, max_redemptions=1, redemption_count=1, status="ACTIVE")
    assigned = MarketingAccessToken(code="ASSIGNED", package_plan_id=package.id, duration_days=30, assigned_email="owner@example.com", status="ACTIVE")
    db_session.add_all([expired, exhausted, assigned])
    db_session.commit()

    assert client.post("/billing/access-tokens/redeem", headers=auth_headers(owner), json={"code": "EXPIRED", "customer_account_id": str(project.customer_account_id)}).status_code == 409
    assert client.post("/billing/access-tokens/redeem", headers=auth_headers(owner), json={"code": "EXHAUSTED", "customer_account_id": str(project.customer_account_id)}).status_code == 409
    assert client.post("/billing/access-tokens/redeem", headers=auth_headers(wrong_user), json={"code": "ASSIGNED", "customer_account_id": str(project.customer_account_id)}).status_code in {403, 409}


def test_unauthorized_admin_and_user_cannot_mark_payment_successful(client, db_session: Session):
    user = create_user(db_session)
    package, _price = seed_billing_catalog(db_session)
    db_session.commit()

    create_token = client.post("/admin/billing/access-tokens", headers=auth_headers(user), json={"code": "NOPE", "package_plan_id": str(package.id), "duration_days": 30})
    fake_success = client.post("/billing/webhooks/flutterwave", json={"event_id": "fake", "data": {"tx_ref": "any", "status": "SUCCESSFUL"}})

    assert create_token.status_code == 403
    assert fake_success.status_code == 401


def test_mock_provider_is_rejected_in_production(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "payment_provider", "mock")

    with pytest.raises(Exception):
        get_payment_provider()


def test_billing_hardening_migration_removes_client_insert_policies():
    migration = (Path(__file__).resolve().parents[2] / "supabase/migrations/202609220004_phase3_security_hardening.sql").read_text(encoding="utf-8")

    assert "drop policy if exists customer_subscriptions_customer_checkout_insert" in migration
    assert "drop policy if exists payment_transactions_customer_checkout_insert" in migration
    assert "create policy customer_subscriptions_customer_checkout_insert" not in migration
    assert "create policy payment_transactions_customer_checkout_insert" not in migration


def test_trusted_backend_write_temporarily_resets_authenticated_rls_context(monkeypatch):
    class FakeDialect:
        name = "postgresql"

    class FakeBind:
        dialect = FakeDialect()

    class FakeSession:
        def __init__(self):
            self.info = {"supabase_rls_applied": True, "supabase_rls_user_id": "00000000-0000-0000-0000-000000000001"}
            self.statements: list[str] = []

        def get_bind(self):
            return FakeBind()

        def execute(self, statement, params=None):
            self.statements.append(str(statement))

    fake_session = FakeSession()
    monkeypatch.setattr(settings, "auth_provider", "supabase")
    monkeypatch.setattr(settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(settings, "supabase_anon_key", "anon")

    with trusted_backend_write(fake_session):
        fake_session.statements.append("trusted write")

    assert fake_session.statements[0] == "reset role"
    assert fake_session.statements[1] == "trusted write"
    assert any("set local role authenticated" in statement for statement in fake_session.statements)
