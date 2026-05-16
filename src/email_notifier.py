"""
email_notifier.py - Email notification system for NetPulse-Shield
Sends alerts for detected attacks and weekly summaries
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class EmailNotifier:
    """Handles email notifications for attack alerts and reports."""

    def __init__(self):
        """Initialize email configuration from .env file."""
        self.sender_email = os.getenv("EMAIL_SENDER")
        self.sender_password = os.getenv("EMAIL_PASSWORD")
        self.smtp_server = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
        self.threshold = float(os.getenv("ATTACK_THRESHOLD_PERCENTAGE", "80"))

        if not self.sender_email or not self.sender_password:
            print("[WARN] Email configuration incomplete. Check .env file.")
            self.configured = False
        else:
            self.configured = True
            print("[OK] Email notifier initialized and ready.")

    def send_alert(self, receiver_email: str, attack_data: dict, confidence: float) -> bool:
        """
        Send an alert email for a detected attack.

        Args:
            receiver_email: Email address to send alert to
            attack_data: Dictionary containing attack information
            confidence: Confidence score as percentage (0-100)

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.configured:
            print("[FAIL] Email notifier not configured.")
            return False

        if confidence < self.threshold:
            print(f"[INFO]  Attack confidence {confidence:.2f}% below threshold {self.threshold}%")
            return False

        try:
            subject = f" Security Alert: Attack Detected - {confidence:.2f}% Confidence"

            body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; }}
        .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; }}
        .header {{ background-color: #d32f2f; color: white; padding: 15px; border-radius: 5px; }}
        .content {{ padding: 15px 0; }}
        .metric {{ background-color: #f9f9f9; padding: 10px; margin: 10px 0; border-left: 4px solid #d32f2f; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 20px; padding-top: 10px; border-top: 1px solid #ddd; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>[WARN] NetPulse-Shield Security Alert</h2>
        </div>
        
        <div class="content">
            <p><strong>Alert Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Confidence Level:</strong> <strong style="color: #d32f2f;">{confidence:.2f}%</strong></p>
            
            <h3>Attack Details:</h3>
"""

            for key, value in attack_data.items():
                body += f'            <div class="metric"><strong>{key}:</strong> {value}</div>\n'

            body += """
        </div>
        
        <div class="footer">
            <p>This is an automated alert from NetPulse-Shield.</p>
            <p>Do not reply to this email. Check your dashboard for more details.</p>
        </div>
    </div>
</body>
</html>
"""

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.sender_email
            msg["To"] = receiver_email

            msg.attach(MIMEText(body, "html"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, receiver_email, msg.as_string())

            print(f"[OK] Alert email sent to {receiver_email}")
            return True

        except Exception as e:
            print(f"[FAIL] Failed to send alert email: {str(e)}")
            return False

    def send_weekly_summary(self, receiver_email: str, alerts_df: pd.DataFrame) -> bool:
        """
        Send a weekly summary of detected attacks.

        Args:
            receiver_email: Email address to send summary to
            alerts_df: DataFrame containing alert data

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.configured:
            print("[FAIL] Email notifier not configured.")
            return False

        if alerts_df.empty:
            print("[INFO]  No alerts to report this week.")
            return False

        try:
            week_start = pd.Timestamp.now() - pd.Timedelta(days=7)
            subject = f" NetPulse-Shield Weekly Security Report - {datetime.now().strftime('%Y-%m-%d')}"

            # Calculate statistics
            total_attacks = len(alerts_df)
            high_confidence_attacks = len(alerts_df[alerts_df.get("confidence", 0) >= 80])
            avg_confidence = alerts_df.get("confidence", pd.Series()).mean() if "confidence" in alerts_df else 0

            body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; }}
        .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; }}
        .header {{ background-color: #1976d2; color: white; padding: 15px; border-radius: 5px; }}
        .stats {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin: 20px 0; }}
        .stat-box {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; text-align: center; }}
        .stat-number {{ font-size: 24px; font-weight: bold; color: #1976d2; }}
        .stat-label {{ font-size: 12px; color: #666; margin-top: 5px; }}
        .table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        .table th, .table td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        .table th {{ background-color: #f5f5f5; font-weight: bold; }}
        .high-risk {{ color: #d32f2f; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 20px; padding-top: 10px; border-top: 1px solid #ddd; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2> Weekly Security Summary</h2>
        </div>
        
        <div class="stats">
            <div class="stat-box">
                <div class="stat-number">{total_attacks}</div>
                <div class="stat-label">Total Attacks</div>
            </div>
            <div class="stat-box">
                <div class="stat-number high-risk">{high_confidence_attacks}</div>
                <div class="stat-label">High Confidence (80%)</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{avg_confidence:.1f}%</div>
                <div class="stat-label">Avg Confidence</div>
            </div>
        </div>
        
        <p><strong>Report Period:</strong> {week_start.strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}</p>
        
        <h3>Recent High-Confidence Attacks:</h3>
        <table class="table">
            <tr>
                <th>Timestamp</th>
                <th>Type</th>
                <th>Confidence</th>
            </tr>
"""

            # Add top attacks to table
            for idx, row in alerts_df.tail(10).iterrows():
                confidence = row.get("confidence", 0)
                attack_type = row.get("label", "Unknown")
                timestamp = row.get("timestamp", "N/A")
                
                body += f"""            <tr>
                <td>{timestamp}</td>
                <td>{attack_type}</td>
                <td class="{'high-risk' if confidence >= 80 else ''}">{confidence:.1f}%</td>
            </tr>
"""

            body += """
        </table>
        
        <p>For detailed information, please visit your NetPulse-Shield dashboard.</p>
        
        <div class="footer">
            <p>This is an automated report from NetPulse-Shield.</p>
            <p>Do not reply to this email.</p>
        </div>
    </div>
</body>
</html>
"""

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.sender_email
            msg["To"] = receiver_email

            msg.attach(MIMEText(body, "html"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, receiver_email, msg.as_string())

            print(f"[OK] Weekly summary email sent to {receiver_email}")
            return True

        except Exception as e:
            print(f"[FAIL] Failed to send weekly summary: {str(e)}")
            return False

    def test_connection(self) -> bool:
        """Test SMTP connection with current configuration."""
        if not self.configured:
            print("[FAIL] Email configuration incomplete.")
            return False

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
            print("[OK] Email connection test successful!")
            return True
        except Exception as e:
            print(f"[FAIL] Email connection test failed: {str(e)}")
            return False


# Example usage / testing
if __name__ == "__main__":
    notifier = EmailNotifier()

    # Test connection
    notifier.test_connection()

    # Example alert data
    example_attack = {
        "Source IP": "192.168.1.100",
        "Destination IP": "10.0.0.1",
        "Port": "445",
        "Protocol": "TCP",
        "Attack Type": "SMB Exploit",
        "Sload": "1250 bytes/s",
        "sttl": "64",
    }

    # Uncomment to test alert email
    # notifier.send_alert("recipient@example.com", example_attack, 85.5)

    print("Email notifier module loaded successfully!")
