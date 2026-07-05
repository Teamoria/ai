"""Database configuration."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global engine

    if engine is None:
        engine = create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=280)

    return engine


def get_session_factory() -> sessionmaker[Session]:
    global SessionLocal

    if SessionLocal is None:
        SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)

    return SessionLocal


def get_session() -> Session:
    try:
        return get_session_factory()()
    except Exception as exc:
        raise RuntimeError("Database session is not available.") from exc
