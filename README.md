# NetPulse-Shield

A self-contained local network-security workflow for anomaly detection, advice generation, and lightweight remediation guidance. This README explains the project structure, how the pieces fit together, and step-by-step developer and user workflows.

Core flow: raw traffic CSV → preprocessing → model train / inference → alerts → advice generation → security report / dashboard.

**Quick summary:** Use `pipeline.py` for a one-command end-to-end run, or `dashboard.py` to operate interactively (with optional Redis/RQ for background jobs).

**Table of contents**

- Project structure
- How it works (high-level)
- Getting started (install, run, retrain)
- Dashboard guide
- Files and responsibilities (file-by-file)
- Developer workflows (tests, linting, retraining)
- Troubleshooting & common issues
- License

---

**Project structure**

- `advisor.py`: high-level orchestration for generating remediation advice (sync fallback and wrappers used by the dashboard and tasks).
- `auto_remediator.py`: helper utilities to perform automated remediation actions (if enabled) — optional and careful use only.
- `clean_data.py`: dataset cleaning and feature engineering pipeline that writes `data/final_project_data.csv`.
- `db.py`: SQLite + SQLAlchemy models and helpers (`Alert`, `AuditLog`) and persistence helpers used by the dashboard and tasks.
- `detector.py`: anomaly detection pipeline (preprocess, train, analyze). Persists model, scaler, `features.joblib`, and `metadata.json` into `models/`.
- `embeddings.py` and `knowledge_base.py`: utilities for RAG/fallback advice when language model assistance is used.
- `remediator.py`: constructs remediation actions (textual guidance) and integrates with `advisor.py`.
- `pipeline.py`: CLI entrypoint that runs the end-to-end flow: read CSV → detect anomalies → persist alerts → generate security report.
- `dashboard.py`: Streamlit app providing interactive exploration, triage, and advice generation (supports async Redis/RQ queue with sync fallback).
- `tasks.py`: RQ tasks for background advice generation — used when Redis is available.
- `models/`: persisted artifacts (model, scaler, feature list, metadata). See [models/](models/README.md) for details.
- `data/`: input datasets and generated CSVs (e.g., `final_project_data.csv`, sample traffic fixtures).
- `tests/`: pytest tests for detector, solver, and pipeline integration.

---

**How it works (high-level)**

- Preprocessing: `clean_data.py` prepares features and writes a canonical CSV. `detector.preprocess()` expects the features listed in `models/features.joblib` (training saves this file).
- Training: `detector.train()` fits a `StandardScaler` + `IsolationForest` and saves `models/netpulse_model.joblib`, `models/netpulse_model_scaler.joblib`, `models/features.joblib`, and `models/metadata.json` (model version, contamination, features list).
- Inference: `detector.analyze()` loads the saved scaler/model/features, validates incoming CSV schema, runs detection, and returns an alerts DataFrame; `db.persist_alerts_from_df()` can save alerts to SQLite.
- Advice: `advisor.py` / `solver.py` and `remediator.py` convert an alert into human-readable remediation advice; `tasks.generate_advice_for_alert()` runs this work in background when queued.
- Dashboard: `dashboard.py` shows charts, the list of alerts, status of Redis/queues, and allows bulk or single alert advice generation (sync fallback if Redis unavailable).

---

**Getting started (development)**

1) Create and activate virtual environment

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS / Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Prepare dataset (the repository includes sample CSVs):

```bash
python clean_data.py
```

This writes `data/final_project_data.csv` used by `pipeline.py` and the dashboard.

3) Run the full pipeline (end-to-end)

```bash
python pipeline.py
```

Options:
- `--no-persist` : run detection but do not persist alerts to DB or disk.
- `--alerts-csv <path>` : write alerts CSV to a custom path.
- `--report <path>` : write the security report to a custom path.

4) Run the dashboard (interactive)

```bash
streamlit run dashboard.py
```

If you want background job processing with Redis/RQ (recommended for production or long-running advice generation), run Redis (Docker example below) and start an RQ worker:

```bash
# start Redis (local Docker)
docker run -p 6379:6379 redis:7

# in another terminal, run an RQ worker
rq worker advisor --url redis://localhost:6379
```

The dashboard detects Redis availability automatically and will enqueue tasks if possible.

---

**Dashboard guide (pages & controls)**

