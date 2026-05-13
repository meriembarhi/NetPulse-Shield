#!/usr/bin/env python
"""
pipeline.py - End-to-End Network Anomaly Detection & Remediation Pipeline

This script orchestrates the complete NetPulse-Shield workflow:
  1. Load network traffic data from CSV
  2. Detect anomalies using Isolation Forest (tunes contamination on a validation split when a Label column exists — same behavior as running detector.py directly)
  3. Generate remediation advice for flagged alerts
  4. Produce a comprehensive security report
  5. When labels exist, write evaluation metrics to metrics.json (path configurable with --metrics)

Usage:
  python pipeline.py                              # Use default data/final_project_data.csv
  python pipeline.py data/my_traffic.csv          # Use custom CSV
  python pipeline.py data/my_traffic.csv --no-persist  # Skip DB persistence

Perfect for automation, batch processing, and CI/CD pipelines.
"""

import os
import sys
import argparse
import logging
import pandas as pd

from detector import NetworkAnomalyDetector
from advisor import NetworkSecurityAdvisor
from webhook import send_alert_to_azure

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_csv(csv_path: str) -> pd.DataFrame:
    """Load and validate CSV file."""
    if not os.path.exists(csv_path):
        logger.error(f"❌ File not found: {csv_path}")
        sys.exit(1)
    
    try:
        df = pd.read_csv(csv_path)
        logger.info(f"✅ Loaded {len(df):,} records from {csv_path}")
        
        # Check for at least one numeric column
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if not numeric_cols:
            logger.error(f"❌ No numeric columns found. Available: {df.columns.tolist()}")
            sys.exit(1)
        
        logger.info(f"   Numeric features: {len(numeric_cols)} ({', '.join(numeric_cols[:5])}{'...' if len(numeric_cols) > 5 else ''})")
        return df
    except Exception as e:
        logger.error(f"❌ Failed to read CSV: {e}")
        sys.exit(1)


def run_anomaly_detection(
    df: pd.DataFrame,
    persist_to_db: bool = True,
    metrics_output_path: str | None = "metrics.json",
) -> pd.DataFrame:
    """Run anomaly detection using Isolation Forest."""
    logger.info("\n" + "="*60)
    logger.info("STEP 1: ANOMALY DETECTION (Isolation Forest)")
    logger.info("="*60)
    
    try:
        detector = NetworkAnomalyDetector(
            contamination='auto',
            persist_to_db=persist_to_db,
            db_path="sqlite:///alerts.db"
        )

        if "Label" in df.columns:
            logger.info(
                "Found column 'Label' — tuning contamination on a stratified "
                "validation split (aligned with detector.py __main__)."
            )
            best_c = detector.tune_contamination(df, label_column="Label")
            detector.contamination = best_c
            logger.info("Using tuned contamination: %.4f", best_c)
        else:
            logger.info(
                "No 'Label' column — skipping contamination sweep; train() will "
                "use default auto contamination when labels are absent."
            )

        if metrics_output_path and "Label" not in df.columns:
            logger.info(
                "Metrics output path set but CSV has no 'Label' column — "
                "skipping metrics.json (no ground truth to evaluate)."
            )

        results = detector.analyze(
            df,
            force_train=True,
            metrics_output_path=metrics_output_path,
        )
        
        anomalies = results[results['is_anomaly']]
        logger.info("\n✅ Detection Complete:")
        logger.info(f"   Total records: {len(results):,}")
        logger.info(f"   Anomalies found: {len(anomalies):,} ({100*len(anomalies)/len(results):.2f}%)")
        
        return results
    except Exception as e:
        logger.error(f"❌ Detection failed: {e}")
        sys.exit(1)


def save_alerts_csv(results: pd.DataFrame, output_path: str = "alerts.csv") -> None:
    """Save top anomalies to alerts.csv for downstream processing."""
    try:
        anomalies = results[results['is_anomaly']].copy()
        
        # Sort by anomaly score (most anomalous first)
        anomalies = anomalies.sort_values('anomaly_score', ascending=True).head(10)
        
        anomalies.to_csv(output_path, index=False)
        logger.info(f"✅ Saved {len(anomalies)} top alerts to {output_path}")
    except Exception as e:
        logger.error(f"⚠️  Failed to save alerts CSV: {e}")


