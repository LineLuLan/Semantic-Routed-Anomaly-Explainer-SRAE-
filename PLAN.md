# SRAE — Implementation Plan (Parallel-Ready)

> This is the **approved** implementation plan for building the Semantic-Routed Anomaly Explainer. It translates `BluePrint.md` into a concrete, phased execution roadmap with file-level ownership so that multiple Claude CLI instances can build in parallel without code conflicts.

---

## 1. Context

`BluePrint.md` defines SRAE — a Postgres-centric pipeline:

```
ML anomaly detection  →  pgvector semantic routing  →  Groq LLM explainer  →  FastAPI + Streamlit
```

This plan exists to satisfy two user requirements on top of the blueprint:

1. **Clear phases with parallel-safety labels** so 2–3 separate Claude CLIs can work simultaneously on different modules with zero merge conflicts.
2. **Tight commit + push cadence** — every small working feature is a single conventional commit pushed to `origin` immediately.

**Environment confirmed**
- Python 3.13, Windows 10.
- Local Postgres install (no Docker).
- GitHub remote: `https://github.com/LineLuLan/Semantic-Routed-Anomaly-Explainer-SRAE-.git`.
- `GROQ_API_KEY` in `.env` (gitignored). ⚠️ Key pasted in chat must be rotated before production use.

---

## 2. Repo layout (designed for conflict-free parallelism)

```
Semantic-Routed-Anomaly-Explainer-SRAE-/
├── .env.example              # Phase 1
├── .env                      # Phase 1 (GITIGNORED — real secrets)
├── .gitignore                # Phase 1
├── requirements.txt          # Phase 1 (shared — finalized here; frozen afterwards)
├── README.md                 # Phase 1 (setup steps)
├── BluePrint.md              # existing
├── PLAN.md                   # this file
├── src/
│   ├── __init__.py
│   ├── config.py             # Phase 1 — env loader
│   ├── db/                   # Phase 1 OWNER
│   │   ├── __init__.py
│   │   ├── connection.py     # SQLAlchemy engine + session
│   │   ├── schema.sql        # CREATE EXTENSION vector + tables
│   │   └── seed.py           # mock time_series + business_rules
│   ├── ml/                   # Phase 2 OWNER (isolated)
│   │   ├── __init__.py
│   │   └── detector.py       # AnomalyDetector class
│   ├── router/               # Phase 3 OWNER (isolated)
│   │   ├── __init__.py
│   │   └── semantic.py       # SemanticRouter class
│   ├── llm/                  # Phase 4 OWNER (isolated)
│   │   ├── __init__.py
│   │   └── explainer.py      # Groq client + prompt template
│   └── app/                  # Phase 5 OWNER
│       ├── __init__.py
│       ├── api.py            # FastAPI
│       └── streamlit_app.py  # Streamlit UI
└── tests/
    ├── test_db.py            # Phase 1
    ├── test_ml.py            # Phase 2
    ├── test_router.py        # Phase 3
    ├── test_llm.py           # Phase 4
    └── test_app.py           # Phase 5
```

---

## 3. Phase plan & parallel-safety matrix

| Phase | Branch | Owns (writes to) | Reads from | Parallel-safe with |
|---|---|---|---|---|
| **1. DB & Data Layer** | `feat/phase-1-db` | `src/db/**`, `src/config.py`, `.env.example`, `.gitignore`, `requirements.txt`, `README.md` | — | **Must run first, solo** |
| **2. ML Layer** | `feat/phase-2-ml` | `src/ml/**`, `tests/test_ml.py` | `src/db/connection.py`, `time_series_data` | **3, 4** |
| **3. Vector Layer** | `feat/phase-3-router` | `src/router/**`, `tests/test_router.py` | `src/db/connection.py`, `business_rules` | **2, 4** |
| **4. LLM Layer** | `feat/phase-4-llm` | `src/llm/**`, `tests/test_llm.py`, fixtures | `.env` for `GROQ_API_KEY` (no DB) | **2, 3** |
| **5. API + UI** | `feat/phase-5-app` | `src/app/**`, `tests/test_app.py` | all of 1–4 | **Must run last, solo** |

**Parallel execution recipe (after Phase 1 merges to main):**

```bash
# CLI-A (terminal 1)
git fetch origin && git checkout -b feat/phase-2-ml origin/main

# CLI-B (terminal 2)
git fetch origin && git checkout -b feat/phase-3-router origin/main

# CLI-C (terminal 3)
git fetch origin && git checkout -b feat/phase-4-llm origin/main
```

