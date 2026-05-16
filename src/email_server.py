"""
email_server.py - Background email notification server for NetPulse-Shield
Runs independently and monitors for new attacks to send alerts
"""
import os
import sys
import time
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from email_notifier import EmailNotifier
from email_scheduler import EmailScheduler

load_dotenv()


class EmailNotificationServer:
    """
    Monitors alerts and sends email notifications.
    Runs as a background service.
    """

    def __init__(self):
        """Initialize the email notification server."""
        self.notifier = EmailNotifier()
        self.scheduler = EmailScheduler()
        self.alerts_file = Path("data/outputs/alerts.csv")
        self.last_alert_time = {}
        self.processed_alerts = set()
        self.receiver_email = os.getenv("RECEIVER_EMAIL", "")
        self.check_interval = int(os.getenv("EMAIL_CHECK_INTERVAL", "60"))  # seconds

        print("=" * 60)
        print(" NetPulse-Shield Email Notification Server")
        print("=" * 60)
        print(f" Sender: {self.notifier.sender_email}")
        print(f" Receiver: {self.receiver_email}")
        print(f"  Check Interval: {self.check_interval} seconds")
        print(f" Alert Threshold: {self.notifier.threshold}%")
        print("=" * 60)

        if not self.receiver_email:
            print("  WARNING: RECEIVER_EMAIL not set in .env file!")
            print("   Set RECEIVER_EMAIL=your@email.com in .env to enable alerts")

        if not self.notifier.configured:
            print("  WARNING: Email not configured properly!")
            print("   Check your .env file for EMAIL_SENDER and EMAIL_PASSWORD")

    def load_alerts(self):
        """Load current alerts from CSV."""
        if self.alerts_file.exists():
            try:
                return pd.read_csv(self.alerts_file)
            except Exception as e:
                print(f" Error loading alerts: {str(e)}")
                return pd.DataFrame()
        return pd.DataFrame()

    def check_new_alerts(self):
        """Check for new alerts and send notifications."""
        if not self.receiver_email:
            return

        alerts_df = self.load_alerts()

        if alerts_df.empty:
            return

        # Check each alert
        for idx, alert in alerts_df.iterrows():
            # Create a unique identifier for this alert
            alert_id = f"{idx}_{alert.get('Timestamp', idx)}"

            # Skip if already processed
            if alert_id in self.processed_alerts:
                continue

            # Extract confidence/score
            confidence_col = None
            confidence = 0

            for col in ["confidence", "anomaly_score", "score", "risk_score"]:
                if col in alert.columns:
                    try:
                        confidence = float(alert[col])
                        confidence_col = col
                        break
                    except (ValueError, TypeError):
                        continue

            # Send alert if confidence exceeds threshold
            if confidence >= self.notifier.threshold:
                attack_data = self._prepare_alert_data(alert)
                self.notifier.send_alert(self.receiver_email, attack_data, confidence)
                self.processed_alerts.add(alert_id)

                # Avoid spam - rate limiting per attack type
                attack_type = alert.get("label", alert.get("attack_category", "Unknown"))
                self.last_alert_time[attack_type] = datetime.now()

    def _prepare_alert_data(self, alert):
        """Prepare alert data for email."""
        attack_data = {}

        # Include relevant columns
        important_cols = [
            "label", "attack_category", "timestamp", "Timestamp",
            "source_ip", "Source IP", "dest_ip", "Destination IP",
            "sport", "source_port", "dport", "dest_port",
            "protocol", "Protocol",
            "Sload", "sload", "Dload", "dload",
            "sbytes", "dbytes",
            "anomaly_score", "confidence", "score"
        ]

        for col in important_cols:
            if col in alert.index:
                value = alert[col]
                if pd.notna(value):
                    # Format column name
                    formatted_col = col.replace("_", " ").title()
                    attack_data[formatted_col] = str(value)

        if not attack_data:
            attack_data = dict(alert.items())

        return attack_data

    def schedule_weekly_report(self):
        """Schedule weekly summary email."""
        self.scheduler.set_receiver_email(self.receiver_email)
        self.scheduler.schedule_weekly_report()
        self.scheduler.run_scheduler()

    def run(self):
        """Start the email notification server loop."""
        print("\n Starting notification monitor...")
        print(f" Monitoring {self.alerts_file} for new alerts")
        print(f" Sending alerts to: {self.receiver_email}")
        print("\nPress Ctrl+C to stop server\n")

        try:
            # Start weekly scheduler
            if self.notifier.configured and self.receiver_email:
                self.schedule_weekly_report()
                print(" Weekly summary scheduler started\n")

            # Main monitoring loop
            while True:
                try:
                    self.check_new_alerts()
                    time.sleep(self.check_interval)

                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    print(f" Error in main loop: {str(e)}")
                    time.sleep(5)

        except KeyboardInterrupt:
            print("\n\n  Server shutting down...")
            self.scheduler.stop_scheduler()
            print(" Email server stopped.")
            sys.exit(0)


def main():
    """Main entry point."""
    server = EmailNotificationServer()

    # Test connection if configured
    if server.notifier.configured:
        print("\n Testing email configuration...")
        if server.notifier.test_connection():
            print()
        else:
            print("\n  Email connection test failed. Check your .env configuration.\n")

    # Start server
    server.run()


if __name__ == "__main__":
    main()
