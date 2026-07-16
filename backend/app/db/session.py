from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        if settings.uses_remote_supabase_auth:
            try:
                db.rollback()
                db.execute(text("reset role"))
                db.execute(text("select set_config('request.jwt.claim.sub', '', false)"))
                db.execute(text("select set_config('request.jwt.claim.role', '', false)"))
                db.commit()
            except Exception:
                db.rollback()
        db.close()
