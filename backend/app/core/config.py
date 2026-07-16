from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Ellenor Events Coordination System"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ellenor_events"
    auth_provider: str = "supabase"
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def allowed_cors_origins(self) -> list[str]:
        origins = [self.frontend_url]
        if self.cors_origins:
            origins.extend(origin.strip() for origin in self.cors_origins.split(",") if origin.strip())
        return list(dict.fromkeys(origins))

    @property
    def uses_remote_supabase_auth(self) -> bool:
        return self.auth_provider == "supabase" and bool(self.supabase_url and self.supabase_anon_key)

    @property
    def jwt_signing_secret(self) -> str:
        return self.supabase_jwt_secret or self.jwt_secret

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
