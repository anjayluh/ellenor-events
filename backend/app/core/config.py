from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Ellenor Events Coordination System"
    environment: str = "development"
    database_url: str | None = None
    database_pooler_url: str | None = None
    postgres_url: str | None = None
    postgres_prisma_url: str | None = None
    postgres_url_non_pooling: str | None = None
    supabase_db_url: str | None = None
    auth_provider: str = "supabase"
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    next_public_supabase_url: str | None = None
    next_public_supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    supabase_jwt_secret: str | None = None
    jwt_secret: str = "development-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    otp_expire_minutes: int = 10
    otp_rate_limit_window_minutes: int = 15
    otp_rate_limit_max_attempts: int = 5
    development_otp_code: str = "000000"
    allow_dev_auth_headers: bool = False
    frontend_url: str = "http://localhost:3000"
    cors_origins: str | None = None
    whatsapp_mode: str = "manual_links"
    email_provider: str = "resend"
    resend_api_key: str | None = None
    resend_from_email: str = "Ellenor Events <noreply@ellenor.events>"
    whatsapp_cloud_api_token: str | None = None
    whatsapp_phone_number_id: str | None = None
    notification_max_attempts: int = 3
    payment_provider: str = "flutterwave"
    flutterwave_secret_key: str | None = None
    flutterwave_public_key: str | None = None
    flutterwave_webhook_secret: str | None = None
    flutterwave_base_url: str = "https://api.flutterwave.com/v3"
    billing_checkout_redirect_url: str | None = None
    billing_grace_period_days: int = 7

    model_config = SettingsConfigDict(
        env_file=("backend/.env", ".env", "backend/.env.local", ".env.local", "../.env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_cors_origins(self) -> list[str]:
        origins = [self.frontend_url]
        if self.cors_origins:
            origins.extend(origin.strip() for origin in self.cors_origins.split(",") if origin.strip())
        return list(dict.fromkeys(origins))

    @property
    def uses_remote_supabase_auth(self) -> bool:
        return self.auth_provider == "supabase" and bool(self.resolved_supabase_url and self.resolved_supabase_anon_key)

    @property
    def has_configured_database_url(self) -> bool:
        return bool(self.configured_database_url)

    @property
    def configured_database_url(self) -> str | None:
        return (
            self.database_pooler_url
            or self.database_url
            or self.postgres_prisma_url
            or self.postgres_url
            or self.postgres_url_non_pooling
            or self.supabase_db_url
        )

    @property
    def resolved_supabase_url(self) -> str | None:
        return self.supabase_url or self.next_public_supabase_url

    @property
    def resolved_supabase_anon_key(self) -> str | None:
        return self.supabase_anon_key or self.next_public_supabase_anon_key

    @property
    def jwt_signing_secret(self) -> str:
        return self.supabase_jwt_secret or self.jwt_secret

    @property
    def sqlalchemy_database_url(self) -> str:
        url = self.configured_database_url
        if not url:
            raise RuntimeError(
                "Database URL is not configured. Set DATABASE_POOLER_URL, DATABASE_URL, "
                "POSTGRES_PRISMA_URL, POSTGRES_URL, POSTGRES_URL_NON_POOLING, or SUPABASE_DB_URL."
            )
        if "localhost" in url or "127.0.0.1" in url:
            raise RuntimeError(
                "Localhost database URLs are not allowed for this deployment. "
                "Set DATABASE_POOLER_URL or DATABASE_URL to the Supabase/Postgres database."
            )
        return self.normalize_database_url(url)

    @staticmethod
    def normalize_database_url(url: str) -> str:
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    @property
    def safe_database_host(self) -> str | None:
        url = self.configured_database_url
        if not url:
            return None
        try:
            from urllib.parse import urlparse

            parsed = urlparse(self.normalize_database_url(url))
            return parsed.hostname
        except ValueError:
            return "invalid"

    @property
    def database_points_to_localhost(self) -> bool:
        host = self.safe_database_host
        return host in {"localhost", "127.0.0.1", "::1"}

    def validate_deployment_configuration(self) -> None:
        errors = []
        if not self.has_configured_database_url:
            errors.append("database URL is missing")
        elif self.database_points_to_localhost:
            errors.append("database URL points to localhost")
        if self.auth_provider == "supabase" and not self.resolved_supabase_url:
            errors.append("Supabase URL is missing")
        if self.auth_provider == "supabase" and not self.resolved_supabase_anon_key:
            errors.append("Supabase anon key is missing")
        if self.is_production and self.payment_provider == "mock":
            errors.append("mock payment provider is not allowed in production")
        if errors:
            raise RuntimeError(
                "Invalid deployment configuration: "
                + "; ".join(errors)
                + ". Configure the backend service environment variables in Vercel."
            )

    @property
    def deployment_config_errors(self) -> list[str]:
        errors = []
        if not self.has_configured_database_url:
            errors.append("database_url_missing")
        elif self.database_points_to_localhost:
            errors.append("database_url_points_to_localhost")
        if self.auth_provider == "supabase" and not self.resolved_supabase_url:
            errors.append("supabase_url_missing")
        if self.auth_provider == "supabase" and not self.resolved_supabase_anon_key:
            errors.append("supabase_anon_key_missing")
        if self.is_production and self.payment_provider == "mock":
            errors.append("mock_payment_provider_in_production")
        return errors

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @property
    def checkout_redirect_url(self) -> str:
        return self.billing_checkout_redirect_url or f"{self.frontend_url.rstrip('/')}/billing"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
