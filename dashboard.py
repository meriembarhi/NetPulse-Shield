import os
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt


# =========================
# Page Configuration
# =========================

st.set_page_config(
    page_title="NetPulse-Shield Dashboard",
    page_icon="🛡️",
    layout="wide"
)


# =========================
# File Paths
# =========================

DATA_FILE = "data/final_project_data.csv"
ALERTS_FILE = "alerts.csv"
REPORT_FILE = "Security_Report.txt"


# =========================
# Helper Function
# =========================

def load_csv(file_path):
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return None


# =========================
# Load Data
# =========================

data = load_csv(DATA_FILE)
alerts = load_csv(ALERTS_FILE)


# =========================
# Header
# =========================

st.title("🛡️ NetPulse-Shield Dashboard")
st.subheader("AI-Based Network Attack Detection and Remediation")

st.markdown("""
This dashboard displays network traffic indicators, detected anomalies, 
and AI-generated remediation recommendations.
""")


# =========================
# Sidebar Navigation
# =========================

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Choose a section",
    [
        "Overview",
        "Traffic Data",
        "Detected Alerts",
        "Security Report"
    ]
)


# =========================
# Overview Page
# =========================

if page == "Overview":
    st.header("📊 General Overview")

    col1, col2, col3 = st.columns(3)

    total_records = len(data) if data is not None else 0
    total_alerts = len(alerts) if alerts is not None else 0
    normal_records = max(total_records - total_alerts, 0)

    col1.metric("Total Traffic Records", total_records)
    col2.metric("Detected Alerts", total_alerts)
    col3.metric("Estimated Normal Records", normal_records)

    st.markdown("---")

    st.subheader("Normal vs Suspicious Traffic")

    if total_records > 0:
        fig, ax = plt.subplots()
        ax.bar(
            ["Normal Traffic", "Suspicious Traffic"],
            [normal_records, total_alerts]
        )
        ax.set_ylabel("Number of Records")
        ax.set_title("Traffic Classification")
        st.pyplot(fig)
    else:
        st.warning("No data file found. Please make sure data/final_project_data.csv exists.")


# =========================
# Traffic Data Page
# =========================

elif page == "Traffic Data":
    st.header("🌐 Network Traffic Data")

    if data is not None:
        st.write("Preview of the cleaned dataset:")
        st.dataframe(data.head(50), use_container_width=True)

        st.subheader("Dataset Information")

        col1, col2 = st.columns(2)
        col1.metric("Number of Rows", data.shape[0])
        col2.metric("Number of Columns", data.shape[1])

        st.write("Columns:")
        st.write(list(data.columns))

        numeric_cols = data.select_dtypes(include=["int64", "float64"]).columns

        if len(numeric_cols) > 0:
            selected_col = st.selectbox(
                "Select a numeric feature to visualize",
                numeric_cols
            )

            fig, ax = plt.subplots()
            ax.hist(data[selected_col].dropna(), bins=30)
            ax.set_title(f"Distribution of {selected_col}")
            ax.set_xlabel(selected_col)
            ax.set_ylabel("Frequency")
            st.pyplot(fig)
        else:
            st.info("No numeric columns found in the dataset.")
    else:
        st.error("data/final_project_data.csv not found.")


# =========================
# Detected Alerts Page
# =========================

elif page == "Detected Alerts":
    st.header("🚨 Detected Suspicious Traffic")

    if alerts is not None:
        st.write("These records were detected as suspicious by the anomaly detection model.")
        st.dataframe(alerts, use_container_width=True)

        st.subheader("Alert Statistics")

        total_alerts = len(alerts)
        st.metric("Total Alerts", total_alerts)

        numeric_cols = alerts.select_dtypes(include=["int64", "float64"]).columns

        if len(numeric_cols) > 0:
            selected_col = st.selectbox(
                "Select an alert feature to visualize",
                numeric_cols
            )

            fig, ax = plt.subplots()
            ax.hist(alerts[selected_col].dropna(), bins=20)
            ax.set_title(f"Alert Distribution by {selected_col}")
            ax.set_xlabel(selected_col)
            ax.set_ylabel("Frequency")
            st.pyplot(fig)
        else:
            st.info("No numeric columns found in alerts.csv.")
    else:
        st.error("alerts.csv not found. Run detector.py first.")


# =========================
# Security Report Page
# =========================

elif page == "Security Report":
    st.header("🛡️ Security Intelligence Report")

    if os.path.exists(REPORT_FILE):
        with open(REPORT_FILE, "r", encoding="utf-8") as file:
            report = file.read()

        # Remove repeated title from the generated report
        report = report.replace("=== NETPULSE-SHIELD: AUTOMATED SECURITY REPORT ===", "")
        report = report.strip()

        st.markdown("""
        <style>
        .report-card {
            background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
            border: 1px solid #30363d;
            border-radius: 18px;
            padding: 28px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.35);
            color: #e6edf3;
            font-family: 'Segoe UI', sans-serif;
            line-height: 1.7;
        }

        .badge-danger {
            display: inline-block;
            background-color: #da3633;
            color: white;
            padding: 6px 14px;
            border-radius: 999px;
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 18px;
        }

        .badge-ai {
            display: inline-block;
            background-color: #238636;
            color: white;
            padding: 6px 14px;
            border-radius: 999px;
            font-size: 14px;
            font-weight: bold;
            margin-left: 8px;
            margin-bottom: 18px;
        }

        .report-section {
            background-color: rgba(255,255,255,0.04);
            padding: 20px;
            border-radius: 14px;
            white-space: pre-wrap;
            font-size: 16px;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="report-card">
            <span class="badge-danger">HIGH RISK</span>
            <span class="badge-ai">AI GENERATED ANALYSIS</span>
            <div class="report-section">{report}</div>
        </div>
        """, unsafe_allow_html=True)

    else:
        st.error("Security_Report.txt not found. Run auto_remediator.py first.")

