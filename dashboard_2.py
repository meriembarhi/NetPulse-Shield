import os
import json
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import Alert, AuditLog, create_db, get_session
from system_utils import check_redis_health, get_queue_stats, bulk_enqueue_advice

# ═══════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ═══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="NetPulse Shield",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_FILE   = "data/final_project_data.csv"
REPORT_FILE = "Security_Report.txt"
DB_PATH     = os.getenv("DATABASE_URL", "sqlite:///alerts.db")
REDIS_URL   = os.getenv("REDIS_URL",    "redis://localhost:6379/0")

create_db(DB_PATH)

# ═══════════════════════════════════════════════════════════════
#  GLOBAL CSS  — Palantir / Foundry aesthetic
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;700&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">

<style>
:root {
  --c-bg:            #05080D;
  --c-surface:       #090D15;
  --c-panel:         #0C1118;
  --c-border:        #1A2535;
  --c-border-hot:    #1E4976;
  --c-accent:        #1D72AA;
  --c-accent-bright: #2A9FD6;
  --c-accent-glow:   rgba(29,114,170,0.18);
  --c-danger:        #C0392B;
  --c-warn:          #E67E22;
  --c-ok:            #27AE60;
  --c-text:          #C8D6E5;
  --c-text-dim:      #5A7A9A;
  --c-text-faint:    #1A2535;
  --font-mono:       'IBM Plex Mono', monospace;
  --font-sans:       'IBM Plex Sans', sans-serif;
  --r: 4px;
}

html, body, [class*="css"], .stApp {
  font-family: var(--font-sans) !important;
  background-color: var(--c-bg) !important;
  color: var(--c-text) !important;
}

/* Scanline overlay */
.stApp::before {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 9999;
  background-image: repeating-linear-gradient(
    0deg, transparent, transparent 3px,
    rgba(0,0,0,0.055) 3px, rgba(0,0,0,0.055) 4px
  );
}

/* Animated top bar sweep */
.stApp::after {
  content: '';
  position: fixed;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg,
    transparent 0%, var(--c-accent) 40%,
    var(--c-accent-bright) 50%, var(--c-accent) 60%, transparent 100%
  );
  background-size: 200% 100%;
  animation: np-sweep 4s linear infinite;
  z-index: 10000;
}
@keyframes np-sweep {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

[data-testid="stSidebar"] {
  background: var(--c-surface) !important;
  border-right: 1px solid var(--c-border) !important;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 0 !important; }

.block-container {
  padding: 1.5rem 2.2rem 4rem !important;
  max-width: 1700px !important;
}

#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

hr {
  border: none !important;
  border-top: 1px solid var(--c-border) !important;
  margin: 1.2rem 0 !important;
}

.stButton > button {
  font-family: var(--font-mono) !important;
  font-size: 0.70rem !important;
  font-weight: 500 !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
  color: var(--c-accent-bright) !important;
  background: transparent !important;
  border: 1px solid var(--c-border-hot) !important;
  border-radius: var(--r) !important;
  padding: 0.45rem 1.1rem !important;
  transition: all 0.15s ease !important;
}
.stButton > button:hover {
  background: var(--c-accent-glow) !important;
  border-color: var(--c-accent-bright) !important;
  color: #fff !important;
  box-shadow: 0 0 14px rgba(42,159,214,0.22) !important;
}

.stTextInput input {
  font-family: var(--font-mono) !important;
  font-size: 0.78rem !important;
  background: var(--c-panel) !important;
  border: 1px solid var(--c-border) !important;
  border-radius: var(--r) !important;
  color: var(--c-text) !important;
}
.stTextInput input:focus {
  border-color: var(--c-accent) !important;
  box-shadow: 0 0 0 3px rgba(29,114,170,0.14) !important;
}

.stDataFrame, [data-testid="stDataFrame"] {
  border: 1px solid var(--c-border) !important;
  border-radius: var(--r) !important;
}

.stAlert { border-radius: var(--r) !important; font-family: var(--font-mono) !important; font-size: 0.74rem !important; }

[data-testid="stMetric"] {
  background: var(--c-panel);
  border: 1px solid var(--c-border);
  border-radius: var(--r);
  padding: 0.75rem 1rem;
}
[data-testid="stMetricValue"] { font-family: var(--font-mono) !important; color: var(--c-accent-bright) !important; }

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--c-bg); }
::-webkit-scrollbar-thumb { background: #1E3A5A; border-radius: 2px; }

/* ── Custom component styles ── */
.np-logo {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--c-accent-bright);
  padding: 18px 0 12px;
  border-bottom: 1px solid var(--c-border);
  margin-bottom: 18px;
}
.np-logo span {
  display: block;
  font-size: 0.50rem;
  letter-spacing: 0.28em;
  color: var(--c-text-dim);
  font-weight: 400;
  margin-top: 4px;
}

