# Email Notification System for NetPulse-Shield

## Overview

The email notification system enables real-time alerts and weekly summaries for detected network attacks. It integrates seamlessly with NetPulse-Shield's anomaly detection pipeline.

## Features

- ✅ **Real-time Attack Alerts** - Sends email immediately when attack confidence exceeds threshold (default 80%)
- ✅ **Weekly Summary Reports** - Automated digest of attacks detected during the week
- ✅ **Configurable Threshold** - Adjust alert sensitivity (0-100%)
- ✅ **Dashboard Integration** - Configure everything from the web dashboard
- ✅ **Multiple Email Providers** - Gmail, Outlook, Yahoo, and custom SMTP
- ✅ **Background Server** - Runs independently to monitor for attacks
- ✅ **REST API** - Optional Flask API for programmatic access

## Quick Start

### 1. Setup Environment Variables

Copy the example file and configure your email:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Gmail Configuration
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password    # 16-char App Password, not your main password!
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587

# Alert Settings
ATTACK_THRESHOLD_PERCENTAGE=80      # Alert threshold (0-100%)
RECEIVER_EMAIL=admin@yourcompany.com

# Weekly Report (optional)
WEEKLY_REPORT_DAY=0                 # 0=Monday, 6=Sunday
WEEKLY_REPORT_TIME=09:00            # HH:MM format
```

### 2. Gmail Setup (Recommended)

If using Gmail:

1. **Enable 2-Step Verification**:
   - Go to [myaccount.google.com](https://myaccount.google.com)
   - Click "Security" → "2-Step Verification"

2. **Generate App Password**:
   - Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   - Select "Mail" and "Windows Computer" (or your device)
   - Copy the 16-character password
   - Use this in `.env` for `EMAIL_PASSWORD`

3. **Test Connection**:
   ```bash
   python src/email_notifier.py
   ```

### 3. Configure via Dashboard

Launch the dashboard and go to **Email Settings** tab:

```bash
streamlit run dashboard.py
```

- Test your SMTP connection
- Set alert threshold
- Configure weekly report schedule
- Input recipient email addresses
- Send test alert

### 4. Run Background Server

Start the email notification server:

```bash
python src/email_server.py
```

The server will:
- Monitor `data/outputs/alerts.csv` for new attacks
- Send email alerts when attacks exceed threshold
- Send weekly summary every configured day/time

### 5. Alternative: Run with Flask API

For REST API support (optional):

```bash
python src/email_api.py
```

Then send alerts programmatically:

```bash
# Send immediate alert
curl -X POST http://localhost:5000/alert \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "attack_data": {
      "Source IP": "192.168.1.100",
      "Attack Type": "SMB Exploit"
    },
    "confidence": 85.5
  }'

# Send weekly report
curl -X POST http://localhost:5000/weekly-report \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com"
  }'
```

## File Structure

```
NetPulse-Shield/
├── .env                          # Email configuration (create from .env.example)
├── .env.example                  # Template file
├── src/
│   ├── email_notifier.py        # Core email sending functionality
│   ├── email_scheduler.py       # Scheduler for weekly reports
│   ├── email_server.py          # Background monitoring service
│   ├── email_api.py             # Optional Flask REST API
│   └── detector.py              # Generates alerts.csv
├── data/
│   └── outputs/
│       └── alerts.csv           # Attack alerts (monitored by server)
└── dashboard.py                 # UI with email configuration
```

## Usage Examples

### Python Integration

```python
from src.email_notifier import EmailNotifier

notifier = EmailNotifier()

# Send alert
attack_data = {
    "Source IP": "192.168.1.100",
    "Attack Type": "DDoS",
    "Duration": "5 seconds"
}

notifier.send_alert("admin@example.com", attack_data, confidence=85.0)

# Send weekly summary
import pandas as pd
alerts_df = pd.read_csv("data/outputs/alerts.csv")
notifier.send_weekly_summary("admin@example.com", alerts_df)

