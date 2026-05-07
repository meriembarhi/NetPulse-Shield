"""
NetPulse-Shield Advanced Analytics Dashboard
A complete redesign with modern UI/UX, real-time monitoring, and advanced visualizations.
"""

import os
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from streamlit_option_menu import option_menu

from db import Alert, AuditLog, create_db, get_session
from detector import NetworkAnomalyDetector
from system_utils import check_redis_health, get_queue_stats

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="NetPulse Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# MODERN THEME & STYLING
# =============================================================================

st.markdown(
    """
    <style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        min-height: 100vh;
    }
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #2c3e50 0%, #34495e 100%);
        box-shadow: 2px 0 15px rgba(0, 0, 0, 0.1);
    }
    
    .css-1d391kg {
        padding-top: 2rem;
    }
    
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        border-left: 4px solid #3498db;
    }
    
    .metric-card.danger {
        border-left-color: #e74c3c;
    }
    
    .metric-card.success {
        border-left-color: #27ae60;
    }
    
    .metric-card.warning {
        border-left-color: #f39c12;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 10px 24px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(102, 126, 234, 0.6);
    }
    
    .header-title {
        color: #2c3e50;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .section-divider {
        margin: 30px 0;
        border: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, #ddd, transparent);
    }
    
    .alert-badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 8px;
        margin-bottom: 8px;
    }
    
    .badge-critical {
        background: #ffe6e6;
        color: #c0392b;
    }
    
    .badge-high {
        background: #fff3e0;
        color: #e67e22;
    }
    
    .badge-medium {
        background: #f0f4ff;
        color: #3498db;
    }
    
    .badge-low {
        background: #e8f5e9;
        color: #27ae60;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #2c3e50;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.95rem;
        color: #7f8c8d;
        font-weight: 500;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #ecf0f1;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# INITIALIZATION
# =============================================================================

DB_PATH = "sqlite:///alerts.db"
DATA_FILE = "data/final_project_data.csv"
ALERTS_FILE = "alerts.csv"
REPORT_FILE = "Security_Report.txt"

create_db(DB_PATH)


@st.cache_data
def load_data(filepath: str) -> pd.DataFrame | None:
    if os.path.exists(filepath):
        return pd.read_csv(filepath)
    return None


# =============================================================================
# SIDEBAR NAVIGATION
# =============================================================================

with st.sidebar:
    st.markdown("## 📊 NetPulse Analytics")
    st.markdown("*Advanced Network Intelligence Platform*")
    st.divider()

    # Auth Check
    env_token = os.getenv("DASHBOARD_TOKEN")
    if env_token:
        if "authenticated" not in st.session_state:
            st.session_state["authenticated"] = False

        if not st.session_state.get("authenticated"):
            pwd = st.text_input("🔑 Access Code", type="password", placeholder="Enter token")
            if st.button("Unlock Dashboard", use_container_width=True):
                if pwd == env_token:
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Invalid code")
            st.stop()
        else:
            st.success("✓ Unlocked", icon="✅")

    st.divider()

    # Quick Actions
    st.markdown("### ⚡ Quick Actions")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔍 ANALYZE", use_container_width=True):
            with st.spinner("Running detection..."):
                try:
                    data = pd.read_csv(DATA_FILE)
                    detector = NetworkAnomalyDetector(contamination=0.05, persist_to_db=True, db_path=DB_PATH)
                    results = detector.analyze(data)
                    alerts_df = results[results["is_anomaly"]].copy()
                    alerts_df.to_csv(ALERTS_FILE, index=False)
                    st.cache_data.clear()
                    st.success("Detection complete!")
                except Exception as e:
                    st.error(f"Error: {str(e)[:40]}")

    with col2:
        if st.button("🤖 ADVISE", use_container_width=True):
            session = get_session(DB_PATH)
            pending = session.query(Alert).filter(Alert.advice.is_(None)).all()
            if pending:
                try:
                    from redis import Redis
                    from rq import Queue

                    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                    redis_conn = Redis.from_url(redis_url)
                    queue = Queue("advisor", connection=redis_conn)

                    for alert in pending:
                        queue.enqueue("tasks.generate_advice_for_alert", alert.id, DB_PATH)

                    st.success(f"Queued {len(pending)}")
                except Exception:
                    from tasks import generate_advice_for_alert

                    for alert in pending:
                        generate_advice_for_alert(alert.id, DB_PATH)
                    st.success(f"Generated {len(pending)}")

                st.cache_data.clear()
            else:
                st.info("No pending alerts")

    st.divider()

    # Navigation
    st.markdown("### 📄 Pages")
    page = option_menu(
        menu_title=None,
        options=["Overview", "Detailed View", "Anomalies", "Insights", "Health Check", "Settings"],
        icons=["graph-up", "table", "exclamation-triangle", "bar-chart", "heart-pulse", "gear"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "5px", "background-color": "#34495e"},
            "icon": {"color": "#ecf0f1", "font-size": "18px"},
            "nav-link": {"color": "#ecf0f1", "font-size": "14px", "--hover-color": "#667eea"},
            "nav-link-selected": {"background-color": "#667eea"},
        },
    )

    st.divider()
    st.caption("Real-time Anomaly Detection & Remediation")
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

# =============================================================================
# LOAD DATA
# =============================================================================

data = load_data(DATA_FILE)
session = get_session(DB_PATH)

alerts_df = None
if session:
    try:
        alerts_query = session.query(Alert).order_by(Alert.created_at.desc())
        alerts_df = pd.read_sql(alerts_query.statement, alerts_query.session.bind)
    except Exception:
        pass

# =============================================================================
# PAGE ROUTING
# =============================================================================

if page == "Overview":
    st.markdown('<h1 class="header-title">📊 Network Overview</h1>', unsafe_allow_html=True)

    if data is not None:
        total_flows = len(data)
        total_alerts = len(alerts_df) if alerts_df is not None else 0
        normal_flows = total_flows - total_alerts
        anomaly_pct = (total_alerts / total_flows * 100) if total_flows > 0 else 0

        # KPI Row 1
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("📦 Total Flows", f"{total_flows:,}", "100%")

        with col2:
            st.metric("✅ Normal", f"{normal_flows:,}", f"{(100 - anomaly_pct):.1f}%")

        with col3:
            st.metric("⚠️ Anomalies", f"{total_alerts:,}", f"{anomaly_pct:.1f}%")

        with col4:
            health = "🟢 Healthy" if anomaly_pct < 5 else "🔴 Critical" if anomaly_pct > 20 else "🟡 Warning"
            st.metric("💓 System", health)

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        # Charts Row
        col_pie, col_timeline = st.columns(2)

        with col_pie:
            st.subheader("Distribution")
            if total_alerts > 0:
                fig = go.Figure(
                    data=[
                        go.Pie(
                            labels=["Normal", "Anomaly"],
                            values=[normal_flows, total_alerts],
                            marker=dict(colors=["#27ae60", "#e74c3c"]),
                            hole=0.4,
                        )
                    ]
                )
                fig.update_layout(
                    showlegend=True,
                    height=350,
                    margin=dict(l=0, r=0, t=0, b=0),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#2c3e50"),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data to display")

        with col_timeline:
            st.subheader("Timeline")
            if alerts_df is not None and len(alerts_df) > 0:
                alerts_df["created_at"] = pd.to_datetime(alerts_df["created_at"])
                daily_counts = alerts_df.groupby(alerts_df["created_at"].dt.date).size()

                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=daily_counts.index,
                        y=daily_counts.values,
                        mode="lines+markers",
                        fill="tozeroy",
                        name="Anomalies",
                        line=dict(color="#e74c3c", width=3),
                        fillcolor="rgba(231, 76, 60, 0.1)",
                    )
                )
                fig.update_layout(
                    height=350,
                    margin=dict(l=0, r=0, t=0, b=0),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#2c3e50"),
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("🔄 Run analysis to load data")

elif page == "Detailed View":
    st.markdown('<h1 class="header-title">🔍 Alert Details</h1>', unsafe_allow_html=True)

    if alerts_df is not None and len(alerts_df) > 0:
        st.info(f"Showing {min(20, len(alerts_df))} of {len(alerts_df)} alerts")

        search_term = st.text_input("🔎 Filter by ID or Status", "")

        filtered = alerts_df.copy()
        if search_term:
            filtered = filtered[
                (filtered["id"].astype(str).str.contains(search_term, case=False))
                | (filtered["status"].astype(str).str.contains(search_term, case=False))
            ]

        st.dataframe(filtered[["id", "created_at", "anomaly_score", "severity", "status"]].head(20), use_container_width=True)
    else:
        st.info("No alerts to display")

elif page == "Anomalies":
    st.markdown('<h1 class="header-title">⚠️ Critical Anomalies</h1>', unsafe_allow_html=True)

    if alerts_df is not None and len(alerts_df) > 0:
        # Sort by score and show top 10
        top_alerts = alerts_df.nlargest(10, "anomaly_score")

        for idx, row in top_alerts.iterrows():
            score = float(row.get("anomaly_score", 0))
            severity = row.get("severity", "unknown")
            status = row.get("status", "new")

            # Determine badge color
            if score > 0.8:
                badge_class = "badge-critical"
            elif score > 0.6:
                badge_class = "badge-high"
            elif score > 0.4:
                badge_class = "badge-medium"
            else:
                badge_class = "badge-low"

            col_info, col_action = st.columns([3, 1])

            with col_info:
                st.markdown(
                    f'<span class="alert-badge {badge_class}">Score: {score:.2f}</span>',
                    unsafe_allow_html=True,
                )
                st.write(f"**Alert #{row['id']}** | {row['created_at']} | Status: {status}")
                if row.get("advice"):
                    st.write(f"💡 {row['advice'][:100]}...")

            with col_action:
                new_status = st.selectbox(
                    "Status",
                    ["new", "investigating", "resolved"],
                    index=["new", "investigating", "resolved"].index(status),
                    key=f"status_{row['id']}",
                )
                if st.button("Save", key=f"save_{row['id']}", use_container_width=True):
                    session.query(Alert).filter(Alert.id == int(row["id"])).update({"status": new_status})
                    session.add(
                        AuditLog(
                            alert_id=int(row["id"]),
                            action="status_changed",
                            actor="analytics_dashboard",
                            note=f"Changed to {new_status}",
                        )
                    )
                    session.commit()
                    st.success("✓ Updated")

            st.divider()
    else:
        st.info("No anomalies detected")

elif page == "Insights":
    st.markdown('<h1 class="header-title">📈 Data Insights</h1>', unsafe_allow_html=True)

    if data is not None:
        tab1, tab2, tab3 = st.tabs(["Load Analysis", "Port Analysis", "Protocol Stats"])

        with tab1:
            if "Sload" in data.columns:
                fig = px.histogram(
                    data,
                    x="Sload",
                    nbins=50,
                    title="Source Load Distribution",
                    color_discrete_sequence=["#667eea"],
                )
                fig.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)

        with tab2:
            if "Sport" in data.columns and "Dport" in data.columns:
                port_analysis = data.groupby(["Sport", "Dport"]).size().nlargest(15).reset_index(name="Count")
                fig = px.bar(
                    port_analysis,
                    x="Count",
                    y=port_analysis["Sport"].astype(str) + "→" + port_analysis["Dport"].astype(str),
                    title="Top 15 Port Pairs",
                    color_discrete_sequence=["#764ba2"],
                    orientation="h",
                )
                fig.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)

        with tab3:
            if "Proto" in data.columns:
                proto_counts = data["Proto"].value_counts()
                fig = px.pie(
                    names=proto_counts.index,
                    values=proto_counts.values,
                    title="Protocol Distribution",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                )
                fig.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#2c3e50"),
                )
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data available")

elif page == "Health Check":
    st.markdown('<h1 class="header-title">🏥 System Health</h1>', unsafe_allow_html=True)

    col_redis, col_db = st.columns(2)

    with col_redis:
        st.subheader("Redis Queue")
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        health = check_redis_health(redis_url)

        if health.get("connected"):
            st.success("✅ Connected")
            stats = get_queue_stats(redis_url)
            if "error" not in stats:
                st.metric("Queue Depth", stats["queue_depth"])
                st.metric("Completed Jobs", stats["jobs_finished"])
                st.metric("Failed Jobs", stats["jobs_failed"])
        else:
            st.error("❌ Redis Offline")
            st.code("redis-server")

    with col_db:
        st.subheader("Database")
        alert_count = session.query(Alert).count()
        advice_pending = session.query(Alert).filter(Alert.advice.is_(None)).count()
        advice_done = session.query(Alert).filter(Alert.advice.isnot(None)).count()

        st.metric("Total Alerts", alert_count)
        st.metric("Pending Advice", advice_pending)
        st.metric("Completed Advice", advice_done)

elif page == "Settings":
    st.markdown('<h1 class="header-title">⚙️ Settings & Export</h1>', unsafe_allow_html=True)

    tab_export, tab_logs = st.tabs(["Data Export", "Audit Logs"])

    with tab_export:
        st.subheader("Download Data")
        col1, col2 = st.columns(2)

        with col1:
            alerts_export = pd.read_sql("SELECT * FROM alerts ORDER BY created_at DESC", session.bind)
            if not alerts_export.empty:
                csv = alerts_export.to_csv(index=False)
                st.download_button("📥 Alerts CSV", csv, "alerts.csv", "text/csv")

        with col2:
            logs_export = pd.read_sql("SELECT * FROM audit_logs ORDER BY timestamp DESC", session.bind)
            if not logs_export.empty:
                csv = logs_export.to_csv(index=False)
                st.download_button("📥 Audit Logs CSV", csv, "audit_logs.csv", "text/csv")

    with tab_logs:
        st.subheader("Recent Activities")
        logs = pd.read_sql("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 50", session.bind)
        if not logs.empty:
            st.dataframe(logs, use_container_width=True)
        else:
            st.info("No audit logs")