.np-title {
  font-family: var(--font-mono);
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--c-text);
  line-height: 1.3;
}
.np-title .acc { color: var(--c-accent-bright); }
.np-subtitle {
  font-family: var(--font-sans);
  font-size: 0.76rem;
  color: var(--c-text-dim);
  margin-top: 4px;
}

.np-section {
  font-family: var(--font-mono);
  font-size: 0.58rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--c-accent-bright);
  border-bottom: 1px solid var(--c-border);
  padding-bottom: 6px;
  margin-bottom: 12px;
  margin-top: 4px;
}

.np-eyebrow {
  font-family: var(--font-mono);
  font-size: 0.58rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--c-text-dim);
}

.np-kpi {
  background: var(--c-panel);
  border: 1px solid var(--c-border);
  border-radius: var(--r);
  padding: 16px 18px 14px;
  position: relative;
  overflow: hidden;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.np-kpi::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 2px;
}
.np-kpi.np-cyan::before  { background: var(--c-accent-bright); }
.np-kpi.np-red::before   { background: var(--c-danger); }
.np-kpi.np-amber::before { background: var(--c-warn); }
.np-kpi.np-green::before { background: var(--c-ok); }
.np-kpi:hover { border-color: var(--c-border-hot); box-shadow: 0 0 18px rgba(29,114,170,0.08); }

.np-kpi-label {
  font-family: var(--font-mono);
  font-size: 0.58rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--c-text-dim);
  margin-bottom: 8px;
}
.np-kpi-value {
  font-family: var(--font-mono);
  font-size: 1.6rem;
  font-weight: 700;
  line-height: 1;
  color: var(--c-text);
}
.np-kpi.np-cyan  .np-kpi-value { color: var(--c-accent-bright); }
.np-kpi.np-red   .np-kpi-value { color: var(--c-danger); }
.np-kpi.np-amber .np-kpi-value { color: var(--c-warn); }
.np-kpi.np-green .np-kpi-value { color: var(--c-ok); }
.np-kpi-sub {
  font-family: var(--font-mono);
  font-size: 0.60rem;
  color: var(--c-text-faint);
  margin-top: 6px;
}

@keyframes np-pulse {
  0%,100% { opacity: 1; transform: scale(1); }
  50%     { opacity: 0.5; transform: scale(0.85); }
}
.np-dot {
  display: inline-block;
  width: 7px; height: 7px;
  border-radius: 50%;
  margin-right: 6px;
  animation: np-pulse 2s ease-in-out infinite;
  position: relative; top: 1px;
}
.np-dot.g { background: var(--c-ok); }
.np-dot.r { background: var(--c-danger); }
.np-dot.a { background: var(--c-warn); }

.np-status-row {
  display: flex;
  align-items: center;
  font-family: var(--font-mono);
  font-size: 0.70rem;
  color: var(--c-text-dim);
  padding: 7px 0;
  border-bottom: 1px solid var(--c-text-faint);
}
.np-status-row .v { color: var(--c-text); font-weight: 500; margin-left: auto; }

.np-stat-panel {
  background: var(--c-panel);
  border: 1px solid var(--c-border);
  border-radius: var(--r);
  padding: 18px 20px;
}
.np-stat-panel h4 {
  font-family: var(--font-mono);
  font-size: 0.58rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--c-accent-bright);
  margin: 0 0 12px;
}

.np-empty {
  border: 1px dashed var(--c-border);
  border-radius: var(--r);
  padding: 32px;
  text-align: center;
  font-family: var(--font-mono);
  font-size: 0.68rem;
  color: var(--c-text-faint);
  letter-spacing: 0.1em;
}