# Test connection
notifier.test_connection()
```

### Detector Integration

The detector automatically logs attacks to `alerts.csv`. The email server monitors this file and sends notifications.

```python
from src.detector import NetworkAnomalyDetector
from src.email_notifier import EmailNotifier

detector = NetworkAnomalyDetector()
detector.train(X_train, y_train)

# Predictions trigger alerts
predictions = detector.predict(X_test)
alerts = detector.get_alerts(predictions)  # Returns alerts.csv

# Email server will pick up new alerts automatically
```

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EMAIL_SENDER` | - | Sender email address |
| `EMAIL_PASSWORD` | - | SMTP password or app password |
| `EMAIL_SMTP_SERVER` | smtp.gmail.com | SMTP server address |
| `EMAIL_SMTP_PORT` | 587 | SMTP port (usually 587 for TLS) |
| `ATTACK_THRESHOLD_PERCENTAGE` | 80 | Alert threshold (%) |
| `RECEIVER_EMAIL` | - | Where to send alerts |
| `WEEKLY_REPORT_DAY` | 0 | Day of week (0=Mon, 6=Sun) |
| `WEEKLY_REPORT_TIME` | 09:00 | Time for weekly report |
| `EMAIL_CHECK_INTERVAL` | 60 | Seconds between alert checks |

## Troubleshooting

### Gmail: "Invalid login credentials"

- Verify **App Password** (not main password)
- Check 2-Step Verification is enabled
- Regenerate app password if needed

### "Connection refused"

- Check SMTP server and port
- Verify firewall allows outgoing email (usually port 587)
- Test with telnet: `telnet smtp.gmail.com 587`

### No emails received

- Check spam/junk folder
- Verify recipient email in `.env`
- Run `python src/email_notifier.py` to test
- Check email server is running: `python src/email_server.py`

### Alerts not being detected

- Verify `alerts.csv` exists at `data/outputs/alerts.csv`
- Run detector: `python src/detector.py`
- Check alert confidence exceeds threshold
- Check `ATTACK_THRESHOLD_PERCENTAGE` in `.env`

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Detector Pipeline                       │
│  clean_data.py → detector.py → alerts.csv               │
└──────────────────────────┬────────────────────────────────┘
                           │
                           ↓
                    ┌──────────────────┐
                    │  Email Server    │
                    │  (monitoring)    │
                    └────────┬─────────┘
                             │
                ┌────────────┼────────────┐
                ↓            ↓            ↓
        Test Connection  Send Alert  Weekly Report
                │            │            │
                └────────────┴────────────┘
                             │
                             ↓
                    ┌──────────────────┐
                    │  SMTP Server     │
                    │  (gmail, etc)    │
                    └────────┬─────────┘
                             │
                             ↓
                    📧 User Inbox 📧
```

## Performance & Monitoring

### Running as System Service (Linux/Mac)

Create systemd service:

```bash
# /etc/systemd/system/netpulse-email.service
[Unit]
Description=NetPulse-Shield Email Notification Server
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/NetPulse-Shield
ExecStart=/usr/bin/python3 src/email_server.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable netpulse-email
sudo systemctl start netpulse-email
sudo systemctl status netpulse-email
```

### Windows Service

Use NSSM (Non-Sucking Service Manager):
```bash
nssm install NetPulseEmail "C:\\Python\\python.exe" "C:\\path\\to\\src\\email_server.py"
nssm start NetPulseEmail
```

## Security Best Practices

⚠️ **Never commit `.env` to Git!**

1. Add to `.gitignore`:
   ```
   .env
   ```

2. Use environment-specific configs:
   - `.env.development`
   - `.env.production`

3. Rotate app passwords regularly

4. Use strong, unique receiver emails

5. Audit email logs periodically

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review `.env` configuration
3. Enable debug logging (modify email_server.py)
4. Check alert data in `data/outputs/alerts.csv`

## License

Same as NetPulse-Shield main project.
