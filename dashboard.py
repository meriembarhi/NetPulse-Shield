import os

import pandas as pd
import plotly.express as px
import streamlit as st

from db import Alert, AuditLog, create_db, get_session
from detector import NetworkAnomalyDetector
from webhook import load_webhook_config, load_webhook_profile, send_alert_via_webhook
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

DATA_FILE = "data/final_project_data.csv"
ALERTS_FILE = "alerts.csv"
REPORT_FILE = "Security_Report.txt"
DB_PATH = "sqlite:///alerts.db"

create_db(DB_PATH)


def load_csv(file_path: str) -> pd.DataFrame | None:
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return None


def get_db_session():
    return get_session(DB_PATH)


def get_siem_status() -> tuple[str | None, str]:
    return load_webhook_config(), load_webhook_profile()


def forward_alerts_to_siem(alerts_df: pd.DataFrame, limit: int = 10) -> int:
    webhook_url, profile = get_siem_status()
    if not webhook_url or alerts_df is None or len(alerts_df) == 0:
        return 0

    sent = 0
    for _, row in alerts_df.head(limit).iterrows():
        alert_payload = row.to_dict()
        alert_payload["alert_id"] = alert_payload.get("alert_id") or alert_payload.get("id") or sent + 1
        alert_payload["description"] = alert_payload.get("description") or f"NetPulse anomaly score {alert_payload.get('anomaly_score')}"
        if send_alert_via_webhook(alert_payload, webhook_url=webhook_url, profile=profile):
            sent += 1

    return sent


st.sidebar.title("🛡️ NetPulse Command")
st.sidebar.subheader("System Actions")

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
            st.experimental_rerun()
else:
    st.sidebar.info("No DASHBOARD_TOKEN set — dashboard is running in dev mode.")

# Auto-run analysis on page load: tune contamination when labels exist,
# run analysis, persist alerts.csv and DB (mirrors the manual button flow).
with st.spinner("Auto-running analysis (tuning if labels available)..."):
    try:
        raw_data = load_csv(DATA_FILE)
        if raw_data is not None:
            has_labels = "Label" in raw_data.columns
            detector = NetworkAnomalyDetector(contamination='auto', persist_to_db=True, db_path=DB_PATH)

            if has_labels:
                st.info("Labels detected — tuning contamination automatically.")
                try:
                    tuned_contamination = detector.tune_contamination(raw_data, label_column="Label")
                    detector.contamination = tuned_contamination
                except Exception as exc:  # tuning can fail; fall back gracefully
                    st.warning(f"Contamination tuning failed: {exc} — using detector fallback.")
            else:
                st.info("No labels found: using detector's automatic contamination fallback.")

            try:
                results = detector.analyze(raw_data)
                alerts_df = results[results["is_anomaly"]].copy()
                alerts_df.to_csv(ALERTS_FILE, index=False)
                st.sidebar.success("Auto-detection complete; alerts saved.")
                st.cache_data.clear()
            except Exception as exc:
                st.sidebar.error(f"Auto-analysis error: {exc}")
        else:
            st.info("No data file available to auto-run analysis.")
    except Exception as exc:
        st.error(f"Auto-run failure: {exc}")

if st.sidebar.button("🚀 1. Run Network Analysis"):
    with st.spinner("Analyzing traffic with Isolation Forest..."):
        try:
            raw_data = pd.read_csv(DATA_FILE)
            has_labels = "Label" in raw_data.columns
            detector = NetworkAnomalyDetector(contamination='auto', persist_to_db=True, db_path=DB_PATH)

            if has_labels:
                st.sidebar.info("Labels found: tuning contamination by F1 before analysis.")
                tuned_contamination = detector.tune_contamination(raw_data, label_column="Label")
                detector.contamination = tuned_contamination
            else:
                st.sidebar.info("No labels found: using automatic contamination fallback.")

            results = detector.analyze(raw_data)

            alerts_df = results[results["is_anomaly"]].copy()
            alerts_df.to_csv(ALERTS_FILE, index=False)

            st.sidebar.success("Detection complete!")
            st.cache_data.clear()
        except Exception as exc:
            st.sidebar.error(f"Detection error: {exc}")

