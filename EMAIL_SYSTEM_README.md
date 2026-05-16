# Email Notification System - Summary

## ✅ What Was Implemented

A complete **email notification system** for NetPulse-Shield that:

### Core Features
- 📧 **Real-time Attack Alerts** - Sends email when attacks exceed 80% confidence threshold
- 📊 **Weekly Summary Reports** - Automated digest of all detected attacks
- ⚙️ **Easy Configuration** - Dashboard UI + .env file support
- 🔄 **Background Service** - Runs independently to monitor attacks
- 🌐 **REST API** (Optional) - Flask endpoints for programmatic access
- 🔐 **Multi-provider Support** - Gmail, Outlook, Yahoo, custom SMTP

### Files Created

**Core Modules** (in `src/`):
- `email_notifier.py` - SMTP email sending
- `email_scheduler.py` - Weekly report scheduling
- `email_server.py` - Background monitoring service
- `email_api.py` - Optional Flask REST API

**Configuration**:
- `.env.example` - Configuration template
- `.env` - Your actual config (created from template, not in Git)

**Documentation**:
- `QUICKSTART_EMAIL.md` - 5-minute setup guide
- `INTEGRATION_GUIDE.md` - Comprehensive integration manual
- `docs/EMAIL_NOTIFICATIONS.md` - Full reference documentation

**Testing & Validation**:
- `test_email_setup.py` - Automated validation script

**Dashboard Enhancement**:
- New "Email Settings" page in `dashboard.py`
- SMTP configuration interface
- Email recipient input
- Test alert functionality
- Alert threshold configuration

**Dependencies**:
- Updated `requirements.txt` with email packages:
  - `python-dotenv` - Environment variables
  - `schedule` - Task scheduling
  - `flask` - REST API (optional)

## 🚀 Quick Start (5 Minutes)

### 1. Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Create config
cp .env.example .env
```

### 2. Configure (Edit .env)
```env
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password      # Gmail: 16-char App Password
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
RECEIVER_EMAIL=admin@company.com
ATTACK_THRESHOLD_PERCENTAGE=80
```

### 3. Test
```bash
python test_email_setup.py
```

### 4. Run
```bash
# Terminal 1: Start email server
python src/email_server.py

# Terminal 2: Run detector (generates alerts)
python src/detector.py

# Terminal 3: View dashboard & configure
streamlit run dashboard.py
```

## 📧 How It Works

```
Detection Pipeline:
┌──────────────────┐
│   detector.py    │
│ (generates       │
│  alerts.csv)     │
└────────┬─────────┘
         │
         ↓
┌──────────────────────┐
│ email_server.py      │
│ (monitors for new    │
│  attacks)            │
└────────┬─────────────┘
         │
         ├→ Confidence > 80%?
         │  YES ↓
         │  SEND ALERT
         │
         └→ Weekly schedule?
            YES ↓
            SEND SUMMARY

Email Format:
┌──────────────────────────────────┐
│ 🚨 Security Alert                │
│ Confidence: 85%                  │
│ Source IP: 192.168.1.100        │
│ Attack Type: SMB Exploit         │
│ Time: 2024-01-15 10:23:45       │
└──────────────────────────────────┘
```

## 🎯 Key Features

### Real-time Alerts
- Sent **immediately** when attack detected above threshold
- HTML formatted with attack details
- Includes: Source IP, Port, Protocol, Attack Type, Confidence, etc.

### Weekly Reports
- Sent every **Monday at 9:00 AM** (configurable)
- Statistics: Total attacks, high-risk count, average confidence
- Recent top 10 attacks listed

### Configurable Threshold
- Default: 80% confidence
- Adjustable via dashboard slider (0-100%)
- Prevents alert fatigue from low-confidence detections

### Multi-Provider Support
- **Gmail**: Use App Password (recommended)
- **Outlook**: office365.com:587
- **Yahoo**: mail.yahoo.com:587
- **Custom**: Any SMTP server

## 📊 Dashboard Integration

New "Email Settings" page includes:

✅ SMTP Configuration
- Email sender address
- Password / App password
- SMTP server
- SMTP port
- Connection test button

✅ Alert Settings
- Confidence threshold slider
- Enable/disable real-time alerts

✅ Weekly Report
- Day selector (Monday-Sunday)
- Time picker (HH:MM)

✅ Recipient Configuration
- Email address input
- Test alert button

✅ Setup Instructions
- Gmail step-by-step guide
- Other provider details
- Troubleshooting tips

## 🔧 Configuration Reference

### .env Variables

```
# Email Sender (Required)
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587

