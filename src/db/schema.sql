-- SRAE schema (Postgres-only, time-series).
-- Run via: python -m src.db.seed  (which applies this file then seeds rows)
--
-- Vector storage was originally pgvector but was pivoted to ChromaDB
-- (see PLAN.md "Architecture Pivot Note") so this schema only contains
-- the relational time-series side. Rule embeddings live in `.chroma/`,
-- managed by Phase 3 (`src/router/`).

CREATE TABLE IF NOT EXISTS time_series_data (
    id          SERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ      NOT NULL,
    metric_name TEXT             NOT NULL,
    value       DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tsd_metric_ts
    ON time_series_data (metric_name, ts);
