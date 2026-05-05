# NetPulse-Shield

NetPulse-Shield is a local network-security workflow for anomaly detection, alert storage, remediation advice, and reporting. The repository supports three ways to run the system:

- interactive dashboard work in `dashboard.py`
- one-command automation in `pipeline.py`
- background advice generation with Redis/RQ and the RAG layer

The current implementation is labels-aware, automatically tunes contamination when labels are present, and falls back safely when they are not.

## What the project does

1. Clean raw UNSW-NB15 data.
2. Select a fixed, domain-guided feature set.
3. Train or load an Isolation Forest detector.
4. Flag anomalies and persist alerts.
5. Generate remediation advice with either RAG or an optional LLM path.
6. Expose the results in a Streamlit dashboard, CSV outputs, and a SQLite database.

## Pipeline Schemas

### 1. Data preparation pipeline

```text
raw UNSW-NB15 CSV
	-> clean_data.py
	-> feature selection + filtering
	-> data/final_project_data.csv
```

Purpose:
- keep the project’s input schema consistent
- reduce the raw dataset to the fields the detector actually uses
- make the downstream detector predictable and reproducible

Current selected feature set:

```text
sttl, dttl, sbytes, dbytes, Sload, Dload, sloss, dloss, Spkts, Dpkts, tcprtt, Sjit, Label
```

### 2. Detection pipeline

```text
data/final_project_data.csv
	-> detector.py
	-> preprocess()
	-> train() or load saved model
	-> analyze()
	-> anomaly score + anomaly flag
	-> alerts.csv + alerts.db
```

Purpose:
- standardize numeric features
- fit or reuse the Isolation Forest model
- detect suspicious flows
- save machine-readable and human-readable outputs

### 3. Contamination selection pipeline

```text
Label column present
	-> use real attack rate

No usable labels
	-> tune_contamination() on validation split

If tuning fails
	-> fallback contamination = 0.05
```

Purpose:
- avoid hard-coding one anomaly rate for every dataset
- prefer labels when they exist
- use F1-based tuning when labels are available but need optimization
- keep the system working even when labels are missing

### 4. Remediation and advice pipeline

```text
alert row
	-> tasks.py
	-> advisor.py
	-> knowledge_base.py + embeddings.py
	-> FAISS retrieval or TF-IDF fallback
	-> remediation text
	-> alerts.db audit/update
```

Purpose:
- turn raw anomalies into analyst-friendly guidance
- use semantic retrieval instead of keyword matching only
- remain functional offline through TF-IDF fallback

### 5. Optional LLM remediation pipeline

```text
alert / anomaly text
	-> remediator.py or auto_remediator.py
	-> Ollama / Llama 3
	-> structured security report
	-> Security_Report.txt
```

Purpose:
- produce more generative, free-form remediation notes
- offer Cisco-style guidance when Ollama is available
- provide a separate path from the RAG system

## Runtime Orchestration

### Interactive dashboard flow

```text
open dashboard.py
	-> auto-run detection on page load
	-> tune contamination if Label exists
	-> run analysis
	-> write alerts.csv
	-> persist alerts in alerts.db
	-> allow advice generation through Redis/RQ or sync fallback
```

### Batch pipeline flow

```text
python pipeline.py
	-> validate CSV
	-> run detection
	-> save alerts.csv
	-> generate Security_Report.txt
```

### Background worker flow

```text
dashboard.py
	-> queue advice job
	-> Redis broker
	-> rq worker advisor
	-> tasks.generate_advice_for_alert()
	-> advisor.py RAG lookup
	-> write advice to alerts.db
```

## Repository Layout and Purpose

- `clean_data.py` prepares the final dataset used by the detector.
- `detector.py` trains, loads, and runs the anomaly detector. It saves:
  - `models/netpulse_model.joblib`
  - `models/netpulse_model_scaler.joblib`
  - `models/netpulse_model_features.joblib`
  - `models/netpulse_model_metadata.json`
- `dashboard.py` is the Streamlit UI. It now auto-runs analysis on load and supports manual reruns and advice generation.
- `pipeline.py` is the canonical CLI for full automation and report generation.
- `db.py` defines SQLite persistence for `Alert` and `AuditLog`.
- `tasks.py` contains the RQ job function for async advice generation.
- `advisor.py` implements the RAG-style remediation advisor.
- `embeddings.py` builds the vector store and handles the embedding fallback.
- `knowledge_base.py` stores the built-in remediation knowledge.
- `remediator.py` and `auto_remediator.py` provide the optional Ollama / LLM-based remediation path.
- `system_utils.py` provides Redis health checks, queue stats, and enqueue helpers.
- `docker-compose.yml` defines `redis`, `web`, and `worker` services.
- `Dockerfile` builds the Streamlit application image.
- `tests/` contains detector and pipeline tests.

