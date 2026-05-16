"""
email_scheduler.py - Schedule email notifications for NetPulse-Shield
Handles weekly summaries and real-time attack alerts
"""
import os
import schedule
import time
import threading
import pandas as pd
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from email_notifier import EmailNotifier

load_dotenv()


class EmailScheduler:
    """Manages scheduled email notifications."""

    def __init__(self):
        """Initialize scheduler."""
        self.notifier = EmailNotifier()
        self.scheduler = schedule.Scheduler()
        self.is_running = False
        self.receiver_email = None
        self.weekly_day = os.getenv("WEEKLY_REPORT_DAY", "0")
        self.weekly_time = os.getenv("WEEKLY_REPORT_TIME", "09:00")

    def set_receiver_email(self, email: str):
        """Set the receiver email address."""
        self.receiver_email = email
        print(f" Receiver email set to: {email}")

    def schedule_weekly_report(self):
        """Schedule weekly summary report."""
        day_map = {
            "0": "monday",
            "1": "tuesday",
            "2": "wednesday",
            "3": "thursday",
            "4": "friday",
            "5": "saturday",
            "6": "sunday",
        }

        day = day_map.get(self.weekly_day, "monday")

        self.scheduler.every().week.at(f"{self.weekly_time}").do(
            self.send_weekly_summary
        )

        print(f" Weekly report scheduled for {day} at {self.weekly_time}")

    def send_weekly_summary(self):
        """Send weekly summary email."""
        if not self.receiver_email:
            print("  No receiver email configured. Skipping weekly summary.")
            return

        try:
            # Try to load alerts from multiple possible locations
            alerts_path = Path("data/outputs/alerts.csv")
            if not alerts_path.exists():
                alerts_path = Path("alerts.csv")

            if alerts_path.exists():
                alerts_df = pd.read_csv(alerts_path)
                self.notifier.send_weekly_summary(self.receiver_email, alerts_df)
            else:
                print("  No alerts file found.")

        except Exception as e:
            print(f" Error sending weekly summary: {str(e)}")

    def send_attack_alert(self, attack_data: dict, confidence: float):
        """
        Send immediate alert email for detected attack.

        Args:
            attack_data: Dictionary containing attack details
            confidence: Confidence percentage (0-100)
        """
        if not self.receiver_email:
            print("  No receiver email configured. Skipping alert.")
            return

        self.notifier.send_alert(self.receiver_email, attack_data, confidence)

    def run_scheduler(self):
        """Run scheduler in background thread."""
        if self.is_running:
            print("  Scheduler already running.")
            return

        self.is_running = True
        scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        scheduler_thread.start()
        print(" Email scheduler started in background.")

    def _scheduler_loop(self):
        """Internal scheduler loop."""
        while self.is_running:
            self.scheduler.run_pending()
            time.sleep(60)  # Check every minute

    def stop_scheduler(self):
        """Stop the scheduler."""
        self.is_running = False
        print("  Email scheduler stopped.")


# Global scheduler instance
_scheduler_instance = None


def get_scheduler():
    """Get or create global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = EmailScheduler()
    return _scheduler_instance


if __name__ == "__main__":
    scheduler = get_scheduler()
    scheduler.set_receiver_email("test@example.com")
    scheduler.schedule_weekly_report()
    scheduler.run_scheduler()

    print("Scheduler running. Press Ctrl+C to stop...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop_scheduler()
