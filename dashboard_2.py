"""
NetPulse-Shield Premium Dashboard
A professional, high-performance alternative dashboard with advanced UI components.
"""

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from db import Alert, AuditLog, create_db, get_session
from detector import NetworkAnomalyDetector
from system_utils import bulk_enqueue_advice, check_redis_health, get_queue_stats

# Page Config
st.set_page_config(
    page_title="NetPulse Premium",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Premium Dark Theme CSS
st.markdown(
    """
    <style>
    :root {
        --primary: #00d9ff;
        --danger: #ff3366;
        --success: #00ff88;
        --warning: #ffaa00;
        --bg-dark: #0f1419;
        --bg-darker: #0a0e17;
        --text-light: #e0e0e0;
    }
    
    html, body, [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, var(--bg-darker) 0%, #1a1f35 100%);
        color: var(--text-light);
    }
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0e17 0%, #121820 100%);
        border-right: 2px solid rgba(0, 217, 255, 0.1);
    }
    
    .stMetric {
        background: linear-gradient(135deg, rgba(0, 217, 255, 0.1) 0%, rgba(0, 217, 255, 0.05) 100%);
        border: 1px solid rgba(0, 217, 255, 0.2);
        border-radius: 12px;
        padding: 20px;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #00d9ff 0%, #0099cc 100%);
        color: #0f1419;
        font-weight: bold;
        border: none;
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        box-shadow: 0 0 20px rgba(0, 217, 255, 0.5);
    }
    
    .premium-header {
        background: linear-gradient(90deg, #00d9ff 0%, #0099cc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.5em;
        font-weight: bold;
        margin-bottom: 20px;
    }
    
    .status-card {
        background: linear-gradient(135deg, rgba(0, 217, 255, 0.15) 0%, rgba(255, 51, 102, 0.05) 100%);
        border: 1px solid rgba(0, 217, 255, 0.2);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
    }
    
    .alert-card {
        background: rgba(255, 51, 102, 0.1);
        border: 1px solid rgba(255, 51, 102, 0.3);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize Database
DB_PATH = "sqlite:///alerts.db"
create_db(DB_PATH)

# Constants
DATA_FILE = "data/final_project_data.csv"
ALERTS_FILE = "alerts.csv"
REPORT_FILE = "Security_Report.txt"


@st.cache_data
def load_csv(file_path: str) -> pd.DataFrame | None:
    """Load CSV with caching."""
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return None


def get_db_session():
    """Get database session."""
    return get_session(DB_PATH)


# SIDEBAR - Premium Style
with st.sidebar:
    st.markdown("## ⚡ NetPulse Premium")
    st.markdown("---")

    # Authentication
    env_token = os.getenv("DASHBOARD_TOKEN")
    if env_token:
        if "auth_token" not in st.session_state:
            st.session_state["auth_token"] = False

        if not st.session_state.get("auth_token"):
            token = st.text_input("🔐 Dashboard Token", type="password", placeholder="Enter token...")
            if st.button("Login", use_container_width=True):
                if token == env_token:
                    st.session_state["auth_token"] = True
                    st.success("Authenticated!")
                    st.rerun()
                else:
                    st.error("Invalid token")
            st.stop()
        else:
            st.success("✅ Authenticated")

    # System Actions
    st.markdown("### 🚀 System Actions")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("▶️ Analyze", use_container_width=True):
            with st.spinner("Running anomaly detection..."):
                try:
                    raw_data = pd.read_csv(DATA_FILE)
                    detector = NetworkAnomalyDetector(contamination=0.05, persist_to_db=True, db_path=DB_PATH)
                    results = detector.analyze(raw_data)
                    alerts_df = results[results["is_anomaly"]].copy()
                    alerts_df.to_csv(ALERTS_FILE, index=False)
                    st.success("✓ Detection complete")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Error: {str(e)[:50]}")

    with col_b:
        if st.button("🤖 Advise", use_container_width=True):
            session = get_db_session()
            if session:
                pending = session.query(Alert).filter(Alert.advice.is_(None)).all()
                if pending:
                    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                    try:
                        from redis import Redis
                        from rq import Queue

                        redis_conn = Redis.from_url(redis_url)
                        queue = Queue("advisor", connection=redis_conn)
                        for alert in pending:
                            queue.enqueue("tasks.generate_advice_for_alert", alert.id, DB_PATH)
                        st.success(f"✓ Queued {len(pending)} jobs")
                    except Exception:
                        from tasks import generate_advice_for_alert

                        for alert in pending:
                            generate_advice_for_alert(alert.id, DB_PATH)
                        st.success(f"✓ Generated {len(pending)} advices")
                    st.cache_data.clear()
                else:
                    st.info("No pending alerts")

    st.markdown("---")

    # Page Navigation
    st.markdown("### 📄 Navigation")
    page = st.radio(
        "Select page",
        ["Dashboard", "Alerts", "Analysis", "Report", "Logs", "System", "Control"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.caption("🔬 Real-time Anomaly Detection Engine")


# MAIN CONTENT
data = load_csv(DATA_FILE)
session = get_db_session()
alerts_data = None

if session:
    try:
        alerts_query = session.query(Alert).order_by(Alert.created_at.desc())
        alerts_data = pd.read_sql(alerts_query.statement, alerts_query.session.bind)
    except Exception:
        alerts_data = None

# PAGE ROUTING
if page == "Dashboard":
    st.markdown('<div class="premium-header">Network Intelligence Dashboard</div>', unsafe_allow_html=True)

    if data is not None:
        total_flows = len(data)
        total_alerts = len(alerts_data) if alerts_data is not None else 0
        health = "CRITICAL" if total_alerts > 1000 else "OPERATIONAL"

        # KPI Cards
        col1, col2, col3, col4 = st.columns(4)

        col1.metric("📊 Total Flows", f"{total_flows:,}")
        col2.metric("⚠️ Anomalies", f"{total_alerts:,}", delta=total_alerts if total_alerts > 0 else None)
        col3.metric("🛡️ Severity", "HIGH" if total_alerts > 500 else "LOW")
        col4.metric("💓 System", health, delta_color="inverse" if health == "CRITICAL" else "normal")

        st.divider()

        # Charts
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Distribution")
            if total_alerts > 0:
                fig_pie = px.pie(
                    names=["Normal", "Anomaly"],
                    values=[total_flows - total_alerts, total_alerts],
                    color_discrete_sequence=["#00ff88", "#ff3366"],
                )
                fig_pie.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font={"color": "#e0e0e0"},
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No anomalies detected yet")

        with col_right:
            st.subheader("Timeline")
            if alerts_data is not None and len(alerts_data) > 0:
                alerts_data["created_at"] = pd.to_datetime(alerts_data["created_at"])
                timeline = alerts_data.groupby(alerts_data["created_at"].dt.date).size()
                fig_line = go.Figure(
                    data=[
                        go.Scatter(
                            x=timeline.index,
                            y=timeline.values,
                            mode="lines+markers",
                            line={"color": "#00d9ff", "width": 3},
                            fill="tozeroy",
                            fillcolor="rgba(0, 217, 255, 0.1)",
                        )
                    ]
                )
                fig_line.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font={"color": "#e0e0e0"},
                    showlegend=False,
                    xaxis_title="Date",
                    yaxis_title="Anomalies",
                )
                st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.warning("📂 No data loaded. Run analysis first.")

elif page == "Alerts":
    st.markdown('<div class="premium-header">Alert Triage</div>', unsafe_allow_html=True)

    if alerts_data is not None and len(alerts_data) > 0:
        st.info(f"📍 Showing top 15 of {len(alerts_data)} alerts")

        for idx, row in alerts_data.head(15).iterrows():
            col_exp, col_score = st.columns([3, 1])
            with col_exp:
                with st.expander(f"Alert #{row.get('id', '?')} | {row.get('created_at', 'N/A')}"):
                    col_1, col_2 = st.columns(2)
                    with col_1:
                        st.write(f"**Score:** {row.get('anomaly_score', 'N/A')}")
                        st.write(f"**Status:** {row.get('status', 'new')}")
                        st.write(f"**Severity:** {row.get('severity', 'unknown')}")
                    with col_2:
                        if row.get("advice"):
                            st.write(f"**Advice:** {row['advice'][:80]}...")
                        else:
                            st.write("**Advice:** Pending")

                    # Status Update
                    new_status = st.selectbox(
                        "Update Status",
                        ["new", "investigating", "resolved", "false_positive"],
                        index=["new", "investigating", "resolved", "false_positive"].index(row.get("status", "new")),
                        key=f"status_{row.get('id', 0)}",
                    )

                    if st.button("💾 Save", key=f"save_{row.get('id', 0)}"):
                        session.query(Alert).filter(Alert.id == int(row["id"])).update({"status": new_status})
                        session.add(
                            AuditLog(alert_id=int(row["id"]), action="status_update", actor="premium_dashboard", note=new_status)
                        )
                        session.commit()
                        st.success("Updated!")

            with col_score:
                score = float(row.get("anomaly_score", 0))
                if score > 0.8:
                    st.error(f"🔴 {score:.2f}")
                elif score > 0.5:
                    st.warning(f"🟡 {score:.2f}")
                else:
                    st.success(f"🟢 {score:.2f}")
    else:
        st.info("No alerts available")

elif page == "Analysis":
    st.markdown('<div class="premium-header">Exploratory Data Analysis</div>', unsafe_allow_html=True)

    if data is not None and alerts_data is not None:
        data_viz = data.copy()
        data_viz["Status"] = "Normal"

        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("Load Distribution")
            if "Sload" in data_viz.columns:
                fig_hist = px.histogram(
                    data_viz,
                    x="Sload",
                    nbins=50,
                    color_discrete_sequence=["#00d9ff"],
                )
                fig_hist.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font={"color": "#e0e0e0"})
                st.plotly_chart(fig_hist, use_container_width=True)

        with col_b:
            st.subheader("Scatter Analysis")
            if "Sload" in data_viz.columns and "Dload" in data_viz.columns:
                fig_scatter = px.scatter(
                    data_viz,
                    x="Sload",
                    y="Dload",
                    color_discrete_sequence=["#00ff88"],
                    opacity=0.6,
                )
                fig_scatter.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font={"color": "#e0e0e0"}
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.warning("Run analysis first")

elif page == "Report":
    st.markdown('<div class="premium-header">Security Report</div>', unsafe_allow_html=True)

    if os.path.exists(REPORT_FILE):
        with open(REPORT_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        st.markdown(
            f'<div class="status-card"><pre style="color: #00d9ff; font-family: monospace; white-space: pre-wrap;">{content}</pre></div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("No report generated yet")

elif page == "Logs":
    st.markdown('<div class="premium-header">Audit Log</div>', unsafe_allow_html=True)

    session = get_db_session()
    logs_query = session.query(AuditLog).order_by(AuditLog.timestamp.desc())
    logs_df = pd.read_sql(logs_query.statement, logs_query.session.bind)

    if logs_df is not None and len(logs_df) > 0:
        st.dataframe(logs_df, use_container_width=True)
        csv = logs_df.to_csv(index=False)
        st.download_button("📥 Export Logs", csv, "audit_logs.csv", "text/csv")
    else:
        st.info("No logs available")

elif page == "System":
    st.markdown('<div class="premium-header">System Health</div>', unsafe_allow_html=True)

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    col_r, col_d = st.columns(2)

    with col_r:
        st.subheader("Redis Queue")
        redis_health = check_redis_health(redis_url)
        if redis_health.get("connected"):
            st.success("✅ Connected")
            queue_stats = get_queue_stats(redis_url)
            if "error" not in queue_stats:
                st.metric("Queue Depth", queue_stats["queue_depth"])
                st.metric("Started", queue_stats["jobs_started"])
                st.metric("Finished", queue_stats["jobs_finished"])
                st.metric("Failed", queue_stats["jobs_failed"])
        else:
            st.error("❌ Offline")
            st.code("docker run -p 6379:6379 redis:7")

    with col_d:
        st.subheader("Database")
        alert_count = session.query(Alert).count()
        audit_count = session.query(AuditLog).count()
        advice_pending = session.query(Alert).filter(Alert.advice.is_(None)).count()
        advice_done = session.query(Alert).filter(Alert.advice.isnot(None)).count()

        st.metric("Alerts", alert_count)
        st.metric("Logs", audit_count)
        st.metric("Pending Advice", advice_pending)
        st.metric("Generated", advice_done)

elif page == "Control":
    st.markdown('<div class="premium-header">Control Panel</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Bulk Actions", "Export"])

    with tab1:
        st.subheader("Enqueue Advice")
        pending = session.query(Alert).filter(Alert.advice.is_(None)).count()
        st.info(f"Pending: {pending}")

        if st.button("🚀 Enqueue All", use_container_width=True):
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            try:
                bulk_enqueue_advice(
                    [a.id for a in session.query(Alert).filter(Alert.advice.is_(None)).all()], DB_PATH, redis_url
                )
                st.success(f"✓ Enqueued {pending}")
            except Exception as e:
                st.error(str(e)[:100])

    with tab2:
        st.subheader("Data Export")
        alerts_df = pd.read_sql("SELECT * FROM alerts ORDER BY created_at DESC", session.bind)
        if not alerts_df.empty:
            st.download_button("📥 Alerts", alerts_df.to_csv(index=False), "alerts.csv")

        logs_df = pd.read_sql("SELECT * FROM audit_logs ORDER BY timestamp DESC", session.bind)
        if not logs_df.empty:
            st.download_button("📥 Logs", logs_df.to_csv(index=False), "logs.csv")
