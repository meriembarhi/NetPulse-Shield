# Email Notification System - Integration Guide

## What Has Been Added

### 1. Core Email Modules

**`src/email_notifier.py`** - Main email functionality
- Sends individual attack alerts
- Sends weekly summary reports
- SMTP connection management
- HTML formatted emails

**`src/email_scheduler.py`** - Scheduling system
- Schedules weekly reports
- Background thread management
- Configurable day/time

**`src/email_server.py`** - Background monitoring service
- Monitors `alerts.csv` for new attacks
- Sends real-time alerts when threshold exceeded
- Auto-detects new alerts
- Runs independently

**`src/email_api.py`** (Optional) - REST API
- Flask endpoints for email operations
- Programmatic alert sending
- Health checks and configuration endpoints

### 2. Configuration Files

**`.env.example`** - Template configuration
```env
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
ATTACK_THRESHOLD_PERCENTAGE=80
RECEIVER_EMAIL=admin@company.com
WEEKLY_REPORT_DAY=0
WEEKLY_REPORT_TIME=09:00
```

**`.env`** - Your actual configuration (created from .env.example, NOT in Git)

### 3. Dashboard Integration

**Enhanced `dashboard.py`**
- New "Email Settings" page with full UI
- SMTP configuration interface
- Email recipient input
- Test connection button
- Send test alert button
- Alert threshold slider
- Weekly report schedule selector
- Setup instructions

### 4. Documentation

**`docs/EMAIL_NOTIFICATIONS.md`** - Full reference guide
- Feature overview
- Setup instructions for multiple email providers
- Configuration reference
- Troubleshooting guide
- Architecture diagrams

**`QUICKSTART_EMAIL.md`** - Quick setup (5 minutes)
- Fast installation steps
- Gmail setup instructions
- Basic usage examples

## How It Works

```
Attack Detection Flow:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Detector generates alerts.csv
                    ↓
2. Email server monitors alerts.csv
                    ↓
3. Server checks confidence > threshold?
                    ↓
          YES ↙      ↘ NO
        Send Alert   Skip
            ↓
4. Email sent to recipient
```

## Getting Started (Step by Step)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `python-dotenv` - Environment variables
- `schedule` - Task scheduling
- `flask` - Optional REST API
- `streamlit` - Dashboard (already in project)

### Step 2: Create .env Configuration

```bash
# Copy template
cp .env.example .env

# Edit with your email provider credentials
# For Gmail: use App Password (16 chars), not main password
```

### Step 3: Configure Email

**Option A: Via Dashboard**

```bash
streamlit run dashboard.py
```

Then navigate to "Email Settings" page:
1. Enter SMTP configuration
2. Click "Test Connection"
3. Set alert threshold (e.g., 80%)
4. Configure weekly report schedule
5. Enter recipient email
6. Click "Save Settings"
7. Send test alert to verify

**Option B: Via .env File**

Edit `.env` directly:

```env
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-16-char-app-password
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
ATTACK_THRESHOLD_PERCENTAGE=80
RECEIVER_EMAIL=admin@yourcompany.com
WEEKLY_REPORT_DAY=0
WEEKLY_REPORT_TIME=09:00
```

### Step 4: Run Email Server

```bash
# Terminal 1: Start email notification server
python src/email_server.py
```

This will:
- Check email configuration
- Test SMTP connection
- Start monitoring `data/outputs/alerts.csv`
- Send alerts automatically
- Send weekly reports on schedule

### Step 5: Run Detection

In another terminal:

```bash
# Terminal 2: Run anomaly detection
python src/detector.py
```

This generates `data/outputs/alerts.csv` which the email server monitors.

### Step 6: View Results

In third terminal:

```bash
# Terminal 3: View dashboard
streamlit run dashboard.py
```

Visit http://localhost:8501 and monitor:
- Detection results
- Alerts generated
- Email notification status

## Configuration Examples

### Gmail

```env
EMAIL_SENDER=john.doe@gmail.com
EMAIL_PASSWORD=abcd efgh ijkl mnop      # 16-char App Password
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
```

Steps:
1. Enable 2FA at https://myaccount.google.com/security
2. Generate App Password at https://myaccount.google.com/apppasswords
3. Use the 16-character password in `.env`

### Microsoft Outlook

```env
EMAIL_SENDER=john@company.onmicrosoft.com
EMAIL_PASSWORD=YourPassword
EMAIL_SMTP_SERVER=smtp.office365.com
EMAIL_SMTP_PORT=587
```

### Self-Hosted or Corporate

```env
EMAIL_SENDER=security@internal.company
EMAIL_PASSWORD=your-password
EMAIL_SMTP_SERVER=mail.internal.company
EMAIL_SMTP_PORT=25
```

## Features Breakdown

### Real-time Attack Alerts

When `detector.py` creates an alert with confidence ≥ threshold:

```
Email Subject: 🚨 Security Alert: Attack Detected - 85.50% Confidence

Email Body (HTML formatted):
┌─────────────────────────────────────┐
│ Alert Time: 2024-01-15 10:23:45     │
│ Confidence: 85.50%                  │
│                                     │
│ Attack Details:                     │
│ • Source IP: 192.168.1.100         │
│ • Destination IP: 10.0.0.1         │
│ • Port: 445                         │
│ • Protocol: TCP                     │
│ • Attack Type: SMB Exploit          │
│ • Sload: 1250 bytes/s              │
└─────────────────────────────────────┘
```

### Weekly Summary Report

Every Monday at 09:00 (configurable):

