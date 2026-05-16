# Quick Start Guide - Email Notifications

## 5-Minute Setup

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure Email (.env file)

**For Gmail:**

```bash
# Copy template
cp .env.example .env
```

Edit `.env`:
```
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-16-char-app-password
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
RECEIVER_EMAIL=admin@company.com
ATTACK_THRESHOLD_PERCENTAGE=80
WEEKLY_REPORT_DAY=0
WEEKLY_REPORT_TIME=09:00
```

**Gmail Setup:**
1. Go to https://myaccount.google.com/security
2. Enable "2-Step Verification"
3. Go to https://myaccount.google.com/apppasswords
4. Generate app password for Mail
5. Copy 16-character password to `.env`

**Other Providers:**
- **Outlook:** `smtp.office365.com:587`
- **Yahoo:** `smtp.mail.yahoo.com:587`

### Step 3: Run Dashboard
```bash
streamlit run dashboard.py
```

Go to **Email Settings** tab and:
- ✅ Test connection
- ✅ Set alert threshold
- ✅ Configure weekly report
- ✅ Send test alert

### Step 4: Start Email Server
In a new terminal:
```bash
python src/email_server.py
```

The server will monitor for attacks and send emails automatically.

## Usage

### Dashboard Configuration
- Open http://localhost:8501
- Click **Email Settings** tab
- Enter recipient email
- Set threshold (e.g., 80%)
- Configure weekly report schedule
- Click "Save Settings"

### Command Line
```bash
# Test email setup
python src/email_notifier.py

# Start monitoring server
python src/email_server.py

# Optional: REST API (separate terminal)
python src/email_api.py
```

### API Requests (if using Flask)
```bash
# Send alert
curl -X POST http://localhost:5000/alert \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "attack_data": {"Type": "DDoS", "Source": "192.168.1.1"},
    "confidence": 85
  }'

# Check health
curl http://localhost:5000/health
```

## What You Get

✅ **Real-time Alerts**
- Email sent instantly when attack detected above threshold
- Formatted with attack details

✅ **Weekly Summary**
- Statistics: total attacks, high-risk count, average confidence
- Lists top 10 recent attacks
- Sent on configured day/time

✅ **Configurable**
- Adjust threshold (0-100%)
- Change recipient email anytime
- Support multiple email providers

✅ **Background Service**
- Runs independently of dashboard
- Monitors alerts automatically
- Sends weekly reports on schedule

## Files Created

```
├── .env                          # Your email configuration (SECRET!)
├── .env.example                  # Template (safe to commit)
├── docs/EMAIL_NOTIFICATIONS.md   # Full documentation
├── src/
│   ├── email_notifier.py        # Core email functionality
│   ├── email_scheduler.py       # Weekly report scheduler
│   ├── email_server.py          # Background monitoring service
│   └── email_api.py             # Optional Flask REST API
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Connection refused" | Check SMTP server/port, verify firewall allows port 587 |
| "Invalid credentials" | Regenerate app password (for Gmail), check .env |
| No emails received | Check spam folder, verify recipient email in .env |
| Alerts not detected | Run `python src/detector.py` first, check threshold |

## Next Steps

1. **Run detector** to generate alerts:
   ```bash
   python src/detector.py
   ```

2. **Start email server**:
   ```bash
   python src/email_server.py
   ```

3. **Monitor dashboard**:
   ```bash
   streamlit run dashboard.py
   ```

4. **Check emails** when attacks are detected!

## Advanced Configuration

### Environment Variables

```
# Core Email
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587

# Alert Settings
ATTACK_THRESHOLD_PERCENTAGE=80    # Alert threshold
RECEIVER_EMAIL=admin@example.com

# Weekly Report
WEEKLY_REPORT_DAY=0               # 0=Mon, 6=Sun
WEEKLY_REPORT_TIME=09:00          # HH:MM

# Server
EMAIL_CHECK_INTERVAL=60           # Seconds between checks
```

### Multiple Recipients

Edit `.env`:
```
RECEIVER_EMAIL=admin@example.com,security@example.com,ciso@example.com
```

Then update email_server.py to handle multiple emails:
```python
emails = os.getenv("RECEIVER_EMAIL", "").split(",")
for email in emails:
    notifier.send_alert(email.strip(), attack_data, confidence)
```

## Support

📖 Full docs: See `docs/EMAIL_NOTIFICATIONS.md`
🐛 Issues: Check troubleshooting section above
💡 Questions: Review code comments in `src/email_notifier.py`

---

**Security Note:** Never commit `.env` to Git! It's already in `.gitignore`.
