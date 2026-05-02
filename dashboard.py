import os
import pandas as pd
import streamlit as st
import plotly.express as px
from detector import NetworkAnomalyDetector
from db import get_session, create_db, Alert, AuditLog
from system_utils import check_redis_health, get_queue_stats, get_job_status, bulk_enqueue_advice

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
DB_PATH = "sqlite:///alerts.db"

# Ensure DB exists
create_db(DB_PATH)

def load_csv(file_path):
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return None

# =========================
# Sidebar & AI Controls
# =========================
st.sidebar.title("🛡️ NetPulse Command")
st.sidebar.subheader("System Actions")

# Simple token-based auth (optional)
ENV_TOKEN = os.getenv("DASHBOARD_TOKEN")
if ENV_TOKEN:
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state.get("authenticated"):
        token_input = st.sidebar.text_input("Enter dashboard token", type="password")
        if st.sidebar.button("Login"):
            if token_input == ENV_TOKEN:
                st.session_state["authenticated"] = True
                st.sidebar.success("Authenticated")
            else:
                st.sidebar.error("Invalid token")
        st.sidebar.warning("This dashboard is protected. Please log in.")
        st.stop()
    else:
        if st.sidebar.button("Logout"):
            st.session_state["authenticated"] = False
            st.experimental_rerun()
else:
    st.sidebar.info("No DASHBOARD_TOKEN set — dashboard is open (dev mode).")

if st.sidebar.button("🚀 1. Run Network Analysis"):
    with st.spinner("Analyse du trafic (Isolation Forest)..."):
        try:
            raw_data = pd.read_csv(DATA_FILE)
            detector = NetworkAnomalyDetector(contamination=0.05, persist_to_db=True, db_path=DB_PATH)
            results = detector.analyze(raw_data)
            # write alerts.csv for backward compatibility
            alerts_df = results[results["is_anomaly"]]
            alerts_df.to_csv(ALERTS_FILE, index=False)
            st.sidebar.success("Détection terminée !")
            st.cache_data.clear() 
        except Exception as e:
            st.sidebar.error(f"Erreur Détection : {e}")

if st.sidebar.button("🤖 2. Generate AI Advice"):
    session = get_session(DB_PATH)
    if session is None:
        st.sidebar.warning("Veuillez d'abord lancer l'analyse.")
    else:
        alerts = session.query(Alert).filter(Alert.advice.is_(None)).all()
        if not alerts:
            st.sidebar.warning("Aucune alerte sans conseil à traiter.")
        else:
            # Try to enqueue tasks with RQ/Redis. If not available, fall back to synchronous generation.
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            try:
                from redis import Redis
                from rq import Queue

                redis_conn = Redis.from_url(redis_url)
                q = Queue('advisor', connection=redis_conn)

                enqueued = 0
                for a in alerts:
                    job = q.enqueue('tasks.generate_advice_for_alert', a.id, DB_PATH)
                    a.advice_job_id = job.id
                    a.advice_status = 'queued'
                    session.add(AuditLog(alert_id=a.id, action='advice_enqueued', actor='dashboard', note=job.id))
                    enqueued += 1
                session.commit()
                st.sidebar.success(f"Enqueued {enqueued} advice jobs (Redis at {redis_url}).")

            except Exception:
                # Fallback: run synchronously (keeps behavior if Redis not available)
                with st.spinner("Génération synchrone de conseils IA (Redis absent)..."):
                    try:
                        from tasks import generate_advice_for_alert
                        processed = 0
                        for a in alerts:
                            generate_advice_for_alert(a.id, DB_PATH)
                            processed += 1
                        st.sidebar.success(f"Generated advice for {processed} alerts (sync fallback).")
                    except Exception as e:
                        st.sidebar.error(f"Erreur génération conseils: {e}")

st.sidebar.markdown("---")
page = st.sidebar.radio("Navigation", ["Overview", "EDA & Insights", "Detected Alerts", "Security Report", "Audit Logs", "System Status", "Control Panel"])

# Load Data
data = load_csv(DATA_FILE)
session = get_session(DB_PATH)
alerts_query = session.query(Alert).order_by(Alert.created_at.desc())
alerts = pd.read_sql(alerts_query.statement, alerts_query.session.bind) if data is not None else None

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
    if alerts is not None and len(alerts) > 0:
        st.error(f"Top 10 des flux suspects sur {len(alerts)} anomalies.")
        # Interactive table with triage controls and job status
        for idx, row in alerts.head(10).iterrows():
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            job_status = 'N/A'
            if row.get('advice_job_id'):
                job_status = get_job_status(row['advice_job_id'], redis_url) or 'unknown'
            
            with st.expander(f"Alert #{row['id']} - Score {row['anomaly_score']} - Job: {job_status}"):
                col_info, col_job = st.columns(2)
                with col_info:
                    st.write(row[['created_at', 'anomaly_score', 'severity', 'status']])
                with col_job:
                    st.write(f"**Job Status:** {job_status}")
                    if row.get('advice_job_id'):
                        st.write(f"**Job ID:** {row['advice_job_id']}")
                
                new_status = st.selectbox('Status', ['new', 'investigating', 'resolved', 'false_positive'], index=['new','investigating','resolved','false_positive'].index(row['status']), key=f"status_{row['id']}")
                if st.button(f"Update status for {row['id']}", key=f"btn_status_{row['id']}"):
                    session.query(Alert).filter(Alert.id == int(row['id'])).update({"status": new_status})
                    session.add(AuditLog(alert_id=int(row['id']), action='status_update', actor='dashboard', note=new_status))
                    session.commit()
                    st.success('Status updated')
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