```
Email Subject: 📊 NetPulse-Shield Weekly Security Report - 2024-01-15

Email Body (HTML formatted):
┌──────────────────────────────────────────────────┐
│           Weekly Security Summary                 │
│                                                   │
│ Total Attacks: 42                                 │
│ High Confidence (≥80%): 15                       │
│ Average Confidence: 73.5%                         │
│                                                   │
│ Report Period: 2024-01-08 to 2024-01-15         │
│                                                   │
│ Recent High-Confidence Attacks:                  │
│ • 2024-01-15 09:15 - DDoS (89.2%)               │
│ • 2024-01-15 08:42 - Port Scan (85.1%)         │
│ • 2024-01-15 07:30 - SMB Exploit (82.3%)       │
└──────────────────────────────────────────────────┘
```

### Threshold Configuration

```
Threshold = 80%
┌─────────────────────────────────────┐
│ Attack Detected                     │
│ Confidence: 85% ✅ → SEND ALERT     │
│ Confidence: 75% ❌ → SKIP            │
│ Confidence: 45% ❌ → SKIP            │
└─────────────────────────────────────┘
```

## API Endpoints (Optional - Flask)

If running `python src/email_api.py`:

### POST /alert

Send attack alert email:

```bash
curl -X POST http://localhost:5000/alert \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "attack_data": {
      "Source IP": "192.168.1.100",
      "Attack Type": "DDoS",
      "Duration": "5 seconds"
    },
    "confidence": 85.5
  }'
```

Response:
```json
{
  "success": true,
  "message": "Alert sent",
  "confidence": 85.5,
  "threshold": 80
}
```

### POST /weekly-report

Send weekly summary:

```bash
curl -X POST http://localhost:5000/weekly-report \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com"}'
```

### POST /test-connection

Test SMTP configuration:

```bash
curl -X POST http://localhost:5000/test-connection
```

### GET /config

Get current configuration:

```bash
curl http://localhost:5000/config
```

### GET /health

Health check:

```bash
curl http://localhost:5000/health
```

## File Structure After Setup

```
NetPulse-Shield/
├── .env                              # ✨ NEW - Your config (SECRET!)
├── .env.example                      # ✨ NEW - Template
├── QUICKSTART_EMAIL.md               # ✨ NEW - Quick guide
├── requirements.txt                  # UPDATED - Added dependencies
├── dashboard.py                      # UPDATED - Added Email Settings page
├── docs/
│   ├── EMAIL_NOTIFICATIONS.md       # ✨ NEW - Full documentation
│   └── remediation_knowledge.txt
├── src/
│   ├── __init__.py
│   ├── email_notifier.py            # ✨ NEW - Core email
│   ├── email_scheduler.py           # ✨ NEW - Scheduling
│   ├── email_server.py              # ✨ NEW - Background service
│   ├── email_api.py                 # ✨ NEW - Optional REST API
│   ├── detector.py                  # UNCHANGED - Works with email
│   ├── auto_remediator.py
│   ├── advisor.py
│   ├── remediator.py
│   ├── solver.py
│   ├── clean_data.py
│   ├── knowledge_base.py
│   └── embeddings.py
└── data/
    └── outputs/
        └── alerts.csv               # Generated by detector, monitored by email_server
```

## Troubleshooting Checklist

- [ ] `.env` file created with SMTP credentials
- [ ] Email credentials are correct (test with `python src/email_notifier.py`)
- [ ] Gmail users: Using 16-char App Password, not main password
- [ ] Port 587 or your SMTP port is accessible (check firewall)
- [ ] Recipient email address is valid
- [ ] `detector.py` has been run to generate `alerts.csv`
- [ ] Email server is running (`python src/email_server.py`)
- [ ] Attack confidence exceeds threshold (default 80%)
- [ ] Check spam/junk folder for emails
- [ ] No `.env` changes needed after first setup

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Invalid login credentials" | For Gmail: regenerate App Password, verify 2FA enabled |
| "Connection timeout" | Check SMTP server address and port, verify firewall |
| "No emails received" | Check spam folder, verify recipient in `.env`, check threshold |
| "Emails sent but empty" | Check alert data in `alerts.csv`, verify detector ran |
| "Weekly report not sent" | Verify WEEKLY_REPORT_DAY/TIME in `.env`, check server running |

## Next Steps

1. **Immediate**
   - [ ] Copy `.env.example` to `.env`
   - [ ] Fill in email credentials
   - [ ] Test with `streamlit run dashboard.py` → Email Settings
   - [ ] Send test alert

2. **Short Term**
   - [ ] Run `python src/detector.py` to generate alerts
   - [ ] Start `python src/email_server.py` in background
   - [ ] Monitor dashboard for alerts
   - [ ] Verify emails are received

3. **Long Term**
   - [ ] Set up email server as system service (systemd/Windows Service)
   - [ ] Configure multiple recipients
   - [ ] Adjust threshold based on your network baseline
   - [ ] Monitor email logs

## Security Notes

⚠️ **CRITICAL: Never commit `.env` to Git!**
- It contains passwords and credentials
- Already in `.gitignore` - use it!
- Use environment-specific configs in production

🔒 **Best Practices:**
- Use strong, unique email passwords
- Rotate app passwords regularly
- Use separate email account for alerts (not personal email)
- Implement rate limiting for very noisy networks
- Review email logs periodically

## Support

📖 **Documentation**: See `docs/EMAIL_NOTIFICATIONS.md` and `QUICKSTART_EMAIL.md`

🐛 **Debugging**: Run `python src/email_notifier.py` to test configuration

💬 **Questions**: Review code comments in email modules

---

**Version**: 1.0  
**Last Updated**: 2024-01-15  
**Status**: ✅ Production Ready
