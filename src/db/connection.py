"""SQLAlchemy engine, session factory, and ORM models.

One engine per process. Callers should use `get_session()` as a context
manager for automatic commit/rollback. The schema itself is owned by
`schema.sql` (single source of truth) — the ORM models below are a
typed read interface for downstream phases.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from functools import lru_cache
from typing import Iterator

from sqlalchemy import DateTime, Engine, Float, String, create_engine, text
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

from src.config import settings


class Base(DeclarativeBase):
    pass


class TimeSeriesData(Base):
    __tablename__ = "time_series_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metric_name: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(
        settings.postgres_url,
        pool_pre_ping=True,
        future=True,
    )


@lru_cache(maxsize=1)
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


@contextmanager
def get_session() -> Iterator[Session]:
    session = _session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ping() -> bool:
    """Return True if the database responds to `SELECT 1`."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