if st.sidebar.button("🤖 2. Generate AI Advice"):
    session = get_db_session()
    if session is None:
        st.sidebar.warning("Please run the analysis first.")
    else:
        alerts_without_advice = session.query(Alert).filter(Alert.advice.is_(None)).all()
        if not alerts_without_advice:
            st.sidebar.warning("No alerts without advice are waiting.")
        else:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            try:
                from redis import Redis
                from rq import Queue

                redis_conn = Redis.from_url(redis_url)
                queue = Queue("advisor", connection=redis_conn)

                enqueued = 0
                for alert in alerts_without_advice:
                    job = queue.enqueue("tasks.generate_advice_for_alert", alert.id, DB_PATH)
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
                st.sidebar.success(f"Enqueued {enqueued} advice jobs (Redis at {redis_url}).")

            except Exception:
                with st.spinner("Generating AI advice synchronously (Redis unavailable)..."):
                    try:
                        from tasks import generate_advice_for_alert

                        processed = 0
                        for alert in alerts_without_advice:
                            generate_advice_for_alert(alert.id, DB_PATH)
                            processed += 1
                        st.sidebar.success(f"Generated advice for {processed} alerts (sync fallback).")
                    except Exception as exc:
                        st.sidebar.error(f"Advice generation error: {exc}")


st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigation",
    ["Overview", "EDA & Insights", "Detected Alerts", "SIEM View", "Security Report", "Audit Logs", "System Status", "Control Panel"],
)

data = load_csv(DATA_FILE)
session = get_db_session()
alerts = None
if session is not None:
    alerts_query = session.query(Alert).order_by(Alert.created_at.desc())
    alerts = pd.read_sql(alerts_query.statement, alerts_query.session.bind)

st.title("🛡️ NetPulse-Shield Dashboard")
st.caption("Local network anomaly detection and remediation dashboard")

siem_url, siem_profile = get_siem_status()

