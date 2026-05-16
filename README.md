# NetPulse-Shield

NetPulse-Shield is an intelligent, Python-based security framework that bridges real-time network monitoring with incident response. It combines **Anomaly Detection (Isolation Forest)** with a **RAG (Retrieval-Augmented Generation) pipeline** to identify threats and deliver expert-level remediation advice. The entire framework runs 100% locally with no external API keys required.

The dashboard is inspired by **Kaspersky CyberMap** (https://cybermap.kaspersky.com/) and includes a **3D rotating globe** with animated attack arcs, real-time counters, and a professional SOC-themed interface.

---

## Features

| Component | Technology | Purpose |
|:---|---:|:---|
| **`clean_data.py`** | Pandas | Preprocesses and normalizes raw network logs (sttl, sbytes, Sload, etc.) |
| **`detector.py`** | Scikit-learn (Isolation Forest) | Unsupervised ML anomaly detection with dynamic contamination tuning |
| **`advisor.py`** | LangChain + FAISS | RAG engine performing semantic similarity search against expert knowledge |
| **`embeddings.py`** | Sentence-Transformers / TF-IDF | Vector engine with offline fallback for air-gapped environments |
| **`remediator.py`** | Ollama (Llama 3) | LLM synthesis generating Cisco IOS ACL commands and risk reports |
| **`solver.py`** | RAG Pipeline | Orchestrator: alerts -> FAISS search -> structured Security_Report.txt |
| **`app.py`** | Flask + Plotly.js + vis-network | Full SOC web dashboard with 3D globe, link analysis graph, and pipeline controls |
| **`dashboard.py`** | Streamlit + Plotly | Alternate SOC dashboard with KPI cards and pipeline controls |
| **`email_notifier.py`** | smtplib | Send email alerts for high-confidence attacks and weekly summaries |

---

## Project Structure

```
NetPulse-Shield/
├── src/                        # Core pipeline modules
│   ├── clean_data.py           # Data preprocessing & feature selection
│   ├── detector.py             # Isolation Forest anomaly detector
│   ├── solver.py               # RAG orchestrator (alerts -> report)
│   ├── remediator.py           # Ollama Llama 3 advanced synthesis
│   ├── auto_remediator.py      # Auto-generated remediation via Ollama
│   ├── advisor.py              # FAISS semantic search engine
│   ├── embeddings.py           # Vector embeddings (online + offline)
│   ├── knowledge_base.py       # Curated security intelligence repository
│   ├── pipeline_runner.py      # Safe subprocess execution for all pipeline steps
│   ├── cyber_attack_map.py     # 3D rotating globe with animated attack arcs
│   ├── email_notifier.py       # SMTP email alert system
│   ├── email_scheduler.py      # Weekly summary scheduler
│   ├── email_api.py            # REST API for email triggers
│   └── email_server.py         # Background email monitoring server
├── data/
│   ├── raw/                    # Raw UNSW-NB15 CSV files
│   ├── processed/              # Cleaned dataset (50k rows, 6 features)
│   └── outputs/                # Generated alerts.csv and Security_Report.txt
├── models/                     # Serialized Isolation Forest + Scaler
├── templates/                  # Flask HTML templates
│   └── index.html              # SOC Dashboard template
├── static/
│   ├── css/style.css           # Dashboard styles
│   └── js/app.js               # Client-side dashboard logic
├── docs/                       # Documentation
│   ├── EMAIL_NOTIFICATIONS.md  # Email setup guide
│   └── remediation_knowledge.txt
├── tests/                      # pytest unit tests
├── app.py                      # Flask web dashboard (primary entry point)
├── dashboard.py                # Streamlit SOC dashboard (alternate)
├── requirements.txt
└── .env                        # Email credentials (Gmail App Password)
```

---

## Quick Start

### 1. Install

```bash
pip install -r requirements.txt
```

### 2. Prepare Data

Place your UNSW-NB15 (or similar) CSV in `data/`, then:

```bash
python src/clean_data.py
```

If cleaned data already exists at `data/processed/final_project_data.csv`, the script skips processing automatically.

### 3. Launch the Dashboard

Choose your preferred interface:

#### Flask Dashboard (Recommended)
```bash
python app.py
```

Opens at **http://localhost:5000** with:
- **SOC Metrics** — Traffic records, detected alerts, normal traffic, critical counts
- **Link Analysis Graph** — Interactive network graph with severity-colored nodes
- **Global Threat Map** — 3D rotating globe with animated attack arcs
- **24h Attack Timeline** — Hourly attack distribution chart
- **Alerts Table** — Filterable by severity and attack type
- **Traffic Viewer** — Raw data preview with feature histograms
- **Security Report** — AI-generated remediation report with HTML/TXT/PDF export
- **Email Settings** — Configure SMTP and send alert emails
- **System Status** — Component health monitoring

#### Streamlit Dashboard (Alternate)
```bash
streamlit run dashboard.py
```

Opens at **http://localhost:8501** with:
- **Overview** — SOC metrics, traffic distribution, attack category breakdown
- **Threat Map** — 3D rotating globe with animated attack arcs
- **Traffic** — DataFrame preview + feature histograms
- **Alerts** — Filterable alert table with score distribution
- **Report** — Security report viewer with download
- **Email** — SMTP config, test & send
- **Status** — File & component status

### 4. Run Pipeline (One-Click)

From either dashboard sidebar:
1. **Clean Data** — Preprocess raw logs
2. **Run Detection** — Isolation Forest anomaly detection
3. **Generate Report** — RAG remediation report
4. **Full Pipeline** — All steps sequentially

### 5. Optional: Advanced AI with Ollama

```bash
ollama pull llama3
python src/remediator.py     # Advanced LLM-based Cisco ACL generation
```

---

## Pipeline Architecture

```
[ Raw CSV Data ]
       |
( clean_data.py ) -> Preprocesses + normalizes network features
       |
( detector.py )   -> Isolation Forest -> alerts.csv
       |
[ alerts.csv ]    <- Pre-flight check (solver verifies this exists)
       |
( solver.py )     -> FAISS similarity search via advisor.py
       |              + knowledge_base.py (security manuals)
       |
[ Security_Report.txt ]  <- Structured remediation advice
       |
( remediator.py - optional )
       + Ollama Llama 3   -> Advanced AI synthesis + Cisco IOS ACL commands
```

---

## Dashboard Preview

The dashboards feature:
- **Dark SOC theme** with gradient headers and KPI cards
- **3D rotating globe** with animated attack arcs
- **Link Analysis** — vis-network interactive graph of traffic nodes
- Color-coded attack types (DoS, Exploits, Recon, etc.)
- Real-time counters for Total Attacks, Blocked, Confidence, Critical threats
- One-click pipeline execution with live output
- Gmail alert integration for high-confidence attacks
- File status tracking for all pipeline components

---

## Email Alerts

Configure Gmail alerts from either dashboard's **Email** tab, or edit `.env` directly:

```ini
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-16-char-app-password
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
ATTACK_THRESHOLD_PERCENTAGE=80
RECEIVER_EMAIL=admin@company.com
WEEKLY_REPORT_DAY=0
WEEKLY_REPORT_TIME=09:00
```

Requires Gmail App Password (enable 2FA, then create App Password).

For detailed setup, see [docs/EMAIL_NOTIFICATIONS.md](docs/EMAIL_NOTIFICATIONS.md).

---

## Dataset

The cleaned dataset (`data/processed/final_project_data.csv`) contains 50,000 rows with:
- `sttl`, `sbytes`, `dbytes`, `sload`, `dload` — network traffic features
- `label` — ground truth (0 = normal, 1 = attack)

Raw UNSW-NB15 CSV files go in `data/raw/`. Sample files are included for testing.

To regenerate from raw data, download [UNSW-NB15](https://research.unsw.edu.au/projects/unsw-nb15-dataset) and place the CSV files in `data/raw/`.

---

## Tests

```bash
pip install pytest
pytest tests/ -v
```

---

## License

MIT
