from __future__ import annotations

import httpx

from app.core.config import settings


class DocumentStorageError(RuntimeError):
    pass


class SupabaseDocumentStorage:
    def _configuration(self) -> tuple[str, str, str]:
        base_url = settings.resolved_supabase_url
        service_key = settings.supabase_service_role_key
        if not base_url or not service_key:
            raise DocumentStorageError("Private document storage is not configured")
        return base_url.rstrip("/"), service_key, settings.document_storage_bucket

    def _headers(self, service_key: str, *, content_type: str | None = None) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {service_key}", "apikey": service_key}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def upload(self, path: str, content: bytes, mime_type: str) -> None:
        base_url, service_key, bucket = self._configuration()
        try:
            response = httpx.post(
                f"{base_url}/storage/v1/object/{bucket}/{path}",
                content=content,
                headers={**self._headers(service_key, content_type=mime_type), "x-upsert": "false"},
                timeout=30,
            )
        except httpx.HTTPError as exc:
            raise DocumentStorageError("Document storage is unavailable") from exc
        if response.is_error:
            raise DocumentStorageError("Document upload was not accepted by storage")

    def sign(self, path: str, expires_in: int) -> str:
        base_url, service_key, bucket = self._configuration()
        try:
            response = httpx.post(
                f"{base_url}/storage/v1/object/sign/{bucket}/{path}",
                json={"expiresIn": expires_in},
                headers=self._headers(service_key),
                timeout=10,
            )
        except httpx.HTTPError as exc:
            raise DocumentStorageError("Document storage is unavailable") from exc
        if response.is_error:
            raise DocumentStorageError("Document preview could not be created")
        try:
            signed_path = response.json().get("signedURL")
        except ValueError as exc:
            raise DocumentStorageError("Document preview response was invalid") from exc
        if not isinstance(signed_path, str) or not signed_path:
            raise DocumentStorageError("Document preview response was invalid")
        if signed_path.startswith("http"):
            return signed_path
        return f"{base_url}/storage/v1{signed_path}"

    def delete(self, path: str) -> None:
        base_url, service_key, bucket = self._configuration()
        try:
            response = httpx.delete(
                f"{base_url}/storage/v1/object/{bucket}",
                json={"prefixes": [path]},
                headers=self._headers(service_key),
                timeout=20,
            )
        except httpx.HTTPError as exc:
            raise DocumentStorageError("Document storage cleanup failed") from exc
        if response.is_error:
            raise DocumentStorageError("Document storage cleanup failed")


storage_client = SupabaseDocumentStorage()
