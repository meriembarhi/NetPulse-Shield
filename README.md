# NetPulse-Shield

NetPulse-Shield is an intelligent, Python-based security framework designed to bridge the gap between real-time network monitoring and incident response. By combining Anomaly Detection via Machine Learning (Isolation Forest) with a Generative AI pipeline, the system not only identifies threats but also delivers expert-level remediation advice and technical configuration commands.  The entire framework operates through a RAG (Retrieval-Augmented Generation) architecture, running 100% locally with no external API keys or internet connection required, ensuring maximum data privacy and infrastructure resilience.


---

## How It Works

NetPulse-Shield operates as a continuous intelligence pipeline, transforming raw network data into actionable security reports through three main stages.  

1. Anomaly Detection (The ML Layer)
The system monitors incoming network traffic, focusing on key features such as Sload (source load), sttl (source time-to-live), and sbytes (source bytes). 

 Isolation Forest Algorithm: 
 The detection engine uses an Isolation Forest model to analyze these features. Unlike traditional models that learn what "normal" traffic looks like, this algorithm specifically identifies "anomalies" by isolating data points that are few and different. 

 Alert Generation: 
 When a data point is flagged as anomalous, its characteristics are captured and sent to the remediation suite.  

2. Context Retrieval (The RAG Engine)
Once an anomaly is detected, the Modular RAG Advisor takes over to find a solution. 

 Vectorization:
 The detected symptoms are converted into a mathematical "embedding" using the Sentence-Transformer model in embeddings.py. 

 Similarity Search: 
 The system queries the FAISS Index to find the most relevant security guides in the knowledge_base.py. Instead of keyword matching, it performs a semantic search to understand the context of the threat (e.g., recognizing that "flooding" and "DDoS" are related).  

 Offline Resilience: 
 If no internet connection is detected, the system automatically falls back to a TF-IDF vectorizer, ensuring security advice is always available even in air-gapped environments. 

 3. Response Generation (The Expert Output)
 Finally, the system synthesizes the gathered information into a human-readable format.

 Standard Report (solver.py): 
 Concatenates the retrieved expert guides into a structured remediation plan. 

 Advanced Synthesis (remediator.py): 
 If Ollama is active, the system sends the data to a local Llama 3 model. The LLM acts as a Senior Security Engineer, providing a risk assessment and generating specific Cisco IOS ACL commands to block the attack at the hardware level. 
---

## Pipeline

```
[ Raw CSV Data ] 
       ↓
( clean_data.py ) ————> Pre-processes and filters network features
       ↓
( detector.py ) ——————> Applies Isolation Forest to detect anomalies
       ↓
 [ alerts.csv ] ——————> Stores identified threats (IPs, Ports, Sload, etc.)
       ↓
( solver.py ) ————————> Orchestrates the Remediation Suite
     ↙   ↘
    /     \_________ [ Standard Path ] —> ( advisor.py ) + ( knowledge_base.py )
   /                                               ↓
[ Advanced Path ]                          ( FAISS Similarity Search )
   ↓                                               ↓
( remediator.py )                          [ Security_Report.txt ]
   ↓                                       (Expert Guidance & Manuals)
( Llama 3 via Ollama )
   ↓
[ Cisco IOS ACL Commands ]
```

---

## Features



| Component | Technology | Core Purpose |
| :--- | :--- | :--- |
| **`clean_data.py`** | **Pandas** | Handles preprocessing, feature selection (e.g., `Sload`, `sttl`), and normalization of raw network logs. |
| **`detector.py`** | **Scikit-learn** | Employs an **Isolation Forest** (Unsupervised ML) to isolate rare and suspicious traffic signatures. |
| **`advisor.py`** | **FAISS** | The RAG engine that performs semantic similarity searches to match threats with expert advice. |
| **`embeddings.py`** | **S-Transformers / TF-IDF** | Converts text into mathematical vectors; includes an offline fallback for air-gapped security. |
| **`remediator.py`** | **Ollama (Llama 3)** | An advanced LLM module that synthesizes risk reports and generates real-time **Cisco IOS ACL** commands. |
| **`solver.py`** | **Python Logic** | The central orchestrator that manages the automated data flow from "Alert" to "Actionable Advice." |
| **`dashboard.py`** | **Streamlit** | An interactive SOC (Security Operations Center) dashboard to visualize detection results and security reports. |