## Important Outputs

- `data/final_project_data.csv` - cleaned dataset used by the detector
- `alerts.csv` - top alerts written by the detector or pipeline
- `alerts.db` - SQLite database for alerts and audit logs
- `models/` - saved model artifacts and metadata
- `Security_Report.txt` - generated remediation report from the pipeline or LLM path

## How the major pieces work

### `clean_data.py`

Purpose: transform raw data into a stable 12-feature dataset.

Why it matters:
- keeps the detector schema predictable
- reduces noise from unused raw columns
- ensures the model trains on the same core inputs every time

### `detector.py`

Purpose: detect anomalies and persist the trained detector.

Behavior:
- loads existing model artifacts if available
- discovers numeric features during training
- saves the exact feature list used at train time
- chooses contamination from labels, tuning, or fallback
- writes anomaly scores and anomaly flags for each row

### `advisor.py`

Purpose: convert an alert description into remediation guidance.

Behavior:
- loads the knowledge base
- splits it into chunks
- builds a FAISS vector store
- retrieves the most relevant remediation snippets
- falls back to generic advice if retrieval fails

### `embeddings.py`

Purpose: provide vector embeddings for semantic search.

Behavior:
- tries HuggingFace sentence-transformer embeddings first
- falls back to local TF-IDF embeddings if needed
- keeps the RAG layer usable offline

### `tasks.py`

Purpose: run advice generation in the background.

Behavior:
- loads the alert from the DB
- creates a short anomaly description
- calls `NetworkSecurityAdvisor`
- stores the advice and audit log entry

### `dashboard.py`

Purpose: provide the human-facing control surface.

Behavior:
- auto-runs detection on page load
- lets you rerun analysis manually
- enqueues advice jobs when Redis is available
- falls back to synchronous advice generation when Redis is not available

### `pipeline.py`

Purpose: run the full project non-interactively.

Behavior:
- validates the input CSV
- runs anomaly detection
- saves alerts
- generates a security report
- is the best entrypoint for automation, CI, and batch execution

### `db.py`

Purpose: store alerts and audit logs in SQLite.

Tables:
- `Alert` stores each anomaly, its score, its serialized features, and advice fields.
- `AuditLog` stores user and worker actions for traceability.

## Deployment Options

### Local development

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python clean_data.py
streamlit run dashboard.py
```

### Batch automation

```bash
python pipeline.py
```

Optional flags:

- `--no-persist` - skip DB writes
- `--alerts-csv <path>` - change the alerts output path
- `--report <path>` - change the report output path

### Docker Compose deployment

```bash
docker-compose up --build
```

Services:
- `redis` - queue broker
- `web` - Streamlit dashboard
- `worker` - background RQ worker

### Optional Ollama / LLM path

This path is separate from the default RAG workflow. It requires a local Ollama installation, the Ollama service running, and a downloaded model such as `llama3`.

```bash
ollama serve
python remediator.py
python auto_remediator.py
```

## Dependencies

Core packages come from `requirements.txt`:

- `scikit-learn`, `pandas`, `numpy`, `joblib` for detection
- `streamlit`, `plotly` for the dashboard
- `SQLAlchemy` for SQLite persistence
- `langchain`, `langchain-community`, `langchain-core`, `langchain-text-splitters` for RAG orchestration
- `sentence-transformers` and `faiss-cpu` for semantic retrieval
- `redis` and `rq` for background jobs
- `ollama` for the optional local LLM path, plus the Ollama app/service and a local model download

## Recommended usage

1. If you want the simplest full run, use `python pipeline.py`.
2. If you want interactive triage, use `streamlit run dashboard.py`.
3. If you want the default remediation engine, use the RAG path exposed by `solver.py` / `advisor.py`.
4. If you want the LLM-only path, start Ollama first, then run `remediator.py` or `auto_remediator.py`.

## Testing and validation

```bash
pytest tests/ -q
ruff check .
```

## Troubleshooting

- If `alerts.csv` is missing, run `python detector.py` or `python pipeline.py`.
- If contamination tuning fails, the detector falls back to `0.05`.
- If Redis is unavailable, the dashboard uses synchronous advice generation.
- If Ollama is unavailable, the RAG advisor still works and the LLM path cannot run.
- If the detector complains about schema mismatch, regenerate `data/final_project_data.csv` and retrain so the saved feature list matches the input.

## License

MIT License