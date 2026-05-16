from pathlib import Path
import sys, os, html
from dotenv import load_dotenv
import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))
from pipeline_runner import PipelineRunner

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"

DATA_CANDIDATES = [
    BASE_DIR / "data" / "processed" / "final_project_data.csv",
    BASE_DIR / "data" / "final_project_data.csv",
]
ALERTS_CANDIDATES = [
    BASE_DIR / "data" / "outputs" / "alerts.csv",
    BASE_DIR / "alerts.csv",
]
REPORT_CANDIDATES = [
    BASE_DIR / "data" / "outputs" / "Security_Report.txt",
    BASE_DIR / "Security_Report.txt",
]

st.set_page_config(page_title="NetPulse-Shield", page_icon="shield", layout="wide")

st.markdown("""
<style>
    .stApp { background: #0a0e17; }
    .block-container { padding: 1.5rem 2rem !important; }
    .main-title {
        font-size: 1.6rem; font-weight: 700;
        background: linear-gradient(135deg, #00bcd4, #26c6da);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .main-sub { color: #546e7a; font-size: 0.8rem; }
    section[data-testid="stSidebar"] { background: #0d111c !important; border-right: 1px solid #1a2332; }
    section[data-testid="stSidebar"] .stButton button {
        width: 100%; border-radius: 8px; font-weight: 500;
        background: #0a0e17; border: 1px solid #1a2332; color: #b0bec5;
    }
    section[data-testid="stSidebar"] .stButton button:hover { border-color: #00bcd4; }
    section[data-testid="stSidebar"] button[kind="primary"] {
        background: linear-gradient(135deg, #00838f, #00bcd4) !important;
        color: white !important; font-weight: 600; border: none !important;
    }
    div[data-testid="stMetric"] {
        background: #0d111c; border: 1px solid #1a2332; border-radius: 12px; padding: 14px;
    }
    div[data-testid="stMetric"]:hover { border-color: #00bcd4; }
    div[data-testid="stMetric"] label { color: #546e7a !important; font-size: 0.7rem !important; text-transform: uppercase; }
    div[data-testid="stMetric"] div { color: #e0e0e0 !important; }
    .stDataFrame { border: 1px solid #1a2332 !important; border-radius: 10px !important; }
    .stDataFrame thead tr th { background: #0d111c !important; color: #00bcd4 !important; font-size: 0.7rem !important; }
    .stDataFrame tbody tr:nth-child(even) { background: #080c14; }
    button[data-baseweb="tab"] { font-size: 0.8rem; font-weight: 500; }
    button[data-baseweb="tab"][aria-selected="true"] { color: #00bcd4 !important; }
    hr { border-color: #1a2332 !important; }
    footer, #MainMenu { display: none; }
    .stat-card {
        background: #0d111c; border: 1px solid #1a2332; border-radius: 12px;
        padding: 16px 20px; text-align: center;
    }
    .stat-card:hover { border-color: #00bcd4; }
    .stat-label { color: #546e7a; font-size: 0.65rem; text-transform: uppercase; letter-spacing: 1px; }
    .stat-value { font-size: 1.8rem; font-weight: 700; }
    .stExpander { border: 1px solid #1a2332 !important; border-radius: 10px !important; background: #0d111c !important; }
    .stExpander summary { font-weight: 600; color: #00bcd4 !important; }
</style>
""", unsafe_allow_html=True)

if "pipeline_runner" not in st.session_state:
    st.session_state.pipeline_runner = PipelineRunner()

def first_existing(paths):
    for p in paths:
        if p.exists(): return p
    return paths[0]

@st.cache_data(show_spinner=False)
def load_csv(path):
    p = Path(path)
    return pd.read_csv(p) if p.exists() else None

def find_col(df, names):
    if df is None: return None
    norm = {c.lower(): c for c in df.columns}
    for n in names:
        if n.lower() in norm: return norm[n.lower()]
    return None

