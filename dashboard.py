"""Streamlit dashboard — UI for NetPulse-Shield pipeline and worker options."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from db import Alert, AuditLog, create_db, get_session
from pipeline import (
    generate_remediation_report,
    load_validated_dataframe,
    run_anomaly_detection,
    run_pipeline,
    save_alerts_csv,
)
from system_utils import bulk_enqueue_advice, check_redis_health, get_job_status, get_queue_stats


st.set_page_config(
    page_title="NetPulse-Shield Dashboard",
    page_icon="🛡️",
    layout="wide",
)

st.markdown(
    """
    <style>
    .main { background-color: #0d1117; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _mask_secret(val: str | None, show: int = 4) -> str:
    if not val:
        return "(not set)"
    if len(val) <= show * 2:
        return "***"
    return val[:show] + "…" + val[-show:]


def load_csv(file_path: str) -> pd.DataFrame | None:
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return None


def render_siem_status():
    """Show which SIEM-related env vars are set (values masked)."""
    webhook = os.getenv("NETPULSE_WEBHOOK_URL")
    ws = os.getenv("NETPULSE_WORKSPACE_ID")
    key = os.getenv("NETPULSE_PRIMARY_KEY")
    st.markdown("**SIEM / webhook (environment)**")
    st.caption("Values are never shown in full. Set these before `streamlit run` or in `.env`.")
    c1, c2, c3 = st.columns(3)
    c1.metric("NETPULSE_WEBHOOK_URL", "set" if webhook else "unset")
    c2.metric("NETPULSE_WORKSPACE_ID", "set" if ws else "unset")
    c3.metric("NETPULSE_PRIMARY_KEY", "set" if key else "unset")
    if webhook:
        st.text("Webhook (masked): " + _mask_secret(webhook, 8))


# --- Auth (unchanged behavior) ---
st.sidebar.title("🛡️ NetPulse Command")
env_token = os.getenv("DASHBOARD_TOKEN")
if env_token:
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state.get("authenticated"):
        token_input = st.sidebar.text_input("Enter dashboard token", type="password")
        if st.sidebar.button("Login"):
            if token_input == env_token:
                st.session_state["authenticated"] = True
                st.sidebar.success("Authenticated")
            else:
                st.sidebar.error("Invalid token")
        st.sidebar.warning("This dashboard is protected. Please log in.")
        st.stop()
    else:
        if st.sidebar.button("Logout"):
            st.session_state["authenticated"] = False
            st.rerun()
else:
    st.sidebar.info("No DASHBOARD_TOKEN set — dashboard is running in dev mode.")

# --- All project options (mirror `python pipeline.py` + extras) ---
st.sidebar.subheader("Project options")
st.sidebar.caption("Same flags as the CLI pipeline unless noted.")

csv_path = st.sidebar.text_input(
    "Input CSV (`csv_path`)",
    value="data/final_project_data.csv",
    help="Path to the traffic CSV (default in repo: data/final_project_data.csv).",
    key="np_csv_path",
)
persist_db = st.sidebar.checkbox(
    "Persist alerts to SQLite",
    value=True,
    help="Uncheck to mirror `--no-persist` (no DB writes from the detector).",
    key="np_persist_db",
)
db_path = st.sidebar.text_input(
    "Database URL (`--db`)",
    value="sqlite:///alerts.db",
    help="SQLAlchemy URL used by the detector and this dashboard.",
    key="np_db_path",
)
alerts_csv = st.sidebar.text_input(
    "Top alerts CSV (`--alerts-csv`)",
    value="alerts.csv",
    key="np_alerts_csv",
)
report_file = st.sidebar.text_input(
    "Security report path (`--report`)",
    value="Security_Report.txt",
    key="np_report_file",
)
write_metrics = st.sidebar.checkbox(
    "Write metrics JSON",
    value=True,
    help="Uncheck to skip metrics file (like `--metrics \"\"`).",
    key="np_write_metrics",
)
metrics_path = st.sidebar.text_input(
    "Metrics JSON path (`--metrics`)",
    value="metrics.json",
    disabled=not st.session_state.get("np_write_metrics", True),
    key="np_metrics_path",
)
compare_lof = st.sidebar.checkbox(
    "Compare Local Outlier Factor (`--compare-lof`)",
    value=False,
    key="np_compare_lof",
)
remediation_backend = st.sidebar.selectbox(
    "Remediation backend (`--remediation`)",
    options=["rag", "ollama"],
    index=0,
    help=(
        "RAG: local advisor. Ollama: requires `ollama serve` and an Ollama model "
        "(default NETPULSE_OLLAMA_MODEL=phi3:mini)."
    ),
    key="np_remediation",
)
ollama_model = st.sidebar.text_input(
    "Ollama model (small recommended)",
    value=os.getenv("NETPULSE_OLLAMA_MODEL", "phi3:mini"),
    help="Used when remediation backend is ollama. Example: llama3:8b or phi3:mini.",
    key="np_ollama_model",
)
force_retrain = st.sidebar.checkbox(
    "Force retrain Isolation Forest",
    value=True,
    help="Uncheck to mirror `--use-saved-model` (score with existing joblib when possible).",
    key="np_force_retrain",
)
redis_url = st.sidebar.text_input(
    "Redis URL (advice queue)",
    value=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    key="np_redis_url",
)

create_db(db_path)

# Make the model available to the Ollama backend for this process.
os.environ["NETPULSE_OLLAMA_MODEL"] = (ollama_model or "phi3:mini").strip()

st.sidebar.markdown("---")
st.sidebar.subheader("Actions")

run_full = st.sidebar.button("Run full pipeline", type="primary", use_container_width=True)
run_detect_only = st.sidebar.button("Detection + alerts CSV only", use_container_width=True)
run_report_only = st.sidebar.button(
    "Generate report from last run",
    help="Uses detection results kept in this session (run detection or full pipeline first).",
    use_container_width=True,
)

st.sidebar.markdown("---")
with st.sidebar.expander("SIEM environment", expanded=False):
    render_siem_status()

st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigation",
    [
        "Overview",
        "Pipeline & metrics",
        "EDA & Insights",
        "Detected Alerts",
        "Security Report",
        "Audit Logs",
        "System Status",
        "Control Panel",
    ],
)

