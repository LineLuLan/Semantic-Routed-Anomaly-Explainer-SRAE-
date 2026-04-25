"""Phase 2 — AnomalyDetector behavior tests.

Verifies that the IsolationForest-backed detector flags the three
anomalies injected by `src.db.seed`:

  - traffic    = 5000   on day 3 at 02:00 UTC (2026-04-20 02:00)
  - sales      = 5      on day 5 at 11:00 UTC (2026-04-22 11:00)
  - error_rate = 12.5   on day 6 at 15:00 UTC (2026-04-23 15:00)

DB-backed tests carry the `requires_db` marker, so they skip cleanly
when Postgres is not running. Re-seed before running:
`python -m src.db.seed`.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.ml.detector import AnomalyDetector


@pytest.mark.requires_db
def test_detect_returns_contract_shape():
    results = AnomalyDetector().detect()

    assert isinstance(results, list)
    assert results, "expected at least the 3 injected anomalies"
    for r in results:
        assert set(r) >= {"timestamp", "metric", "value", "status"}
        assert r["status"] == "anomaly"
        assert isinstance(r["metric"], str)
        assert isinstance(r["value"], float)
        assert isinstance(r["timestamp"], str)


@pytest.mark.requires_db
def test_detect_flags_three_injected_anomalies():
    results = AnomalyDetector().detect()
    by_key = {(r["metric"], round(r["value"], 3)): r for r in results}

    expected = {
        ("traffic", 5000.0): datetime(2026, 4, 20, 2, 0, tzinfo=timezone.utc),
        ("sales", 5.0): datetime(2026, 4, 22, 11, 0, tzinfo=timezone.utc),
        ("error_rate", 12.5): datetime(2026, 4, 23, 15, 0, tzinfo=timezone.utc),
    }
    for key, expected_ts in expected.items():
        assert key in by_key, (
            f"missing injected anomaly {key}; flagged keys = {sorted(by_key)}"
        )
        assert by_key[key]["timestamp"] == expected_ts.isoformat()
