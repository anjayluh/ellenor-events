from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global engine
    if engine is None:
        engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
    return engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _session_factory


def SessionLocal() -> Session:
    return get_session_factory()()


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
