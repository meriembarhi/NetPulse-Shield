# SIEM Integration Quick Reference

## 📋 What Gets Sent to SIEM
```json
{
  "source": "NetPulse-Shield",
  "timestamp": "2026-05-07T10:30:00Z",
  "alert_id": 123,
  "severity": "high",
  "anomaly_score": -0.95,
  "source_ip": "10.0.0.5",
  "destination_ip": "10.0.0.20",
  "attack_type": "DDoS",
  "description": "Suspicious traffic pattern",
  "advice": "Block source IP"
}
```

## 🎯 Simple Step-by-Step (TL;DR)

### Step 1: Create webhook.py
```python
# webhook.py - Send alerts to SIEM

import json
import urllib.request
import logging

logger = logging.getLogger(__name__)

def send_alert_via_webhook(alert, webhook_url=None, advice=None):
    """Send alert to SIEM via HTTP POST"""
    
    if not webhook_url:
        return False
    
    # Build JSON
    payload = {
        "source": "NetPulse-Shield",
        "timestamp": alert.get("timestamp"),
        "alert_id": alert.get("alert_id"),
        "severity": alert.get("severity", "medium"),
        "anomaly_score": alert.get("anomaly_score"),
        "source_ip": alert.get("source_ip"),
        "destination_ip": alert.get("destination_ip"),
        "attack_type": alert.get("attack_type"),
        "description": alert.get("description"),
        "advice": advice
    }
    
    body = json.dumps(payload).encode("utf-8")
    
    # Send HTTP POST
    try:
        request = urllib.request.Request(
            webhook_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(request, timeout=5) as response:
            if 200 <= response.status < 300:
                logger.info("Alert sent to SIEM")
                return True
    except Exception as e:
        logger.warning(f"SIEM send failed: {e}")
    
    return False
```

### Step 2: Update pipeline.py
```python
# At top of pipeline.py, add:
from webhook import send_alert_via_webhook
import os

# In generate_remediation_report(), add:
webhook_url = os.getenv("NETPULSE_WEBHOOK_URL")

# Inside the loop, after getting advice:
alert_payload = row.to_dict()
alert_payload["advice"] = advice
send_alert_via_webhook(alert_payload, webhook_url=webhook_url, advice=advice)
```

### Step 3: Configure SIEM
```bash
# PowerShell:
$env:NETPULSE_WEBHOOK_URL = "http://localhost:9200/netpulse-alerts"

# Or Linux/Mac:
export NETPULSE_WEBHOOK_URL="http://localhost:9200/netpulse-alerts"
```

### Step 4: Start SIEM
```bash
# Elasticsearch + Kibana (Docker):
docker run -d -p 9200:9200 -e "discovery.type=single-node" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0

docker run -d -p 5601:5601 \
  docker.elastic.co/kibana/kibana:8.11.0
```

### Step 5: Run & Verify
```bash
# Run pipeline:
python pipeline.py

# Check Kibana:
# Open http://localhost:5601
# Go to Discover → Select "netpulse-alerts" index
# Should see alerts!
```

## 🧪 Testing Without SIEM

```bash
# Use webhook.site (free, instant):
$env:NETPULSE_WEBHOOK_URL = "https://webhook.site/your-unique-url"
python pipeline.py

# Check webhook.site - alerts appear in real-time!
```

## ❌ Common Mistakes (Don't Do These!)

| Mistake | Problem | Solution |
|---------|---------|----------|
| Crash if webhook fails | Pipeline breaks | Always return False, never crash |
| Send before advice ready | Data incomplete | Send AFTER advice generation |
| Synchronous only | Blocks on SIEM delay | Use timeout, handle gracefully |
| Bad JSON format | SIEM rejects | Validate JSON before sending |
| No error handling | Silent failures | Log all errors, don't crash |
| Hardcoded SIEM URL | Not flexible | Use environment variables |
| No timeout | Hangs forever | Set 5-10 second timeout |

## 📊 SIEM Platform URLs

| Platform | Endpoint | Port | Index |
|----------|----------|------|-------|
| Elasticsearch | http://host:9200 | 9200 | /netpulse-alerts |
| Wazuh | http://host:55000 | 55000 | /alerts |
| Splunk | http://host:8088 | 8088 | /services/collector |
| Generic | http://host:port/path | varies | varies |

## 🔍 Debug Checklist

```
When alerts aren't appearing in SIEM:

1. [ ] Is SIEM running?
   - curl http://siem-url (should respond)

2. [ ] Is webhook configured?
   - echo $env:NETPULSE_WEBHOOK_URL (should show URL)

3. [ ] Is NetPulse sending?
   - Check logs for "Alert sent to SIEM"

4. [ ] Is SIEM receiving?
   - Check SIEM logs for POST requests

5. [ ] Is JSON valid?
   - Use webhook.site to see actual JSON

6. [ ] Is URL correct?
   - curl the URL manually to test

7. [ ] Is firewall blocking?
   - Check firewall allows connection
```

## 💾 Environment Variables

```bash
# Required:
NETPULSE_WEBHOOK_URL = "http://your-siem:9200/alerts"

# Optional:
NETPULSE_WEBHOOK_TIMEOUT = "5"        # seconds
NETPULSE_WEBHOOK_BATCH_SIZE = "100"   # alerts per batch
NETPULSE_WEBHOOK_RETRY = "true"       # retry on failure
```

## 🎓 Before You Start Coding

**You should understand:**
1. What is HTTP POST? → Sending data to server
2. What is JSON? → Text format for data
3. What is webhook? → URL that receives data
4. What is error handling? → Don't crash on failures
5. What is logging? → Print messages for debugging

**You should have:**
1. NetPulse-Shield running
2. Python 3.10+ installed
3. A SIEM chosen (or webhook.site for testing)
4. 30 minutes of time
5. Patience and curiosity!

## 📖 Reading Order

1. **First:** SIEM_INTEGRATION_GUIDE.md (full guide - THIS FILE)
2. **Then:** Phase 1 only (understanding concepts)
3. **Then:** Phase 2 (write webhook.py)
4. **Test with:** webhook.site
5. **Then:** Phase 3 (integrate with pipeline)
6. **Test with:** Real SIEM
7. **Then:** Phases 4-5 (dashboard + async)
8. **Finally:** Phases 6-7 (testing + docs)

## ⏱️ Time Estimate

| Phase | Time | Difficulty |
|-------|------|-----------|
| Phase 1: Understanding | 30 min | Easy |
| Phase 2: Webhook Code | 45 min | Medium |
| Phase 3: Pipeline Integration | 20 min | Easy |
| Phase 4: Dashboard | 30 min | Medium |
| Phase 5: Async | 15 min | Medium |
| Phase 6: Testing | 30 min | Easy |
| Phase 7: Docs | 20 min | Easy |
| **Total** | **3 hours** | **Medium** |

## 🆘 Where to Get Help

1. **Webhook errors?** Check Phase 2.3 (error handling)
2. **Integration questions?** Check Phase 3 (pipeline)
3. **SIEM setup issues?** Check Phase 6.2 (SIEM testing)
4. **Troubleshooting?** Check the guide's troubleshooting section
5. **Stuck?** Re-read Phase 1 (understanding)

---

**Pro Tip:** Print this page! Keep it as a reference while coding.
