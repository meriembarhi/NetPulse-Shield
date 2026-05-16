import os
import sys
import time
import pandas as pd


def main():
    alert_candidates = ["data/outputs/alerts.csv", "alerts.csv"]
    alert_file = None
    for p in alert_candidates:
        if os.path.exists(p):
            alert_file = p
            break

    if alert_file is None:
        print("\n" + "=" * 55)
        print("NETPULSE-SHIELD: SYSTEM ERROR")
        print("=" * 55)
        print("Could not find alerts.csv")
        print("Run 'python detector.py' first to identify anomalies.")
        print("=" * 55 + "\n")
        sys.exit(1)

    print("NetPulse-Shield -- RAG Advisor")
    print(f"[INFO] Loading alerts from {alert_file}")
    print("[INFO] Initializing RAG pipeline (loading AI models, may take 60s)...")
    sys.stdout.flush()

    t0 = time.time()
    from advisor import NetworkSecurityAdvisor
    advisor = NetworkSecurityAdvisor()
    print(f"[OK] RAG advisor loaded in {time.time()-t0:.1f}s")
    sys.stdout.flush()

    alerts = pd.read_csv(alert_file)

    report = "=== NETPULSE-SHIELD: RAG SECURITY REPORT ===\n\n"

    for index, row in alerts.head(5).iterrows():
        features = {k: v for k, v in row.items()
                    if k not in ('anomaly', 'anomaly_score', 'is_anomaly')}
        desc = ", ".join(f"{k}={v}" for k, v in features.items())
        query = f"Network anomaly detected with features: {desc}"

        print(f"\n[ANALYSIS] Threat #{index+1}")
        sys.stdout.flush()

        t1 = time.time()
        advice = advisor.get_remediation_advice(query)
        print(f"  Retrieved in {time.time()-t1:.1f}s")
        sys.stdout.flush()

        report += f"THREAT #{index+1}\n"
        report += f"Symptoms: {desc}\n"
        report += f"Remediation:\n{advice}\n"
        report += "-" * 40 + "\n"

    os.makedirs("data/outputs", exist_ok=True)
    report_path = "data/outputs/Security_Report.txt"
    with open(report_path, "w") as f:
        f.write(report)
    with open("Security_Report.txt", "w") as f:
        f.write(report)

    print(f"\n[OK] Report saved to {report_path}")


if __name__ == "__main__":
    main()