def generate_remediation_report(
    results: pd.DataFrame,
    output_path: str = "Security_Report.txt",
) -> None:
    """Generate remediation advice for detected anomalies."""
    logger.info("\n" + "="*60)
    logger.info("STEP 2: REMEDIATION ADVICE GENERATION")
    logger.info("="*60)
    
    try:
        advisor = NetworkSecurityAdvisor(top_k=3)
        webhook_url = os.getenv("NETPULSE_WEBHOOK_URL")
        workspace_id = os.getenv("NETPULSE_WORKSPACE_ID")
        primary_key = os.getenv("NETPULSE_PRIMARY_KEY")
        
        anomalies = results[results['is_anomaly']].copy()
        if len(anomalies) == 0:
            logger.info("ℹ️  No anomalies detected. Skipping advice generation.")
            return
        
        report_lines = [
            "=" * 70,
            "🛡️  NETPULSE-SHIELD: AI SECURITY REPORT",
            "=" * 70,
            "",
        ]
        
        for idx, (_, row) in enumerate(anomalies.head(5).iterrows(), 1):
            # Build threat description from available features
            features = {k: v for k, v in row.items() 
                       if k not in ['anomaly', 'anomaly_score', 'is_anomaly', 'Label']}
            
            description = f"Anomaly detected with anomaly_score={row['anomaly_score']:.4f}. "
            description += f"Features: {', '.join(f'{k}={v:.2f}' for k, v in list(features.items())[:3])}"
            
            logger.info(f"\n[Anomaly {idx}/{min(5, len(anomalies))}] Retrieving advice...")
            advice = advisor.get_remediation_advice(description)

            alert_payload = row.to_dict()
            alert_payload["description"] = description
            send_alert_to_azure(
                alert_payload,
                webhook_url=webhook_url,
                advice=advice,
                workspace_id=workspace_id,
                primary_key=primary_key,
            )
            
            report_lines.append(f"[ALERT {idx}] Anomaly Score: {row['anomaly_score']:.4f}")
            report_lines.append("-" * 70)
            report_lines.append(advice)
            report_lines.append("")
        
        report_lines.append("=" * 70)
        report_lines.append("End of Report")
        report_lines.append("=" * 70)
        
        report_text = "\n".join(report_lines)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        logger.info(f"\n✅ Security report saved to {output_path}")
    except Exception as e:
        logger.error(f"⚠️  Failed to generate report: {e}")


def main():
    """Orchestrate the full pipeline."""
    parser = argparse.ArgumentParser(
        description="Run the complete NetPulse-Shield pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pipeline.py                              # Default: data/final_project_data.csv
  python pipeline.py data/my_traffic.csv          # Custom CSV
  python pipeline.py data/my_traffic.csv --no-persist  # Skip DB storage
        """
    )
    parser.add_argument(
        'csv_path',
        nargs='?',
        default='data/final_project_data.csv',
        help='Path to network traffic CSV (default: data/final_project_data.csv)'
    )
    parser.add_argument(
        '--no-persist',
        action='store_true',
        help='Skip saving alerts to database'
    )
    parser.add_argument(
        '--alerts-csv',
        default='alerts.csv',
        help='Output path for alerts CSV (default: alerts.csv)'
    )
    parser.add_argument(
        '--report',
        default='Security_Report.txt',
        help='Output path for security report (default: Security_Report.txt)'
    )
    parser.add_argument(
        '--metrics',
        default='metrics.json',
        help='Path for evaluation metrics JSON when Label column exists (default: metrics.json). '
        'Use empty string to skip writing metrics.',
    )

    
    args = parser.parse_args()
    
    logger.info("🚀 NetPulse-Shield Pipeline Starting...")
    logger.info("   Version 2.0 (Professional-Grade)")
    
    # ===== STEP 1: Load & Validate Data =====
    logger.info("\n" + "="*60)
    logger.info("STEP 0: DATA VALIDATION")
    logger.info("="*60)
    df = validate_csv(args.csv_path)
    
    metrics_path = args.metrics.strip() or None

    # ===== STEP 2: Run Anomaly Detection =====
    results = run_anomaly_detection(
        df,
        persist_to_db=not args.no_persist,
        metrics_output_path=metrics_path,
    )
    
    # ===== STEP 3: Save Alerts =====
    save_alerts_csv(results, args.alerts_csv)
    
    # ===== STEP 4: Generate Remediation Report =====
    generate_remediation_report(
        results,
        args.report,
    )
    
    logger.info("\n" + "="*60)
    logger.info("✅ PIPELINE COMPLETE")
    logger.info("="*60)
    logger.info("\nOutput files:")
    logger.info(f"  • {args.alerts_csv} — Top 10 anomalies detected")
    logger.info(f"  • {args.report} — Remediation advice for top 5 anomalies")
    if metrics_path:
        logger.info(f"  • {metrics_path} — Evaluation metrics (when Label column is present)")
    logger.info("  • alerts.db — Alert database (if --no-persist not used)")
    logger.info("\nNext steps:")
    logger.info("  • Review alerts in alerts.csv")
    logger.info("  • Read security recommendations in Security_Report.txt")
    logger.info("  • Use dashboard for interactive triage: streamlit run dashboard.py")


if __name__ == "__main__":
    main()
