"""
email_api.py - Optional Flask REST API for email notifications
Provides HTTP endpoints for sending alerts programmatically
"""
import os
import sys
from pathlib import Path
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from email_notifier import EmailNotifier

load_dotenv()

app = Flask(__name__)
notifier = EmailNotifier()


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "email_configured": notifier.configured,
        "threshold": notifier.threshold
    }), 200


@app.route("/alert", methods=["POST"])
def send_alert():
    """
    Send an alert email.

    Expected JSON:
    {
        "email": "recipient@example.com",
        "attack_data": {
            "Source IP": "192.168.1.100",
            "Attack Type": "SMB Exploit"
        },
        "confidence": 85.5
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        email = data.get("email")
        attack_data = data.get("attack_data", {})
        confidence = float(data.get("confidence", 0))

        if not email:
            return jsonify({"error": "Email address required"}), 400

        if not attack_data:
            return jsonify({"error": "Attack data required"}), 400

        success = notifier.send_alert(email, attack_data, confidence)

        return jsonify({
            "success": success,
            "message": "Alert sent" if success else "Alert not sent (check threshold)",
            "confidence": confidence,
            "threshold": notifier.threshold
        }), 200 if success else 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/weekly-report", methods=["POST"])
def send_weekly_report():
    """
    Send weekly summary email.

    Expected JSON:
    {
        "email": "recipient@example.com"
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        email = data.get("email")

        if not email:
            return jsonify({"error": "Email address required"}), 400

        # Load alerts
        alerts_path = Path("data/outputs/alerts.csv")
        if not alerts_path.exists():
            alerts_path = Path("alerts.csv")

        if alerts_path.exists():
            alerts_df = pd.read_csv(alerts_path)
            success = notifier.send_weekly_summary(email, alerts_df)
        else:
            return jsonify({"error": "No alerts file found"}), 404

        return jsonify({
            "success": success,
            "message": "Weekly report sent" if success else "Failed to send report"
        }), 200 if success else 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/test-connection", methods=["POST"])
def test_connection():
    """Test SMTP connection."""
    try:
        success = notifier.test_connection()
        return jsonify({
            "success": success,
            "message": "Connection successful" if success else "Connection failed"
        }), 200 if success else 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/config", methods=["GET"])
def get_config():
    """Get current email configuration."""
    return jsonify({
        "sender": notifier.sender_email,
        "smtp_server": notifier.smtp_server,
        "smtp_port": notifier.smtp_port,
        "threshold": notifier.threshold,
        "configured": notifier.configured
    }), 200


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    print("=" * 60)
    print(" NetPulse-Shield Email API Server")
    print("=" * 60)
    print(f" Sender: {notifier.sender_email}")
    print(f" Threshold: {notifier.threshold}%")
    print("=" * 60)

    if not notifier.configured:
        print("  WARNING: Email not configured!")
        print("   Set EMAIL_SENDER and EMAIL_PASSWORD in .env")
    else:
        print("\n Email configured. Testing connection...")
        notifier.test_connection()

    print("\n Starting Flask API on http://localhost:5000")
    print(" API Endpoints:")
    print("   POST /alert - Send alert email")
    print("   POST /weekly-report - Send weekly summary")
    print("   POST /test-connection - Test SMTP connection")
    print("   GET  /config - Get email configuration")
    print("   GET  /health - Health check")
    print("\nPress Ctrl+C to stop server\n")

    app.run(debug=True, host="localhost", port=5000)