# --- Run actions ---
metrics_file = (metrics_path.strip() or None) if write_metrics else None
last_err = None

if run_full:
    with st.spinner("Running full pipeline…"):
        try:
            results = run_pipeline(
                csv_path,
                persist_to_db=persist_db,
                alerts_csv=alerts_csv,
                report_path=report_file,
                metrics_path=metrics_file,
                compare_lof=compare_lof,
                remediation_backend=remediation_backend,
                db_path=db_path,
                force_train=force_retrain,
            )
            st.session_state["last_detection_results"] = results
            st.session_state["last_csv_path"] = csv_path
            st.session_state["last_run_message"] = "Full pipeline completed."
            st.rerun()
        except Exception as exc:
            last_err = str(exc)
            st.session_state["last_run_message"] = f"Error: {exc}"

if run_detect_only:
    with st.spinner("Running detection…"):
        try:
            df = load_validated_dataframe(csv_path)
            results = run_anomaly_detection(
                df,
                persist_to_db=persist_db,
                metrics_output_path=metrics_file,
                compare_lof=compare_lof,
                db_path=db_path,
                force_train=force_retrain,
            )
            save_alerts_csv(results, alerts_csv)
            st.session_state["last_detection_results"] = results
            st.session_state["last_csv_path"] = csv_path
            st.session_state["last_run_message"] = "Detection + alerts CSV completed."
            st.rerun()
        except Exception as exc:
            last_err = str(exc)
            st.session_state["last_run_message"] = f"Error: {exc}"

if run_report_only:
    results = st.session_state.get("last_detection_results")
    if results is None:
        st.session_state["last_run_message"] = "No results in session — run detection or full pipeline first."
    else:
        with st.spinner("Writing security report…"):
            try:
                generate_remediation_report(
                    results,
                    report_file,
                    remediation_backend=remediation_backend,
                )
                st.session_state["last_run_message"] = f"Report written to {report_file}."
                st.rerun()
            except Exception as exc:
                st.session_state["last_run_message"] = f"Report error: {exc}"

if last_err:
    st.error(last_err)

