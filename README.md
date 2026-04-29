# NetPulse-Shield

A Python-based network security assistant that detects anomalous traffic patterns
with machine learning and delivers actionable remediation advice through a
Retrieval-Augmented Generation (RAG) pipeline — all running locally with no
external API keys required.

---

## Features

| Component | Technology | Purpose |
|-----------|-----------|---------|
| `detector.py` | scikit-learn **Isolation Forest** | Unsupervised anomaly detection on network traffic features |
| `solver.py` | **LangChain** + FAISS + sentence-transformers | RAG pipeline that retrieves and formats remediation advice |

---

## Project Structure

```
NetPulse-Shield/
├── detector.py             # Isolation Forest anomaly detector [cite: 12]
├── auto_remediator.py      # Bridge to Llama 3 for remediation advice [cite: 17]
├── clean_data.py           # Filters the raw dataset into a usable size [cite: 6]
├── requirements.txt        # Python dependencies (Pandas, Scikit-learn, Ollama) [cite: 25, 27]
├── .gitignore              # Prevents large data/logs from being uploaded
├── data/
│   ├── README.md           # Guide for local data setup
│   └── final_project_data.csv # Optimized dataset with 50,000 records [cite: 7]
└── Security_Report.txt     # Final AI-generated security report
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the anomaly detector

```bash
python detector.py
```

On first run, `detector.py` generates `data/sample_traffic.csv` with synthetic
traffic data (475 normal flows + 25 anomalous flows at a 5% anomaly rate), trains
an Isolation Forest model with `contamination=0.1` (telling the model to flag the
10% most anomalous-looking records), and prints the top-5 most anomalous records.

**Example output:**
```
NetPulse-Shield — Network Anomaly Detector
==================================================
Generating sample traffic data …
Sample data saved to data/sample_traffic.csv

Total records analysed : 500
Anomalies detected     : 50  (10.0 %)

Top 5 anomalies (lowest score = most anomalous):
 packet_size  duration  bytes_sent  packets_per_second  anomaly_score
 1412.34      0.00       54823.12   612.45              -0.3421
 ...
```

### 3. Run the RAG advisor

```bash
python solver.py
```

Or pass a custom anomaly description:

```bash
python solver.py "High packets_per_second from single IP targeting port 22 — possible SSH brute-force."
```

**Example output:**
```
NetPulse-Shield — RAG-based Security Advisor
==================================================
Initialising knowledge base and embeddings …
Ready.

Query: High packets_per_second from single IP targeting port 22 …

Remediation Advice
--------------------------------------------------
[Relevant guidance 1]
Brute-Force Login Attack Remediation
...
1. Temporarily ban the source IP using fail2ban or similar tooling.
2. Enforce multi-factor authentication (MFA) on all remote-access services.
...
```
### 4. Launch the Interactive Dashboard

To visualize the detection results and read the AI security report in a professional interface, run:

```bash
streamlit run dashboard.py

Voici exactement le contenu à copier et à insérer dans ton fichier README.md, juste après la section 3. Run the RAG advisor (vers la ligne 89 selon ta capture d'écran) :

Markdown
### 4. Launch the Interactive Dashboard

To visualize the detection results and read the AI security report in a professional interface, run:

```bash
streamlit run dashboard.py
```
The dashboard will automatically open in your default browser at http://localhost:8501.

📊 Interactive Dashboard
The NetPulse-Shield Dashboard transforms raw network logs into actionable security intelligence through four specialized views:

Overview: Real-time visualization of network health, comparing normal traffic volume against detected suspicious activities.

Traffic Data: Exploratory Data Analysis (EDA) tools to inspect the cleaned dataset and visualize feature distributions (e.g., packet size, duration).

Detected Alerts: A dedicated forensics view showing the specific records flagged by the Isolation Forest model for further investigation.

Security Intelligence Report: A custom-styled briefing area that displays the Llama 3 remediation strategy, formatted for quick reading by security analysts.

### 5. Use the components programmatically

```python
from detector import NetworkAnomalyDetector, generate_sample_data
from solver import NetworkSecurityAdvisor

# --- Detection ---
df = generate_sample_data(n_samples=1000)
detector = NetworkAnomalyDetector(contamination=0.05)
results = detector.analyze(df)

anomalies = results[results["is_anomaly"]]
print(f"Detected {len(anomalies)} anomalies")

# --- Remediation ---
advisor = NetworkSecurityAdvisor()                    # loads docs/remediation_knowledge.txt
advice = advisor.get_remediation_advice(
    "Extremely high bytes_sent (50 000) with very short duration — possible data exfiltration."
)
print(advice)
```

---

## Configuration

### Detector

| Parameter       | Default | Description                       |
|-----------------|---------|-----------------------------------|
| `contamination` | `0.1`   | Expected anomaly fraction (0–0.5) |
| `n_estimators`  | `100`   | Number of trees in the ensemble   |
| `random_state`  | `42`    | Seed for reproducibility          |

### Advisor

| Parameter             | Default            | Description                                   |
|-----------------------|--------------------|-----------------------------------------------|
| `knowledge_base_path` | `None`             | Path to a custom knowledge-base file (falls back to `docs remediation_knowledge.txt`) |
| `embedding_model`     | `all-MiniLM-L6-v2` | sentence-transformers model for embedding     |
| `top_k`               | `3`                | Number of document chunks retrieved per query |
| `llm_pipeline`        | `None`             | Optional Hugging Face text-generation pipeline for LLM synthesis |

---

## Extending the Knowledge Base

Edit `docs/remediation_knowledge.txt` to add new threat categories.
Separate sections with a line containing only `---`.  The solver will
automatically pick up changes the next time it is initialised.

---

## License

[MIT](LICENSE)
