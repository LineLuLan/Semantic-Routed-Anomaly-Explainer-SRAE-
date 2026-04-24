"""Seed script for SRAE.

Applies `schema.sql`, then populates:
- `time_series_data` with a week of hourly mock metrics (`traffic`, `sales`,
  `error_rate`) containing several injected anomalies so the ML layer has
  something interesting to find.
- `business_rules` with a small catalog of playbooks, embedded with the
  `sentence-transformers/all-MiniLM-L6-v2` model (384 dims).

Run:
    python -m src.db.seed             # idempotent: truncates then re-seeds
    python -m src.db.seed --skip-rules  # only time-series
"""

from __future__ import annotations

import argparse
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

BUSINESS_RULES: list[tuple[str, str]] = [
    (
        "High late-night traffic between 1 AM and 4 AM indicates possible bot "
        "scraping or a scheduled crawler hitting the site.",
        "Check firewall logs and enable rate limiting for the affected endpoints.",
    ),
    (
        "A sudden drop in sales during normal business hours signals a broken "
        "checkout, payment gateway failure, or expired promotion.",
        "Inspect the checkout funnel, verify payment provider status, and review "
        "recent deploys.",
    ),
    (
        "A spike in error_rate on API endpoints points to a bad deploy, a "
        "downstream dependency outage, or a database slowdown.",
        "Roll back the latest deploy, page the on-call engineer, and check "
        "dependency dashboards.",
    ),
    (
        "Traffic falling to near zero across all metrics suggests a CDN outage, "
        "DNS failure, or upstream load balancer issue.",
        "Verify CDN status page, run DNS probes from external locations, and "
        "confirm load balancer health checks.",
    ),
    (
        "Sales surging far above forecast without a marketing campaign can mean "
        "pricing is mis-configured or an external viral event is driving demand.",
        "Audit recent pricing changes, confirm stock levels, and prepare "
        "scaling for the surge.",
    ),
    (
        "An elevated error_rate combined with flat traffic implies a backend "
        "regression rather than a user-facing issue.",
        "Inspect application logs, look for recent schema migrations, and verify "
        "background worker health.",
    ),
]


def _apply_schema() -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    # Split on semicolons that end a line so we can execute each statement.
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    with get_engine().begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
    LOG.info("Applied schema (%d statements)", len(statements))


def _truncate() -> None:
    with get_session() as s:
        s.execute(text("TRUNCATE TABLE time_series_data RESTART IDENTITY"))
        s.execute(text("TRUNCATE TABLE business_rules RESTART IDENTITY"))


def _generate_time_series() -> list[dict]:
    """One week of hourly data for three metrics with injected anomalies."""
    start = datetime(2026, 4, 18, 0, 0, tzinfo=timezone.utc)
    rows: list[dict] = []

    # Baselines + diurnal shape.
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
        # Day 3, 2 AM: late-night traffic spike (bot scraping).
        if hour_offset == 2 * 24 + 2:
            traffic = 5000
        # Day 5, 11 AM: sales collapse during business hours.
        if hour_offset == 4 * 24 + 11:
            sales = 5
        # Day 6, 3 PM: error rate spike.
        if hour_offset == 5 * 24 + 15:
            error_rate = 12.5

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


def _seed_business_rules() -> int:
    # Import here so phases that don't need embeddings can run --skip-rules
    # without forcing a sentence-transformers install.
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(settings.embedding_model)
    texts = [r[0] for r in BUSINESS_RULES]
    embeddings = model.encode(texts, normalize_embeddings=True).tolist()

    payload = [
        {
            "rule_text": rule_text,
            "suggested_action": action,
            "embedding": embedding,
        }
        for (rule_text, action), embedding in zip(BUSINESS_RULES, embeddings)
    ]

    with get_session() as s:
        s.execute(
            text(
                "INSERT INTO business_rules (rule_text, suggested_action, embedding) "
                "VALUES (:rule_text, :suggested_action, :embedding)"
            ),
            payload,
        )
    LOG.info("Inserted %d business rules", len(payload))
    return len(payload)


def main() -> None:
    logging.basicConfig(
        level=settings.log_level, format="%(asctime)s %(levelname)s %(message)s"
    )
    parser = argparse.ArgumentParser(description="Seed SRAE database.")
    parser.add_argument(
        "--skip-rules",
        action="store_true",
        help="Only seed time-series data (avoids downloading the embedding model).",
    )
    args = parser.parse_args()

    if not ping():
        raise SystemExit(
            "Cannot reach Postgres at the configured POSTGRES_URL. "
            "Verify your .env and that the server is running."
        )

    _apply_schema()
    _truncate()
    _seed_time_series()
    if not args.skip_rules:
        _seed_business_rules()
    LOG.info("Seed complete.")


if __name__ == "__main__":
    main()