- **Overview**: high-level metrics — total processed flows, detected anomalies, alerts trend.
- **EDA & Insights**: interactive plots (Plotly) for feature distributions and outlier overlays.
- **Detected Alerts**: table of anomalies, filterable by severity, with action buttons to generate advice.
- **Security Report**: aggregated report written by `pipeline.py` and downloadable from the UI.
- **Audit Logs**: shows `AuditLog` entries from `db.py` for jobs and user actions.
- **System Status**: shows Redis connection, queue length, and last worker heartbeat.
- **Control Panel**: run detection on-demand, retrain model, or bulk enqueue advice. `DASHBOARD_TOKEN` can be used to enable a simple login gate (see environment variables below).

Environment variables used by the dashboard:

- `DASHBOARD_TOKEN` : optional simple access token for the UI.
- `DATABASE_URL` : optional override for SQLite path (default `sqlite:///netpulse.db`).
- `REDIS_URL` : Redis connection URL (default `redis://localhost:6379`).

---

**Files and responsibilities (file-by-file)**

- `clean_data.py` — input: raw CSV(s) in `data/`; output: cleaned `final_project_data.csv`. Use this to add or modify features.
- `detector.py` — key functions:
	- `preprocess(df, training=False)` : validates and transforms incoming DataFrame; in training mode it accepts the input schema and saves `features.joblib`.
	- `train(df, contamination=0.01)` : fits the scaler and `IsolationForest`, and saves artifacts to `models/`.
	- `analyze(df)` : runs inference using saved artifacts and returns alerts DataFrame.

- `db.py` — SQLAlchemy ORM models:
	- `Alert` : persisted alert with fields like `id`, `created_at`, `feature_json`, `score`, and `advice`.
	- `AuditLog` : records background job events and user operations for traceability.

- `tasks.py` — RQ task entrypoints invoked by the dashboard; e.g., `generate_advice_for_alert(alert_id, db_path)` will compute advice and update the DB.

- `advisor.py`, `solver.py`, `remediator.py` — multiple layers of advice generation:
	- `solver.py` provides rule-based or heuristic mappings from alert features to likely causes.
	- `advisor.py` orchestrates LLM or embedding-based fallbacks (RAG via `embeddings.py` and `knowledge_base.py`) when available.
	- `remediator.py` formats suggested remediation steps.

- `pipeline.py` — CLI glue: accepts input CSV, runs `detector.analyze()` or `train()` when needed, persists outputs, and collects advice for top alerts.

---

**Developer workflows**

- Run tests:

```bash
pytest tests/ -q
```

- Linting (ruff):

```bash
ruff check .
```

- Re-train model (force new model artifacts):

```bash
python -c "from detector import train; import pandas as pd; df = pd.read_csv('data/final_project_data.csv'); train(df, contamination=0.01)"
```

- Recreate the DB (if you need a clean DB):

```bash
python -c "from db import create_db; create_db('sqlite:///netpulse.db')"
```

---

**Troubleshooting & common issues**

- Port 6379 already in use when starting Redis (Docker): stop the conflicting container or map to another host port with `-p 6380:6379` and set `REDIS_URL` accordingly.
- Missing dependencies in `.venv`: ensure you activate the correct virtualenv and run `pip install -r requirements.txt`.
- Feature/Schema mismatch error in `detector` ("Label present at fit-time but missing at transform-time"): re-run training (`detector.train()`) to re-generate `models/features.joblib` or ensure the input CSV has the same columns as `models/features.joblib`.
- Dashboard shows no Redis: verify `REDIS_URL` and that Redis is reachable from the machine where the dashboard runs.
- Tests failing after local edits: run `pytest -q` and inspect the failing assertions in `tests/`; update `models/` artifacts if tests depend on cached artifacts.

---

**Operational notes**

- Model artifacts are stored under `models/`. Keep this folder in `.gitignore` for production (unless you intentionally commit a baseline model).
- Use the RQ worker named `advisor` to process advice tasks: `rq worker advisor --url redis://localhost:6379`.
- Back up `netpulse.db` (or your configured SQLite path) if you want to preserve alerts and audit logs between runs.

---

If you'd like, I can:

- Expand this README with step-by-step screenshots or Streamlit page navigation notes.
- Add a short `CONTRIBUTING.md` describing how to add new rules to `solver.py` or add new features in `clean_data.py`.

---

## License

MIT License