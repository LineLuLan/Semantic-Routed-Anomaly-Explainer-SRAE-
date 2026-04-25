"""Seed script for SRAE.

Applies `schema.sql`, then populates `time_series_data` with a week of
hourly mock metrics (`traffic`, `sales`, `error_rate`) containing several
injected anomalies so the ML layer has something interesting to find.

Business rules live in ChromaDB and are seeded separately by Phase 3
(`src/router/`).

Run:
    python -m src.db.seed             # idempotent: truncates then re-seeds
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text

from src.config import settings
from src.db.connection import get_engine, get_session, ping

LOG = logging.getLogger(__name__)
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# Deterministic seed so tests can rely on the injected anomalies.
RNG = random.Random(42)


def _apply_schema() -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    with get_engine().begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
    LOG.info("Applied schema (%d statements)", len(statements))


def _truncate() -> None:
    with get_session() as s:
        s.execute(text("TRUNCATE TABLE time_series_data RESTART IDENTITY"))


def _generate_time_series() -> list[dict]:
    """One week of hourly data for three metrics with injected anomalies."""
    start = datetime(2026, 4, 18, 0, 0, tzinfo=timezone.utc)
    rows: list[dict] = []

    for hour_offset in range(7 * 24):
        ts = start + timedelta(hours=hour_offset)
        hour = ts.hour

        # Traffic: daytime peak, nighttime trough.
        traffic_base = 1200 + 800 * max(0, (1 - abs(hour - 14) / 10))
        traffic = traffic_base + RNG.gauss(0, 60)

        # Sales: business hours only.
        sales = (200 + RNG.gauss(0, 25)) if 9 <= hour <= 21 else RNG.gauss(30, 10)

        # Error rate: low by default.
        error_rate = max(0.0, RNG.gauss(0.8, 0.2))

        # --- Injected anomalies ---
        if hour_offset == 2 * 24 + 2:
            traffic = 5000  # Day 3, 2 AM: late-night traffic spike
        if hour_offset == 4 * 24 + 11:
            sales = 5  # Day 5, 11 AM: sales collapse
        if hour_offset == 5 * 24 + 15:
            error_rate = 12.5  # Day 6, 3 PM: error rate spike

        rows.append({"ts": ts, "metric_name": "traffic", "value": round(traffic, 2)})
        rows.append({"ts": ts, "metric_name": "sales", "value": round(max(0, sales), 2)})
        rows.append(
            {"ts": ts, "metric_name": "error_rate", "value": round(error_rate, 3)}
        )
    return rows


def _seed_time_series() -> int:
    rows = _generate_time_series()
    with get_session() as s:
        s.execute(
            text(
                "INSERT INTO time_series_data (ts, metric_name, value) "
                "VALUES (:ts, :metric_name, :value)"
            ),
            rows,
        )
    LOG.info("Inserted %d time-series rows", len(rows))
    return len(rows)


def main() -> None:
    logging.basicConfig(
        level=settings.log_level, format="%(asctime)s %(levelname)s %(message)s"
    )

    if not ping():
        raise SystemExit(
            "Cannot reach Postgres at the configured POSTGRES_URL. "
            "Verify your .env and that the server is running."
        )

    _apply_schema()
    _truncate()
    _seed_time_series()
    LOG.info("Seed complete.")


if __name__ == "__main__":
    main()