msg = st.session_state.get("last_run_message")
if msg:
    if msg.startswith("Error") or "error" in msg.lower():
        st.warning(msg)
    else:
        st.success(msg)
    st.session_state.pop("last_run_message", None)

session = get_session(db_path)
alerts = None
if session is not None:
    alerts_query = session.query(Alert).order_by(Alert.created_at.desc())
    alerts = pd.read_sql(alerts_query.statement, alerts_query.session.bind)

data = load_csv(csv_path)

st.title("🛡️ NetPulse-Shield Dashboard")
st.caption(
    "Configure the same options as `python pipeline.py` in the sidebar, then run the pipeline "
    "or individual steps. Remediation for queued jobs uses `NETPULSE_REMEDIATION_MODE` when "
    "the worker is started without a per-job backend; buttons below pass the sidebar choice "
    "for synchronous and enqueued paths."
)

if page == "Overview":
    st.header("📊 Overview")
    if data is not None:
        total_records = len(data)
        total_alerts_db = len(alerts) if alerts is not None else 0
        last_res = st.session_state.get("last_detection_results")
        n_flagged = int(last_res["is_anomaly"].sum()) if last_res is not None else None

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Rows in CSV", total_records)
        col2.metric("Alerts in DB", total_alerts_db)
        col3.metric(
            "Last run anomalies",
            n_flagged if n_flagged is not None else "—",
            help="From the last detection or full pipeline run in this session.",
        )
        col4.metric("Remediation (report)", remediation_backend)

        if last_res is not None and len(last_res) == len(data):
            n_norm = int((~last_res["is_anomaly"]).sum())
            n_anom = int(last_res["is_anomaly"].sum())
            pie_vals = [n_norm, n_anom]
            pie_names = ["Normal", "Anomaly"]
        else:
            pie_vals = [max(total_records - total_alerts_db, 0), min(total_alerts_db, total_records)]
            pie_names = ["Normal (approx.)", "Anomaly (approx.)"]

        fig = px.pie(
            names=pie_names,
            values=pie_vals,
            color_discrete_sequence=["#238636", "#da3633"],
            hole=0.4,
        )
        st.plotly_chart(fig, use_container_width=True)
        if last_res is None or len(last_res) != len(data):
            st.caption("Pie uses approximate split from DB counts unless session results match CSV length.")
    else:
        st.info("Set a valid input CSV path and run the pipeline to populate this page.")

elif page == "Pipeline & metrics":
    st.header("Pipeline & metrics")
    st.subheader("Active configuration")
    st.json(
        {
            "csv_path": csv_path,
            "persist_db": persist_db,
            "db_path": db_path,
            "alerts_csv": alerts_csv,
            "report_file": report_file,
            "metrics_path": metrics_file,
            "compare_lof": compare_lof,
            "remediation_backend": remediation_backend,
            "force_retrain": force_retrain,
            "redis_url": redis_url,
        }
    )
    mpath = metrics_path.strip() if write_metrics else ""
    if mpath and os.path.exists(mpath):
        st.subheader(metrics_path)
        try:
            with open(mpath, encoding="utf-8") as f:
                payload = json.load(f)
            st.json(payload)
        except Exception as exc:
            st.error(f"Could not read metrics JSON: {exc}")
    else:
        st.info("Metrics file not found yet — run the pipeline with labels and metrics enabled.")