DATA_FILE = first_existing(DATA_CANDIDATES)
ALERTS_FILE = first_existing(ALERTS_CANDIDATES)
REPORT_FILE = first_existing(REPORT_CANDIDATES)
data = load_csv(str(DATA_FILE))
alerts = load_csv(str(ALERTS_FILE))
report = REPORT_FILE.read_text(encoding="utf-8", errors="ignore") if REPORT_FILE and REPORT_FILE.exists() else None

st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;margin-bottom:8px;">
    <div><div class="main-title">NetPulse-Shield</div><div class="main-sub">Security Operations Center</div></div>
    <div style="display:flex;gap:16px;align-items:center;font-size:0.75rem;color:#546e7a;">
        <span>&#9679; System Online</span>
    </div>
</div>
<hr style="margin:0 0 16px;">
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:8px 0 12px;border-bottom:1px solid #1a2332;margin-bottom:12px;">
        <div style="font-weight:700;font-size:1rem;color:#00bcd4;">Pipeline</div>
    </div>
    """, unsafe_allow_html=True)

    ai_mode = st.radio("AI Backend", ["RAG (Local)", "Ollama (Llama 3)"],
        index=0, horizontal=True, label_visibility="collapsed")
    mode = "ollama" if "Ollama" in ai_mode else "rag"
    st.session_state.pipeline_runner.ai_mode = mode

    cols = st.columns(2)
    with cols[0]:
        if st.button("Clean", use_container_width=True, key="b1"):
            with st.spinner(""):
                s, o, e = st.session_state.pipeline_runner.run_clean_data()
                if s:
                    st.success("OK")
                    st.cache_data.clear()
                else:
                    st.error("Failed")
                if o: st.code(o)
                if e: st.code(e)
    with cols[1]:
        if st.button("Detect", use_container_width=True, key="b2"):
            with st.spinner(""):
                s, o, e = st.session_state.pipeline_runner.run_detector()
                if s:
                    st.success("OK")
                    st.cache_data.clear()
                else:
                    st.error("Failed")
                if o: st.code(o)
                if e: st.code(e)
    cols = st.columns(2)
    with cols[0]:
        if st.button("Report", use_container_width=True, key="b3"):
            with st.spinner(""):
                s, o, e = st.session_state.pipeline_runner.run_report(mode)
                if s:
                    st.success("OK")
                else:
                    st.warning("Issues")
                if o: st.code(o)
                if e: st.code(e)
    with cols[1]:
        if st.button("Run All", use_container_width=True, type="primary", key="b4"):
            with st.spinner(""):
                s, o, e = st.session_state.pipeline_runner.run_full_pipeline(mode)
                if s:
                    st.success("Done")
                else:
                    st.error("Failed")
                st.code(o or "")
                if e: st.code(e)

    st.markdown(f"""
    <hr>
    <div style="font-size:0.65rem;color:#546e7a;line-height:1.8;">
        <div>Mode: <span style="color:#00bcd4;">{ai_mode}</span></div>
        <div>Data: <span style="color:#78909c;">{DATA_FILE.name if DATA_FILE and DATA_FILE.exists() else 'N/A'}</span></div>
        <div>Alerts: <span style="color:#78909c;">{ALERTS_FILE.name if ALERTS_FILE and ALERTS_FILE.exists() else 'N/A'}</span></div>
    </div>
    """, unsafe_allow_html=True)

tabs = st.tabs(["Overview", "Threat Map", "Traffic", "Alerts", "Report", "Email", "Status"])

# ===================== OVERVIEW =====================
with tabs[0]:
    total_rec = len(data) if data is not None else 0
    total_alt = len(alerts) if alerts is not None else 0
    normal = max(total_rec - total_alt, 0)
    sev_col = find_col(alerts, ["severity", "risk_level"])
    crit = 0
    if alerts is not None and sev_col:
        crit = int(alerts[sev_col].astype(str).str.lower().isin(["critical", "high"]).sum())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Traffic Records", f"{total_rec:,}")
    m2.metric("Detected Alerts", f"{total_alt:,}", delta_color="inverse")
    m3.metric("Normal Traffic", f"{normal:,}")
    m4.metric("High / Critical", f"{crit:,}")

    col1, col2 = st.columns([1, 1.5])
    with col1:
        if total_rec > 0:
            fig = px.pie(names=["Normal", "Suspicious"], values=[normal, total_alt],
                hole=0.5, color_discrete_map={"Normal": "#00e676", "Suspicious": "#ff1744"})
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#78909c", size=10), margin=dict(l=0, r=0, t=30, b=0),
                title="Traffic Distribution", legend=dict(orientation="h", y=1.08))
            fig.update_traces(textinfo="label+percent")
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        atk_col = find_col(alerts, ["attack_category", "attack_cat", "predicted_attack", "label"])
        if alerts is not None and atk_col:
            counts = alerts[atk_col].astype(str).value_counts().reset_index()
            counts.columns = ["type", "count"]
            fig = px.bar(counts.head(10), x="count", y="type", orientation="h",
                title="Attack Categories", color="count", color_continuous_scale="reds", text="count")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#78909c", size=10), margin=dict(l=0, r=0, t=30, b=0),
                yaxis=dict(autorange="reversed"), coloraxis_showscale=False)
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

# ===================== THREAT MAP =====================
with tabs[1]:
    st.markdown("### Global Threat Map")
    st.markdown("Drag the globe to rotate. Arc colors show attack types.")

    if alerts is None or alerts.empty:
        st.warning("No alerts found. Run detection first.")
    else:
        from cyber_attack_map import create_attack_globe, create_attack_statistics
        stats = create_attack_statistics(alerts)

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Attacks", f"{stats['total_attacks']:,}")
        m2.metric("High Confidence", f"{stats['high_confidence']:,}")
        m3.metric("Blocked", f"{stats['blocked']:,}")
        m4.metric("Critical", f"{stats['critical_count']:,}")
        m5.metric("Avg Confidence", f"{stats['avg_confidence']:.1f}%")

        try:
            fig = create_attack_globe(alerts)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "scrollZoom": True})
        except Exception as e:
            st.error(f"Globe error: {e}")

        st.markdown("""
        <div style="display:flex;justify-content:center;flex-wrap:wrap;gap:6px 18px;font-size:0.75rem;color:#78909c;">
            <span style="color:#b71c1c;">&#9679; DoS/DDoS</span>
            <span style="color:#ff1744;">&#9679; Exploits</span>
            <span style="color:#ff9100;">&#9679; Brute Force</span>
            <span style="color:#ffc107;">&#9679; Fuzzers</span>
            <span style="color:#2196f3;">&#9679; Recon/Scan</span>
            <span style="color:#9c27b0;">&#9679; Shellcode</span>
            <span style="color:#9e9e9e;">&#9679; Other</span>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Attack Distribution**")
            if stats["attack_types"]:
                import plotly.graph_objects as go
                from cyber_attack_map import _get_marker_color as gmc
                adf = pd.DataFrame(list(stats["attack_types"].items()), columns=["Type", "Count"]).sort_values("Count", ascending=False)
                colors = [gmc(t) for t in adf["Type"]]
                f2 = go.Figure([go.Bar(x=adf["Type"], y=adf["Count"], marker_color=colors, marker_line_width=0)])
                f2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#78909c", size=9), margin=dict(l=5, r=5, t=5, b=25),
                    xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#1a2332"), height=220)
                st.plotly_chart(f2, use_container_width=True, config={"displayModeBar": False})
        with col2:
            st.markdown("**Recent Threats**")
            r = alerts.head(8).copy()
            dc = [c for c in ["label", "anomaly_score"] if c in r.columns] or list(r.columns[:3])
            st.dataframe(r[dc], use_container_width=True, height=230)

