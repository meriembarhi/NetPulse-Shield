# SIEM Integration Guide for NetPulse-Shield
## Complete Beginner's Guide

---

## 📖 What is SIEM and Why Integrate It?

### What is SIEM?
**SIEM = Security Information and Event Management**

Think of SIEM as a **security control center** that:
- **Collects** alerts from multiple sources (like NetPulse-Shield)
- **Stores** them in a centralized database
- **Analyzes** them to find patterns and threats
- **Visualizes** security data on dashboards
- **Responds** to incidents automatically

### Why Integrate SIEM with NetPulse-Shield?

**Without SIEM:**
- Alerts stay only in CSV files or local database
- Hard to search/analyze trends
- No real-time monitoring across systems
- Manual effort to investigate incidents

**With SIEM:**
- All alerts flow to a central location
- Real-time dashboards and searches
- Automated correlation of events
- Historical analysis of attack patterns
- Easy compliance reporting

### How Does NetPulse Send Data to SIEM?

```
NetPulse Detects Anomaly
    ↓
Creates Alert Object
    ↓
Formats Alert as JSON (standardized format)
    ↓
Sends JSON via HTTP POST (webhook)
    ↓
SIEM Receives and Stores
    ↓
SIEM Displays on Dashboard
```

---

## 🏗️ Architecture Overview

### Current NetPulse Structure
```
pipeline.py → Detect Anomalies → Save to alerts.csv + SQLite
               ↓
           dashboard.py → Show on Streamlit UI
```

### After SIEM Integration
```
pipeline.py → Detect Anomalies → Save to alerts.csv + SQLite
               ↓
            FORMAT AS JSON (webhook payload)
               ↓
            SEND VIA HTTP POST
               ↓
            SIEM (Elasticsearch/Splunk/Wazuh)
               ↓
            SIEM Dashboard & Analysis
```

---

## 📋 Detailed To-Do List for SIEM Integration

### Phase 1: Understanding (Before Coding)
- [ ] **Task 1.1:** Choose Your SIEM Platform
- [ ] **Task 1.2:** Understand HTTP Webhooks
- [ ] **Task 1.3:** Set Up SIEM Locally (Optional)

### Phase 2: Create Webhook Module
- [ ] **Task 2.1:** Create webhook.py (Alert Formatter)
- [ ] **Task 2.2:** Implement Alert Payload Builder
- [ ] **Task 2.3:** Implement HTTP Sender

### Phase 3: Integrate with Pipeline
- [ ] **Task 3.1:** Import webhook in pipeline.py
- [ ] **Task 3.2:** Add webhook configuration variables
- [ ] **Task 3.3:** Call webhook after each alert detection

### Phase 4: Integrate with Dashboard
- [ ] **Task 4.1:** Add webhook config UI
- [ ] **Task 4.2:** Show SIEM connection status
- [ ] **Task 4.3:** Add manual alert forwarding button

### Phase 5: Integrate with Async Tasks
- [ ] **Task 5.1:** Send webhook from background workers

### Phase 6: Testing & Validation
- [ ] **Task 6.1:** Test locally with mock SIEM
- [ ] **Task 6.2:** Test with real SIEM
- [ ] **Task 6.3:** Verify data appears in SIEM UI

### Phase 7: Documentation & Deployment
- [ ] **Task 7.1:** Document configuration
- [ ] **Task 7.2:** Create setup guide for users
- [ ] **Task 7.3:** Add troubleshooting section

---

## 🎯 Detailed Explanation of Each Task

### **Phase 1: Understanding (Before Coding)**

#### **Task 1.1: Choose Your SIEM Platform**

**What is this?**
You need to pick a SIEM system to receive the alerts. Different SIEM systems have different requirements.

**Popular SIEM Options for Beginners:**

1. **Elasticsearch Stack (ELK)** ⭐ Recommended for beginners
   - Free, open-source
   - Easy to set up locally
   - Good documentation
   - Perfect for learning
   - Components: Elasticsearch (storage) + Logstash (processor) + Kibana (UI)

2. **Wazuh**
   - Free, specialized for security
   - Has built-in alert management
   - Good for network monitoring
   
3. **Splunk**
   - Powerful, professional
   - Paid (has free trial)
   - Steep learning curve
   - Industry standard

4. **Graylog**
   - Open-source
   - Lightweight
   - Good for smaller deployments

**Recommendation for Beginners:** Start with **Elasticsearch Stack** or **Wazuh** (both have free versions)

**Action Items:**
- Decide which SIEM you'll use
- Note: This choice doesn't affect NetPulse code much—our webhook is flexible

---

#### **Task 1.2: Understand HTTP Webhooks**

**What is a Webhook?**