.np-report {
  background: var(--c-panel);
  border: 1px solid var(--c-border);
  border-radius: var(--r);
  padding: 20px 24px;
  font-family: var(--font-mono);
  font-size: 0.70rem;
  line-height: 1.9;
  color: rgba(200,214,229,0.7);
  white-space: pre-wrap;
  max-height: 380px;
  overflow-y: auto;
}

@keyframes np-blink { 0%,100%{opacity:1} 50%{opacity:0} }
.np-cursor { animation: np-blink 1.1s step-end infinite; color: var(--c-accent-bright); }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════
def kpi(cls, label, value, sub=""):
    return (
        f'<div class="np-kpi {cls}">'
        f'<div class="np-kpi-label">{label}</div>'
        f'<div class="np-kpi-value">{value}</div>'
        + (f'<div class="np-kpi-sub">{sub}</div>' if sub else "")
        + "</div>"
    )

def section(text):
    st.markdown(f'<div class="np-section">// {text}</div>', unsafe_allow_html=True)

def dot(color):
    return f'<span class="np-dot {color}"></span>'

PLOT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="IBM Plex Mono, monospace", color="#5A7A9A", size=10),
    margin=dict(l=4, r=4, t=24, b=4),
    xaxis=dict(showgrid=False, zeroline=False, linecolor="#1A2535",
               tickfont=dict(size=10), tickcolor="#1A2535"),
    yaxis=dict(showgrid=True, gridcolor="rgba(26,37,53,0.7)", zeroline=False,
               tickfont=dict(size=10)),
    hoverlabel=dict(bgcolor="#090D15", bordercolor="#1E4976",
                    font=dict(family="IBM Plex Mono, monospace", color="#C8D6E5", size=11)),
)


# ═══════════════════════════════════════════════════════════════
#  DATA  (logic unchanged)
# ═══════════════════════════════════════════════════════════════
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


# ═══════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div class="np-logo">
      NETPULSE SHIELD
      <span>THREAT INTELLIGENCE PLATFORM</span>
    </div>""", unsafe_allow_html=True)

    if os.getenv("DASHBOARD_TOKEN"):
        token = st.text_input("ACCESS TOKEN", type="password", placeholder="••••••••")
        if token != os.getenv("DASHBOARD_TOKEN"):
            st.error("Unauthorized.")
            st.stop()

    st.markdown('<div class="np-eyebrow" style="margin-bottom:8px;">Operations</div>', unsafe_allow_html=True)
    if st.button("⚡  RUN DETECTION"):
        st.info("Invoke pipeline.py for full analysis runs.")

    st.markdown("---")
    now = datetime.now()
    st.markdown(f"""
    <div style="font-family:'IBM Plex Mono',monospace;font-size:0.60rem;color:#1A2535;line-height:2.2;">
      <div style="color:#5A7A9A;">SESSION · {now.strftime('%Y-%m-%d')}</div>
      <div style="color:#2A3A4A;">{now.strftime('%H:%M:%S')} UTC</div>
    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  LOAD DATA
# ═══════════════════════════════════════════════════════════════
data    = load_data()
session = get_session(DB_PATH)
alerts  = load_alerts(session) if session is not None else pd.DataFrame()
pending = int(alerts[alerts["advice"].isna()].shape[0]) if not alerts.empty else 0
now     = datetime.now()


# ═══════════════════════════════════════════════════════════════
#  PAGE HEADER
# ═══════════════════════════════════════════════════════════════
h_l, h_r = st.columns([5, 2])
with h_l:
    st.markdown(f"""
    <div class="np-title">
      <span class="acc">▶</span> NETPULSE SHIELD
      <span style="font-weight:300;color:#5A7A9A;font-size:0.82rem;"> / CONTROL CENTER</span>
      <span class="np-cursor">_</span>
    </div>
    <div class="np-subtitle">Anomaly detection · AI triage · Real-time remediation intelligence</div>
    """, unsafe_allow_html=True)
