import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.hazmat.primitives.hashes import SHA256

from app.core.config import settings

_JWKS_CACHE: dict[str, object] = {"expires_at": 0.0, "keys": []}


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(f"{data}{padding}".encode("ascii"))


def _json_dumps(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _decode_jwt_json(segment: str) -> dict:
    return json.loads(_base64url_decode(segment))


def _load_supabase_jwks(force_refresh: bool = False) -> list[dict]:
    supabase_url = settings.resolved_supabase_url
    if not supabase_url:
        raise ValueError("Supabase URL is not configured")

    now = time.time()
    if not force_refresh and now < float(_JWKS_CACHE["expires_at"]):
        return list(_JWKS_CACHE["keys"])

    response = httpx.get(f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json", timeout=5)
    response.raise_for_status()
    keys = response.json().get("keys", [])
    _JWKS_CACHE["keys"] = keys
    _JWKS_CACHE["expires_at"] = now + 600
    return keys


def _find_supabase_jwk(kid: str) -> dict:
    for force_refresh in (False, True):
        for key in _load_supabase_jwks(force_refresh=force_refresh):
            if key.get("kid") == kid:
                return key
    raise ValueError("Supabase signing key was not found")


def _jwk_to_es256_public_key(jwk: dict):
    if jwk.get("kty") != "EC" or jwk.get("crv") != "P-256":
        raise ValueError("Unsupported Supabase signing key")
    x = int.from_bytes(_base64url_decode(jwk["x"]), "big")
    y = int.from_bytes(_base64url_decode(jwk["y"]), "big")
    return ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()


def decode_supabase_access_token(token: str) -> tuple[UUID, dict]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        header = _decode_jwt_json(encoded_header)
        if header.get("alg") != "ES256":
            raise ValueError("Unsupported Supabase token algorithm")
        kid = header.get("kid")
        if not kid:
            raise ValueError("Missing Supabase token key id")

        jwk = _find_supabase_jwk(kid)
        public_key = _jwk_to_es256_public_key(jwk)
        signature = _base64url_decode(encoded_signature)
        if len(signature) != 64:
            raise ValueError("Invalid Supabase token signature length")
        der_signature = utils.encode_dss_signature(
            int.from_bytes(signature[:32], "big"),
            int.from_bytes(signature[32:], "big"),
        )
        public_key.verify(der_signature, f"{encoded_header}.{encoded_payload}".encode("ascii"), ec.ECDSA(SHA256()))

        payload = _decode_jwt_json(encoded_payload)
        subject = payload.get("sub")
        expires_at = payload.get("exp")
        issuer = payload.get("iss")
        audience = payload.get("aud")
        supabase_url = settings.resolved_supabase_url
        expected_issuer = f"{supabase_url.rstrip('/')}/auth/v1" if supabase_url else None
        if not subject or not expires_at:
            raise ValueError("Missing Supabase token claims")
        if issuer != expected_issuer:
            raise ValueError("Invalid Supabase token issuer")
        if audience != "authenticated":
            raise ValueError("Invalid Supabase token audience")
        if datetime.now(timezone.utc).timestamp() >= float(expires_at):
            raise ValueError("Supabase access token expired")
        return UUID(subject), payload
    except (InvalidSignature, KeyError, ValueError, json.JSONDecodeError, TypeError, httpx.HTTPError) as exc:
        raise ValueError("Invalid Supabase access token") from exc


def create_access_token(
    user_id: UUID,
    extra_claims: dict | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    expires_at = datetime.now(timezone.utc) + (
        expires_delta if expires_delta is not None else timedelta(minutes=settings.access_token_expire_minutes)
    )
    header = {"alg": settings.jwt_algorithm, "typ": "JWT"}
    payload = {"sub": str(user_id), "exp": int(expires_at.timestamp()), "iss": "eecs-api"}
    if extra_claims:
        payload.update(extra_claims)

    encoded_header = _base64url_encode(_json_dumps(header))
    encoded_payload = _base64url_encode(_json_dumps(payload))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(settings.jwt_signing_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_base64url_encode(signature)}"


def decode_access_token(token: str) -> UUID:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        header = _decode_jwt_json(encoded_header)
        if header.get("alg") != settings.jwt_algorithm:
            raise ValueError("Unsupported token algorithm")

        signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
        expected_signature = hmac.new(settings.jwt_signing_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_signature = _base64url_decode(encoded_signature)
        if not hmac.compare_digest(expected_signature, actual_signature):
            raise ValueError("Invalid token signature")

        payload = _decode_jwt_json(encoded_payload)
        subject = payload.get("sub")
        expires_at = payload.get("exp")
        issuer = payload.get("iss")
        if not subject or not expires_at:
            raise ValueError("Missing token claims")
        if settings.uses_remote_supabase_auth and settings.environment == "production":
            expected_issuer = f"{settings.supabase_url.rstrip('/')}/auth/v1" if settings.supabase_url else None
            if issuer != expected_issuer:
                raise ValueError("Invalid token issuer")
        if datetime.now(timezone.utc).timestamp() >= float(expires_at):
            raise ValueError("Access token expired")
        return UUID(subject)
    except (ValueError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError("Invalid access token") from exc
