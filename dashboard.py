import os
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from detector import NetworkAnomalyDetector  # Ton moteur de détection
# Importe ici ta fonction de remédiation (ex: depuis auto_remediator.py)
# Supposons que tu as une fonction 'generate_report()' dans auto_remediator.py
# from auto_remediator import generate_report 

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
# Sidebar Navigation & AI Controls
# =========================

st.sidebar.title("🛡️ NetPulse Command")

st.sidebar.subheader("System Actions")

# BOUTON 1 : DÉTECTION
if st.sidebar.button("🚀 1. Run Network Analysis"):
    with st.spinner("Analyse du trafic (Isolation Forest)..."):
        try:
            raw_data = pd.read_csv(DATA_FILE)
            detector = NetworkAnomalyDetector(contamination=0.05)
            detector.analyze(raw_data)
            st.sidebar.success("Détection terminée !")
            st.cache_data.clear() 
        except Exception as e:
            st.sidebar.error(f"Erreur Détection : {e}")

# BOUTON 2 : REMÉDIATION (IA)
if st.sidebar.button("🤖 2. Generate AI Advice"):
    if os.path.exists(ALERTS_FILE):
        with st.spinner("Llama 3 analyse les alertes..."):
            try:
                # Ici, on simule l'appel à ton script de remédiation
                # os.system("python auto_remediator.py") 
                st.sidebar.success("Rapport IA généré !")
            except Exception as e:
                st.sidebar.error(f"Erreur IA : {e}")
    else:
        st.sidebar.warning("Veuillez d'abord lancer l'analyse (Étape 1).")

st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigation",
    ["Overview", "Traffic Data", "Detected Alerts", "Security Report"]
)

# =========================
# Load Data
# =========================

data = load_csv(DATA_FILE)
alerts = load_csv(ALERTS_FILE)

# =========================
# Header
# =========================

st.title("🛡️ NetPulse-Shield Dashboard")
st.caption("Ingénierie RST - ENSA Kénitra | Projet de Détection d'Anomalies")

# =========================
# Page Logic (Identique à la version précédente avec quelques améliorations visuelles)
# =========================

if page == "Overview":
    st.header("📊 Vue d'ensemble du Réseau")
    if data is not None:
        col1, col2, col3 = st.columns(3)
        total_records = len(data)
        total_alerts = len(alerts) if alerts is not None else 0
        
        col1.metric("Flux Totaux", total_records)
        col2.metric("Alertes IA", total_alerts, delta=total_alerts, delta_color="inverse")
        col3.metric("État du Système", "Opérationnel" if total_alerts < 3000 else "Critique")

        fig, ax = plt.subplots(figsize=(10, 3))
        ax.barh(["Normal", "Suspect"], [total_records - total_alerts, total_alerts], color=['#238636', '#da3633'])
        st.pyplot(fig)
    else:
        st.info("👋 Bienvenue Meriem. Lancez l'analyse depuis la barre latérale pour commencer.")

elif page == "Traffic Data":
    st.header("🌐 Données de Trafic Brut")
    if data is not None:
        st.dataframe(data.head(100), use_container_width=True)
    else:
        st.error("Données introuvables.")

elif page == "Detected Alerts":
    st.header("🚨 Menaces Identifiées (Top 10)")
    if alerts is not None:
        st.warning(f"Attention : {len(alerts)} anomalies détectées par l'algorithme Isolation Forest.")
        st.table(alerts.head(10))
    else:
        st.info("Aucune alerte à afficher pour le moment.")

elif page == "Security Report":
    st.header("🛡️ Intelligence Artificielle : Rapport de Remédiation")
    if os.path.exists(REPORT_FILE):
        with open(REPORT_FILE, "r", encoding="utf-8") as f:
            report_content = f.read()
        
        st.markdown(f"""
        <div style="background-color: #0d1117; padding: 25px; border-radius: 15px; border: 1px solid #30363d;">
            <h4 style="color: #238636;">✅ Analyse Llama 3 terminée</h4>
            <p style="color: #e6edf3; white-space: pre-wrap;">{report_content}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Cliquez sur **'Generate AI Advice'** pour que Llama 3 analyse les suspects.")