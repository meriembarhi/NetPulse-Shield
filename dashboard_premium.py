import os
import json
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from db import Alert, AuditLog, create_db, get_session
from system_utils import check_redis_health, get_queue_stats, bulk_enqueue_advice

# Premium Dashboard - clean, modern, and professional layout
st.set_page_config(page_title="NetPulse Shield — Control Center", page_icon="🛡️", layout="wide")

# Global paths
DATA_FILE = "data/final_project_data.csv"
REPORT_FILE = "Security_Report.txt"
DB_PATH = os.getenv("DATABASE_URL", "sqlite:///alerts.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

create_db(DB_PATH)

# Styles: subtle dark theme with glassy cards
st.markdown(
    """
    <style>
    .reportview-container { background: linear-gradient(180deg, #0f1720, #071022); }
    .sidebar .sidebar-content { background: #071022; }
    .card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.04); padding: 16px; border-radius: 12px; }
    .kpi { font-size: 22px; font-weight: 700; }
    .muted { color: rgba(255,255,255,0.65); }
    </style>
    """,
    unsafe_allow_html=True,
)

# Utility
@st.cache_data(ttl=60)
def load_data(path=DATA_FILE):
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()


def load_alerts(session):
    try:
        q = session.query(Alert).order_by(Alert.created_at.desc())
        return pd.read_sql(q.statement, q.session.bind)
    except Exception:
        return pd.DataFrame()


# Sidebar controls
st.sidebar.header("NetPulse Controls")
if os.getenv("DASHBOARD_TOKEN"):
    token = st.sidebar.text_input("Access token", type="password")
    if token != os.getenv("DASHBOARD_TOKEN"):
        st.sidebar.error("Enter valid token to continue")
        st.stop()

st.sidebar.subheader("Actions")
if st.sidebar.button("Run Detection (sample)"):
    st.sidebar.info("Run the CLI pipeline or use `pipeline.py` for full runs.")

st.sidebar.markdown("---")

# Main header
col_title, col_spacer, col_logo = st.columns([6, 1, 1])
with col_title:
    st.markdown("# 🛡️ NetPulse Shield — Control Center")
    st.markdown("<div class='muted'>Premium interactive view — alerts, trends, and triage</div>", unsafe_allow_html=True)
with col_logo:
    st.image("https://raw.githubusercontent.com/plotly/datasets/master/logo.png", width=64)

# Load data
data = load_data()
session = get_session(DB_PATH)
alerts = load_alerts(session) if session is not None else pd.DataFrame()

# Top KPIs
kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
with kpi_col1:
    st.markdown("<div class='card'><div class='kpi'>Total Flows</div><div class='muted'>%s</div></div>" % (len(data)), unsafe_allow_html=True)
with kpi_col2:
    st.markdown("<div class='card'><div class='kpi'>Total Alerts</div><div class='muted'>%s</div></div>" % (len(alerts)), unsafe_allow_html=True)
with kpi_col3:
    pending = int(alerts[alerts['advice'].isna()].shape[0]) if not alerts.empty else 0
    st.markdown("<div class='card'><div class='kpi'>Advice Pending</div><div class='muted'>%s</div></div>" % (pending), unsafe_allow_html=True)
with kpi_col4:
    st.markdown("<div class='card'><div class='kpi'>Last Run</div><div class='muted'>%s</div></div>" % (datetime.now().isoformat(timespec='seconds')), unsafe_allow_html=True)

st.markdown("---")

# Filters row
f_col1, f_col2, f_col3, f_col4 = st.columns([2, 2, 2, 4])
with f_col1:
    severity = st.select_slider("Severity", options=["low", "medium", "high", "critical"], value=("low", "critical"))
with f_col2:
    min_score = st.slider("Min anomaly score", 0.0, 1.0, 0.5)
with f_col3:
    date_range = st.date_input("Created between", [])
with f_col4:
    search = st.text_input("Search by IP / Flow ID / note")

# Charts and insights
chart_col_left, chart_col_right = st.columns([2, 1])
with chart_col_left:
    st.subheader("Alerts Over Time")
    if not alerts.empty:
        alerts['created_at'] = pd.to_datetime(alerts['created_at'])
        series = alerts.groupby(pd.Grouper(key='created_at', freq='D')).size().reset_index(name='count')
        fig = px.line(series, x='created_at', y='count', title='Daily Alerts', markers=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.empty()

with chart_col_right:
    st.subheader("Feature Correlation (sample)")
    if not data.empty:
        sample = data.sample(min(2000, len(data)))
        if 'Sload' in sample.columns and 'Dload' in sample.columns:
            fig2 = px.scatter(sample, x='Sload', y='Dload', opacity=0.6, title='Sload vs Dload')
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info('Feature sample unavailable')
    else:
        st.info('No raw data loaded')

st.markdown("---")

# Alerts table with selection and actions
st.subheader("Detected Alerts — Triage")
if alerts.empty:
    st.info("No alerts in DB. Run the analysis or import alerts.csv.")
else:
    display = alerts.copy()
    # basic filtering
    if search:
        display = display[display.apply(lambda r: search.lower() in json.dumps(r.to_dict()).lower(), axis=1)]
    display = display[display['anomaly_score'] >= min_score]

    selected = st.multiselect("Select alerts for bulk actions", options=display['id'].tolist())

    st.dataframe(display.head(200))

    action_col1, action_col2 = st.columns(2)
    with action_col1:
        if st.button("🔁 Enqueue selected for advice"):
            if not selected:
                st.warning("No alerts selected")
            else:
                redis_health = check_redis_health(REDIS_URL)
                if redis_health.get('connected'):
                    enqueued = bulk_enqueue_advice(selected, DB_PATH, REDIS_URL)
                    st.success(f"Enqueued {enqueued} alerts for advice")
                else:
                    st.info("Redis unavailable — generating advice synchronously")
                    from tasks import generate_advice_for_alert
                    for aid in selected:
                        generate_advice_for_alert(aid, DB_PATH)
                    st.success(f"Generated advice for {len(selected)} alerts (sync)")
    with action_col2:
        if st.button("📥 Export selected as CSV"):
            if not selected:
                st.warning("No alerts selected")
            else:
                out_df = display[display['id'].isin(selected)]
                csv = out_df.to_csv(index=False)
                st.download_button("Download CSV", csv, file_name='selected_alerts.csv', mime='text/csv')

st.markdown("---")

# Security report
st.subheader("Security Report")
if os.path.exists(REPORT_FILE):
    with open(REPORT_FILE, 'r', encoding='utf-8') as fh:
        rep = fh.read()
    st.markdown(rep)
else:
    st.info("No report generated yet. Run `pipeline.py` to create a Security_Report.txt")

# System status footer
st.markdown("---")
col_a, col_b = st.columns(2)
with col_a:
    st.write("**System Status**")
    redis_status = check_redis_health(REDIS_URL)
    if redis_status.get('connected'):
        st.success(f"Redis connected: {REDIS_URL}")
        qstats = get_queue_stats(REDIS_URL)
        if 'queue_depth' in qstats:
            st.metric("Queue Depth", qstats['queue_depth'])
    else:
        st.error("Redis not available — background tasks disabled")
with col_b:
    st.write("**Database**")
    if session is not None:
        try:
            st.write(f"Alerts in DB: {session.query(Alert).count()}")
            st.write(f"Audit entries: {session.query(AuditLog).count()}")
        except Exception:
            st.write("Database: unavailable")
    else:
        st.write("DB session unavailable")

# End
st.sidebar.caption("Premium dashboard created by the development team — contact for customization")