with h_r:
    st.markdown(f"""
    <div style="text-align:right;font-family:'IBM Plex Mono',monospace;font-size:0.58rem;
                color:#2A3A4A;line-height:2.2;padding-top:6px;">
      <div style="color:#5A7A9A;letter-spacing:0.14em;">LAST REFRESH</div>
      <div style="color:#C8D6E5;font-size:0.70rem;">{now.strftime('%Y-%m-%dT%H:%M:%S')}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("---")


# ═══════════════════════════════════════════════════════════════
#  KPI ROW
# ═══════════════════════════════════════════════════════════════
section("SYSTEM OVERVIEW")
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(kpi("np-cyan",  "TOTAL FLOWS",    f"{len(data):,}",  "captured packets"), unsafe_allow_html=True)
with k2:
    st.markdown(kpi("np-red",   "TOTAL ALERTS",   f"{len(alerts):,}", "anomalies flagged"), unsafe_allow_html=True)
with k3:
    st.markdown(kpi("np-amber", "ADVICE PENDING", str(pending),      "awaiting triage"),   unsafe_allow_html=True)
with k4:
    st.markdown(kpi("np-green", "LAST RUN",       now.strftime("%H:%M"), now.strftime("%Y-%m-%d")), unsafe_allow_html=True)

st.markdown("<div style='margin:1rem 0'></div>", unsafe_allow_html=True)
st.markdown("---")


# ═══════════════════════════════════════════════════════════════
#  FILTERS
# ═══════════════════════════════════════════════════════════════
section("FILTERS")
f1, f2, f3, f4 = st.columns([2, 2, 2, 4])
with f1:
    severity   = st.select_slider("Severity", options=["low","medium","high","critical"], value=("low","critical"))
with f2:
    min_score  = st.slider("Min anomaly score", 0.0, 1.0, 0.5)
with f3:
    date_range = st.date_input("Created between", [])
with f4:
    search     = st.text_input("Search  ·  IP / Flow ID / note", placeholder="e.g. 192.168.1.100")

st.markdown("---")


# ═══════════════════════════════════════════════════════════════
#  CHARTS
# ═══════════════════════════════════════════════════════════════
section("INTELLIGENCE VIEW")
c_l, c_r = st.columns([3, 2])

with c_l:
    st.markdown('<div class="np-eyebrow" style="margin-bottom:6px;">Alert Volume · Daily</div>', unsafe_allow_html=True)
    if not alerts.empty:
        alerts["created_at"] = pd.to_datetime(alerts["created_at"])
        series = alerts.groupby(pd.Grouper(key="created_at", freq="D")).size().reset_index(name="count")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=series["created_at"], y=series["count"],
            mode="none", fill="tozeroy",
            fillcolor="rgba(29,114,170,0.07)",
            showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=series["created_at"], y=series["count"],
            mode="lines+markers",
            line=dict(color="#2A9FD6", width=2, shape="spline"),
            marker=dict(size=5, color="#2A9FD6", line=dict(color="#05080D", width=2)),
            fill="none", showlegend=False,
            hovertemplate="<b>%{x|%b %d}</b><br>Alerts: <b>%{y}</b><extra></extra>",
        ))
        fig.update_layout(**PLOT_BASE)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.markdown('<div class="np-empty">NO ALERT DATA · RUN PIPELINE TO POPULATE</div>', unsafe_allow_html=True)

with c_r:
    st.markdown('<div class="np-eyebrow" style="margin-bottom:6px;">Feature Distribution · Sload vs Dload</div>', unsafe_allow_html=True)
    if not data.empty and "Sload" in data.columns and "Dload" in data.columns:
        sample = data.sample(min(2000, len(data)))
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=sample["Sload"], y=sample["Dload"],
            mode="markers",
            marker=dict(size=3, color=sample["Sload"],
                        colorscale=[[0,"#1A2535"],[0.4,"#1D72AA"],[0.75,"#2A9FD6"],[1,"#C0392B"]],
                        opacity=0.6, showscale=False),
            hovertemplate="Sload: %{x:.2f}<br>Dload: %{y:.2f}<extra></extra>",
        ))
        fig2.update_layout(**PLOT_BASE)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
    else:
        st.markdown('<div class="np-empty">NO FEATURE DATA · LOAD DATASET TO VIEW</div>', unsafe_allow_html=True)

st.markdown("---")


# ═══════════════════════════════════════════════════════════════
#  ALERTS TRIAGE
# ═══════════════════════════════════════════════════════════════
section("THREAT TRIAGE")
if alerts.empty:
    st.markdown('<div class="np-empty">NO ALERTS IN DATABASE · RUN ANALYSIS OR IMPORT alerts.csv</div>', unsafe_allow_html=True)
else:
    display = alerts.copy()
    if search:
        display = display[display.apply(lambda r: search.lower() in json.dumps(r.to_dict()).lower(), axis=1)]
    display = display[display["anomaly_score"] >= min_score]

    selected = st.multiselect("SELECT ALERTS FOR BULK ACTION", options=display["id"].tolist(), placeholder="Choose alert IDs…")
    st.dataframe(display.head(200), use_container_width=True, height=300)

    a1, a2 = st.columns(2)
    with a1:
        if st.button("⟳  ENQUEUE FOR ADVICE"):
            if not selected:
                st.warning("No alerts selected.")
            else:
                redis_health = check_redis_health(REDIS_URL)
                if redis_health.get("connected"):
                    enqueued = bulk_enqueue_advice(selected, DB_PATH, REDIS_URL)
                    st.success(f"Enqueued {enqueued} alerts.")
                else:
                    st.info("Redis unavailable — running synchronously.")
                    from tasks import generate_advice_for_alert
                    for aid in selected:
                        generate_advice_for_alert(aid, DB_PATH)
                    st.success(f"Generated advice for {len(selected)} alerts.")
    with a2:
        if st.button("↓  EXPORT CSV"):
            if not selected:
                st.warning("No alerts selected.")
            else:
                out_df = display[display["id"].isin(selected)]
                csv = out_df.to_csv(index=False)
                st.download_button("Download", csv, file_name="selected_alerts.csv", mime="text/csv")

st.markdown("---")


# ═══════════════════════════════════════════════════════════════
#  SECURITY REPORT
# ═══════════════════════════════════════════════════════════════
section("SECURITY REPORT")
if os.path.exists(REPORT_FILE):
    with open(REPORT_FILE, "r", encoding="utf-8") as fh:
        rep = fh.read()
    st.markdown(f'<div class="np-report">{rep}</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="np-empty">NO REPORT FOUND · RUN pipeline.py TO GENERATE Security_Report.txt</div>', unsafe_allow_html=True)

st.markdown("---")


# ═══════════════════════════════════════════════════════════════
#  SYSTEM STATUS
# ═══════════════════════════════════════════════════════════════
section("INFRASTRUCTURE STATUS")
s1, s2 = st.columns(2)

with s1:
    redis_ok = check_redis_health(REDIS_URL).get("connected", False)
    st.markdown(f"""
    <div class="np-stat-panel">
      <h4>QUEUE / REDIS</h4>
      <div class="np-status-row">
        {dot("g" if redis_ok else "r")}
        {"CONNECTED" if redis_ok else "OFFLINE"}
        <span class="v">{REDIS_URL}</span>
      </div>""", unsafe_allow_html=True)
    if redis_ok:
        qstats = get_queue_stats(REDIS_URL)
        if "queue_depth" in qstats:
            st.markdown(f'<div class="np-status-row">QUEUE DEPTH<span class="v">{qstats["queue_depth"]}</span></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with s2:
    st.markdown('<div class="np-stat-panel"><h4>DATABASE</h4>', unsafe_allow_html=True)
    if session is not None:
        try:
            ac = session.query(Alert).count()
            uc = session.query(AuditLog).count()
            st.markdown(f"""
      <div class="np-status-row">{dot("g")} CONNECTED <span class="v">SQLite</span></div>
      <div class="np-status-row">ALERTS<span class="v">{ac:,}</span></div>
      <div class="np-status-row">AUDIT ENTRIES<span class="v">{uc:,}</span></div>
      """, unsafe_allow_html=True)
        except Exception:
            st.markdown(f'{dot("r")} UNAVAILABLE', unsafe_allow_html=True)
    else:
        st.markdown(f'{dot("r")} SESSION UNAVAILABLE', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  FOOTER
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<div style="margin-top:3rem;padding-top:1.2rem;border-top:1px solid #1A2535;
            display:flex;justify-content:space-between;align-items:center;
            font-family:'IBM Plex Mono',monospace;font-size:0.56rem;
            color:#1A2535;letter-spacing:0.14em;">
  <span>NETPULSE SHIELD  ·  THREAT INTELLIGENCE PLATFORM</span>
  <span>BUILD 2024.1  ·  ALL SYSTEMS MONITORED</span>
</div>""", unsafe_allow_html=True)