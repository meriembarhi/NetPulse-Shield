import os
import json
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import Alert, AuditLog, create_db, get_session
from system_utils import check_redis_health, get_queue_stats, bulk_enqueue_advice

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NetPulse Shield — Control Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global paths ────────────────────────────────────────────────────────────────
DATA_FILE  = "data/final_project_data.csv"
REPORT_FILE = "Security_Report.txt"
DB_PATH    = os.getenv("DATABASE_URL", "sqlite:///alerts.db")
REDIS_URL  = os.getenv("REDIS_URL",    "redis://localhost:6379/0")

create_db(DB_PATH)

# ── Premium CSS ─────────────────────────────────────────────────────────────────
st.markdown(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">

    <style>
    /* ── Root variables ─────────────────────────────────── */
    :root {
        --bg-primary:   #080D14;
        --bg-secondary: #0D1520;
        --bg-card:      rgba(255,255,255,0.035);
        --border:       rgba(0,242,255,0.12);
        --border-hover: rgba(0,242,255,0.35);
        --cyan:         #00F2FF;
        --cyan-dim:     rgba(0,242,255,0.15);
        --cyan-glow:    rgba(0,242,255,0.25);
        --red:          #FF4B4B;
        --red-dim:      rgba(255,75,75,0.15);
        --amber:        #FFB347;
        --amber-dim:    rgba(255,179,71,0.15);
        --green:        #00E676;
        --green-dim:    rgba(0,230,118,0.15);
        --text-primary: #E8EDF5;
        --text-muted:   rgba(232,237,245,0.45);
        --text-subtle:  rgba(232,237,245,0.25);
        --radius:       12px;
        --radius-sm:    8px;
        --font-body:    'DM Sans', sans-serif;
        --font-mono:    'Space Mono', monospace;
    }

    /* ── Global reset ───────────────────────────────────── */
    html, body, [class*="css"] {
        font-family: var(--font-body);
        color: var(--text-primary);
    }
    .stApp {
        background: var(--bg-primary);
        background-image:
            radial-gradient(ellipse 80% 50% at 50% -20%, rgba(0,242,255,0.06) 0%, transparent 60%),
            radial-gradient(ellipse 40% 30% at 85% 10%, rgba(0,100,255,0.05) 0%, transparent 50%);
    }

    /* ── Sidebar glass ──────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: rgba(13,21,32,0.85) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid var(--border) !important;
    }
    [data-testid="stSidebar"] * { font-family: var(--font-body); }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: var(--cyan) !important;
        font-family: var(--font-mono) !important;
        font-size: 0.75rem !important;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }

    /* ── Main content padding ────────────────────────────── */
    .block-container {
        padding: 2rem 2.5rem 4rem !important;
        max-width: 1600px;
    }

    /* ── Typography ──────────────────────────────────────── */
    h1 { font-size: 1.65rem !important; font-weight: 700 !important; letter-spacing: -0.02em; }
    h2, h3 { font-weight: 600 !important; letter-spacing: -0.01em; }

    /* ── Divider ─────────────────────────────────────────── */
    hr {
        border: none !important;
        border-top: 1px solid var(--border) !important;
        margin: 1.5rem 0 !important;
    }

    /* ── Buttons ─────────────────────────────────────────── */
    .stButton > button {
        background: var(--cyan-dim) !important;
        border: 1px solid var(--border) !important;
        color: var(--cyan) !important;
        border-radius: var(--radius-sm) !important;
        font-family: var(--font-body) !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        padding: 0.5rem 1.1rem !important;
        transition: all 0.2s ease !important;
        letter-spacing: 0.01em;
    }
    .stButton > button:hover {
        background: rgba(0,242,255,0.22) !important;
        border-color: var(--border-hover) !important;
        box-shadow: 0 0 16px var(--cyan-glow) !important;
        transform: translateY(-1px) !important;
    }

    /* ── Inputs ──────────────────────────────────────────── */
    .stTextInput > div > div > input,
    .stSelectSlider > div,
    .stSlider > div {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-sm) !important;
        color: var(--text-primary) !important;
    }

    /* ── DataFrame ───────────────────────────────────────── */
    .stDataFrame {
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        overflow: hidden;
    }
    [data-testid="stDataFrame"] > div {
        border-radius: var(--radius) !important;
    }

    /* ── Info / success / error boxes ───────────────────── */
    .stAlert {
        border-radius: var(--radius-sm) !important;
        font-size: 0.85rem !important;
    }

    /* ── Metric widget ───────────────────────────────────── */
    [data-testid="stMetric"] {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 1rem 1.2rem;
    }

    /* ── Plotly chart containers ─────────────────────────── */
    .js-plotly-plot .plotly { border-radius: var(--radius); }

    /* ── Scrollbar ───────────────────────────────────────── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg-primary); }
    ::-webkit-scrollbar-thumb { background: rgba(0,242,255,0.2); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(0,242,255,0.4); }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Helper: KPI card HTML ────────────────────────────────────────────────────────
def kpi_card(icon_svg, label, value, accent="#00F2FF", accent_bg="rgba(0,242,255,0.10)"):
    return f"""
    <div style="
        background: rgba(255,255,255,0.030);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 18px 20px;
        display: flex;
        align-items: center;
        gap: 16px;
        transition: border-color 0.2s;
        height: 100%;
    ">
        <div style="
            width: 44px; height: 44px; flex-shrink: 0;
            background: {accent_bg};
            border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
        ">
            {icon_svg}
        </div>
        <div>
            <div style="font-size:0.72rem; color:rgba(232,237,245,0.45); letter-spacing:0.1em; text-transform:uppercase; font-weight:500; margin-bottom:4px;">{label}</div>
            <div style="font-size:1.55rem; font-weight:700; color:{accent}; font-family:'DM Sans',sans-serif; line-height:1;">{value}</div>
        </div>
    </div>
    """

# ── SVG icons ─────────────────────────────────────────────────────────────────
ICON_FLOWS = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00F2FF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>'
ICON_ALERT = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF4B4B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>'
ICON_CLOCK = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FFB347" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'
ICON_CHECK = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00E676" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>'

# ── Plotly theme ──────────────────────────────────────────────────────────────
PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans, sans-serif", color="rgba(232,237,245,0.7)", size=12),
    margin=dict(l=8, r=8, t=36, b=8),
    xaxis=dict(
        showgrid=False, zeroline=False,
        linecolor="rgba(255,255,255,0.08)",
        tickfont=dict(size=11),
    ),
    yaxis=dict(
        showgrid=True, gridcolor="rgba(255,255,255,0.04)", zeroline=False,
        tickfont=dict(size=11),
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        bordercolor="rgba(255,255,255,0.06)",
        borderwidth=1,
    ),
    hoverlabel=dict(
        bgcolor="#0D1520",
        bordercolor="rgba(0,242,255,0.3)",
        font=dict(family="DM Sans, sans-serif", color="#E8EDF5"),
    ),
)

# ── Utility ───────────────────────────────────────────────────────────────────
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


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:1.5rem;">
            <span style="font-size:1.5rem;">🛡️</span>
            <span style="font-family:'Space Mono',monospace;font-size:0.85rem;font-weight:700;
                         color:#00F2FF;letter-spacing:0.04em;">NETPULSE<br>SHIELD</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if os.getenv("DASHBOARD_TOKEN"):
        token = st.text_input("Access token", type="password", placeholder="Enter token…")
        if token != os.getenv("DASHBOARD_TOKEN"):
            st.error("Enter valid token to continue")
            st.stop()

    st.markdown("**ACTIONS**")
    if st.button("⚡ Run Detection (sample)"):
        st.info("Run the CLI pipeline or use `pipeline.py` for full runs.")

    st.markdown("---")
    st.caption("NetPulse Shield v2 · Premium")


# ── Page header ───────────────────────────────────────────────────────────────
col_title, col_ts = st.columns([5, 2])
with col_title:
    st.markdown("## 🛡️ NetPulse Shield — Control Center")
    st.markdown(
        "<p style='color:rgba(232,237,245,0.45);font-size:0.88rem;margin-top:-8px;'>"
        "Real-time anomaly detection · Triage & remediation · AI-powered insights"
        "</p>",
        unsafe_allow_html=True,
    )
with col_ts:
    st.markdown(
        f"<div style='text-align:right;padding-top:8px;'>"
        f"<span style='font-family:Space Mono,monospace;font-size:0.72rem;"
        f"color:rgba(0,242,255,0.6);letter-spacing:0.06em;'>"
        f"LAST REFRESH<br>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span></div>",
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── Load data ─────────────────────────────────────────────────────────────────
data    = load_data()
session = get_session(DB_PATH)
alerts  = load_alerts(session) if session is not None else pd.DataFrame()

# ── KPI row ───────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
pending = int(alerts[alerts["advice"].isna()].shape[0]) if not alerts.empty else 0

with k1:
    st.markdown(
        kpi_card(ICON_FLOWS, "Total Flows", f"{len(data):,}",
                 accent="#00F2FF", accent_bg="rgba(0,242,255,0.10)"),
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        kpi_card(ICON_ALERT, "Total Alerts", f"{len(alerts):,}",
                 accent="#FF4B4B", accent_bg="rgba(255,75,75,0.10)"),
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        kpi_card(ICON_CLOCK, "Advice Pending", f"{pending}",
                 accent="#FFB347", accent_bg="rgba(255,179,71,0.10)"),
        unsafe_allow_html=True,
    )
with k4:
    st.markdown(
        kpi_card(ICON_CHECK, "Last Run", datetime.now().strftime("%H:%M:%S"),
                 accent="#00E676", accent_bg="rgba(0,230,118,0.10)"),
        unsafe_allow_html=True,
    )

st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
st.markdown("---")

# ── Filters ───────────────────────────────────────────────────────────────────
st.markdown(
    "<p style='font-size:0.72rem;letter-spacing:0.1em;text-transform:uppercase;"
    "color:rgba(0,242,255,0.6);font-weight:600;margin-bottom:8px;'>FILTERS</p>",
    unsafe_allow_html=True,
)
f_col1, f_col2, f_col3, f_col4 = st.columns([2, 2, 2, 4])
with f_col1:
    severity = st.select_slider(
        "Severity", options=["low", "medium", "high", "critical"], value=("low", "critical")
    )
with f_col2:
    min_score = st.slider("Min anomaly score", 0.0, 1.0, 0.5)
with f_col3:
    date_range = st.date_input("Created between", [])
with f_col4:
    search = st.text_input("🔍  Search by IP / Flow ID / note", placeholder="e.g. 192.168.1.1")

st.markdown("---")

# ── Charts ────────────────────────────────────────────────────────────────────
chart_left, chart_right = st.columns([3, 2])

with chart_left:
    st.markdown("#### Alerts Over Time")
    if not alerts.empty:
        alerts["created_at"] = pd.to_datetime(alerts["created_at"])
        series = (
            alerts
            .groupby(pd.Grouper(key="created_at", freq="D"))
            .size()
            .reset_index(name="count")
        )
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=series["created_at"], y=series["count"],
            mode="lines+markers",
            line=dict(color="#00F2FF", width=2.5),
            marker=dict(size=6, color="#00F2FF",
                        line=dict(color="#080D14", width=2)),
            fill="tozeroy",
            fillcolor="rgba(0,242,255,0.06)",
            hovertemplate="<b>%{x|%b %d}</b><br>Alerts: %{y}<extra></extra>",
        ))
        fig.update_layout(title="Daily Alert Volume", **PLOT_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.markdown(
            "<div style='background:rgba(255,255,255,0.03);border:1px dashed rgba(255,255,255,0.08);"
            "border-radius:12px;padding:40px;text-align:center;"
            "color:rgba(232,237,245,0.35);font-size:0.88rem;'>"
            "No alert data · Run the pipeline to populate</div>",
            unsafe_allow_html=True,
        )

with chart_right:
    st.markdown("#### Feature Correlation")
    if not data.empty:
        sample = data.sample(min(2000, len(data)))
        if "Sload" in sample.columns and "Dload" in sample.columns:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=sample["Sload"], y=sample["Dload"],
                mode="markers",
                marker=dict(
                    size=4,
                    color=sample["Sload"],
                    colorscale=[[0, "#00F2FF"], [0.5, "#0080FF"], [1, "#FF4B4B"]],
                    opacity=0.55,
                    showscale=False,
                ),
                hovertemplate="Sload: %{x:.2f}<br>Dload: %{y:.2f}<extra></extra>",
            ))
            fig2.update_layout(title="Sload vs Dload", **PLOT_LAYOUT)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Feature sample unavailable")
    else:
        st.info("No raw data loaded")

st.markdown("---")

# ── Alerts triage table ───────────────────────────────────────────────────────
st.markdown("#### 🚨 Detected Alerts — Triage")

if alerts.empty:
    st.markdown(
        "<div style='background:rgba(255,75,75,0.06);border:1px solid rgba(255,75,75,0.15);"
        "border-radius:12px;padding:24px 28px;color:rgba(232,237,245,0.55);font-size:0.88rem;'>"
        "No alerts in database. Run the analysis pipeline or import <code>alerts.csv</code>.</div>",
        unsafe_allow_html=True,
    )
else:
    display = alerts.copy()

    if search:
        display = display[
            display.apply(lambda r: search.lower() in json.dumps(r.to_dict()).lower(), axis=1)
        ]
    display = display[display["anomaly_score"] >= min_score]

    selected = st.multiselect(
        "Select alerts for bulk actions",
        options=display["id"].tolist(),
        placeholder="Choose alert IDs…",
    )

    st.dataframe(
        display.head(200),
        use_container_width=True,
        height=320,
    )

    action_col1, action_col2 = st.columns(2)
    with action_col1:
        if st.button("🔁 Enqueue selected for advice"):
            if not selected:
                st.warning("No alerts selected")
            else:
                redis_health = check_redis_health(REDIS_URL)
                if redis_health.get("connected"):
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
                out_df = display[display["id"].isin(selected)]
                csv = out_df.to_csv(index=False)
                st.download_button(
                    "Download CSV",
                    csv,
                    file_name="selected_alerts.csv",
                    mime="text/csv",
                )

st.markdown("---")

# ── Security report ───────────────────────────────────────────────────────────
st.markdown("#### 📄 Security Report")
if os.path.exists(REPORT_FILE):
    with open(REPORT_FILE, "r", encoding="utf-8") as fh:
        rep = fh.read()
    st.markdown(
        f"<div style='background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.06);"
        f"border-radius:12px;padding:24px 28px;font-family:Space Mono,monospace;"
        f"font-size:0.78rem;line-height:1.7;color:rgba(232,237,245,0.8);"
        f"white-space:pre-wrap;max-height:420px;overflow-y:auto;'>{rep}</div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        "<div style='background:rgba(255,179,71,0.06);border:1px solid rgba(255,179,71,0.15);"
        "border-radius:12px;padding:20px 24px;color:rgba(232,237,245,0.55);font-size:0.85rem;'>"
        "No report generated yet. Run <code>pipeline.py</code> to create <code>Security_Report.txt</code>.</div>",
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── System status ─────────────────────────────────────────────────────────────
st.markdown(
    "<p style='font-size:0.72rem;letter-spacing:0.1em;text-transform:uppercase;"
    "color:rgba(0,242,255,0.6);font-weight:600;margin-bottom:12px;'>SYSTEM STATUS</p>",
    unsafe_allow_html=True,
)
col_a, col_b = st.columns(2)

with col_a:
    st.markdown(
        "<div style='background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);"
        "border-radius:12px;padding:20px 22px;'>",
        unsafe_allow_html=True,
    )
    st.markdown("**Redis / Queue**")
    redis_status = check_redis_health(REDIS_URL)
    if redis_status.get("connected"):
        st.success(f"Connected · {REDIS_URL}")
        qstats = get_queue_stats(REDIS_URL)
        if "queue_depth" in qstats:
            st.metric("Queue Depth", qstats["queue_depth"])
    else:
        st.error("Redis unavailable — background tasks disabled")
    st.markdown("</div>", unsafe_allow_html=True)

with col_b:
    st.markdown(
        "<div style='background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);"
        "border-radius:12px;padding:20px 22px;'>",
        unsafe_allow_html=True,
    )
    st.markdown("**Database**")
    if session is not None:
        try:
            alert_count = session.query(Alert).count()
            audit_count = session.query(AuditLog).count()
            c1, c2 = st.columns(2)
            c1.metric("Alerts", f"{alert_count:,}")
            c2.metric("Audit Entries", f"{audit_count:,}")
        except Exception:
            st.error("Database unavailable")
    else:
        st.error("DB session unavailable")
    st.markdown("</div>", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    "<div style='margin-top:2rem;text-align:center;color:rgba(232,237,245,0.2);"
    "font-size:0.72rem;font-family:Space Mono,monospace;letter-spacing:0.06em;'>"
    "NETPULSE SHIELD · PREMIUM CONTROL CENTER · AI-POWERED NETWORK SECURITY"
    "</div>",
    unsafe_allow_html=True,
)