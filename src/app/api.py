"""SRAE FastAPI application.

Exposes:
- GET  /health    — liveness probe (Postgres + Chroma reachability).
- POST /analyze   — run the full pipeline:
    detect anomalies (Phase 2)
      → batch-route via SemanticRouter (Phase 3)
        → explain via LLM Explainer (Phase 4, parallelized in live mode)
          → return list[AnalysisReport].
- GET  /timeseries — raw rows for charts.

Heavy clients (SentenceTransformer in Router, IsolationForest model in
Detector) are instantiated once at startup via the FastAPI lifespan and
reused across requests.
"""

from __future__ import annotations

from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select

from src.db.connection import TimeSeriesData, get_session, ping
from src.llm.explainer import Explainer
from src.ml.detector import AnomalyDetector
from src.router.semantic import SemanticRouter


class AnalysisReport(BaseModel):
    timestamp: str
    metric: str
    value: float
    status: str
    rule_text: str | None
    suggested_action: str | None
    distance: float
    confidence: str
    explanation: str


class AnalyzeResponse(BaseModel):
    total_anomalies: int
    returned: int
    mock_llm: bool
    by_metric: dict[str, int]
    reports: list[AnalysisReport]


class HealthResponse(BaseModel):
    status: str
    postgres: bool
    chroma: bool
    groq_configured: bool


class TimeSeriesPoint(BaseModel):
    timestamp: str
    metric: str
    value: float


class TimeSeriesResponse(BaseModel):
    points: list[TimeSeriesPoint]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.detector = AnomalyDetector()
    try:
        app.state.router = SemanticRouter()
    except Exception as exc:
        # Chroma collection may not be seeded yet — surface as a clear error
        # rather than crashing the whole app.
        app.state.router = None
        app.state.router_error = str(exc)
    else:
        app.state.router_error = None
    yield


app = FastAPI(
    title="SRAE — Semantic-Routed Anomaly Explainer",
    description="Detect anomalies in time-series data, route to a business "
    "playbook via cosine similarity, and explain with an LLM.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    from src.config import settings

    postgres_ok = ping()
    chroma_ok = app.state.router is not None
    return HealthResponse(
        status="ok" if (postgres_ok and chroma_ok) else "degraded",
        postgres=postgres_ok,
        chroma=chroma_ok,
        groq_configured=settings.has_groq_key,
    )


def _parse_iso(label: str, value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        # `fromisoformat` accepts "Z" since Python 3.11+.
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid ISO 8601 value for {label!r}: {value!r} ({exc})",
        ) from exc


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(
    limit: int = Query(default=10, ge=1, le=100),
    mock: bool = Query(default=False, description="Use mock LLM (fast, deterministic)"),
    since: str | None = Query(default=None, description="ISO 8601 lower bound"),
    until: str | None = Query(default=None, description="ISO 8601 upper bound"),
) -> AnalyzeResponse:
    if app.state.router is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "SemanticRouter unavailable — run `python -m src.router.seed_chroma` "
                f"first. Cause: {app.state.router_error}"
            ),
        )

    since_dt = _parse_iso("since", since)
    until_dt = _parse_iso("until", until)

    anomalies = app.state.detector.detect(since=since_dt, until=until_dt)
    total = len(anomalies)
    by_metric = dict(Counter(a["metric"] for a in anomalies))
    if not anomalies:
        return AnalyzeResponse(
            total_anomalies=0,
            returned=0,
            mock_llm=mock,
            by_metric=by_metric,
            reports=[],
        )

    # Sort newest first so the UI shows recent issues at the top.
    anomalies.sort(key=lambda a: a["timestamp"], reverse=True)
    selected = anomalies[:limit]

    # 1× encode + 1× Chroma round-trip for the whole batch.
    queries = [
        f"Metric '{a['metric']}' reached {a['value']} at {a['timestamp']} ({a['status']})."
        for a in selected
    ]
    rules = app.state.router.route_many(queries)

    # Parallel Groq calls in live mode; in-process map in mock mode.
    explainer = Explainer(mock=mock)
    explanations = explainer.explain_many(zip(selected, rules))

    reports: list[AnalysisReport] = []
    for anomaly, rule, explanation in zip(selected, rules, explanations):
        reports.append(
            AnalysisReport(
                timestamp=anomaly["timestamp"],
                metric=anomaly["metric"],
                value=anomaly["value"],
                status=anomaly["status"],
                rule_text=rule["rule_text"],
                suggested_action=rule["suggested_action"],
                distance=rule["distance"],
                confidence=rule["confidence"],
                explanation=explanation,
            )
        )

    return AnalyzeResponse(
        total_anomalies=total,
        returned=len(reports),
        mock_llm=mock,
        by_metric=by_metric,
        reports=reports,
    )


@app.get("/timeseries", response_model=TimeSeriesResponse)
def timeseries(
    metric: str | None = Query(default=None, description="Filter by metric name"),
    limit: int = Query(default=1000, ge=1, le=5000),
    since: str | None = Query(default=None, description="ISO 8601 lower bound"),
    until: str | None = Query(default=None, description="ISO 8601 upper bound"),
) -> TimeSeriesResponse:
    since_dt = _parse_iso("since", since)
    until_dt = _parse_iso("until", until)

    stmt = select(TimeSeriesData).order_by(
        TimeSeriesData.metric_name, TimeSeriesData.ts
    )
    if metric:
        stmt = stmt.where(TimeSeriesData.metric_name == metric)
    if since_dt is not None:
        stmt = stmt.where(TimeSeriesData.ts >= since_dt)
    if until_dt is not None:
        stmt = stmt.where(TimeSeriesData.ts <= until_dt)
    stmt = stmt.limit(limit)

    with get_session() as session:
        rows = session.execute(stmt).scalars().all()

    points = [
        TimeSeriesPoint(
            timestamp=r.ts.isoformat(),
            metric=r.metric_name,
            value=r.value,
        )
        for r in rows
    ]
    return TimeSeriesResponse(points=points)


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "name": "SRAE API",
        "version": "0.2.0",
        "endpoints": ["/health", "/analyze", "/timeseries"],
        "ui": "http://localhost:3000",
    }