if page == "Overview":
    st.header("📊 Network Overview")
    if data is not None:
        total_records = len(data)
        total_alerts = len(alerts) if alerts is not None else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Flows", total_records)
        col2.metric("AI Alerts", total_alerts, delta=total_alerts, delta_color="inverse")
        col3.metric("System State", "Operational" if total_alerts < 3000 else "Critical")

        fig = px.pie(
            names=["Normal", "Anomaly"],
            values=[total_records - total_alerts, total_alerts],
            color_discrete_sequence=["#238636", "#da3633"],
            hole=0.4,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Welcome. Run the analysis to get started.")

elif page == "EDA & Insights":
    st.header("🔍 EDA & Insights")
    if data is not None and alerts is not None:
        data_viz = data.copy()
        data_viz["Status"] = "Normal"
        data_viz.loc[data_viz.index.isin(alerts.index), "Status"] = "Anomaly"

        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("📈 Sload Distribution")
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
            st.subheader("📍 Scatter Plot: Sload vs Dload")
            fig_scatter = px.scatter(
                data_viz,
                x="Sload",
                y="Dload",
                color="Status",
                hover_data=["sttl", "sbytes"],
                color_discrete_map={"Normal": "#238636", "Anomaly": "#da3633"},
                opacity=0.6,
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.warning("Run the analysis first to view the EDA section.")

elif page == "Detected Alerts":
    st.header("🚨 Detected Alerts (Top 10)")
    if alerts is not None and len(alerts) > 0:
        st.error(f"Top 10 suspicious flows from {len(alerts)} anomalies.")
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        for _, row in alerts.head(10).iterrows():
            job_status = "N/A"
            if row.get("advice_job_id"):
                job_status = get_job_status(row["advice_job_id"], redis_url) or "unknown"

            with st.expander(f"Alert #{row['id']} - Score {row['anomaly_score']} - Job: {job_status}"):
                col_info, col_job = st.columns(2)
                with col_info:
                    st.write(row[["created_at", "anomaly_score", "severity", "status"]])
                with col_job:
                    st.write(f"**Job Status:** {job_status}")
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
    else:
        st.info("No alerts available yet.")

elif page == "SIEM View":
    st.header("🔗 SIEM Integration & Visualization")

    col1, col2, col3 = st.columns(3)
    col1.metric("SIEM Status", "Connected" if siem_url else "Not configured")
    col2.metric("SIEM Profile", siem_profile)
    col3.metric("Kibana", "http://localhost:5601")

    if siem_url:
        st.success(f"Alerts will be sent to: {siem_url}")
    else:
        st.warning("Set NETPULSE_WEBHOOK_URL to connect this dashboard to the SIEM.")

    if alerts is not None and len(alerts) > 0:
        alerts_view = alerts.copy()
        if "created_at" in alerts_view.columns:
            alerts_view["created_at"] = pd.to_datetime(alerts_view["created_at"], errors="coerce")

        vis_col1, vis_col2 = st.columns(2)
        with vis_col1:
            st.subheader("Anomaly Score Distribution")
            if "anomaly_score" in alerts_view.columns:
                fig_scores = px.histogram(
                    alerts_view,
                    x="anomaly_score",
                    nbins=20,
                    color="severity" if "severity" in alerts_view.columns else None,
                    color_discrete_sequence=["#238636", "#d29922", "#da3633"],
                )
                st.plotly_chart(fig_scores, use_container_width=True)
            else:
                st.info("No anomaly_score column available in alerts data.")

        with vis_col2:
            st.subheader("Alerts Over Time")
            if "created_at" in alerts_view.columns and "anomaly_score" in alerts_view.columns:
                fig_time = px.scatter(
                    alerts_view,
                    x="created_at",
                    y="anomaly_score",
                    color="severity" if "severity" in alerts_view.columns else None,
                    hover_data=[c for c in ["id", "status", "advice_status"] if c in alerts_view.columns],
                )
                st.plotly_chart(fig_time, use_container_width=True)
            else:
                st.info("Alerts need created_at and anomaly_score to plot the timeline.")

        st.subheader("Forward Recent Alerts to SIEM")
        forward_limit = st.slider("Alerts to forward", min_value=1, max_value=min(25, len(alerts)), value=min(10, len(alerts)))
        if st.button("Send latest alerts to SIEM", key="send_to_siem"):
            forwarded = forward_alerts_to_siem(alerts, limit=forward_limit)
            st.success(f"Forwarded {forwarded} alerts to the SIEM.")

        st.subheader("Recent Alert Records")
        st.dataframe(alerts.head(20), use_container_width=True)
    else:
        st.info("Run the anomaly detection first to populate SIEM-linked alerts.")

elif page == "Security Report":
    st.header("🛡️ Security Report")
    if os.path.exists(REPORT_FILE):
        with open(REPORT_FILE, "r", encoding="utf-8") as f:
            report_content = f.read()
        st.markdown(
            f'<div style="background-color: #161b22; padding: 20px; border-radius: 10px; border: 1px solid #30363d;">{report_content}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("Generate the report to view the latest remediation guidance.")

elif page == "Audit Logs":
    st.header("🧾 Audit Logs")
    try:
        session = get_db_session()
        logs_query = session.query(AuditLog).order_by(AuditLog.timestamp.desc())
        logs_df = pd.read_sql(logs_query.statement, logs_query.session.bind)
        if logs_df is not None and len(logs_df) > 0:
            st.dataframe(logs_df)
            csv = logs_df.to_csv(index=False)
            st.download_button("Download audit logs as CSV", csv, file_name="audit_logs.csv", mime="text/csv")
        else:
            st.info("No audit logs available yet.")
    except Exception as exc:
        st.error(f"Error loading audit logs: {exc}")

elif page == "System Status":
    st.header("🔧 System Status & Health")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔴 Redis Connection")
        redis_health = check_redis_health(redis_url)
        if redis_health.get("connected"):
            st.success(f"✅ Connected to {redis_url}")
            queue_stats = get_queue_stats(redis_url)
            if "error" not in queue_stats:
                st.metric("Queue Depth", queue_stats["queue_depth"])
                st.metric("Jobs Started", queue_stats["jobs_started"])
                st.metric("Jobs Finished", queue_stats["jobs_finished"])
                st.metric("Jobs Failed", queue_stats["jobs_failed"])
            else:
                st.error(f"Error fetching stats: {queue_stats['error']}")
        else:
            st.error(f"❌ Redis not available: {redis_health.get('error')}")
            st.info("**To enable background jobs, start Redis separately:**")
            st.code("redis-server", language="bash")

    with col2:
        st.subheader("📊 Database")
        session = get_db_session()
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
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    st.subheader("Bulk Operations")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Generate Advice")
        session = get_db_session()
        pending_count = session.query(Alert).filter(Alert.advice.is_(None)).count()
        st.info(f"Alerts pending advice: {pending_count}")

        if st.button("🤖 Enqueue All Pending Advice", key="bulk_enqueue"):
            try:
                redis_health = check_redis_health(redis_url)
                if redis_health.get("connected"):
                    pending_alerts = session.query(Alert).filter(Alert.advice.is_(None)).all()
                    alert_ids = [alert.id for alert in pending_alerts]
                    if alert_ids:
                        enqueued = bulk_enqueue_advice(alert_ids, DB_PATH, redis_url)
                        st.success(f"✅ Enqueued {enqueued} advice jobs")
                    else:
                        st.info("No pending alerts to enqueue")
                else:
                    st.error(f"❌ Redis not available: {redis_health.get('error')}")
            except Exception as exc:
                st.error(f"Error: {exc}")

    with col2:
        st.markdown("### Data Export")
        session = get_db_session()
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
    st.info("To run background workers outside the dashboard, use this command:")
    st.code("rq worker advisor", language="bash")
