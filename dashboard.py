import os
import pandas as pd
import streamlit as st
import plotly.express as px
from detector import NetworkAnomalyDetector 

# =========================
# Page Configuration
# =========================
st.set_page_config(
    page_title="NetPulse-Shield Dashboard",
    page_icon="🛡️",
    layout="wide"
)

# Custom CSS pour le style ENSA Kénitra
st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# =========================
# File Paths
# =========================
DATA_FILE = "data/final_project_data.csv"
ALERTS_FILE = "alerts.csv"
REPORT_FILE = "Security_Report.txt"

def load_csv(file_path):
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return None

# =========================
# Sidebar & AI Controls
# =========================
st.sidebar.title("🛡️ NetPulse Command")
st.sidebar.subheader("System Actions")

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

if st.sidebar.button("🤖 2. Generate AI Advice"):
    if os.path.exists(ALERTS_FILE):
        with st.spinner("Llama 3 analyse les alertes..."):
            # Simulation de l'appel au script de remédiation
            st.sidebar.success("Rapport IA généré !")
    else:
        st.sidebar.warning("Veuillez d'abord lancer l'analyse.")

st.sidebar.markdown("---")
page = st.sidebar.radio("Navigation", ["Overview", "EDA & Insights", "Detected Alerts", "Security Report"])

# Load Data
data = load_csv(DATA_FILE)
alerts = load_csv(ALERTS_FILE)

# Header
st.title("🛡️ NetPulse-Shield Dashboard")
st.caption("Ingénierie RST - ENSA Kénitra | Surveillance Réseau par IA")

# =========================
# Page Logic
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

        # Graphique simple de répartition
        labels = ['Normal', 'Anomalie']
        values = [total_records - total_alerts, total_alerts]
        fig = px.pie(names=labels, values=values, color_discrete_sequence=['#238636', '#da3633'], hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("👋 Bienvenue Meriem. Lancez l'analyse pour commencer.")

elif page == "EDA & Insights":
    st.header("🔍 Exploration des Données (EDA)")
    if data is not None and alerts is not None:
        # On fusionne pour marquer les anomalies visuellement
        data_viz = data.copy()
        # Création d'une colonne de statut pour le graphique
        data_viz['Status'] = 'Normal'
        # On marque comme 'Anomalie' les lignes présentes dans alerts
        data_viz.loc[data_viz.index.isin(alerts.index), 'Status'] = 'Anomalie'

        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("📈 Distribution de la Charge (Sload)")
            fig_hist = px.histogram(data_viz, x="Sload", color="Status", 
                                    marginal="box", barmode="overlay",
                                    color_discrete_map={'Normal': '#238636', 'Anomalie': '#da3633'})
            st.plotly_chart(fig_hist, use_container_width=True)

        with col_b:
            st.subheader("📍 Scatter Plot : Sload vs Dload")
            fig_scatter = px.scatter(data_viz, x="Sload", y="Dload", color="Status",
                                     hover_data=['sttl', 'sbytes'],
                                     color_discrete_map={'Normal': '#238636', 'Anomalie': '#da3633'},
                                     opacity=0.6)
            st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.warning("Veuillez lancer l'analyse pour visualiser l'EDA.")

elif page == "Detected Alerts":
    st.header("🚨 Menaces Identifiées (Top 10)")
    if alerts is not None:
        st.error(f"Top 10 des flux suspects sur {len(alerts)} anomalies.")
        st.table(alerts.head(10)) # Affichage en tableau fixe pour la clarté
    else:
        st.info("Aucune alerte pour le moment.")

elif page == "Security Report":
    st.header("🛡️ Rapport de Remédiation IA")
    if os.path.exists(REPORT_FILE):
        with open(REPORT_FILE, "r", encoding="utf-8") as f:
            report_content = f.read()
        st.markdown(f'<div style="background-color: #161b22; padding: 20px; border-radius: 10px; border: 1px solid #30363d;">{report_content}</div>', unsafe_allow_html=True)
    else:
        st.info("Générez le rapport IA pour voir les conseils de Llama 3.")