# ===================== TRAFFIC =====================
with tabs[2]:
    st.markdown("### Network Traffic Data")
    if data is None:
        st.warning("No data. Run pipeline first.")
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("Rows", f"{data.shape[0]:,}")
        m2.metric("Features", f"{data.shape[1]:,}")
        m3.metric("Memory", f"{data.memory_usage(deep=True).sum()/1e6:.2f} MB")
        st.dataframe(data.head(100), use_container_width=True, height=350)
        nc = data.select_dtypes(include=["int64", "float64"]).columns.tolist()
        if nc:
            sel = st.selectbox("Feature distribution", nc)
            f = px.histogram(data, x=sel, nbins=40)
            f.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#78909c", size=10), margin=dict(l=5, r=5, t=5, b=25),
                xaxis=dict(gridcolor="#1a2332"), yaxis=dict(gridcolor="#1a2332"))
            st.plotly_chart(f, use_container_width=True)

# ===================== ALERTS =====================
with tabs[3]:
    st.markdown("### SOC Alert Center")
    if alerts is None:
        st.info("No alerts. Run detection.")
    else:
        f_alerts = alerts.copy()
        sv = find_col(f_alerts, ["severity", "risk_level"])
        at = find_col(f_alerts, ["attack_category", "attack_cat", "predicted_attack", "label"])
        c1, c2 = st.columns(2)
        if sv:
            opts = sorted(f_alerts[sv].dropna().astype(str).unique())
            sel = c1.multiselect("Severity", opts, default=opts)
            f_alerts = f_alerts[f_alerts[sv].astype(str).isin(sel)]
        if at:
            opts = sorted(f_alerts[at].dropna().astype(str).unique())
            sel = c2.multiselect("Type", opts, default=opts)
            f_alerts = f_alerts[f_alerts[at].astype(str).isin(sel)]
        st.metric("Displayed", f"{len(f_alerts):,}")
        st.dataframe(f_alerts, use_container_width=True, height=360)
        sc = find_col(f_alerts, ["anomaly_score", "score", "decision_score"])
        if sc:
            f = px.histogram(f_alerts, x=sc, nbins=30, title="Score Distribution")
            f.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#78909c", size=10), margin=dict(l=5, r=5, t=5, b=25),
                xaxis=dict(gridcolor="#1a2332"), yaxis=dict(gridcolor="#1a2332"))
            st.plotly_chart(f, use_container_width=True)