Each CLI writes to its own folder only → zero file-level overlap → clean PRs → merge in any order.

**Single shared-file rule:** `requirements.txt` is frozen at the end of Phase 1 with the full dependency set for Phases 2–5. No later branch edits it. This removes the only realistic conflict source.

---

## 4. Commit & push cadence

After **every small working unit** inside a phase:

1. `git add <specific files>` (never `git add -A`).
2. `git commit -m "<type>(<scope>): <short desc>"` — conventional commits.
3. `git push -u origin <branch>` — immediate, so you can inspect on GitHub.

**Example Phase 1 commit sequence (actual):**

- `chore: add .gitignore, .env.example, and requirements.txt`
- `docs: add project blueprint for SRAE architecture`
- `docs: add PLAN.md`
- `feat(db): add SQLAlchemy connection + config loader`
- `feat(db): add schema.sql with pgvector extension and tables`
- `feat(db): add seed script with mock time-series and business rules`
- `test(db): verify connection and schema`
- `docs(readme): add local Postgres setup steps`

At end of phase → `gh pr create` → review → merge → delete branch.

---

## 5. Module I/O contracts (locks interfaces so parallel phases don't drift)

### Phase 1 — tables

```sql
-- time_series_data
id           SERIAL PRIMARY KEY,
ts           TIMESTAMPTZ NOT NULL,
metric_name  TEXT NOT NULL,
value        DOUBLE PRECISION NOT NULL

-- business_rules
id                SERIAL PRIMARY KEY,
rule_text         TEXT NOT NULL,
suggested_action  TEXT NOT NULL,
embedding         vector(384)   -- all-MiniLM-L6-v2 dims
```

### Phase 2 — `AnomalyDetector.detect() → list[dict]`

```python
[{"timestamp": "2026-04-25T01:00:00", "metric": "traffic", "value": 5000.0, "status": "anomaly"}, ...]
```

### Phase 3 — `SemanticRouter.route(text: str) → dict`

```python
{"rule_text": "...", "suggested_action": "...", "distance": 0.12}
```

### Phase 4 — `Explainer.explain(anomaly: dict, rule: dict) → str`

Returns a single human-readable report string.

### Phase 5 — FastAPI

`POST /analyze` → runs detect → route (per anomaly) → explain → returns list of reports. Streamlit calls the API and renders results.

---

## 6. Skills in use

- **`postgresql`** — pgvector extension, indexes, cosine distance operator `<=>`.
- **`python`** — package structure, type hints, dotenv.
- **`fastapi`** — Phase 5 API (Pydantic models, DI).
- **`testing-toolkit`** — pytest fixtures and DB setup/teardown.
- **`commit-crafter`** — conventional commit messages.
- **`git-workflow`** — branches, PRs via `gh`.
- **`env-vars`** — `.env` + `python-dotenv`.
- **`quality-gate`** — lint/type check before each commit.

---

## 7. Verification (end-to-end)

**Phase 1**

```bash
python -m src.db.seed           # creates tables + seeds mock data
pytest tests/test_db.py -v
```

**Phase 2**

```bash
pytest tests/test_ml.py -v      # detector flags injected spike
```

**Phase 3**

```bash
pytest tests/test_router.py -v  # "late-night traffic" → bot-scraping rule (distance < 0.35)
```

**Phase 4**

```bash
pytest tests/test_llm.py -v     # Groq or mocked response, prompt renders
```

**Phase 5 (manual smoke)**

```bash
uvicorn src.app.api:app --reload                # terminal 1
streamlit run src/app/streamlit_app.py          # terminal 2
# Click "Analyze" → anomalies + routed rules + LLM explanations render
```

---

## 8. Risks & mitigations

- **Local Postgres missing `pgvector`** → Phase 1 detects and prints platform-specific install instructions before failing.
- **Windows `psycopg2-binary` install quirks** → fall back to `psycopg[binary]` (psycopg3) if needed.
- **Groq rate limits / invalid key** → Phase 4 ships a `--mock` mode so Phase 5 is testable without a live key.
- **⚠️ Exposed Groq key in chat** → rotate at console.groq.com before real use.

---

## 9. Execution order

1. **Solo, now:** Phase 1 on `feat/phase-1-db`, commit-per-step, push, open PR, merge.
2. **Parallel option:** open 2 more terminals/CLIs after merge; each works an isolated branch from the matrix in §3.
3. **Solo, last:** Phase 5 after 2/3/4 are all merged.
