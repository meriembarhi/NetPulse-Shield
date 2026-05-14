#!/usr/bin/env python
"""
pipeline.py - End-to-End Network Anomaly Detection & Remediation Pipeline

This script orchestrates the complete NetPulse-Shield workflow:
  1. Load network traffic data from CSV
  2. Detect anomalies using Isolation Forest (tunes contamination on a validation split when a Label column exists — same behavior as running detector.py directly)
  3. Generate remediation advice for flagged alerts
  4. Produce a comprehensive security report
  5. When labels exist, write evaluation metrics to metrics.json (path configurable with --metrics)
  6. Optional --compare-lof: second baseline (Local Outlier Factor) on the same scaled features, stored in metrics.json next to Isolation Forest metrics

Usage:
  python pipeline.py                              # Use default data/final_project_data.csv
  python pipeline.py data/my_traffic.csv          # Use custom CSV
  python pipeline.py data/my_traffic.csv --no-persist  # Skip DB persistence
  python pipeline.py data/my_traffic.csv --compare-lof  # + Local Outlier Factor baseline in metrics.json

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


def load_validated_dataframe(csv_path: str) -> pd.DataFrame:
    """Load and validate CSV; raises on failure (for dashboards and programmatic callers)."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"File not found: {csv_path}")

    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:
        raise ValueError(f"Failed to read CSV: {exc}") from exc

    logger.info("✅ Loaded %s records from %s", f"{len(df):,}", csv_path)

    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    if not numeric_cols:
        raise ValueError(f"No numeric columns found. Available: {df.columns.tolist()}")

    logger.info(
        "   Numeric features: %s (%s)",
        len(numeric_cols),
        ", ".join(numeric_cols[:5]) + ("..." if len(numeric_cols) > 5 else ""),
    )
    return df


def validate_csv(csv_path: str) -> pd.DataFrame:
    """Load and validate CSV file; on error logs and exits (CLI entry point)."""
    try:
        return load_validated_dataframe(csv_path)
    except Exception as exc:
        logger.error("❌ %s", exc)
        sys.exit(1)


