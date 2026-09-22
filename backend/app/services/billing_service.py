from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.config import settings
from app.models.billing import CustomerSubscription, MarketingAccessToken, MarketingAccessTokenRedemption, PaymentEvent, PaymentTransaction
from app.models.catalog import PackagePlan, PackagePrice
from app.models.customer_account import AccountEntitlement
from app.models.customer_account import CustomerAccountMember
from app.models.user import User
from app.schemas.billing import MarketingAccessTokenCreate, MarketingAccessTokenUpdate
from app.services.catalog_service import price_is_current
from app.services.customer_account_service import get_or_create_primary_account_for_user, require_account_member
from app.services.package_entitlement_service import get_package_grants
from app.services.payment_provider import PaymentProvider, get_payment_provider


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def comparable_time(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def add_period(start: datetime, billing_interval: str) -> datetime:
    if billing_interval == "YEARLY":
        return start + timedelta(days=365)
    if billing_interval == "ONE_TIME":
        return start + timedelta(days=365)
    return start + timedelta(days=30)


def require_account_owner(db: Session, customer_account_id: UUID, user_id: UUID) -> CustomerAccountMember:
    membership = require_account_member(db, customer_account_id, user_id)
    if membership.role != "OWNER":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer account owner access required")
    return membership


def resolve_owned_account(db: Session, current_user: CurrentUser, customer_account_id: UUID | None):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authenticated user does not exist")
    if customer_account_id:
        require_account_owner(db, customer_account_id, current_user.id)
        return customer_account_id
    account = get_or_create_primary_account_for_user(db, user)
    return account.id


def get_price_with_package_or_404(db: Session, package_price_id: UUID) -> tuple[PackagePrice, PackagePlan]:
    row = (
        db.query(PackagePrice, PackagePlan)
        .join(PackagePlan, PackagePlan.id == PackagePrice.package_plan_id)
        .filter(PackagePrice.id == package_price_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package price not found")
    return row


def validate_checkout_price(price: PackagePrice, package: PackagePlan) -> None:
    if package.status != "ACTIVE" or not package.is_public:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Package is not available for checkout")
    if not price_is_current(price):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Package price is not available for checkout")


def create_checkout(
    db: Session,
    *,
    current_user: CurrentUser,
    package_price_id: UUID,
    customer_account_id: UUID | None = None,
    provider: PaymentProvider | None = None,
) -> tuple[CustomerSubscription, PaymentTransaction]:
    account_id = resolve_owned_account(db, current_user, customer_account_id)
    price, package = get_price_with_package_or_404(db, package_price_id)
    validate_checkout_price(price, package)
    subscription = CustomerSubscription(
        customer_account_id=account_id,
        package_plan_id=package.id,
        package_price_id=price.id,
        status="INCOMPLETE",
        access_source="PAID",
        currency=price.currency,
        amount_minor=price.amount_minor,
        billing_interval=price.billing_interval,
        provider=(provider or get_payment_provider()).name,
        metadata_json={"package_code": package.code},
    )
    db.add(subscription)
    db.flush()
    provider_reference = f"ellenor-{subscription.id.hex}-{uuid4().hex[:8]}"
    transaction = PaymentTransaction(
        customer_account_id=account_id,
        subscription_id=subscription.id,
        package_price_id=price.id,
        amount_minor=price.amount_minor,
        currency=price.currency,
        provider=subscription.provider,
        provider_reference=provider_reference,
        status="INITIATED",
        metadata_json={"package_plan_id": str(package.id), "package_code": package.code},
    )
    db.add(transaction)
    db.flush()
    active_provider = provider or get_payment_provider(subscription.provider)
    session = active_provider.create_checkout_session(
        transaction_id=transaction.id,
        provider_reference=provider_reference,
        amount_minor=transaction.amount_minor,
        currency=transaction.currency,
        customer_email=current_user.email,
        redirect_url=settings.checkout_redirect_url,
        metadata={"subscription_id": str(subscription.id), "customer_account_id": str(account_id)},
    )
    transaction.checkout_url = session.checkout_url
    transaction.metadata_json = {**(transaction.metadata_json or {}), "provider_payload": session.provider_payload}
    transaction.updated_at = now_utc()
    db.flush()
    return subscription, transaction


def source_matches_subscription(entitlement: AccountEntitlement, subscription: CustomerSubscription) -> bool:
    return (entitlement.metadata_json or {}).get("subscription_id") == str(subscription.id)


def activate_subscription_entitlements(db: Session, subscription: CustomerSubscription) -> list[AccountEntitlement]:
    activated: list[AccountEntitlement] = []
    grants = get_package_grants(db, subscription.package_plan_id)
    for grant in grants:
        quantity = grant.quantity
        if grant.value_type == "BOOLEAN":
            quantity = 1
        existing = None
        for entitlement in db.query(AccountEntitlement).filter(AccountEntitlement.customer_account_id == subscription.customer_account_id, AccountEntitlement.key == grant.entitlement_key).with_for_update().all():
            if source_matches_subscription(entitlement, subscription):
                existing = entitlement
                break
        if not existing:
            existing = AccountEntitlement(customer_account_id=subscription.customer_account_id, key=grant.entitlement_key, used_quantity=0)
            db.add(existing)
        existing.quantity = quantity
        existing.status = "ACTIVE"
        existing.starts_at = subscription.current_period_start
        existing.expires_at = subscription.current_period_end
        existing.metadata_json = {
            "source": subscription.access_source,
            "subscription_id": str(subscription.id),
            "package_plan_id": str(subscription.package_plan_id),
            "package_price_id": str(subscription.package_price_id) if subscription.package_price_id else None,
            "scope": grant.scope,
            "value_type": grant.value_type,
            "grant_id": str(grant.id),
        }
        existing.updated_at = now_utc()
        activated.append(existing)
    db.flush()
    return activated


def deactivate_subscription_entitlements(db: Session, subscription: CustomerSubscription) -> None:
    current = now_utc()
    entitlements = db.query(AccountEntitlement).filter(AccountEntitlement.customer_account_id == subscription.customer_account_id).with_for_update().all()
    for entitlement in entitlements:
        if source_matches_subscription(entitlement, subscription):
            entitlement.status = "INACTIVE"
            entitlement.expires_at = current
            entitlement.updated_at = current
    db.flush()


def activate_subscription(db: Session, subscription: CustomerSubscription, *, period_start: datetime | None = None, period_end: datetime | None = None) -> CustomerSubscription:
    start = period_start or now_utc()
    end = period_end or add_period(start, subscription.billing_interval)
    subscription.status = "ACTIVE"
    subscription.started_at = subscription.started_at or start
    subscription.current_period_start = start
    subscription.current_period_end = end
    subscription.ended_at = None
    subscription.updated_at = now_utc()
    activate_subscription_entitlements(db, subscription)
    db.flush()
    return subscription


def renew_subscription(db: Session, subscription: CustomerSubscription, *, period_end: datetime | None = None) -> CustomerSubscription:
    start = subscription.current_period_end or now_utc()
    end = period_end or add_period(start, subscription.billing_interval)
    subscription.current_period_start = start
    subscription.current_period_end = end
    subscription.status = "ACTIVE"
    subscription.updated_at = now_utc()
    activate_subscription_entitlements(db, subscription)
    db.flush()
    return subscription


def cancel_subscription(db: Session, subscription: CustomerSubscription, *, cancel_at_period_end: bool = True) -> CustomerSubscription:
    subscription.cancel_at_period_end = cancel_at_period_end
    subscription.cancelled_at = now_utc()
    if not cancel_at_period_end:
        subscription.status = "CANCELLED"
        subscription.ended_at = subscription.cancelled_at
        deactivate_subscription_entitlements(db, subscription)
    subscription.updated_at = now_utc()
    db.flush()
    return subscription


def list_account_subscriptions(db: Session, customer_account_ids: list[UUID]) -> list[CustomerSubscription]:
    if not customer_account_ids:
        return []
    return (
        db.query(CustomerSubscription)
        .filter(CustomerSubscription.customer_account_id.in_(customer_account_ids))
        .order_by(CustomerSubscription.created_at.desc())
        .all()
    )


def list_account_payments(db: Session, customer_account_ids: list[UUID]) -> list[PaymentTransaction]:
    if not customer_account_ids:
        return []
    return (
        db.query(PaymentTransaction)
        .filter(PaymentTransaction.customer_account_id.in_(customer_account_ids))
        .order_by(PaymentTransaction.created_at.desc())
        .limit(50)
        .all()
    )


def validate_verified_payment(transaction: PaymentTransaction, verified) -> None:
    if not verified.provider_reference or verified.provider_reference != transaction.provider_reference:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Verified payment reference did not match transaction")
    if not verified.provider_transaction_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Verified payment is missing provider transaction ID")
    if verified.amount_minor is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Verified payment is missing amount")
    if verified.currency is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Verified payment is missing currency")
    if verified.amount_minor != transaction.amount_minor:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment amount did not match transaction")
    if verified.currency != transaction.currency:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment currency did not match transaction")


def process_verified_payment(db: Session, transaction: PaymentTransaction, verified_status: str, provider_transaction_id: str | None = None) -> CustomerSubscription | None:
    if transaction.status == "SUCCESSFUL" and verified_status == "SUCCESSFUL":
        return db.query(CustomerSubscription).filter(CustomerSubscription.id == transaction.subscription_id).first() if transaction.subscription_id else None
    if transaction.status in {"CANCELLED", "REFUNDED"} and verified_status == "SUCCESSFUL":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment transaction is no longer payable")
    transaction.status = verified_status
    if provider_transaction_id:
        transaction.provider_transaction_id = provider_transaction_id
    transaction.updated_at = now_utc()
    subscription = db.query(CustomerSubscription).filter(CustomerSubscription.id == transaction.subscription_id).first() if transaction.subscription_id else None
    if verified_status == "SUCCESSFUL" and subscription:
        activate_subscription(db, subscription)
    elif verified_status == "FAILED" and subscription and subscription.status != "ACTIVE":
        subscription.status = "FAILED"
        subscription.updated_at = now_utc()
    elif verified_status == "PENDING" and subscription and subscription.status == "INCOMPLETE":
        transaction.status = "PENDING"
    db.flush()
    return subscription


def get_or_create_payment_event(db: Session, *, provider: PaymentProvider, payload: dict, verified_reference: str, verified_transaction_id: str | None) -> tuple[PaymentEvent, bool]:
    data = payload.get("data") or payload
    event_id = str(payload.get("event_id") or payload.get("id") or data.get("event_id") or data.get("id") or f"{verified_reference}:{verified_transaction_id or 'unknown'}")
    existing_event = db.query(PaymentEvent).filter(PaymentEvent.provider == provider.name, PaymentEvent.provider_event_id == event_id).first()
    if existing_event:
        return existing_event, False
    event = PaymentEvent(
        provider=provider.name,
        provider_event_id=event_id,
        event_type=str(payload.get("event") or payload.get("type") or "payment"),
        provider_reference=verified_reference,
        provider_transaction_id=verified_transaction_id,
        signature_valid=True,
        payload_json=payload,
    )
    db.add(event)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing_event = db.query(PaymentEvent).filter(PaymentEvent.provider == provider.name, PaymentEvent.provider_event_id == event_id).first()
        if existing_event:
            return existing_event, False
        raise
    return event, True


def process_provider_webhook(db: Session, *, provider: PaymentProvider, headers: dict[str, str], payload: dict) -> tuple[PaymentEvent, PaymentTransaction | None, CustomerSubscription | None]:
    if not provider.verify_webhook_signature(headers, payload):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid payment webhook signature")
    webhook_payment = provider.parse_webhook(payload)
    if not webhook_payment.provider_reference:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Payment webhook is missing a transaction reference")
    event, is_new_event = get_or_create_payment_event(
        db,
        provider=provider,
        payload=payload,
        verified_reference=webhook_payment.provider_reference,
        verified_transaction_id=webhook_payment.provider_transaction_id,
    )
    if not is_new_event and event.status == "PROCESSED":
        transaction = db.query(PaymentTransaction).filter(PaymentTransaction.provider == provider.name, PaymentTransaction.provider_reference == webhook_payment.provider_reference).first()
        subscription = db.query(CustomerSubscription).filter(CustomerSubscription.id == transaction.subscription_id).first() if transaction and transaction.subscription_id else None
        return event, transaction, subscription
    transaction = db.query(PaymentTransaction).filter(PaymentTransaction.provider == provider.name, PaymentTransaction.provider_reference == webhook_payment.provider_reference).with_for_update().first()
    if not transaction:
        event.status = "IGNORED"
        event.error = "Payment transaction reference was not found"
        db.flush()
        return event, None, None
    verified = provider.verify_transaction(
        provider_transaction_id=webhook_payment.provider_transaction_id,
        provider_reference=transaction.provider_reference,
        webhook_payload=payload,
    )
    try:
        validate_verified_payment(transaction, verified)
    except HTTPException as exc:
        event.status = "FAILED"
        event.error = str(exc.detail)
        db.flush()
        raise
    subscription = process_verified_payment(db, transaction, verified.status, provider_transaction_id=verified.provider_transaction_id)
    event.status = "PROCESSED"
    event.processed_at = now_utc()
    db.flush()
    return event, transaction, subscription


def create_marketing_access_token(db: Session, payload: MarketingAccessTokenCreate, *, created_by: UUID | None = None) -> MarketingAccessToken:
    existing = db.query(MarketingAccessToken).filter(MarketingAccessToken.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Access token code already exists")
    package = db.query(PackagePlan).filter(PackagePlan.id == payload.package_plan_id).first()
    if not package:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    if payload.package_price_id:
        price, price_package = get_price_with_package_or_404(db, payload.package_price_id)
        if price_package.id != package.id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Access token price must belong to the package")
    token = MarketingAccessToken(
        code=payload.code,
        package_plan_id=payload.package_plan_id,
        package_price_id=payload.package_price_id,
        duration_days=payload.duration_days,
        starts_at=payload.starts_at,
        expires_at=payload.expires_at,
        max_redemptions=payload.max_redemptions,
        assigned_email=str(payload.assigned_email).lower() if payload.assigned_email else None,
        assigned_user_id=payload.assigned_user_id,
        status=payload.status,
        internal_notes=payload.internal_notes,
        created_by=created_by,
        metadata_json=payload.metadata,
    )
    db.add(token)
    db.flush()
    return token


def update_marketing_access_token(db: Session, token: MarketingAccessToken, payload: MarketingAccessTokenUpdate) -> MarketingAccessToken:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(token, "metadata_json" if field == "metadata" else field, value)
    token.updated_at = now_utc()
    db.flush()
    return token


def validate_marketing_access_token(token: MarketingAccessToken, current_user: CurrentUser) -> None:
    current = now_utc()
    if token.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Access token is not active")
    if token.starts_at and comparable_time(token.starts_at) > current:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Access token is not active yet")
    if token.expires_at and comparable_time(token.expires_at) <= current:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Access token has expired")
    if token.max_redemptions is not None and token.redemption_count >= token.max_redemptions:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Access token has no redemptions remaining")
    if token.assigned_email and (current_user.email or "").lower() != token.assigned_email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access token is assigned to another email")
    if token.assigned_user_id and token.assigned_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access token is assigned to another user")


def redeem_marketing_access_token(db: Session, *, current_user: CurrentUser, code: str, customer_account_id: UUID | None = None) -> CustomerSubscription:
    account_id = resolve_owned_account(db, current_user, customer_account_id)
    token = db.query(MarketingAccessToken).filter(MarketingAccessToken.code == code).with_for_update().first()
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access token not found")
    validate_marketing_access_token(token, current_user)
    duplicate = (
        db.query(MarketingAccessTokenRedemption)
        .filter(
            MarketingAccessTokenRedemption.access_token_id == token.id,
            ((MarketingAccessTokenRedemption.customer_account_id == account_id) | (MarketingAccessTokenRedemption.user_id == current_user.id)),
        )
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Access token has already been redeemed")
    redeemed = (
        db.query(MarketingAccessToken)
        .filter(
            MarketingAccessToken.id == token.id,
            ((MarketingAccessToken.max_redemptions.is_(None)) | (MarketingAccessToken.redemption_count < MarketingAccessToken.max_redemptions)),
        )
        .update({MarketingAccessToken.redemption_count: MarketingAccessToken.redemption_count + 1, MarketingAccessToken.updated_at: now_utc()}, synchronize_session=False)
    )
    if redeemed != 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Access token has no redemptions remaining")
    db.flush()
    db.refresh(token)
    start = now_utc()
    end = start + timedelta(days=token.duration_days)
    subscription = CustomerSubscription(
        customer_account_id=account_id,
        package_plan_id=token.package_plan_id,
        package_price_id=token.package_price_id,
        status="ACTIVE",
        access_source="MARKETING",
        currency="UGX",
        amount_minor=0,
        billing_interval="MONTHLY",
        current_period_start=start,
        current_period_end=end,
        started_at=start,
        provider="marketing",
        metadata_json={"access_token_id": str(token.id), "access_token_code": token.code},
    )
    db.add(subscription)
    db.flush()
    activate_subscription_entitlements(db, subscription)
    redemption = MarketingAccessTokenRedemption(access_token_id=token.id, customer_account_id=account_id, user_id=current_user.id, subscription_id=subscription.id)
    db.add(redemption)
    token.updated_at = now_utc()
    db.flush()
    return subscription
