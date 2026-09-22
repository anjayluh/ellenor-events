from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.core.config import settings


def parse_amount_minor(value) -> int | None:
    if value is None:
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Provider payment amount was invalid") from exc
    if amount != amount.to_integral_value():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Provider payment amount was invalid")
    return int(amount)


@dataclass(frozen=True)
class CheckoutSession:
    checkout_url: str
    provider_reference: str
    provider_payload: dict


@dataclass(frozen=True)
class VerifiedPayment:
    provider_transaction_id: str | None
    provider_reference: str
    status: str
    amount_minor: int | None = None
    currency: str | None = None


class PaymentProvider:
    name = "provider"

    def create_checkout_session(
        self,
        *,
        transaction_id: UUID,
        provider_reference: str,
        amount_minor: int,
        currency: str,
        customer_email: str | None,
        redirect_url: str,
        metadata: dict,
    ) -> CheckoutSession:
        raise NotImplementedError

    def verify_webhook_signature(self, headers: dict[str, str], payload: dict) -> bool:
        raise NotImplementedError

    def parse_webhook(self, payload: dict) -> VerifiedPayment:
        raise NotImplementedError

    def verify_transaction(self, *, provider_transaction_id: str | None, provider_reference: str, webhook_payload: dict) -> VerifiedPayment:
        raise NotImplementedError


class FlutterwaveProvider(PaymentProvider):
    name = "flutterwave"

    def create_checkout_session(
        self,
        *,
        transaction_id: UUID,
        provider_reference: str,
        amount_minor: int,
        currency: str,
        customer_email: str | None,
        redirect_url: str,
        metadata: dict,
    ) -> CheckoutSession:
        if not settings.flutterwave_secret_key:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Flutterwave checkout is not configured")
        payload = {
            "tx_ref": provider_reference,
            "amount": amount_minor,
            "currency": currency,
            "redirect_url": redirect_url,
            "customer": {"email": customer_email or "customer@ellenor.events"},
            "customizations": {"title": "Ellenor Events subscription"},
            "meta": {"transaction_id": str(transaction_id), **metadata},
        }
        try:
            response = httpx.post(
                f"{settings.flutterwave_base_url.rstrip('/')}/payments",
                headers={"Authorization": f"Bearer {settings.flutterwave_secret_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=15,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail="Flutterwave rejected checkout creation") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Flutterwave checkout is unavailable") from exc
        data = response.json()
        checkout_url = ((data.get("data") or {}).get("link") or "").strip()
        if not checkout_url:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Flutterwave checkout response was incomplete")
        return CheckoutSession(checkout_url=checkout_url, provider_reference=provider_reference, provider_payload=data)

    def verify_webhook_signature(self, headers: dict[str, str], payload: dict) -> bool:
        webhook_secret = settings.flutterwave_webhook_secret
        return bool(webhook_secret and headers.get("verif-hash") == webhook_secret)

    def parse_webhook(self, payload: dict) -> VerifiedPayment:
        data = payload.get("data") or payload
        provider_reference = str(data.get("tx_ref") or data.get("reference") or "")
        raw_status = str(data.get("status") or payload.get("status") or "").lower()
        status_map = {"successful": "SUCCESSFUL", "success": "SUCCESSFUL", "failed": "FAILED", "cancelled": "CANCELLED", "pending": "PENDING"}
        return VerifiedPayment(
            provider_transaction_id=str(data.get("id")) if data.get("id") is not None else None,
            provider_reference=provider_reference,
            status=status_map.get(raw_status, "PENDING"),
            amount_minor=parse_amount_minor(data.get("amount")),
            currency=data.get("currency"),
        )

    def verify_transaction(self, *, provider_transaction_id: str | None, provider_reference: str, webhook_payload: dict) -> VerifiedPayment:
        if not settings.flutterwave_secret_key:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Flutterwave verification is not configured")
        if provider_transaction_id:
            url = f"{settings.flutterwave_base_url.rstrip('/')}/transactions/{provider_transaction_id}/verify"
            params = None
        else:
            url = f"{settings.flutterwave_base_url.rstrip('/')}/transactions/verify_by_reference"
            params = {"tx_ref": provider_reference}
        try:
            response = httpx.get(
                url,
                headers={"Authorization": f"Bearer {settings.flutterwave_secret_key}"},
                params=params,
                timeout=15,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail="Flutterwave verification rejected the transaction") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Flutterwave verification is unavailable") from exc
        payload = response.json()
        data = payload.get("data") or {}
        raw_status = str(data.get("status") or payload.get("status") or "").lower()
        status_map = {"successful": "SUCCESSFUL", "success": "SUCCESSFUL", "failed": "FAILED", "cancelled": "CANCELLED", "pending": "PENDING"}
        verified_reference = str(data.get("tx_ref") or data.get("reference") or provider_reference)
        return VerifiedPayment(
            provider_transaction_id=str(data.get("id")) if data.get("id") is not None else provider_transaction_id,
            provider_reference=verified_reference,
            status=status_map.get(raw_status, "PENDING"),
            amount_minor=parse_amount_minor(data.get("amount")),
            currency=data.get("currency"),
        )


class MockPaymentProvider(PaymentProvider):
    name = "mock"

    def create_checkout_session(
        self,
        *,
        transaction_id: UUID,
        provider_reference: str,
        amount_minor: int,
        currency: str,
        customer_email: str | None,
        redirect_url: str,
        metadata: dict,
    ) -> CheckoutSession:
        return CheckoutSession(
            checkout_url=f"https://payments.example.test/checkout/{provider_reference}",
            provider_reference=provider_reference,
            provider_payload={"mock": True, "transaction_id": str(transaction_id), "amount_minor": amount_minor, "currency": currency},
        )

    def verify_webhook_signature(self, headers: dict[str, str], payload: dict) -> bool:
        return headers.get("x-mock-payment-secret") == "test-webhook-secret"

    def parse_webhook(self, payload: dict) -> VerifiedPayment:
        data = payload.get("data") or payload
        return VerifiedPayment(
            provider_transaction_id=str(data.get("id")) if data.get("id") is not None else None,
            provider_reference=str(data.get("tx_ref") or data.get("provider_reference") or ""),
            status=str(data.get("status") or "PENDING").upper(),
            amount_minor=parse_amount_minor(data.get("amount_minor")),
            currency=data.get("currency"),
        )

    def verify_transaction(self, *, provider_transaction_id: str | None, provider_reference: str, webhook_payload: dict) -> VerifiedPayment:
        return self.parse_webhook(webhook_payload)


def get_payment_provider(provider: str | None = None) -> PaymentProvider:
    provider_name = (provider or settings.payment_provider).lower()
    if provider_name == "mock":
        if settings.is_production:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Mock payments are not allowed in production")
        return MockPaymentProvider()
    return FlutterwaveProvider()
