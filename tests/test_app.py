"""Phase 5 — FastAPI integration tests.

Uses TestClient to drive the app through its real lifespan, so the
detector + router get loaded against the actual srae DB and Chroma
collection. Tests are gated on `requires_db` because /analyze and
/timeseries depend on the Postgres seed.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.app.api import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_root_endpoint(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "SRAE API"
    assert "/analyze" in body["endpoints"]


def test_health_endpoint(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in {"ok", "degraded"}
    assert isinstance(body["postgres"], bool)
    assert isinstance(body["chroma"], bool)
    assert isinstance(body["groq_configured"], bool)


@pytest.mark.requires_db
def test_analyze_with_mock_llm_returns_reports(client: TestClient) -> None:
    r = client.post("/analyze?mock=true&limit=5")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mock_llm"] is True
    assert body["total_anomalies"] >= 3, "expected at least 3 injected anomalies"
    assert body["returned"] == min(5, body["total_anomalies"])

    for report in body["reports"]:
        assert set(report) >= {
            "timestamp",
            "metric",
            "value",
            "status",
            "rule_text",
            "suggested_action",
            "distance",
            "explanation",
        }
        assert report["status"] == "anomaly"
        assert report["explanation"].startswith("[MOCK]")


@pytest.mark.requires_db
def test_analyze_flags_known_injections(client: TestClient) -> None:
    r = client.post("/analyze?mock=true&limit=100")
    assert r.status_code == 200
    body = r.json()
    triples = {(r["metric"], round(r["value"], 3)) for r in body["reports"]}

    assert ("traffic", 5000.0) in triples
    assert ("sales", 5.0) in triples
    assert ("error_rate", 12.5) in triples


@pytest.mark.requires_db
def test_timeseries_returns_points(client: TestClient) -> None:
    r = client.get("/timeseries?metric=traffic&limit=500")
    assert r.status_code == 200
    body = r.json()
    assert len(body["points"]) == 168  # 7 days * 24 hours
    for p in body["points"]:
        assert p["metric"] == "traffic"
        assert isinstance(p["value"], float)


def test_cors_headers_for_localhost_3000(client: TestClient) -> None:
    r = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    # CORS preflight should respond with allow-origin
    assert r.status_code in (200, 204)
    assert r.headers.get("access-control-allow-origin") in (
        "http://localhost:3000",
        "*",
    )
