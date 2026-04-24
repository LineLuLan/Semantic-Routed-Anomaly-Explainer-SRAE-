# Semantic-Routed Anomaly Explainer (SRAE)

> Detect anomalies in business time-series data, route each anomaly to the
> nearest "playbook" via pgvector semantic search, and generate a
> human-readable explanation with a Groq-hosted LLM.

📄 **[BluePrint.md](BluePrint.md)** — architecture and I/O contracts.
🗺️ **[PLAN.md](PLAN.md)** — phase-by-phase execution plan with parallel-safety matrix.

---

## Architecture

```
Postgres ──► AnomalyDetector ──► SemanticRouter ──► Explainer ──► FastAPI ──► Streamlit
(time-series)  (IsolationForest)   (pgvector cosine)   (Groq Llama-3)
```

One Postgres instance is the single source of truth:
- **relational storage** for time-series metrics,
- **vector storage** (via the `pgvector` extension) for business-rule
  embeddings.

---

## Local setup

### 1. Prerequisites

- **Python 3.11+** (tested on 3.13).
- **Postgres 14+** with the **`pgvector`** extension installed.
  - Windows: install pgvector via the Stack Builder or build from
    [pgvector/pgvector](https://github.com/pgvector/pgvector).
  - Linux: `sudo apt install postgresql-16-pgvector` (adjust version).
  - macOS: `brew install pgvector`.

### 2. Create the database

```sql
CREATE DATABASE srae;
-- Then from any connection to the `srae` DB (needs superuser once):
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. Clone, venv, install

```bash
git clone https://github.com/LineLuLan/Semantic-Routed-Anomaly-Explainer-SRAE-.git
cd Semantic-Routed-Anomaly-Explainer-SRAE-

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 4. Configure secrets

```bash
cp .env.example .env
# then edit .env:
#   POSTGRES_URL=postgresql+psycopg2://<user>:<pwd>@localhost:5432/srae
#   GROQ_API_KEY=sk_...   # from https://console.groq.com/keys
```

### 5. Apply schema + seed mock data

```bash
python -m src.db.seed
```

This applies `src/db/schema.sql`, truncates the tables, then inserts
one week of hourly metrics (with three injected anomalies) plus a small
catalog of business rules embedded with `all-MiniLM-L6-v2` (384 dims).

To seed only the time-series (avoids the first-run embedding-model
download):

```bash
python -m src.db.seed --skip-rules
```

### 6. Run tests

```bash
pytest -v
```

Tests that need Postgres are marked `requires_db` and auto-skip if the
database is unreachable, so the suite runs cleanly regardless.

---

## Repo map (current: Phase 1)

```
src/
├── config.py            # env loader (.env + os.environ)
├── db/
│   ├── connection.py    # SQLAlchemy engine, session, ping()
│   ├── schema.sql       # CREATE EXTENSION vector + tables + index
│   └── seed.py          # mock data generator
├── ml/        (Phase 2 — upcoming)
├── router/    (Phase 3 — upcoming)
├── llm/       (Phase 4 — upcoming)
└── app/       (Phase 5 — upcoming)

tests/
└── test_db.py           # Phase 1 smoke tests
```

See [PLAN.md](PLAN.md) for the full parallel-execution matrix across
all five phases.

---

## Contributing / parallel work

Each phase owns a disjoint set of folders. To work on two phases at
once with zero merge conflicts, open a new branch per phase:

```bash
git checkout -b feat/phase-2-ml origin/main       # CLI A
git checkout -b feat/phase-3-router origin/main   # CLI B
git checkout -b feat/phase-4-llm origin/main      # CLI C
```

Commit after every small working unit. Push immediately. Open a PR
per branch when the phase is green.
