import os
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from detector import NetworkAnomalyDetector  # Importation de ton moteur IA

# =========================
# Page Configuration
# =========================

st.set_page_config(
    page_title="NetPulse-Shield Dashboard",
    page_icon="🛡️",
    layout="wide"
)

# =========================
# File Paths
# =========================

DATA_FILE = "data/final_project_data.csv"
ALERTS_FILE = "alerts.csv"
REPORT_FILE = "Security_Report.txt"

# =========================
# Helper Function
# =========================

def load_csv(file_path):
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return None

# =========================
# Sidebar Navigation & Control
# =========================

st.sidebar.title("🛡️ NetPulse Control")

# --- NOUVEAU : Bouton de commande interactif ---
st.sidebar.subheader("System Commands")
if st.sidebar.button("🚀 Run Network Analysis"):
    with st.spinner("L'IA analyse le flux réseau (50 000 lignes)..."):
        try:
            # On charge les données brutes
            raw_data = pd.read_csv(DATA_FILE)
            # On initialise le détecteur avec tes paramètres ENSA (contamination 5%)
            detector = NetworkAnomalyDetector(contamination=0.05)
            # On lance l'analyse (cela va aussi mettre à jour alerts.csv et models/)
            detector.analyze(raw_data)
            st.sidebar.success("Analyse terminée avec succès !")
            # On force le rechargement des données pour l'affichage
            st.cache_data.clear() 
        except Exception as e:
            st.sidebar.error(f"Erreur : {e}")

st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Choose a section",
    ["Overview", "Traffic Data", "Detected Alerts", "Security Report"]
)

# =========================
# Load Data (Rechargé à chaque clic sur le bouton)
# =========================

data = load_csv(DATA_FILE)
alerts = load_csv(ALERTS_FILE)

# =========================
# Header
# =========================

st.title("🛡️ NetPulse-Shield Dashboard")
st.subheader("AI-Based Network Attack Detection and Remediation")

# =========================
# Overview Page
# =========================

if page == "Overview":
    st.header("📊 General Overview")

    if data is not None:
        col1, col2, col3 = st.columns(3)
        total_records = len(data)
        total_alerts = len(alerts) if alerts is not None else 0
        normal_records = max(total_records - total_alerts, 0)

        col1.metric("Total Traffic Records", total_records)
        col2.metric("Detected Alerts", total_alerts, delta_color="inverse")
        col3.metric("Estimated Normal Records", normal_records)

        st.markdown("---")
        st.subheader("Normal vs Suspicious Traffic")

        fig, ax = plt.subplots(figsize=(10, 4))
        colors = ['#238636', '#da3633'] # Vert pour normal, Rouge pour alerte
        ax.bar(["Normal Traffic", "Suspicious Traffic"], [normal_records, total_alerts], color=colors)
        ax.set_ylabel("Number of Records")
        st.pyplot(fig)
    else:
        st.warning("⚠️ En attente de données. Cliquez sur 'Run Network Analysis' dans la barre latérale.")

# =========================
# Traffic Data Page
# =========================

elif page == "Traffic Data":
    st.header("🌐 Network Traffic Data")

    if data is not None:
        st.write("Aperçu du dataset (50 000 enregistrements) :")
        st.dataframe(data.head(50), use_container_width=True)
        
        col1, col2 = st.columns(2)
        col1.metric("Total Rows", data.shape[0])
        col2.metric("Total Features", data.shape[1])

        numeric_cols = data.select_dtypes(include=["int64", "float64"]).columns
        selected_col = st.selectbox("Visualiser la distribution d'une caractéristique", numeric_cols)

        fig, ax = plt.subplots()
        ax.hist(data[selected_col].dropna(), bins=30, color='#1f77b4', edgecolor='white')
        ax.set_title(f"Distribution de {selected_col}")
        st.pyplot(fig)
    else:
        st.error("Fichier data/final_project_data.csv introuvable.")

# =========================
# Detected Alerts Page
# =========================

elif page == "Detected Alerts":
    st.header("🚨 Detected Suspicious Traffic")

    if alerts is not None:
        st.info(f"L'IA a isolé {len(alerts)} flux suspects nécessitant une attention immédiate.")
        st.dataframe(alerts, use_container_width=True)

        st.subheader("Top Threat Features")
        numeric_cols = alerts.select_dtypes(include=["int64", "float64"]).columns
        selected_col = st.selectbox("Analyser la caractéristique des alertes", numeric_cols)

        fig, ax = plt.subplots()
        ax.hist(alerts[selected_col].dropna(), bins=20, color='#da3633', edgecolor='white')
        ax.set_title(f"Concentration des alertes sur {selected_col}")
        st.pyplot(fig)
    else:
        st.error("Aucune alerte trouvée. Lancez l'analyse depuis la barre latérale.")

# =========================
# Security Report Page
# =========================

elif page == "Security Report":
    st.header("🛡️ Security Intelligence Report")

    if os.path.exists(REPORT_FILE):
        with open(REPORT_FILE, "r", encoding="utf-8") as file:
            report = file.read()

        report = report.replace("=== NETPULSE-SHIELD: AUTOMATED SECURITY REPORT ===", "").strip()

        st.markdown("""
        <style>
        .report-card {
            background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
            border: 1px solid #30363d; border-radius: 18px; padding: 28px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.35); color: #e6edf3;
            font-family: 'Segoe UI', sans-serif; line-height: 1.7;
        }
        .badge-danger {
            background-color: #da3633; color: white; padding: 6px 14px;
            border-radius: 999px; font-size: 14px; font-weight: bold;
        }
        .report-section {
            background-color: rgba(255,255,255,0.04); padding: 20px;
            border-radius: 14px; white-space: pre-wrap; font-size: 16px; margin-top: 15px;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="report-card">
            <span class="badge-danger">CRITICAL THREAT ANALYSIS</span>
            <div class="report-section">{report}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("💡 Une fois l'analyse terminée, utilisez le module de remédiation pour générer ce rapport.")
