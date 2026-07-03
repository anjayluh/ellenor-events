from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Ellenor Events Coordination System"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ellenor_events"
    auth_provider: str = "supabase"
    jwt_secret: str = "development-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    otp_expire_minutes: int = 10
    otp_rate_limit_window_minutes: int = 15
    otp_rate_limit_max_attempts: int = 5
    development_otp_code: str = "000000"
    allow_dev_auth_headers: bool = False
    frontend_url: str = "http://localhost:3000"
    whatsapp_mode: str = "manual_links"
    email_provider: str = "resend"
    resend_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
