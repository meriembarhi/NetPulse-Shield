# NetPulse-Shield

NetPulse-Shield is a local network security workflow for anomaly detection and remediation guidance.

Core flow: raw traffic CSV → anomaly detection → alerts → remediation advice → security report.

## What’s in the repo

- `clean_data.py` prepares the raw dataset.
- `detector.py` trains and runs an Isolation Forest detector.
- `advisor.py`, `solver.py`, and `remediator.py` generate remediation guidance.
- `dashboard.py` provides the Streamlit UI.
- `pipeline.py` runs the full workflow end to end from the command line.
- `tests/` contains unit and integration tests.

## Dashboard

The Streamlit dashboard includes these pages:

- Overview
- EDA & Insights
- Detected Alerts
- Security Report
- Audit Logs
- System Status
- Control Panel

The dashboard runs in dev mode without Redis. If Redis is available, it can queue advice generation jobs in the background; otherwise it falls back to synchronous processing.

## Requirements

- Python 3.10+
- The dependencies in `requirements.txt`
- Optional: Docker if you want Redis-backed background jobs

## Quick Start

1. Create and activate a virtual environment.

```bash
python -m venv .venv
source .venv/bin/activate  # or .\.venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
```

2. Prepare the dataset.

```bash
python clean_data.py
```

This generates `data/final_project_data.csv`, which is the main input used by the project.

3. Run the full pipeline.

```bash
python pipeline.py
```

This loads `data/final_project_data.csv`, detects anomalies, writes `alerts.csv`, and generates `Security_Report.txt`.

Common options:

```bash
python pipeline.py data/my_traffic.csv
python pipeline.py --no-persist
python pipeline.py --alerts-csv my_alerts.csv --report my_report.txt
```

4. Launch the dashboard.

```bash
streamlit run dashboard.py
```

The dashboard works in dev mode without Redis. If Redis is available, it can queue background advice jobs.

## Redis-backed background jobs

Redis is optional but recommended if you want asynchronous advice generation.

Start Redis with Docker:

```bash
docker run -p 6379:6379 redis:7
```

Then restart the dashboard. The System Status page will show whether Redis is connected.

## Tests

```bash
pytest tests/ -q
```

The repo currently includes passing detector, solver, and pipeline integration tests.

## Notes

- `DASHBOARD_TOKEN` enables a simple login gate in the dashboard.
- `alerts.csv` and `Security_Report.txt` are generated files.
- The model files in `models/` are cached artifacts used by the detector.

## License

MIT License