# ===================== REPORT =====================
with tabs[4]:
    st.markdown("### Security Report")
    if not REPORT_FILE.exists() or report is None:
        st.info("No report. Run Report in pipeline.")
    else:
        sr = html.escape(report)
        st.markdown(f'<pre style="background:#0d111c;border:1px solid #1a2332;border-radius:12px;padding:20px;color:#c8d6e5;font-size:0.8rem;white-space:pre-wrap;">{sr}</pre>', unsafe_allow_html=True)
        st.download_button("Download Report", data=report, file_name="Security_Report.txt", mime="text/plain")

# ===================== EMAIL =====================
with tabs[5]:
    st.markdown("### Email Notifications")

    with st.expander("SMTP Configuration", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            es = st.text_input("Email", value=os.getenv("EMAIL_SENDER", ""), key="es")
            ep = st.text_input("Password", type="password", value=os.getenv("EMAIL_PASSWORD", ""), key="ep")
        with c2:
            ss = st.text_input("SMTP Server", value=os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com"), key="ss")
            sp = st.number_input("Port", value=int(os.getenv("EMAIL_SMTP_PORT", "587")), min_value=1, max_value=65535, key="sp")
        if st.button("Test Connection"):
            try:
                import smtplib
                with smtplib.SMTP(ss, sp) as s:
                    s.starttls(); s.login(es, ep)
                st.success("SMTP connection OK")
            except Exception as e:
                st.error(f"Failed: {e}")

    with st.expander("Alert Settings"):
        at = st.slider("Confidence Threshold", 0, 100, int(os.getenv("ATTACK_THRESHOLD_PERCENTAGE", "80")))
        st.info(f"Alerts for >= {at}% confidence")

    with st.expander("Weekly Summary"):
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        c1, c2 = st.columns(2)
        with c1:
            wd = st.selectbox("Day", range(7), format_func=lambda x: days[x], index=int(os.getenv("WEEKLY_REPORT_DAY", "0")))
        with c2:
            wt = st.time_input("Time", value=pd.to_datetime(os.getenv("WEEKLY_REPORT_TIME", "09:00")).time())
        st.info(f"Weekly: {days[wd]} at {wt.strftime('%H:%M')}")

    if "recv" not in st.session_state: st.session_state.recv = ""
    re = st.text_input("Recipient Email", value=st.session_state.recv, placeholder="admin@company.com")
    st.session_state.recv = re

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save Config", use_container_width=True):
            with open(".env", "w") as f:
                f.write(f"EMAIL_SENDER={es}\nEMAIL_PASSWORD={ep}\nEMAIL_SMTP_SERVER={ss}\nEMAIL_SMTP_PORT={sp}\nWEEKLY_REPORT_DAY={wd}\nWEEKLY_REPORT_TIME={wt.strftime('%H:%M')}\nATTACK_THRESHOLD_PERCENTAGE={at}\nRECEIVER_EMAIL={re}\n")
            st.success("Saved to .env")
    with c2:
        if st.button("Send Test", use_container_width=True):
            if not re: st.error("Enter recipient")
            else:
                try:
                    sys.path.insert(0, str(SRC_DIR))
                    from email_notifier import EmailNotifier
                    n = EmailNotifier()
                    ta = {"Type": "Test", "Source": "192.168.1.1", "Dest": "10.0.0.1", "Time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")}
                    st.success("Test email sent!") if n.send_alert(re, ta, 90.0) else st.error("Send failed")
                except Exception as e:
                    st.error(f"Error: {e}")

    if alerts is not None and not alerts.empty:
        st.markdown("**Recent Alerts**")
        st.dataframe(alerts.head(10), use_container_width=True)

# ===================== STATUS =====================
with tabs[6]:
    st.markdown("### System Status")
    files = {
        "Processed Data": DATA_FILE, "Alerts": ALERTS_FILE, "Security Report": REPORT_FILE,
        "clean_data.py": SRC_DIR / "clean_data.py", "detector.py": SRC_DIR / "detector.py",
        "solver.py": SRC_DIR / "solver.py",
    }
    rows = []
    for n, p in files.items():
        ok = p.exists() if p else False
        rows.append({"Component": n, "Status": "OK" if ok else "Missing", "Path": str(p.relative_to(BASE_DIR)) if ok and p else str(p or "")})
    sdf = pd.DataFrame(rows)

    def clr(v):
        if v == "OK": return "color: #00e676; font-weight: 600"
        return "color: #ff1744; font-weight: 600"
    st.dataframe(sdf.style.applymap(clr, subset=["Status"]), use_container_width=True, height=280)

    st.markdown("""
    <div style="background:#0d111c;border:1px solid #1a2332;border-radius:12px;padding:18px;margin-top:12px;">
        <div style="font-weight:600;color:#00bcd4;font-size:0.85rem;margin-bottom:6px;">About</div>
        <div style="color:#78909c;font-size:0.75rem;line-height:1.6;">
            Inspired by Kaspersky CyberMap (cybermap.kaspersky.com).<br>
            Stack: Streamlit / scikit-learn (Isolation Forest) / LangChain / FAISS / Plotly / Ollama
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<hr style="margin:16px 0 4px;">
<div style="text-align:center;color:#3a4a5a;font-size:0.6rem;padding:4px 0;">
    NetPulse-Shield &bull; AI Network Security &bull; Local-First
</div>
""", unsafe_allow_html=True)
