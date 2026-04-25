"""Phase 1 smoke tests.

Verifies that:
- config loads from .env,
- the Postgres ping succeeds,
- `time_series_data` exists with the expected row count after seeding.

All DB-backed tests carry the `requires_db` marker so CI or local runs
without Postgres just skip them.

Vector storage moved to ChromaDB (Phase 3) — see PLAN.md Architecture
Pivot Note. No pgvector assertions in this phase.
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


@pytest.mark.requires_db
def test_seed_populates_rows():
    with get_engine().connect() as conn:
        ts_rows = conn.execute(text("SELECT COUNT(*) FROM time_series_data")).scalar()

    # Seed generates 7 days * 24 hours * 3 metrics = 504 rows.
    assert ts_rows == 504, f"expected 504 time-series rows, got {ts_rows}"
