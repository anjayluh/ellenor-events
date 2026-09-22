from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.billing import CustomerSubscription, PaymentTransaction
from app.models.catalog import PackagePlan
from app.models.customer_account import AccountEntitlement
from app.schemas.billing import (
    BillingOverview,
    CheckoutCreate,
    CheckoutRead,
    CustomerSubscriptionRead,
    FlutterwaveWebhookRead,
    MarketingAccessTokenRedeem,
    PaymentTransactionRead,
    SubscriptionCancelRequest,
)
from app.services.billing_service import (
    cancel_subscription,
    create_checkout,
    list_account_payments,
    list_account_subscriptions,
    process_provider_webhook,
    redeem_marketing_access_token,
    require_account_owner,
)
from app.services.customer_account_service import list_user_account_memberships
from app.services.payment_provider import get_payment_provider

router = APIRouter()


def serialize_payment(transaction: PaymentTransaction) -> PaymentTransactionRead:
    return PaymentTransactionRead.model_validate(transaction)


def subscription_entitlement_summary(db: Session, subscription: CustomerSubscription) -> list[dict]:
    entitlements = db.query(AccountEntitlement).filter(AccountEntitlement.customer_account_id == subscription.customer_account_id).all()
    return [
        {
            "key": entitlement.key,
            "quantity": entitlement.quantity,
            "used_quantity": entitlement.used_quantity,
            "status": entitlement.status,
            "expires_at": entitlement.expires_at,
            "source": (entitlement.metadata_json or {}).get("source"),
        }
        for entitlement in entitlements
        if (entitlement.metadata_json or {}).get("subscription_id") == str(subscription.id)
    ]


def serialize_subscription(subscription: CustomerSubscription, db: Session) -> CustomerSubscriptionRead:
    package = db.query(PackagePlan).filter(PackagePlan.id == subscription.package_plan_id).first()
    return CustomerSubscriptionRead(
        id=subscription.id,
        customer_account_id=subscription.customer_account_id,
        package_plan_id=subscription.package_plan_id,
        package_price_id=subscription.package_price_id,
        status=subscription.status,
        access_source=subscription.access_source,
        currency=subscription.currency,
        amount_minor=subscription.amount_minor,
        billing_interval=subscription.billing_interval,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
        cancelled_at=subscription.cancelled_at,
        started_at=subscription.started_at,
        ended_at=subscription.ended_at,
        provider=subscription.provider,
        package_name=package.name if package else None,
        entitlement_summary=subscription_entitlement_summary(db, subscription),
        created_at=subscription.created_at,
        updated_at=subscription.updated_at,
    )


@router.post("/checkout", response_model=CheckoutRead)
def start_checkout(payload: CheckoutCreate, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    subscription, transaction = create_checkout(db, current_user=current_user, package_price_id=payload.package_price_id, customer_account_id=payload.customer_account_id)
    db.commit()
    db.refresh(subscription)
    db.refresh(transaction)
    return CheckoutRead(
        transaction_id=transaction.id,
        subscription_id=subscription.id,
        customer_account_id=subscription.customer_account_id,
        package_price_id=payload.package_price_id,
        amount_minor=transaction.amount_minor,
        currency=transaction.currency,
        billing_interval=subscription.billing_interval,
        provider=transaction.provider,
        provider_reference=transaction.provider_reference,
        checkout_url=transaction.checkout_url or "",
        status=transaction.status,
    )


@router.get("/subscription", response_model=BillingOverview)
def get_billing_overview(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    account_ids = [account.id for account, _membership in list_user_account_memberships(db, current_user.id)]
    subscriptions = list_account_subscriptions(db, account_ids)
    payments = list_account_payments(db, account_ids)
    return BillingOverview(
        subscriptions=[serialize_subscription(subscription, db) for subscription in subscriptions],
        payments=[serialize_payment(payment) for payment in payments],
    )


@router.post("/subscription/cancel", response_model=CustomerSubscriptionRead)
def cancel_customer_subscription(payload: SubscriptionCancelRequest, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    subscription = db.query(CustomerSubscription).filter(CustomerSubscription.id == payload.subscription_id).first()
    if not subscription:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    require_account_owner(db, subscription.customer_account_id, current_user.id)
    cancel_subscription(db, subscription, cancel_at_period_end=payload.cancel_at_period_end)
    db.commit()
    db.refresh(subscription)
    return serialize_subscription(subscription, db)


@router.post("/access-tokens/redeem", response_model=CustomerSubscriptionRead)
def redeem_access_token(payload: MarketingAccessTokenRedeem, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    subscription = redeem_marketing_access_token(db, current_user=current_user, code=payload.code, customer_account_id=payload.customer_account_id)
    db.commit()
    db.refresh(subscription)
    return serialize_subscription(subscription, db)


@router.post("/webhooks/flutterwave", response_model=FlutterwaveWebhookRead)
async def flutterwave_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    provider = get_payment_provider("mock" if get_payment_provider().name == "mock" else "flutterwave")
    event, transaction, subscription = process_provider_webhook(db, provider=provider, headers=dict(request.headers), payload=payload)
    db.commit()
    return FlutterwaveWebhookRead(
        status=event.status,
        event_id=event.id,
        transaction_id=transaction.id if transaction else None,
        subscription_id=subscription.id if subscription else None,
    )