A webhook is simply an **HTTP POST request** that sends data to another server.

**Analogy:**
- Regular request: "Hey server, do you have data for me?"
- Webhook: "Hey server, I'm sending you data right now"

**Simple Example:**
```
When NetPulse detects an anomaly:
  1. Create this JSON object:
     {
       "alert_id": 123,
       "source_ip": "10.0.0.5",
       "severity": "high",
       "timestamp": "2026-05-07T10:30:00Z"
     }
  
  2. Send it via HTTP POST to:
     http://your-siem:9200/alerts
  
  3. SIEM receives and stores it
```

**Key Concepts:**
- **URL:** Where to send the data (SIEM endpoint)
- **JSON:** Standardized data format (human-readable)
- **HTTP POST:** The method of sending (like submitting a form)
- **Headers:** Metadata about the request (content type, auth token, etc.)
- **Timeout:** How long to wait for SIEM response before giving up (5 seconds is typical)

**Why Webhooks?**
- No persistent connection needed
- Works across firewalls
- Standard HTTP protocol
- Easy to debug (can test with curl or Postman)

**Action Items:**
- Understand that webhook = HTTP POST with JSON data
- Know that SIEM has an endpoint/port that receives this data
- Realize this is non-blocking: if SIEM is down, NetPulse continues working

---

#### **Task 1.3: Set Up SIEM Locally (Optional)**

**What is this?**
Running a real SIEM on your machine so you can test end-to-end.

**Option A: Docker (Easiest if you still have Docker)**
```bash
docker run -d -p 9200:9200 -e "discovery.type=single-node" docker.elastic.co/elasticsearch/elasticsearch:8.0.0
docker run -d -p 5601:5601 docker.elastic.co/kibana/kibana:8.0.0
```
Then access Kibana at: http://localhost:5601

**Option B: Manual Installation (More involved)**
- Download Elasticsearch, unzip, run
- Download Kibana, configure, run
- Takes 10-15 minutes

**Option C: Skip This Step (Advanced)**
- Use a test webhook service instead (e.g., webhook.site)
- See alerts being received in real-time
- No full SIEM needed for initial testing

**Action Items:**
- Decide if you want a full SIEM setup now or test first
- If testing first: use webhook.site (no setup needed)
- If setting up SIEM: choose Elasticsearch or Wazuh
- Note the SIEM URL and port (e.g., http://localhost:9200)

---

### **Phase 2: Create Webhook Module**

#### **Task 2.1: Create webhook.py (Alert Formatter)**

**What is this?**
A Python module that:
1. Takes an alert object from NetPulse
2. Formats it as JSON
3. Sends it to the SIEM via HTTP

**Key Functions to Implement:**

```python
# Function 1: Load configuration from environment
def load_webhook_config():
    """Get SIEM URL from environment variable"""
    # Returns: "http://localhost:9200" (or None if not set)

# Function 2: Build JSON payload
def build_webhook_payload(alert, advice=None, profile="generic"):
    """Convert alert to standardized JSON"""
    # Input: Alert object + advice string
    # Output: Dictionary with all fields formatted for SIEM

# Function 3: Send the data
def send_alert_via_webhook(alert, webhook_url=None, advice=None):
    """POST the alert to SIEM"""
    # Input: Alert object + SIEM URL
    # Output: True if sent successfully, False if failed
    # Important: Never crash if SIEM is down—return False instead
```

**Webhook Payload Structure (What gets sent to SIEM):**
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
  "description": "Suspicious traffic pattern detected",
  "advice": "Block source IP and enable rate limiting"
}
```

**Error Handling (Very Important!):**
- If SIEM is offline → log error but don't crash
- If SIEM is slow → timeout after 5 seconds
- If JSON is malformed → log error but continue
- **Golden Rule:** webhook failures should NEVER stop the detection pipeline

**Action Items:**
- Create file: `webhook.py`
- Implement 3 functions listed above
- Add error handling for network failures
- Test each function individually

---

#### **Task 2.2: Implement Alert Payload Builder**

**What is this?**
The function that converts NetPulse alerts into SIEM-friendly JSON.

**Why is this important?**
Different SIEM platforms expect different field names:
- Elasticsearch likes: `@timestamp`, `message`, `level`
- Wazuh likes: `rule`, `agent`, `manager`, `data`
- Generic systems like: `timestamp`, `description`, `severity`

**Implementation Strategy:**

```python
def build_webhook_payload(alert, advice=None, profile="generic"):
    """
    Convert NetPulse alert to SIEM-friendly JSON
    
    Inputs:
    - alert: Dict/object with anomaly data
    - advice: String with remediation recommendation
    - profile: "generic", "elasticsearch", "wazuh", etc.
    
    Output:
    - JSON-serializable dictionary
    """
    
    # Step 1: Extract key fields (handle missing data gracefully)
    alert_id = alert.get("alert_id") or alert.get("id")
    severity = alert.get("severity") or infer_severity(alert.get("anomaly_score"))
    timestamp = alert.get("timestamp") or datetime.now().isoformat()
    
    # Step 2: Build base payload (works with any SIEM)
    base_payload = {
        "source": "NetPulse-Shield",
        "timestamp": timestamp,
        "alert_id": alert_id,
        "severity": severity,
        "anomaly_score": alert.get("anomaly_score"),
        "source_ip": alert.get("source_ip"),
        "destination_ip": alert.get("destination_ip"),
        "attack_type": alert.get("attack_type"),
        "description": alert.get("description"),
        "advice": advice
    }
    
    # Step 3: Add profile-specific fields
    if profile == "wazuh":
        # Wazuh expects this structure
        base_payload["rule"] = {"id": "100001", "level": 10}
        base_payload["agent"] = {"name": "NetPulse-Shield", "id": "000"}
    
    elif profile == "elasticsearch":
        # Elasticsearch prefers @timestamp
        base_payload["@timestamp"] = timestamp
    
    return base_payload
