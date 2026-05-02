# NetPulse-Shield — One-Page Handout

Purpose: a concise, beginner-friendly summary you can share. Covers CI, Ruff, the DB, system flow, commands, and a short glossary.

---

1) CI (Continuous Integration)
- What: Automated checks that run on every push/PR (tests, linting).
- Why: Catches regressions early and ensures code stays healthy.
- How to show it: run locally with the same commands CI uses:

```bash
# Lint (what CI runs)
ruff check .

# Tests
pytest -q
```

2) Ruff (linter)
- What: A fast tool that enforces code style and finds simple bugs.
- Examples:
  - `F401`: import is unused — remove it.
  - `E711`: compare to None using `is None`, not `== None`.
- How to run: `ruff check .`

3) `db.py` (what it is and what it does)
- Purpose: a small persistence layer using SQLite and SQLAlchemy to store Alerts and AuditLogs.
- Key objects:
  - `Alert`: one detected anomaly. Fields include `id`, `created_at`, `anomaly_score`, `is_anomaly`, `severity`, `status`, `feature_json`, `advice`, `advice_job_id`, `advice_status`.
  - `AuditLog`: records actions (who did what and when).
- Key helpers:
  - `create_db(db_path)`: creates DB and tables.
  - `get_session(db_path)`: returns a session to read/write rows.
  - `persist_alerts_from_df(df, db_path)`: insert alerts from a pandas DataFrame.
- Simple concept: you call `session.add(obj)` then `session.commit()` to save.

4) System flow (step-by-step)
- Data: CSV input in `data/`.
- Detection: `detector.py` reads CSV, computes anomalies, optionally persists to DB.
- Dashboard: Streamlit UI (`dashboard.py`) reads alerts from DB and shows them.
- Triage: analyst updates `status` in UI; each change writes an `AuditLog`.
- Advice generation (two modes):
  1. Background (recommended): dashboard enqueues jobs to Redis via RQ; a worker runs `tasks.generate_advice_for_alert` and writes advice back into DB.
  2. Synchronous (fallback): if Redis isn't available, dashboard runs advice generation directly (blocks UI but keeps functionality).

5) Commands to run the stack locally

Virtualenv + install:
```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run dashboard (no Redis):
```bash
streamlit run dashboard.py
```

Run Redis (for background jobs):
```bash
docker run -p 6379:6379 redis:7
```

Start a worker (in the venv):
```bash
rq worker advisor
```

Or run everything with Docker Compose:
```bash
docker-compose up --build
```

6) Short glossary (one-line definitions to repeat)
- CI: automated checks run on code changes (tests + lint).
- Ruff: Python linter that enforces rules and finds small bugs.
- SQLite: tiny file-based database (no server required).
- SQLAlchemy: library that maps Python classes to DB tables (ORM).
- Redis: fast in-memory store used as a job queue backend.
- RQ: Redis Queue, a simple Python task queue.
- Worker: background process that executes queued jobs.
- AuditLog: table storing user/worker actions for traceability.

---

If you want I can also:
- Export this file to PDF and attach it, or
- Produce a one-slide slide or printable PDF with the same content.

File: HANDOUT.md — created in the repository root.