---

## Project Structure

```
NetPulse-Shield/
NetPulse-Shield/
├── detector.py                # ML Engine: Isolation Forest anomaly detector + joblib persistence
├── solver.py                  # RAG Orchestrator: Entry point for the remediation suite
├── advisor.py                 # RAG Logic: Performs FAISS similarity search and matches threats
├── embeddings.py              # Vector Engine: Sentence-Transformers with TF-IDF fallback
├── knowledge_base.py          # Intelligence Repository: Structured expert security manuals[cite: 1]
├── remediator.py              # Advanced AI: Direct Llama 3 advisor for Cisco IOS commands
├── dashboard.py               # Streamlit visual interface for interactive results
├── clean_data.py              # Data Engineering: Pre-processes and filters raw datasets
├── requirements.txt           # Python dependencies (scikit-learn, FAISS, ollama, etc.)
├── Security_Report.txt        # Sample AI-generated security output
├── .gitignore                 # Standard exclusions (including models/*.joblib)
├── LICENSE                    # Project licensing
├── data/
│   └── README.md              # Instructions for dataset placement
├── models/
│   ├── netpulse_model.joblib  # Generated Isolation Forest model
│   └── netpulse_model_scaler.joblib # Saved data scaler
└── docs/
    └── remediation_knowledge.txt # Raw knowledge source for the RAG advisor[cite: 1]
```

---

## Dataset

> **The dataset is not included in this repo due to file size. You must set it up manually.**

This project expects a network traffic CSV containing at minimum these columns: `sttl`, `sbytes`, `dbytes`, `Sload`, `Dload`, and optionally `Label`.