```

**Field Mapping Guide:**
```
NetPulse Field          → SIEM Field
anomaly_score          → severity (convert number to text)
src_ip/srcip           → source_ip
dst_ip/dstip           → destination_ip
Label                  → attack_type
alert_id or id         → alert_id
created_at/timestamp   → timestamp
description            → description or message
advice                 → remediation or recommendation
```

**Severity Mapping (Example):**
```
anomaly_score ≤ -0.8  → "critical" or "high"
anomaly_score ≤ -0.5  → "medium"
anomaly_score ≤ 0     → "low"
```

**Action Items:**
- Implement base payload builder (supports all SIEMs)
- Add profile support (at least "generic" and "wazuh")
- Test with sample alert data
- Verify JSON is valid and complete

---

#### **Task 2.3: Implement HTTP Sender**

**What is this?**
The function that actually POSTs the JSON to the SIEM.

**Core Implementation:**

```python
import json
import urllib.request
from urllib.error import URLError, HTTPError

def send_alert_via_webhook(alert, webhook_url=None, advice=None, timeout=5):
    """
    Send alert to SIEM via HTTP POST
    
    Inputs:
    - alert: Alert object/dict
    - webhook_url: SIEM endpoint (e.g., "http://localhost:9200/alerts")
    - advice: Remediation text
    - timeout: Seconds to wait before giving up
    
    Returns:
    - True if sent successfully
    - False if failed (logs error but doesn't crash)
    """
    
    # Step 1: Check if webhook is configured
    if not webhook_url:
        logger.info("Webhook not configured—skipping SIEM send")
        return False
    
    # Step 2: Build payload
    payload = build_webhook_payload(alert, advice)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    
    # Step 3: Create HTTP request with headers
    request = urllib.request.Request(
        webhook_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "NetPulse-Shield/1.0"
        },
        method="POST"
    )
    
    # Step 4: Send and handle responses
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            if 200 <= status < 300:
                logger.info(f"Alert sent to SIEM ({status})")
                return True
            else:
                logger.warning(f"SIEM returned status {status}")
                return False
    
    except HTTPError as e:
        logger.warning(f"SIEM rejected request: {e.code}")
        return False
    
    except URLError as e:
        logger.warning(f"Cannot reach SIEM: {e.reason}")
        return False
    
    except TimeoutError:
        logger.warning(f"SIEM request timed out after {timeout}s")
        return False
    
    except Exception as e:
        logger.error(f"Unexpected error sending to SIEM: {e}")
        return False
```

**Error Handling Details:**

| Error Type | Cause | Action |
|-----------|-------|--------|
| URLError | SIEM offline or unreachable | Log warning, return False |
| HTTPError (4xx) | Bad request format | Log warning, check JSON format |
| HTTPError (5xx) | SIEM server error | Log warning, retry later |
| Timeout | SIEM slow | Log warning, return False |
| JSON error | Invalid data | Log error, skip alert |

**Testing the Function:**

```python
# Test with mock SIEM
test_alert = {
    "alert_id": 1,
    "severity": "high",
    "source_ip": "10.0.0.5",
    "anomaly_score": -0.95
}