# Alert Settings
ATTACK_THRESHOLD_PERCENTAGE=80

# Recipient (Set via dashboard or .env)
RECEIVER_EMAIL=admin@company.com

# Weekly Report
WEEKLY_REPORT_DAY=0                # 0=Mon, 6=Sun
WEEKLY_REPORT_TIME=09:00           # HH:MM

# Server
EMAIL_CHECK_INTERVAL=60            # Seconds between checks
```

## 📱 API Endpoints (Optional)

If running `python src/email_api.py`:

```bash
# Send alert
POST /alert
{
  "email": "admin@example.com",
  "attack_data": {"Type": "DDoS"},
  "confidence": 85
}

# Send weekly report
POST /weekly-report
{"email": "admin@example.com"}

# Test connection
POST /test-connection

# Get config
GET /config

# Health check
GET /health
```

## ✨ Gmail Setup Steps

1. Go to https://myaccount.google.com/security
2. Enable "2-Step Verification"
3. Go to https://myaccount.google.com/apppasswords
4. Select "Mail" and "Windows Computer"
5. Copy 16-character password
6. Use in `.env` for EMAIL_PASSWORD

## 🧪 Validation

Run the test script to verify everything:

```bash
python test_email_setup.py
```

Checks:
- Package imports
- .env configuration
- Email connection
- Directory structure
- Email modules
- Dashboard
- Alerts file

## 📚 Documentation

Three documentation files provided:

1. **QUICKSTART_EMAIL.md** (5 min read)
   - Fast setup
   - Gmail instructions
   - Basic examples

2. **INTEGRATION_GUIDE.md** (15 min read)
   - Complete overview
   - Step-by-step setup
   - Configuration examples
   - Feature breakdown
   - API reference

3. **docs/EMAIL_NOTIFICATIONS.md** (30 min read)
   - Full reference
   - All email providers
   - Troubleshooting
   - Architecture diagrams
   - System services setup

## 🛡️ Security

⚠️ **Important**: Never commit `.env` to Git!
- Already in `.gitignore`
- Contains passwords and credentials
- Keep backups of .env locally

🔒 Best Practices:
- Use separate email account for alerts
- Use App Passwords (not main password)
- Rotate credentials regularly
- Review email logs periodically

## 🔍 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Invalid credentials" | For Gmail: regenerate App Password |
| "Connection timeout" | Check SMTP server/port, verify firewall |
| "No emails received" | Check spam folder, verify recipient |
| "Alerts not detected" | Run detector first, check threshold |

## 📋 Next Steps

1. **Immediate**
   ```bash
   cp .env.example .env
   # Edit .env with your email credentials
   python test_email_setup.py
   ```

2. **Short Term**
   ```bash
   python src/detector.py         # Generate alerts
   python src/email_server.py     # Start monitoring
   streamlit run dashboard.py     # View dashboard
   ```

3. **Long Term**
   - Setup as system service
   - Configure multiple recipients
   - Adjust threshold based on your network
   - Monitor email logs

## 📞 Support

- **Quick Help**: QUICKSTART_EMAIL.md
- **Full Docs**: INTEGRATION_GUIDE.md & docs/EMAIL_NOTIFICATIONS.md
- **Test Setup**: `python test_email_setup.py`
- **Code Comments**: Review source code in `src/email_*.py`

---

**Status**: ✅ Production Ready
**Version**: 1.0
**License**: Same as NetPulse-Shield