1. Download your dataset (e.g. [UNSW-NB15](https://research.unsw.edu.au/projects/unsw-nb15-dataset) or [CIC-IDS2017](https://www.unb.ca/cic/datasets/ids-2017.html))
2. Place the raw file anywhere accessible
3. Update the path in `clean_data.py` and run it
4. The output `data/final_project_data.csv` (50,000 rows) will be created automatically

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Prepare your data

```bash
python clean_data.py
```

### 3. Run the AI-Powered Anomaly Detection (detector.py)

This core module handles the intelligence layer of NetPulse-Shield. It utilizes the Isolation Forest algorithm—an unsupervised learning method ideal for identifying rare items or observations that differ significantly from the majority of the network traffic.

```bash
python detector.py
```
Key Technical Features:

Dynamic Contamination Calibration: The script automatically calculates the optimal contamination parameter by analyzing the distribution of labels in your dataset, ensuring higher detection accuracy.  

Expert Feature Engineering: Specifically filters and scales network-specific features like Sload (Source Load) and Dload (Destination Load) while handling infinite values (inf) and missing data (NaN) to prevent model crashes.  

Model Persistence: Both the trained Isolation Forest and the StandardScaler are serialized using joblib. This allows the system to reload the specific network "signature" instantly without retraining.  

Performance Benchmarking: Generates a detailed Classification Report (Precision, Recall, and F1-Score) to validate the model's effectiveness against known attack labels.

**Example output:**

```
NetPulse-Shield — Network Anomaly Detector
==================================================
✅ Model and Scaler loaded from models/netpulse_model.joblib
📊 Calculated Contamination: 0.0542

--- 📈 Model Performance Report ---
              precision    recall  f1-score   support
      Normal       0.98      0.96      0.97     47290
      Attack       0.89      0.92      0.90      2710

Total records analysed : 50000
Anomalies detected     : 2710 (5.4 %)
✅ Alerts saved in 'alerts.csv'

### 4. Run the AI Remediation Suite (solver.py)

This module serves as the primary orchestrator for the RAG-based remediation pipeline. It reads identified threats from alerts.csv and generates specialized security reports by querying the internal intelligence system.



```bash
python solver.py
```
How the Pipeline Operates:

Intelligent Retrieval: The advisor.py module takes raw anomaly data and queries a FAISS index to find the most relevant security protocols stored in knowledge_base.py.  

Semantic Matching: Using the Sentence-Transformers engine in embeddings.py, the system understands the context of the threat—matching a "high-load volumetric spike" to a "DDoS Mitigation" manual even without exact keyword matches.  

Offline Resilience: In air-gapped network environments, the pipeline automatically switches to a TF-IDF vectorizer to ensure security advice is always available without an internet connection.  

Expert Output: Generates a structured Security_Report.txt that provides a diagnostic summary, risk assessment, and step-by-step mitigation instructions.


Example Output (Security_Report.txt):
==================================================
🛡️ NETPULSE-SHIELD: AI SECURITY REPORT
==================================================
[!] THREAT DETECTED: Volumetric Denial of Service (DDoS)
[!] CONFIDENCE: High
--------------------------------------------------
DIAGNOSIS:
The system detected an extreme Sload characteristic of a 
UDP/TCP flood attack designed to saturate network bandwidth.

REMEDIATION STEPS:
1. Identify and null-route the source IP addresses found in alerts.csv.
2. Enable unicast Reverse Path Forwarding (uRPF) on the edge router.
3. Apply a rate-limiting policy to the affected interface.
==================================================

### 5. Interactive Query Mode (solver.py)

```bash
python solver.py "High Sload from single IP targeting port 22 — possible SSH brute-force."
```
Why this is useful:

Manual Incident Response: If you observe suspicious activity outside of the automated logs, you can get instant expert advice by describing the "symptoms".

Semantic Retrieval: Because it uses FAISS and Vector Embeddings, you don't need to use exact keywords. The system understands the intent of your query (e.g., it knows "SSH brute-force" relates to "Authentication Security").

Zero-Latency Knowledge: Accesses the curated manuals in knowledge_base.py instantly without searching through raw documentation files.

### 6. Advanced AI Remediation with Llama 3 (remediator.py)
For environments with local AI support, this module leverages Ollama to provide a deeper level of technical synthesis. It transforms raw network anomalies into production-ready configuration commands.

Prerequisites:

Install Ollama.

Pull the model: ollama pull llama3

```bash
ollama pull llama3
python remediator.py
```

Features:

Cisco IOS Integration: Unlike the standard advisor, this module is specifically prompted to generate ready-to-deploy Access Control List (ACL) commands to harden network infrastructure in real-time.

Deep Feature Analysis: The AI interprets raw metrics like sttl (Time-to-Live) and sbytes to diagnose the specific attack vector (e.g., distinguishing between a simple scan and a complex C2 beacon).

Risk Assessment: Provides a "Senior Engineer" perspective on the threat's impact on network availability and data integrity.

### 7. Launch the interactive dashboard

The NetPulse-Shield dashboard transforms raw network logs into actionable intelligence, providing a centralized interface for network administrators.

```bash
streamlit run dashboard.py
```
The application launches at `http://localhost:8501`  and features four strategic modules:

📊 Network Overview: A high-level summary of total traffic flows and the real-time anomaly rate detected by the AI.

🔍 EDA & Insights (Exploratory Data Analysis):

Traffic Load Distribution: Visualizes Sload (Source Load) to identify suspicious congestion patterns.

Interactive Scatter Plots: Analyzes the correlation between inbound and outbound flows to detect asymmetric behaviors (e.g., DoS/DDoS attacks).

🚨 Security Alerts: A detailed breakdown of priority threats identified by the Isolation Forest algorithm.

🛡️ AI Remediation Report: Dynamic access to strategic security recommendations generated by Llama 3 to help harden network infrastructure.


---

## Configuration

### Detector (`detector.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `contamination` | `Dynamic` | The expected fraction of anomalies. Your script automatically calculates this by analyzing the distribution of labels in the dataset for higher precision. |
| `n_estimators` | `100` | Number of trees in the ensemble |
| `random_state` | `42` | Seed for reproducibility ensures that the model results are reproducible and consistent across different runs. |

### RAG Advisor (`solver.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `knowledge_base_path` | `docs/remediation_knowledge.txt` | The source file for security manuals. The system intelligently falls back to built-in RST protocols if the file is missing. |
| `embedding_model` | `all-MiniLM-L6-v2` | High-efficiency vector model for semantic search. Auto-falls back to TF-IDF if the environment is offline. |
| `top_k` | `3` | Determines the granularity of advice by retrieving the top 3 most relevant knowledge chunks for every detected threat. |
| `llm_pipeline` | `None` | Optional Hugging Face text-generation pipeline for LLM synthesis |

---

## Extending the Knowledge Base

Edit `docs/remediation_knowledge.txt` to add new threat categories. Separate sections with a line containing only `---`. The advisor picks up changes automatically on next initialisation.

---

## License

MIT LICENSE