elif page == "EDA & Insights":
    st.header("🔍 EDA & Insights")
    last_res = st.session_state.get("last_detection_results")
    if data is not None and last_res is not None and len(last_res) == len(data):
        data_viz = data.copy()
        data_viz["Status"] = np.where(last_res["is_anomaly"].to_numpy(), "Anomaly", "Normal")

        if "Sload" in data_viz.columns and "Dload" in data_viz.columns:
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("Sload distribution")
                fig_hist = px.histogram(
                    data_viz,
                    x="Sload",
                    color="Status",
                    marginal="box",
                    barmode="overlay",
                    color_discrete_map={"Normal": "#238636", "Anomaly": "#da3633"},
                )
                st.plotly_chart(fig_hist, use_container_width=True)
            with col_b:
                st.subheader("Sload vs Dload")
                fig_scatter = px.scatter(
                    data_viz,
                    x="Sload",
                    y="Dload",
                    color="Status",
                    hover_data=[c for c in ("sttl", "sbytes") if c in data_viz.columns],
                    color_discrete_map={"Normal": "#238636", "Anomaly": "#da3633"},
                    opacity=0.6,
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.warning("This CSV has no Sload/Dload columns — open raw columns below.")
            st.dataframe(data_viz.head(50))
    else:
        st.warning(
            "Run **Detection** or **Full pipeline** on this CSV first so anomaly flags align "
            "row-by-row with the file (same length required)."
        )

elif page == "Detected Alerts":
    st.header("🚨 Detected Alerts (from DB)")
    if alerts is not None and len(alerts) > 0:
        st.error(f"Showing top 10 of {len(alerts)} stored alerts.")
        for _, row in alerts.head(10).iterrows():
            job_status = "N/A"
            if row.get("advice_job_id"):
                job_status = get_job_status(row["advice_job_id"], redis_url) or "unknown"

            with st.expander(f"Alert #{row['id']} — score {row['anomaly_score']} — job: {job_status}"):
                col_info, col_job = st.columns(2)
                with col_info:
                    st.write(row[["created_at", "anomaly_score", "severity", "status"]])
                with col_job:
                    st.write(f"**Job status:** {job_status}")
                    if row.get("advice_job_id"):
                        st.write(f"**Job ID:** {row['advice_job_id']}")

                status_options = ["new", "investigating", "resolved", "false_positive"]
                current_status = row.get("status", "new")
                try:
                    status_index = status_options.index(current_status)
                except ValueError:
                    status_index = 0

                new_status = st.selectbox(
                    "Status",
                    status_options,
                    index=status_index,
                    key=f"status_{row['id']}",
                )
                if st.button(f"Update status for {row['id']}", key=f"btn_status_{row['id']}"):
                    session.query(Alert).filter(Alert.id == int(row["id"])).update({"status": new_status})
                    session.add(
                        AuditLog(
                            alert_id=int(row["id"]),
                            action="status_update",
                            actor="dashboard",
                            note=new_status,
                        )
                    )
                    session.commit()
                    st.success("Status updated")
                    st.rerun()
    else:
        st.info("No alerts in the database yet (or persistence was disabled).")

elif page == "Security Report":
    st.header("🛡️ Security Report")
    path = Path(report_file)
    if path.exists():
        report_content = path.read_text(encoding="utf-8")
        st.text_area("Report contents", report_content, height=480)
    else:
        st.info(f"No file at `{report_file}` — run the full pipeline or generate the report.")

elif page == "Audit Logs":
    st.header("🧾 Audit Logs")
    try:
        logs_query = session.query(AuditLog).order_by(AuditLog.timestamp.desc())
        logs_df = pd.read_sql(logs_query.statement, logs_query.session.bind)
        if logs_df is not None and len(logs_df) > 0:
            st.dataframe(logs_df)
            csv = logs_df.to_csv(index=False)
            st.download_button("Download audit logs as CSV", csv, file_name="audit_logs.csv", mime="text/csv")
        else:
            st.info("No audit logs yet.")
    except Exception as exc:
        st.error(f"Error loading audit logs: {exc}")

elif page == "System Status":
    st.header("🔧 System Status & Health")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Redis")
        redis_health = check_redis_health(redis_url)
        if redis_health.get("connected"):
            st.success(f"Connected to {redis_url}")
            queue_stats = get_queue_stats(redis_url)
            if "error" not in queue_stats:
                st.metric("Queue depth", queue_stats["queue_depth"])
                st.metric("Jobs started", queue_stats["jobs_started"])
                st.metric("Jobs finished", queue_stats["jobs_finished"])
                st.metric("Jobs failed", queue_stats["jobs_failed"])
            else:
                st.error(f"Stats error: {queue_stats['error']}")
        else:
            st.error(f"Redis not available: {redis_health.get('error')}")
            st.code("redis-server", language="bash")

    with col2:
        st.subheader("Database")
        alert_count = session.query(Alert).count()
        audit_count = session.query(AuditLog).count()
        st.metric("Total alerts", alert_count)
        st.metric("Audit log entries", audit_count)
        st.caption(f"URL: `{db_path}`")

        advice_pending = session.query(Alert).filter(Alert.advice.is_(None)).count()
        advice_done = session.query(Alert).filter(Alert.advice.isnot(None)).count()
        st.metric("Advice pending", advice_pending)
        st.metric("Advice generated", advice_done)

elif page == "Control Panel":
    st.header("⚙️ Control Panel")

    st.subheader("Generate advice (RAG or Ollama)")
    st.caption(
        "Uses the remediation backend selected in the sidebar for sync calls. "
        "For Redis workers, the same value is passed per job; workers can also read "
        "`NETPULSE_REMEDIATION_MODE` if the third argument is null."
    )
    pending_count = session.query(Alert).filter(Alert.advice.is_(None)).count()
    st.info(f"Alerts pending advice: {pending_count}")

    if st.button("Enqueue pending advice (Redis)", key="enqueue_pending"):
        try:
            redis_health = check_redis_health(redis_url)
            if not redis_health.get("connected"):
                st.error(f"Redis not available: {redis_health.get('error')}")
            else:
                from redis import Redis
                from rq import Queue

                redis_conn = Redis.from_url(redis_url)
                queue = Queue("advisor", connection=redis_conn)
                alerts_without = session.query(Alert).filter(Alert.advice.is_(None)).all()
                enqueued = 0
                for alert in alerts_without:
                    job = queue.enqueue(
                        "tasks.generate_advice_for_alert",
                        alert.id,
                        db_path,
                        remediation_backend,
                    )
                    alert.advice_job_id = job.id
                    alert.advice_status = "queued"
                    session.add(
                        AuditLog(
                            alert_id=alert.id,
                            action="advice_enqueued",
                            actor="dashboard",
                            note=job.id,
                        )
                    )
                    enqueued += 1
                session.commit()
                st.success(f"Enqueued {enqueued} job(s) with backend={remediation_backend}.")
                st.rerun()
        except Exception as exc:
            st.error(f"Enqueue error: {exc}")

    if st.button("Generate pending advice (sync, no Redis)", key="sync_advice"):
        from tasks import generate_advice_for_alert

        alerts_without = session.query(Alert).filter(Alert.advice.is_(None)).all()
        processed = 0
        for alert in alerts_without:
            generate_advice_for_alert(alert.id, db_path, remediation_backend)
            processed += 1
        st.success(f"Generated advice for {processed} alert(s).")
        st.rerun()

    st.markdown("---")
    st.subheader("Bulk enqueue")
    if st.button("Enqueue all pending (bulk)", key="bulk_enqueue"):
        try:
            redis_health = check_redis_health(redis_url)
            if redis_health.get("connected"):
                pending_alerts = session.query(Alert).filter(Alert.advice.is_(None)).all()
                alert_ids = [a.id for a in pending_alerts]
                if alert_ids:
                    enqueued = bulk_enqueue_advice(alert_ids, db_path, redis_url, remediation_backend)
                    st.success(f"Enqueued {enqueued} job(s).")
                    st.rerun()
                else:
                    st.info("Nothing pending.")
            else:
                st.error(f"Redis not available: {redis_health.get('error')}")
        except Exception as exc:
            st.error(f"Error: {exc}")

    st.markdown("---")
    st.subheader("Exports")
    alerts_df = pd.read_sql("SELECT * FROM alerts ORDER BY created_at DESC", session.bind)
    if not alerts_df.empty:
        st.download_button(
            "Download alerts CSV",
            alerts_df.to_csv(index=False),
            file_name="alerts_export.csv",
            mime="text/csv",
        )
    logs_df = pd.read_sql("SELECT * FROM audit_logs ORDER BY timestamp DESC", session.bind)
    if not logs_df.empty:
        st.download_button(
            "Download audit logs CSV",
            logs_df.to_csv(index=False),
            file_name="audit_logs_export.csv",
            mime="text/csv",
        )

    st.markdown("---")
    st.subheader("Worker commands")
    st.code("rq worker advisor", language="bash")
    st.caption("Set `NETPULSE_REMEDIATION_MODE=ollama` or `rag` before starting the worker if you enqueue without per-job backend.")