# This will fail (no SIEM running), but should NOT crash
result = send_alert_via_webhook(test_alert, "http://localhost:9200/alerts")
print(f"Send result: {result}")  # Should print: Send result: False
```

**Action Items:**
- Implement send function with error handling
- Use urllib.request (standard library—no extra dependencies)
- Test that it handles all error types gracefully
- Verify it never crashes pipeline

---

### **Phase 3: Integrate with Pipeline**

#### **Task 3.1: Import webhook in pipeline.py**

**What is this?**
Making pipeline.py aware of the webhook module.

**Action Items:**
```python
# Add to top of pipeline.py (after existing imports)
from webhook import build_webhook_payload, send_alert_via_webhook
```

---

#### **Task 3.2: Add webhook configuration variables**

**What is this?**
Reading SIEM URL from environment variables so users can configure it without changing code.

**Implementation:**

```python
import os

# Add to main() function or before it
webhook_url = os.getenv("NETPULSE_WEBHOOK_URL")  # e.g., "http://localhost:9200/alerts"
webhook_enabled = webhook_url is not None

if webhook_enabled:
    logger.info(f"SIEM webhook configured: {webhook_url}")
else:
    logger.info("No SIEM webhook configured (alerts stay local)")
```

**How Users Configure It:**

```bash
# Windows PowerShell
$env:NETPULSE_WEBHOOK_URL = "http://localhost:9200/alerts"

# Linux/Mac
export NETPULSE_WEBHOOK_URL="http://localhost:9200/alerts"

# Then run
python pipeline.py
```

**Action Items:**
- Read NETPULSE_WEBHOOK_URL from environment
- Log whether webhook is enabled or not
- Pass webhook_url to remediation report function

---

#### **Task 3.3: Call webhook after each alert detection**

**What is this?**
Actually sending alerts to SIEM in the pipeline.

**Current Flow:**
```
Detect Anomaly → Save to CSV → Generate Advice → Done
```

**New Flow:**
```
Detect Anomaly → Save to CSV → Send to SIEM → Generate Advice → Done
```

**Implementation:**

In `generate_remediation_report()` function:

```python
def generate_remediation_report(results, output_path="Security_Report.txt"):
    """Generate report and optionally send to SIEM"""
    
    advisor = NetworkSecurityAdvisor(top_k=3)
    anomalies = results[results['is_anomaly']].copy()
    
    report_lines = [...]
    
    for idx, (_, row) in enumerate(anomalies.head(5).iterrows(), 1):
        description = f"Anomaly detected..."
        advice = advisor.get_remediation_advice(description)
        
        # 👇 NEW: Send to SIEM
        alert_payload = row.to_dict()
        alert_payload["description"] = description
        alert_payload["advice"] = advice
        
        # This never fails—webhook returns False if down
        sent = send_alert_via_webhook(alert_payload, webhook_url=webhook_url, advice=advice)
        if sent:
            logger.info(f"Alert {idx} sent to SIEM")
        
        report_lines.append(f"[ALERT {idx}] Anomaly Score: {row['anomaly_score']:.4f}")
        # ... rest of reporting
```

**Key Points:**
- Call webhook AFTER getting advice
- Pass both alert data AND advice
- Check return value (True/False) for logging
- Never crash if webhook fails

**Action Items:**
- Modify `generate_remediation_report()` to call webhook
- Pass webhook_url from main()
- Test that alerts are sent when SIEM is running
- Test that pipeline continues when SIEM is down

---

### **Phase 4: Integrate with Dashboard**

#### **Task 4.1: Add webhook config UI**

**What is this?**
Let users see/configure SIEM settings in the Streamlit dashboard.

**Implementation:**

```python
import os

# Add to dashboard.py (near top)
def get_webhook_config():
    """Check if webhook is configured"""
    url = os.getenv("NETPULSE_WEBHOOK_URL")
    return {"configured": url is not None, "url": url}

# Add to sidebar or new page
webhook_config = get_webhook_config()

st.sidebar.markdown("---")
st.sidebar.subheader("🔗 SIEM Configuration")

if webhook_config["configured"]:
    st.sidebar.success(f"✅ SIEM Connected")
    st.sidebar.text(f"URL: {webhook_config['url']}")
else:
    st.sidebar.warning("⚠️ SIEM Not Configured")
    st.sidebar.info("Set NETPULSE_WEBHOOK_URL environment variable to enable")
