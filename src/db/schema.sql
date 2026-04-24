-- SRAE schema
-- Run via: python -m src.db.seed  (which applies this file then seeds rows)
-- pgvector must be installed in the Postgres instance (CREATE EXTENSION
-- requires superuser the first time).

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS time_series_data (
    id          SERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ      NOT NULL,
    metric_name TEXT             NOT NULL,
    value       DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tsd_metric_ts
    ON time_series_data (metric_name, ts);

CREATE TABLE IF NOT EXISTS business_rules (
    id               SERIAL PRIMARY KEY,
    rule_text        TEXT        NOT NULL,
    suggested_action TEXT        NOT NULL,
    embedding        vector(384) NOT NULL
);

-- IVFFlat index for cosine distance (<=> operator).
-- `lists` is a small number for our seed size; tune upwards on real data.
CREATE INDEX IF NOT EXISTS idx_rules_embedding_cosine
    ON business_rules
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 10);
