from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        if settings.uses_remote_supabase_auth and db.info.get("supabase_rls_applied"):
            try:
                if db.get_bind().dialect.name != "postgresql":
                    db.close()
                    return
                db.rollback()
            except Exception:
                db.rollback()
        db.close()