```

**Action Items:**
- Add webhook config display in sidebar
- Show SIEM connection status
- Display SIEM URL if configured
- Show setup instructions if not configured

---

#### **Task 4.2: Show SIEM connection status**

**What is this?**
Let users know if the SIEM is actually reachable.

**Implementation:**

```python
def check_siem_health(webhook_url, timeout=2):
    """Test if SIEM is responding"""
    if not webhook_url:
        return {"status": "not_configured"}
    
    try:
        # Send test request
        request = urllib.request.Request(
            webhook_url,
            data=b'{"test": true}',
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {"status": "healthy", "code": response.status}
    except:
        return {"status": "unreachable"}

# In dashboard:
webhook_config = get_webhook_config()
if webhook_config["configured"]:
    health = check_siem_health(webhook_config["url"])
    
    if health["status"] == "healthy":
        st.sidebar.success("✅ SIEM is responding")
    elif health["status"] == "unreachable":
        st.sidebar.error("❌ Cannot reach SIEM")
    else:
        st.sidebar.warning("⚠️ SIEM not configured")
```

**Action Items:**
- Add SIEM health check function
- Display status in dashboard
- Show helpful error messages

---

#### **Task 4.3: Add manual alert forwarding button**

**What is this?**
Let users manually send selected alerts to SIEM from dashboard.

**Implementation:**

```python
import pandas as pd

# Add to Detected Alerts page in dashboard

st.subheader("Forward Alerts to SIEM")

webhook_config = get_webhook_config()
if webhook_config["configured"] and alerts is not None:
    # Let user select how many alerts
    forward_count = st.slider("Number of alerts to forward", 1, min(10, len(alerts)), 5)
    
    if st.button("📤 Send to SIEM"):
        count = 0
        for _, row in alerts.head(forward_count).iterrows():
            payload = row.to_dict()
            if send_alert_via_webhook(payload, webhook_url=webhook_config["url"]):
                count += 1
        
        st.success(f"✅ Forwarded {count} alerts to SIEM")
else:
    st.warning("SIEM not configured or no alerts available")
```

**Action Items:**
- Add alert forwarding section in dashboard
- Allow user to select how many alerts
- Show success/failure messages
- Handle SIEM being offline gracefully

---

### **Phase 5: Integrate with Async Tasks**

#### **Task 5.1: Send webhook from background workers**

**What is this?**
When using Redis/RQ for background advice generation, also send alerts to SIEM.

**Current Code (tasks.py):**
```python
def generate_advice_for_alert(alert_id, db_path):
    # Get alert from DB
    alert = session.query(Alert).filter(Alert.id == alert_id).one()
    
    # Generate advice
    advice = advisor.get_remediation_advice(...)
    alert.advice = advice
    session.commit()
```

**New Code:**
```python
def generate_advice_for_alert(alert_id, db_path):
    alert = session.query(Alert).filter(Alert.id == alert_id).one()
    advice = advisor.get_remediation_advice(...)
    alert.advice = advice
    
    # 👇 NEW: Send to SIEM after generating advice
    webhook_url = os.getenv("NETPULSE_WEBHOOK_URL")
    if webhook_url:
        payload = {
            "alert_id": alert.id,
            "anomaly_score": alert.anomaly_score,
            "description": ...,
            "advice": advice
        }
        send_alert_via_webhook(payload, webhook_url)
    
    session.commit()
```

**Action Items:**
- Import webhook in tasks.py
- Read NETPULSE_WEBHOOK_URL environment variable
- Send alert after advice generation
- Don't crash if webhook fails

---

### **Phase 6: Testing & Validation**

#### **Task 6.1: Test locally with mock SIEM**

**What is this?**
Verify webhook code works before using real SIEM.

**Using webhook.site (No Setup Required):**

1. Go to https://webhook.site
2. Copy the unique URL (e.g., `https://webhook.site/abc123def456`)
3. Set environment variable:
   ```bash
   $env:NETPULSE_WEBHOOK_URL = "https://webhook.site/abc123def456"
   ```
4. Run pipeline:
   ```bash
   python pipeline.py
   ```
5. Check webhook.site—you should see your alerts arrive in real-time!

**Benefits:**
- No SIEM needed
- Instant visual feedback
- Easy to debug JSON format
- Free and immediate

**Test Checklist:**
- [ ] Alert appears on webhook.site
- [ ] JSON format is valid
- [ ] All fields are present
- [ ] Timestamps are correct
- [ ] Severity levels make sense

**Manual Testing:**

```python
# test_webhook.py
from webhook import send_alert_via_webhook

test_alert = {
    "alert_id": 99,
    "severity": "critical",
    "source_ip": "192.168.1.1",
    "destination_ip": "10.0.0.1",
    "anomaly_score": -0.95,
    "description": "Test alert"
}

result = send_alert_via_webhook(
    test_alert,
    webhook_url="https://webhook.site/your-unique-url",
    advice="This is a test alert"
)

print(f"Alert sent: {result}")
```

**Action Items:**
- Test with webhook.site
- Verify JSON appears correctly
- Check all fields are included
- Test with multiple alerts
- Test when webhook is offline (should return False, no crash)

---

#### **Task 6.2: Test with real SIEM**

**What is this?**
Send alerts to actual SIEM and verify they appear in UI.

**Setup Elasticsearch (If Chosen):**

```bash
# Using Docker (easiest)
docker run -d -p 9200:9200 -e "discovery.type=single-node" docker.elastic.co/elasticsearch/elasticsearch:8.11.0

# Wait 10 seconds, then:
docker run -d -p 5601:5601 docker.elastic.co/kibana/kibana:8.11.0

# Access at: http://localhost:5601
```

**Configure NetPulse:**

```bash
$env:NETPULSE_WEBHOOK_URL = "http://localhost:9200/netpulse-alerts"
python pipeline.py
```

**Verify in Kibana:**

1. Open http://localhost:5601
2. Go to "Dev Tools" → "Console"
3. Search for your alerts:
   ```
   GET /netpulse-alerts/_search
   ```
4. You should see JSON response with your alerts

**Test Checklist:**
- [ ] Elasticsearch receives POST requests (check logs)
- [ ] Kibana shows data in indices
- [ ] Can search alerts by severity
- [ ] Can filter by timestamp
- [ ] Timestamps are correct
- [ ] All fields indexed and searchable

**Action Items:**
- Deploy SIEM (Elasticsearch or chosen platform)
- Test sending alerts
- Verify data appears in SIEM UI
- Create sample dashboards
- Test searching/filtering alerts

---

#### **Task 6.3: Verify data appears in SIEM UI**

**What is this?**
Create visual confirmation that SIEM has your alerts.

**For Elasticsearch/Kibana:**

```
1. Open http://localhost:5601
2. Go to "Discover"
3. Create new view
4. Select "netpulse-alerts" index
5. Set date range to "Last 1 hour"
6. Should see your alerts as table rows
7. Click on any alert to see full JSON
```

**Create Dashboard (Optional but useful):**

```
1. In Kibana, go to "Dashboards"
2. Click "Create Dashboard"
3. Add visualizations:
   - Alert count over time (line chart)
   - Severity distribution (pie chart)
   - Top source IPs (bar chart)
   - Top attack types (table)
4. Save dashboard as "NetPulse-Shield Alerts"
```

**Action Items:**
- Access SIEM UI
- Verify alerts are searchable
- Create sample queries
- Build dashboard (optional)
- Take screenshots for documentation

---

### **Phase 7: Documentation & Deployment**

#### **Task 7.1: Document configuration**

**What is this?**
Write down how users configure the SIEM integration.

**Create SIEM_SETUP.md:**

```markdown
# SIEM Integration Setup

## Quick Start

### 1. Set Environment Variable
```bash
# Windows PowerShell
$env:NETPULSE_WEBHOOK_URL = "http://your-siem:9200/alerts"

# Linux/Mac
export NETPULSE_WEBHOOK_URL="http://your-siem:9200/alerts"
```

### 2. Run Pipeline
```bash
python pipeline.py
```

### 3. Verify in SIEM UI
- Open your SIEM dashboard
- Search for recent alerts
- Verify all fields are present

## Supported SIEM Platforms

### Elasticsearch (Recommended)
- Free, open-source
- URL: `http://localhost:9200/netpulse-alerts`
- UI: http://localhost:5601

### Wazuh
- URL: `http://wazuh-server:5000/alerts`
- Requires HTTP integration configured

### Generic HTTP Endpoint
- Works with any system that accepts POST requests
- URL format: `http://host:port/endpoint`

## Environment Variables

| Variable | Required | Example |
|----------|----------|---------|
| NETPULSE_WEBHOOK_URL | No | http://localhost:9200/alerts |
| NETPULSE_WEBHOOK_TIMEOUT | No | 5 (seconds) |

## Payload Format

Alerts sent as JSON:
```json
{
  "source": "NetPulse-Shield",
  "timestamp": "2026-05-07T10:30:00Z",
  "alert_id": 123,
  "severity": "high",
  "anomaly_score": -0.95,
  "advice": "..."
}
```

## Troubleshooting

**Q: Alerts not appearing in SIEM**
A: 
- Verify NETPULSE_WEBHOOK_URL is set
- Check SIEM is running and accessible
- Review logs: `python pipeline.py` should show webhook status

**Q: SIEM rejects connection**
A:
- Verify URL is correct
- Check firewall allows connection
- Verify SIEM endpoint accepts POST requests

**Q: Webhook timeouts**
A:
- SIEM is slow, increase timeout
- Or improve network connection
- Pipeline continues—alerts stay local
```

**Action Items:**
- Create SIEM_SETUP.md
- Include all SIEM platform instructions
- Add troubleshooting section
- Document payload format
- List all environment variables

---

#### **Task 7.2: Create setup guide for users**

**What is this?**
Step-by-step guide for new users.

**Create docs/SIEM_INTEGRATION_SETUP.md:**

```markdown
# How to Set Up SIEM Integration with NetPulse-Shield

## For Complete Beginners

### What You'll Need
1. NetPulse-Shield (already installed)
2. A SIEM platform (we recommend Elasticsearch)
3. 15 minutes of time

### Step-by-Step Instructions

#### Step 1: Choose and Install SIEM

**Option A: Elasticsearch (Recommended for Learning)**
```bash
# If you have Docker:
docker run -d -p 9200:9200 -e "discovery.type=single-node" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0

# Wait 30 seconds, then start Kibana:
docker run -d -p 5601:5601 \
  docker.elastic.co/kibana/kibana:8.11.0

# Verify Elasticsearch is running:
curl http://localhost:9200
# You should see JSON response

# Verify Kibana is running:
# Open http://localhost:5601 in browser
```

**Option B: Wazuh (Alternative)**
- Download from wazuh.com
- Follow their installation guide
- Note the API URL

#### Step 2: Configure NetPulse-Shield

```bash
# Open PowerShell or terminal
# Set the SIEM URL (for Elasticsearch):
$env:NETPULSE_WEBHOOK_URL = "http://localhost:9200/netpulse-alerts"

# Verify it's set:
echo $env:NETPULSE_WEBHOOK_URL
# Should print: http://localhost:9200/netpulse-alerts
```

#### Step 3: Run NetPulse Pipeline

```bash
# In NetPulse-Shield directory:
python pipeline.py

# Watch for log messages:
# ✅ "Webhook configured: http://localhost:9200/..."
# ✅ "Alert sent to SIEM (200)"
```

#### Step 4: Verify in SIEM UI

**For Elasticsearch/Kibana:**
1. Open http://localhost:5601
2. Click "Discover" in left menu
3. Create new data view → Select "netpulse-alerts" index
4. Set time range to "Last 1 hour"
5. You should see your alerts!

#### Step 5: Create a Dashboard

1. In Kibana, click "Dashboards"
2. Click "Create Dashboard"
3. Click "Add a panel"
4. Select visualization type (e.g., "Metric")
5. Set search to "netpulse-alerts"
6. Configure (e.g., count alerts by severity)
7. Save and admire your work!

### Common Issues

**Issue: Alerts not showing in SIEM**
1. Check environment variable is set: `echo $env:NETPULSE_WEBHOOK_URL`
2. Verify SIEM is running: `curl http://localhost:9200`
3. Check NetPulse logs for errors
4. Try testing with webhook.site first

**Issue: "Connection refused" error**
1. Make sure SIEM is running (docker ps)
2. Verify port number is correct (9200 for Elasticsearch)
3. Try accessing SIEM UI directly in browser

**Issue: Alerts in SIEM but fields look weird**
1. Elasticsearch might be auto-creating weird mappings
2. Delete index: `curl -X DELETE http://localhost:9200/netpulse-alerts`
3. Re-run pipeline to recreate with correct schema

### Next Steps
- Explore SIEM features (searching, filtering, alerting)
- Create custom dashboards for your needs
- Set up automated responses (optional)
- Integrate with other security tools
```

**Action Items:**
- Create detailed step-by-step guide
- Include Docker commands
- Add screenshots (if possible)
- Include troubleshooting for common issues
- Keep language simple for beginners

---

#### **Task 7.3: Add troubleshooting section**

**What is this?**
FAQ and solutions for common problems.

**Create TROUBLESHOOTING.md:**

```markdown
# SIEM Integration Troubleshooting

## Issue: "Webhook not configured"

**Symptom:** Pipeline runs but no messages about SIEM

**Cause:** NETPULSE_WEBHOOK_URL environment variable not set

**Solution:**
```bash
# Check if variable is set
echo $env:NETPULSE_WEBHOOK_URL

# If empty, set it:
$env:NETPULSE_WEBHOOK_URL = "http://localhost:9200/alerts"

# Verify it was set:
echo $env:NETPULSE_WEBHOOK_URL
```

## Issue: "Cannot reach SIEM" warnings

**Symptom:** Logs show "URLError" or "connection refused"

**Cause:** SIEM is not running or URL is wrong

**Solution:**
```bash
# 1. Verify SIEM is running (Elasticsearch):
curl http://localhost:9200

# If fails, start Elasticsearch:
docker run -d -p 9200:9200 -e "discovery.type=single-node" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0

# 2. Verify URL in environment variable is correct
echo $env:NETPULSE_WEBHOOK_URL

# 3. Test connection manually:
curl -X POST http://localhost:9200/test \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

## Issue: Alerts show in SIEM but data looks incorrect

**Symptom:** SIEM has alerts but fields are empty or in wrong format

**Cause:** JSON payload structure doesn't match SIEM expectations

**Solution:**
```bash
# 1. Check what's being sent to SIEM:
# Use webhook.site for instant feedback
$env:NETPULSE_WEBHOOK_URL = "https://webhook.site/unique-url"
python pipeline.py

# 2. View raw JSON on webhook.site
# Verify all fields are present and formatted correctly

# 3. Compare with expected format in SIEM docs
# Adjust webhook.py if needed
```

## Issue: SIEM requests are timing out

**Symptom:** Logs show "TimeoutError" or "took longer than 5 seconds"

**Cause:** SIEM is slow or network is congested

**Solution:**
```bash
# Option 1: Increase timeout
# In webhook.py, change timeout from 5 to 10:
send_alert_via_webhook(..., timeout=10)

# Option 2: Check SIEM performance
# Monitor SIEM CPU/memory usage
# Might need to optimize SIEM queries

# Option 3: Use async mode
# Configure pipeline to not wait for SIEM response
```

## Issue: Dashboard shows no alerts but logs say they were sent

**Symptom:** NetPulse logs show "Alert sent to SIEM" but Kibana is empty

**Cause:** SIEM index doesn't exist or has wrong name

**Solution:**
```bash
# 1. Check what indices exist in Elasticsearch:
curl http://localhost:9200/_cat/indices

# 2. Look for "netpulse-alerts" index
# If missing, SIEM might be rejecting requests

# 3. Check if index has different name:
# Update NETPULSE_WEBHOOK_URL to match

# 4. Delete and recreate index:
curl -X DELETE http://localhost:9200/netpulse-alerts
# Re-run pipeline to recreate
```

## Getting Help

If none of these solutions work:

1. **Check NetPulse logs:** Look for error messages
2. **Check SIEM logs:** Check SIEM's own logs for rejection reasons
3. **Test with webhook.site:** Verify JSON is being sent correctly
4. **Check network connectivity:** `ping` SIEM hostname
5. **Review SIEM documentation:** Verify your API endpoint is correct

## Performance Tips

- **Large alert batches slow:** Send gradually instead of all at once
- **SIEM indexing slow:** Consider archiving old alerts
- **Network latency high:** Increase timeout or use batching
- **Memory usage high:** Reduce alert retention period

```

**Action Items:**
- Create comprehensive troubleshooting guide
- Include solutions for all common issues
- Add diagnostic commands
- Provide step-by-step debugging process
- Include performance optimization tips

---

## 📊 Complete To-Do Checklist

```
## Phase 1: Understanding
- [ ] Task 1.1: Choose SIEM platform
- [ ] Task 1.2: Learn about HTTP webhooks
- [ ] Task 1.3: Set up SIEM locally (optional)

## Phase 2: Create Webhook Module
- [ ] Task 2.1: Create webhook.py file
- [ ] Task 2.2: Implement payload builder function
- [ ] Task 2.3: Implement HTTP sender function

## Phase 3: Integrate with Pipeline
- [ ] Task 3.1: Import webhook in pipeline.py
- [ ] Task 3.2: Add webhook configuration variables
- [ ] Task 3.3: Call webhook after alert detection

## Phase 4: Integrate with Dashboard
- [ ] Task 4.1: Add webhook config UI
- [ ] Task 4.2: Add SIEM health check display
- [ ] Task 4.3: Add manual alert forwarding button

## Phase 5: Async Integration
- [ ] Task 5.1: Send webhook from background workers

## Phase 6: Testing
- [ ] Task 6.1: Test with webhook.site
- [ ] Task 6.2: Test with real SIEM
- [ ] Task 6.3: Verify data in SIEM UI

## Phase 7: Documentation
- [ ] Task 7.1: Document configuration options
- [ ] Task 7.2: Create beginner setup guide
- [ ] Task 7.3: Create troubleshooting guide
```

---

## 🎓 Key Learning Outcomes

After completing this guide, you'll understand:

1. **What SIEM is** and why it's useful
2. **How webhooks work** (HTTP POST requests)
3. **How to format data** for external systems
4. **Error handling** in distributed systems
5. **End-to-end integration** patterns
6. **Testing** non-critical failures
7. **User documentation** best practices

---

## 📚 Additional Resources

- **Elasticsearch Documentation:** https://www.elastic.co/guide/en/elasticsearch/reference/
- **Wazuh Documentation:** https://documentation.wazuh.com/
- **HTTP POST Requests:** https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST
- **JSON Format:** https://www.json.org/
- **Webhook.site:** https://webhook.site/ (for testing)

---

**Remember:** Start with Phase 1 (understanding), don't rush to coding. Take it step-by-step, test frequently, and you'll have a working SIEM integration in no time!