elif page == "Audit Logs":
    st.header("🧾 Audit Logs")
    try:
        session = get_session(DB_PATH)
        logs_query = session.query(AuditLog).order_by(AuditLog.timestamp.desc())
        logs_df = pd.read_sql(logs_query.statement, logs_query.session.bind)
        if logs_df is not None and len(logs_df) > 0:
            st.dataframe(logs_df)
            csv = logs_df.to_csv(index=False)
            st.download_button("Download audit logs as CSV", csv, file_name="audit_logs.csv", mime="text/csv")
        else:
            st.info("No audit logs available yet.")
    except Exception as e:
        st.error(f"Error loading audit logs: {e}")

elif page == "System Status":
    st.header("🔧 System Status & Health")
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔴 Redis Connection")
        redis_health = check_redis_health(redis_url)
        if redis_health.get('connected'):
            st.success(f"✅ Connected to {redis_url}")
            queue_stats = get_queue_stats(redis_url)
            if 'error' not in queue_stats:
                st.metric("Queue Depth", queue_stats['queue_depth'])
                st.metric("Jobs Started", queue_stats['jobs_started'])
                st.metric("Jobs Finished", queue_stats['jobs_finished'])
                st.metric("Jobs Failed", queue_stats['jobs_failed'])
            else:
                st.error(f"Error fetching stats: {queue_stats['error']}")
        else:
            st.error(f"❌ Redis not available: {redis_health.get('error')}")
            st.info("**To enable background jobs:**")
            st.code("docker run -p 6379:6379 redis:7", language="bash")
    
    with col2:
        st.subheader("📊 Database")
        session = get_session(DB_PATH)
        alert_count = session.query(Alert).count()
        audit_count = session.query(AuditLog).count()
        st.metric("Total Alerts", alert_count)
        st.metric("Audit Log Entries", audit_count)
        
        advice_pending = session.query(Alert).filter(Alert.advice.is_(None)).count()
        advice_done = session.query(Alert).filter(Alert.advice.isnot(None)).count()
        st.metric("Advice Pending", advice_pending)
        st.metric("Advice Generated", advice_done)

elif page == "Control Panel":
    st.header("⚙️ Control Panel")
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    st.subheader("Bulk Operations")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Generate Advice")
        session = get_session(DB_PATH)
        pending_count = session.query(Alert).filter(Alert.advice.is_(None)).count()
        st.info(f"Alerts pending advice: {pending_count}")
        
        if st.button("🤖 Enqueue All Pending Advice", key="bulk_enqueue"):
            try:
                redis_health = check_redis_health(redis_url)
                if redis_health.get('connected'):
                    pending_alerts = session.query(Alert).filter(Alert.advice.is_(None)).all()
                    alert_ids = [a.id for a in pending_alerts]
                    if alert_ids:
                        enqueued = bulk_enqueue_advice(alert_ids, DB_PATH, redis_url)
                        st.success(f"✅ Enqueued {enqueued} advice jobs")
                    else:
                        st.info("No pending alerts to enqueue")
                else:
                    st.error(f"❌ Redis not available: {redis_health.get('error')}")
            except Exception as e:
                st.error(f"Error: {e}")
    
    with col2:
        st.markdown("### Data Export")
        session = get_session(DB_PATH)
        alerts_df = pd.read_sql("SELECT * FROM alerts ORDER BY created_at DESC", session.bind)
        if not alerts_df.empty:
            csv = alerts_df.to_csv(index=False)
            st.download_button("📥 Download Alerts CSV", csv, file_name="alerts_export.csv", mime="text/csv")
        
        logs_df = pd.read_sql("SELECT * FROM audit_logs ORDER BY timestamp DESC", session.bind)
        if not logs_df.empty:
            csv = logs_df.to_csv(index=False)
            st.download_button("📥 Download Audit Logs CSV", csv, file_name="audit_logs_export.csv", mime="text/csv")
    
    st.markdown("---")
    st.subheader("Worker Commands")
    st.info("To run background workers outside the dashboard, use these commands:")
    st.code("rq worker advisor", language="bash")
    st.markdown("**Or with Docker:**")
    st.code("docker-compose up --build", language="bash")