def run_anomaly_detection(
    df: pd.DataFrame,
    persist_to_db: bool = True,
    metrics_output_path: str | None = "metrics.json",
    compare_lof: bool = False,
    db_path: str = "sqlite:///alerts.db",
    force_train: bool = True,
) -> pd.DataFrame:
    """Run anomaly detection using Isolation Forest."""
    logger.info("\n" + "="*60)
    logger.info("STEP 1: ANOMALY DETECTION (Isolation Forest)")
    logger.info("="*60)
    
    try:
        detector = NetworkAnomalyDetector(
            contamination='auto',
            persist_to_db=persist_to_db,
            db_path=db_path,
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

        if compare_lof and "Label" not in df.columns:
            logger.info("--compare-lof ignored: no 'Label' column for evaluation.")

        if compare_lof and not metrics_output_path:
            logger.info(
                "--compare-lof: LOF metrics will be printed only (no metrics file path; "
                "pass --metrics to persist baselines)."
            )

        results = detector.analyze(
            df,
            force_train=force_train,
            metrics_output_path=metrics_output_path,
            compare_lof=compare_lof,
        )
        
        anomalies = results[results['is_anomaly']]
        logger.info("\n✅ Detection Complete:")
        logger.info(f"   Total records: {len(results):,}")
        logger.info(f"   Anomalies found: {len(anomalies):,} ({100*len(anomalies)/len(results):.2f}%)")
        
        return results
    except Exception as exc:
        logger.error("❌ Detection failed: %s", exc)
        raise RuntimeError(f"Detection failed: {exc}") from exc


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


def _get_advice_fn(remediation_backend: str):
    """Return callable(description: str) -> str for the chosen backend."""
    backend = (remediation_backend or "rag").strip().lower()
    if backend == "ollama":
        from remediator import get_remediation_advice as ollama_advice

        return ollama_advice
    advisor = NetworkSecurityAdvisor(top_k=3)
    return advisor.get_remediation_advice


def generate_remediation_report(
    results: pd.DataFrame,
    output_path: str = "Security_Report.txt",
    remediation_backend: str = "rag",
) -> None:
    """Generate remediation advice for detected anomalies.

    remediation_backend
        ``\"rag\"`` (default): ``NetworkSecurityAdvisor``. ``\"ollama\"``: ``remediator.get_remediation_advice``
        (requires a running Ollama service and the ``llama3`` model).
    """
    logger.info("\n" + "="*60)
    logger.info("STEP 2: REMEDIATION ADVICE GENERATION (%s)", remediation_backend)
    logger.info("="*60)
    
    try:
        get_advice = _get_advice_fn(remediation_backend)
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
            advice = get_advice(description)

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


def run_pipeline(
    csv_path: str,
    *,
    persist_to_db: bool = True,
    alerts_csv: str = "alerts.csv",
    report_path: str = "Security_Report.txt",
    metrics_path: str | None = "metrics.json",
    compare_lof: bool = False,
    remediation_backend: str = "rag",
    db_path: str = "sqlite:///alerts.db",
    force_train: bool = True,
) -> pd.DataFrame:
    """Run the full NetPulse-Shield pipeline (same steps as ``python pipeline.py``)."""
    df = load_validated_dataframe(csv_path)
    metrics = metrics_path.strip() or None if isinstance(metrics_path, str) else metrics_path

    results = run_anomaly_detection(
        df,
        persist_to_db=persist_to_db,
        metrics_output_path=metrics,
        compare_lof=compare_lof,
        db_path=db_path,
        force_train=force_train,
    )
    save_alerts_csv(results, alerts_csv)
    generate_remediation_report(
        results,
        report_path,
        remediation_backend=remediation_backend,
    )
    return results


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
  python pipeline.py data/my_traffic.csv --compare-lof  # Add LOF baseline to metrics.json
  python pipeline.py --remediation ollama             # Report via Ollama (llama3)
  python pipeline.py --use-saved-model               # Score with existing joblib if present
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
    parser.add_argument(
        '--compare-lof',
        action='store_true',
        help='When Label is present, also fit Local Outlier Factor on the same scaled X and '
        'store metrics under baselines in the metrics JSON (or print only if metrics disabled).',
    )
    parser.add_argument(
        '--remediation',
        choices=['rag', 'ollama'],
        default='rag',
        help='Remediation backend for the security report (default: rag). '
        'ollama requires a running Ollama service and an Ollama model '
        '(default NETPULSE_OLLAMA_MODEL=llama3:8b).',
    )
    parser.add_argument(
        '--db',
        default='sqlite:///alerts.db',
        dest='db_path',
        help='SQLAlchemy URL for SQLite alert persistence (default: sqlite:///alerts.db)',
    )
    parser.add_argument(
        '--use-saved-model',
        action='store_true',
        help='Score with an existing saved model when available instead of retraining.',
    )

    
    args = parser.parse_args()
    
    logger.info("🚀 NetPulse-Shield Pipeline Starting...")
    logger.info("   Version 2.0")
    
    metrics_path = args.metrics.strip() or None

    try:
        run_pipeline(
            args.csv_path,
            persist_to_db=not args.no_persist,
            alerts_csv=args.alerts_csv,
            report_path=args.report,
            metrics_path=metrics_path,
            compare_lof=args.compare_lof,
            remediation_backend=args.remediation,
            db_path=args.db_path,
            force_train=not args.use_saved_model,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        logger.error("❌ %s", exc)
        sys.exit(1)
    
    logger.info("\n" + "="*60)
    logger.info("✅ PIPELINE COMPLETE")
    logger.info("="*60)
    logger.info("\nOutput files:")
    logger.info(f"  • {args.alerts_csv} — Top 10 anomalies detected")
    logger.info(f"  • {args.report} — Remediation advice for top 5 anomalies")
    if metrics_path:
        logger.info(f"  • {metrics_path} — Evaluation metrics (when Label column is present)")
        if args.compare_lof:
            logger.info(
                '      └ includes Local Outlier Factor baseline under "baselines" '
                "(same scaled features, same contamination as Isolation Forest)"
            )
    logger.info("  • alerts.db — Alert database (if --no-persist not used)")
    logger.info("\nNext steps:")
    logger.info("  • Review alerts in alerts.csv")
    logger.info("  • Read security recommendations in Security_Report.txt")
    logger.info("  • Use dashboard for interactive triage: streamlit run dashboard.py")


if __name__ == "__main__":
    main()
