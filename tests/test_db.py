"""Phase 1 smoke tests.

Verifies that:
- the pgvector extension is installed,
- both tables exist with the expected columns,
- the seed script populates plausible row counts.

All DB-backed tests carry the `requires_db` marker so CI or local runs
without Postgres just skip them.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from src.db.connection import get_engine, ping


def test_config_loads():
    from src.config import settings

    assert settings.postgres_url.startswith("postgresql")
    assert settings.embedding_model.endswith("all-MiniLM-L6-v2")


@pytest.mark.requires_db
def test_ping_succeeds():
    assert ping() is True


@pytest.mark.requires_db
def test_pgvector_extension_installed():
    with get_engine().connect() as conn:
        row = conn.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        ).first()
    assert row is not None, "pgvector extension not installed — run `python -m src.db.seed`"


@pytest.mark.requires_db
def test_tables_exist():
    with get_engine().connect() as conn:
        tables = {
            r[0]
            for r in conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
            )
        }
    assert "time_series_data" in tables
    assert "business_rules" in tables


@pytest.mark.requires_db
def test_seed_populates_rows():
    with get_engine().connect() as conn:
        ts_rows = conn.execute(text("SELECT COUNT(*) FROM time_series_data")).scalar()
        rule_rows = conn.execute(text("SELECT COUNT(*) FROM business_rules")).scalar()

    # Seed generates 7 days * 24 hours * 3 metrics = 504 rows.
    assert ts_rows == 504, f"expected 504 time-series rows, got {ts_rows}"
    assert rule_rows >= 5, f"expected at least 5 business rules, got {rule_rows}"


@pytest.mark.requires_db
def test_embedding_dimension_is_384():
    """pgvector stores the dimension at the column level; verify it matches
    the all-MiniLM-L6-v2 output size the Router will use."""
    with get_engine().connect() as conn:
        row = conn.execute(
            text(
                "SELECT atttypmod FROM pg_attribute "
                "WHERE attrelid = 'business_rules'::regclass "
                "AND attname = 'embedding'"
            )
        ).first()
    assert row is not None
    # pgvector encodes dim as atttypmod; 384 is the expected value.
    assert row[0] == 384
