"""
NetPulse Shield — Premium Minimalistic Web Dashboard
Serves a clean, minimal dashboard with the same features as dashboard.py
Run with: python web_dashboard.py
"""

import os
import pandas as pd
from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS

from db import Alert, AuditLog, create_db, get_session
from detector import NetworkAnomalyDetector
from system_utils import check_redis_health, get_queue_stats

# ═════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═════════════════════════════════════════════════════════════════════════════

app = Flask(__name__)
CORS(app)

DB_PATH = "sqlite:///alerts.db"
create_db(DB_PATH)

# ═════════════════════════════════════════════════════════════════════════════
# HTML TEMPLATE
# ═════════════════════════════════════════════════════════════════════════════

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NetPulse Shield — Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { height: 100%; }

:root {
  --bg: #ffffff;
  --surf: #f8f9fa;
  --panel: #ffffff;
  --bdr: #e0e0e0;
  --acc: #2563eb;
  --danger: #dc2626;
  --warn: #f59e0b;
  --ok: #10b981;
  --txt: #1f2937;
  --txt-dim: #6b7280;
  --txt-light: #9ca3af;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: var(--bg);
  color: var(--txt);
  font-size: 14px;
  line-height: 1.6;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 40px 20px;
}

header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 40px;
  border-bottom: 1px solid var(--bdr);
  padding-bottom: 20px;
}

.header-title {
  font-size: 28px;
  font-weight: 600;
  letter-spacing: -0.5px;
}

.header-subtitle {
  color: var(--txt-dim);
  font-size: 13px;
  margin-top: 4px;
}

.nav-tabs {
  display: flex;
  gap: 2px;
  margin-bottom: 30px;
  border-bottom: 1px solid var(--bdr);
}

.nav-tab {
  padding: 12px 16px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--txt-dim);
  font-size: 13px;
  font-weight: 500;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.nav-tab:hover {
  color: var(--txt);
  background: var(--surf);
}

.nav-tab.active {
  color: var(--acc);
  border-bottom-color: var(--acc);
}

.section { display: none; }
.section.active { display: block; }

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.metric {
  background: var(--panel);
  border: 1px solid var(--bdr);
  border-radius: 8px;
  padding: 20px;
  transition: all 0.2s;
}

.metric:hover {
  border-color: var(--acc);
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.metric-label {
  color: var(--txt-dim);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--txt);
  margin-bottom: 4px;
}

.metric-sub {
  color: var(--txt-light);
  font-size: 12px;
}

.chart-container {
  background: var(--panel);
  border: 1px solid var(--bdr);
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 20px;
}

.table-container {
  background: var(--panel);
  border: 1px solid var(--bdr);
  border-radius: 8px;
  overflow: hidden;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th {
  background: var(--surf);
  padding: 12px 16px;
  text-align: left;
  font-weight: 600;
  font-size: 12px;
  color: var(--txt-dim);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--bdr);
}

td {
  padding: 12px 16px;
  border-bottom: 1px solid var(--bdr);
  font-size: 13px;
}

tr:last-child td { border-bottom: none; }
tr:hover td { background: var(--surf); }

.badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.badge.danger { background: rgba(220, 38, 38, 0.1); color: var(--danger); }
.badge.warn { background: rgba(245, 158, 11, 0.1); color: var(--warn); }
.badge.ok { background: rgba(16, 185, 129, 0.1); color: var(--ok); }
.badge.info { background: rgba(37, 99, 235, 0.1); color: var(--acc); }

.button {
  display: inline-block;
  padding: 10px 16px;
  background: var(--acc);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.2s;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.button:hover {
  background: #1d4ed8;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

.button.secondary {
  background: transparent;
  border: 1px solid var(--bdr);
  color: var(--txt);
}

.button.secondary:hover {
  background: var(--surf);
  border-color: var(--acc);
  color: var(--acc);
}

.alert-card {
  background: var(--panel);
  border: 1px solid var(--bdr);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.alert-card:hover {
  border-color: var(--acc);
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.alert-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.alert-id {
  font-weight: 600;
  color: var(--acc);
}

.alert-score {
  font-size: 12px;
  color: var(--txt-dim);
}

.alert-content {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s;
}

.alert-card.expanded .alert-content {
  max-height: 500px;
  padding-top: 12px;
  border-top: 1px solid var(--bdr);
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--txt-dim);
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--bdr);
  border-radius: 6px;
  font-family: inherit;
  font-size: 13px;
  transition: all 0.2s;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--acc);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.1);
}

.footer {
  text-align: center;
  color: var(--txt-light);
  font-size: 12px;
  margin-top: 40px;
  padding-top: 20px;
  border-top: 1px solid var(--bdr);
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid var(--bdr);
  border-top-color: var(--acc);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.controls {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--bdr);
}

.status-row:last-child { border-bottom: none; }
.status-label { color: var(--txt-dim); }
.status-value { font-weight: 600; }
</style>
</head>
<body>

<div class="container">
  <header>
    <div>
      <div class="header-title">NetPulse Shield</div>
      <div class="header-subtitle">Network Anomaly Detection & Remediation</div>
    </div>
    <div style="font-size: 12px; color: var(--txt-light); text-align: right;">
      <div id="current-time" style="font-weight: 600;"></div>
      <div>Last refresh: <span id="refresh-time">--:--:--</span></div>
    </div>
  </header>

  <div class="nav-tabs" id="nav-tabs">
    <button class="nav-tab active" onclick="switchTab('overview')">Overview</button>
    <button class="nav-tab" onclick="switchTab('alerts')">Detected Alerts</button>
    <button class="nav-tab" onclick="switchTab('audit')">Audit Logs</button>
    <button class="nav-tab" onclick="switchTab('system')">System Status</button>
    <button class="nav-tab" onclick="switchTab('control')">Control Panel</button>
  </div>

  <!-- OVERVIEW TAB -->
  <div id="overview" class="section active">
    <h2 style="margin-bottom: 20px; font-size: 20px; font-weight: 600;">Network Overview</h2>
    
    <div class="metric-grid">
      <div class="metric">
        <div class="metric-label">Total Flows</div>
        <div class="metric-value" id="metric-flows">0</div>
        <div class="metric-sub">Network packets analyzed</div>
      </div>
      <div class="metric">
        <div class="metric-label">AI Alerts</div>
        <div class="metric-value" id="metric-alerts">0</div>
        <div class="metric-sub">Detected anomalies</div>
      </div>
      <div class="metric">
        <div class="metric-label">System State</div>
        <div class="metric-value" id="metric-state">Operational</div>
        <div class="metric-sub" style="color: var(--ok);">All systems healthy</div>
      </div>
      <div class="metric">
        <div class="metric-label">Detection Rate</div>
        <div class="metric-value" id="metric-rate">0.0%</div>
        <div class="metric-sub">Anomaly percentage</div>
      </div>
    </div>

    <div class="chart-container" style="height: 300px;">
      <h3 style="margin-bottom: 16px; font-size: 14px; font-weight: 600;">Anomaly Distribution</h3>
      <canvas id="pieChart"></canvas>
    </div>
  </div>

  <!-- ALERTS TAB -->
  <div id="alerts" class="section">
    <h2 style="margin-bottom: 20px; font-size: 20px; font-weight: 600;">Detected Alerts (Top 10)</h2>
    <div id="alerts-list"></div>
  </div>

  <!-- AUDIT TAB -->
  <div id="audit" class="section">
    <h2 style="margin-bottom: 20px; font-size: 20px; font-weight: 600;">Audit Logs</h2>
    <div style="margin-bottom: 16px;">
      <button class="button" onclick="downloadAuditLogs()">Download CSV</button>
    </div>
    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Alert ID</th>
            <th>Action</th>
            <th>Actor</th>
            <th>Note</th>
          </tr>
        </thead>
        <tbody id="audit-tbody"></tbody>
      </table>
    </div>
  </div>

  <!-- SYSTEM STATUS TAB -->
  <div id="system" class="section">
    <h2 style="margin-bottom: 20px; font-size: 20px; font-weight: 600;">System Status & Health</h2>
    
    <div class="metric-grid" style="grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));">
      <div class="metric">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
          <div style="width: 8px; height: 8px; border-radius: 50%; background: var(--ok); animation: pulse 2s infinite;"></div>
          <div class="metric-label" style="margin: 0;">Redis Connection</div>
        </div>
        <div id="redis-status" style="font-size: 12px; color: var(--ok);">Checking...</div>
      </div>
      <div class="metric">
        <div class="metric-label">Queue Depth</div>
        <div class="metric-value" id="queue-depth" style="font-size: 24px;">0</div>
      </div>
      <div class="metric">
        <div class="metric-label">Jobs Started</div>
        <div class="metric-value" id="jobs-started" style="font-size: 24px;">0</div>
      </div>
      <div class="metric">
        <div class="metric-label">Jobs Failed</div>
        <div class="metric-value" id="jobs-failed" style="font-size: 24px; color: var(--danger);">0</div>
      </div>
    </div>
  </div>

  <!-- CONTROL PANEL TAB -->
  <div id="control" class="section">
    <h2 style="margin-bottom: 20px; font-size: 20px; font-weight: 600;">Control Panel</h2>
    
    <div class="controls">
      <button class="button" onclick="runAnalysis()">
        <span id="analysis-btn-text">Run Network Analysis</span>
      </button>
      <button class="button secondary" onclick="generateAdvice()">
        <span id="advice-btn-text">Generate AI Advice</span>
      </button>
    </div>

    <div id="control-output" style="background: var(--surf); border: 1px solid var(--bdr); border-radius: 8px; padding: 16px; display: none;">
      <div style="color: var(--txt-dim); font-size: 12px; font-weight: 600; margin-bottom: 8px;">Output</div>
      <div id="control-output-text" style="font-family: monospace; font-size: 12px; color: var(--txt-dim); white-space: pre-wrap; word-break: break-all;"></div>
    </div>
  </div>

  <div class="footer">
    <div>NetPulse Shield © 2024 | Local Network Threat Intelligence</div>
  </div>
</div>

<style>
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
</style>

<script>
// Tab switching
function switchTab(tabName) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  
  document.getElementById(tabName).classList.add('active');
  event.target.classList.add('active');
  
  if (tabName === 'overview') loadOverview();
  if (tabName === 'alerts') loadAlerts();
  if (tabName === 'audit') loadAuditLogs();
  if (tabName === 'system') loadSystemStatus();
}

// Live clock
function updateClock() {
  const now = new Date();
  document.getElementById('current-time').textContent = 
    now.toLocaleTimeString() + ' UTC';
  document.getElementById('refresh-time').textContent =
    now.toLocaleTimeString();
}
setInterval(updateClock, 1000);
updateClock();

// Pie chart
let pieChart = null;
function initPieChart() {
  const ctx = document.getElementById('pieChart').getContext('2d');
  if (pieChart) pieChart.destroy();
  pieChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Normal', 'Anomaly'],
      datasets: [{
        data: [0, 0],
        backgroundColor: ['#10b981', '#dc2626'],
        borderColor: 'white',
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom' } }
    }
  });
}
initPieChart();

// Load overview
async function loadOverview() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    document.getElementById('metric-flows').textContent = data.total_flows.toLocaleString();
    document.getElementById('metric-alerts').textContent = data.total_alerts.toLocaleString();
    document.getElementById('metric-state').textContent = data.total_alerts < 3000 ? 'Operational' : 'Critical';
    document.getElementById('metric-rate').textContent = (data.anomaly_rate * 100).toFixed(1) + '%';
    
    const total = data.total_flows;
    const anomalies = data.total_alerts;
    if (pieChart) {
      pieChart.data.datasets[0].data = [total - anomalies, anomalies];
      pieChart.update();
    }
  } catch (e) { console.error(e); }
}

// Load alerts
async function loadAlerts() {
  try {
    const res = await fetch('/api/alerts');
    const data = await res.json();
    const html = data.alerts.slice(0, 10).map((a, i) => `
      <div class="alert-card" onclick="this.classList.toggle('expanded')">
        <div class="alert-header">
          <span class="alert-id">Alert #${a.id}</span>
          <span class="alert-score">Score: ${a.anomaly_score.toFixed(2)}</span>
        </div>
        <div class="alert-content">
          <div class="status-row">
            <span class="status-label">Status:</span>
            <span class="status-value">${a.status}</span>
          </div>
          <div class="status-row">
            <span class="status-label">Severity:</span>
            <span class="badge ${a.severity === 'high' ? 'danger' : a.severity === 'medium' ? 'warn' : 'ok'}">${a.severity}</span>
          </div>
          <div class="status-row">
            <span class="status-label">Timestamp:</span>
            <span class="status-value">${a.timestamp}</span>
          </div>
          <div style="margin-top: 12px;">
            <select onchange="updateAlertStatus(${a.id}, this.value)" style="padding: 8px; border: 1px solid var(--bdr); border-radius: 4px;">
              <option value="new" ${a.status === 'new' ? 'selected' : ''}>New</option>
              <option value="investigating" ${a.status === 'investigating' ? 'selected' : ''}>Investigating</option>
              <option value="resolved" ${a.status === 'resolved' ? 'selected' : ''}>Resolved</option>
              <option value="false_positive" ${a.status === 'false_positive' ? 'selected' : ''}>False Positive</option>
            </select>
          </div>
        </div>
      </div>
    `).join('');
    document.getElementById('alerts-list').innerHTML = html || '<p style="color: var(--txt-dim);">No alerts available</p>';
  } catch (e) { console.error(e); }
}

// Load audit logs
async function loadAuditLogs() {
  try {
    const res = await fetch('/api/audit');
    const data = await res.json();
    const html = data.logs.map(l => `
      <tr>
        <td>${new Date(l.timestamp).toLocaleString()}</td>
        <td>${l.alert_id || '-'}</td>
        <td>${l.action}</td>
        <td>${l.actor}</td>
        <td>${l.note || '-'}</td>
      </tr>
    `).join('');
    document.getElementById('audit-tbody').innerHTML = html || '<tr><td colspan="5" style="text-align: center; color: var(--txt-dim);">No audit logs</td></tr>';
  } catch (e) { console.error(e); }
}

// Load system status
async function loadSystemStatus() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    document.getElementById('redis-status').textContent = data.redis_connected ? '✓ Connected' : '✗ Disconnected';
    document.getElementById('queue-depth').textContent = data.queue_depth;
    document.getElementById('jobs-started').textContent = data.jobs_processed;
    document.getElementById('jobs-failed').textContent = '0';
  } catch (e) { console.error(e); }
}

// Run analysis
async function runAnalysis() {
  const btn = document.getElementById('analysis-btn-text');
  btn.textContent = 'Running...';
  try {
    const res = await fetch('/api/run-analysis', { method: 'POST' });
    const data = await res.json();
    document.getElementById('control-output').style.display = 'block';
    document.getElementById('control-output-text').textContent = data.message;
    btn.textContent = 'Run Network Analysis';
    loadOverview();
  } catch (e) {
    document.getElementById('control-output-text').textContent = 'Error: ' + e;
    btn.textContent = 'Run Network Analysis';
  }
}

// Generate advice
async function generateAdvice() {
  const btn = document.getElementById('advice-btn-text');
  btn.textContent = 'Generating...';
  try {
    const res = await fetch('/api/generate-advice', { method: 'POST' });
    const data = await res.json();
    document.getElementById('control-output').style.display = 'block';
    document.getElementById('control-output-text').textContent = data.message;
    btn.textContent = 'Generate AI Advice';
  } catch (e) {
    document.getElementById('control-output-text').textContent = 'Error: ' + e;
    btn.textContent = 'Generate AI Advice';
  }
}

// Update alert status
async function updateAlertStatus(alertId, status) {
  try {
    await fetch(`/api/alert/${alertId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    });
  } catch (e) { console.error(e); }
}

// Download audit logs
async function downloadAuditLogs() {
  try {
    const res = await fetch('/api/audit');
    const data = await res.json();
    const csv = 'timestamp,alert_id,action,actor,note\\n' +
      data.logs.map(l => `"${new Date(l.timestamp).toLocaleString()}","${l.alert_id || ''}","${l.action}","${l.actor}","${l.note || ''}"`).join('\\n');
    const a = document.createElement('a');
    a.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv);
    a.download = 'audit_logs.csv';
    a.click();
  } catch (e) { console.error(e); }
}

// Initial load
loadOverview();
</script>

</body>
</html>

<div class="shell">

  <!-- ── SIDEBAR ── -->
  <aside class="sidebar">
    <div class="sb-logo">
      <div class="sb-logo-name">NETPULSE<br>SHIELD</div>
      <div class="sb-logo-sub">THREAT INTELLIGENCE PLATFORM</div>
    </div>

    <nav class="sb-nav">
      <div class="sb-nav-label">Navigation</div>

      <div class="sb-nav-item active" onclick="setNav(this)">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="1" y="1" width="6" height="6" rx="1"/><rect x="9" y="1" width="6" height="6" rx="1"/><rect x="1" y="9" width="6" height="6" rx="1"/><rect x="9" y="9" width="6" height="6" rx="1"/></svg>
        OVERVIEW
      </div>
      <div class="sb-nav-item" onclick="setNav(this)">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><polyline points="1,13 5,7 9,10 15,3"/></svg>
        ANALYTICS
      </div>
      <div class="sb-nav-item" onclick="setNav(this)">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 2L9.5 6h4L10 9l1.5 4L8 11l-3.5 2L6 9 2.5 6h4z"/></svg>
        TRIAGE
      </div>
      <div class="sb-nav-item" onclick="setNav(this)">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><polyline points="8,5 8,8 10,10"/></svg>
        AUDIT LOG
      </div>
      <div class="sb-nav-item" onclick="setNav(this)">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="5" r="2.5"/><path d="M2 14c0-3.3 2.7-6 6-6s6 2.7 6 6"/></svg>
        SETTINGS
      </div>
    </nav>

    <div class="sb-footer">
      <div class="sb-footer-time">
        <b id="live-time">--:--:--</b>
        UTC SESSION
      </div>
    </div>
  </aside>

  <!-- ── MAIN ── -->
  <div class="main">

    <!-- topbar -->
    <header class="topbar">
      <div class="topbar-title">
        <span class="acc">▶</span>
        NETPULSE SHIELD
        <span class="dim">/ CONTROL CENTER<span class="cursor">_</span></span>
      </div>
      <div class="topbar-right">
        <div class="topbar-ts">
          <b id="live-date">----</b>
          LAST REFRESH
        </div>
        <div class="live-badge">LIVE</div>
      </div>
    </header>

    <!-- scrollable content -->
    <div class="content">

      <!-- KPIs -->
      <div class="sec">// SYSTEM OVERVIEW</div>
      <div class="kpi-grid">
        <div class="kpi c">
          <div class="kpi-label">TOTAL FLOWS</div>
          <div class="kpi-val" id="kv-flows">0</div>
          <div class="kpi-sub">captured packets</div>
        </div>
        <div class="kpi r">
          <div class="kpi-label">TOTAL ALERTS</div>
          <div class="kpi-val" id="kv-alerts">0</div>
          <div class="kpi-sub">anomalies flagged</div>
        </div>
        <div class="kpi a">
          <div class="kpi-label">ADVICE PENDING</div>
          <div class="kpi-val" id="kv-pending">0</div>
          <div class="kpi-sub">awaiting triage</div>
        </div>
        <div class="kpi g">
          <div class="kpi-label">ANOMALY RATE</div>
          <div class="kpi-val" id="kv-rate">0.0<span style="font-size:1.1rem">%</span></div>
          <div class="kpi-sub">contamination factor</div>
        </div>
      </div>

      <!-- Charts -->
      <div class="sec">// INTELLIGENCE VIEW</div>
      <div class="charts">
        <div class="chart-panel">
          <div class="chart-eyebrow">ALERT VOLUME · DAILY TREND</div>
          <canvas id="lineChart" height="130"></canvas>
        </div>
        <div class="chart-panel">
          <div class="chart-eyebrow">ANOMALY SCORE DISTRIBUTION</div>
          <canvas id="barChart" height="130"></canvas>
        </div>
      </div>

      <!-- Filters -->
      <div class="sec">// THREAT TRIAGE</div>
      <div class="filter-bar">
        <span class="filter-label">SEVERITY</span>
        <select class="filter-input" id="sev-filter" onchange="applyFilters()">
          <option value="all">ALL</option>
          <option value="high">HIGH</option>
          <option value="medium">MEDIUM</option>
          <option value="low">LOW</option>
        </select>
        <div class="filter-sep"></div>
        <span class="filter-label">MIN SCORE</span>
        <input class="filter-input" type="number" id="score-filter" value="0.0" min="0" max="1" step="0.05" style="width:72px" onchange="applyFilters()">
        <div class="filter-sep"></div>
        <span class="filter-label">SEARCH</span>
        <input class="filter-input" type="text" id="search-filter" placeholder="IP / Flow ID…" style="flex:1" oninput="applyFilters()">
        <button class="filter-btn" onclick="exportCSV()">↓ EXPORT CSV</button>
      </div>

      <!-- Table -->
      <div class="tbl-wrap">
        <div class="tbl-header">
          <span class="tbl-header-title">DETECTED ANOMALIES</span>
          <span class="tbl-count" id="tbl-count">SHOWING 0 OF 0</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>FLOW ID</th>
              <th>SOURCE IP</th>
              <th>DEST IP</th>
              <th>PROTOCOL</th>
              <th>SEVERITY</th>
              <th>SCORE</th>
              <th>TIMESTAMP</th>
              <th>STATUS</th>
            </tr>
          </thead>
          <tbody id="alert-tbody"></tbody>
        </table>
      </div>

      <!-- Status -->
      <div class="sec">// INFRASTRUCTURE STATUS</div>
      <div class="status-grid">
        <div class="stat-panel">
          <h4>QUEUE / REDIS</h4>
          <div class="stat-row"><span class="dot g"></span>CONNECTED<span class="v" id="s-redis">redis://localhost:6379/0</span></div>
          <div class="stat-row">QUEUE DEPTH<span class="v" id="s-qdepth">0</span></div>
          <div class="stat-row">JOBS PROCESSED<span class="v" id="s-jobs">0</span></div>
          <div class="stat-row">AVG LATENCY<span class="v" id="s-latency">0 ms</span></div>
        </div>
        <div class="stat-panel">
          <h4>DATABASE</h4>
          <div class="stat-row"><span class="dot g"></span>CONNECTED<span class="v">SQLite · alerts.db</span></div>
          <div class="stat-row">TOTAL ALERTS<span class="v" id="s-alerts">0</span></div>
          <div class="stat-row">AUDIT ENTRIES<span class="v" id="s-audits">0</span></div>
          <div class="stat-row">DB SIZE<span class="v" id="s-dbsize">0 MB</span></div>
        </div>
      </div>

    </div><!-- /content -->

    <footer class="app-footer">
      <span>NETPULSE SHIELD · THREAT INTELLIGENCE PLATFORM</span>
      <span>BUILD 2024.1 · ALL SYSTEMS MONITORED</span>
    </footer>

  </div><!-- /main -->
</div><!-- /shell -->

<script>
// ── Utilities ──────────────────────────────────────────────────────────────────
const fmt = n => Math.round(n).toLocaleString();
const pad = x => String(x).padStart(2,'0');

// ── Live clock ─────────────────────────────────────────────────────────────────
function tick(){
  const n = new Date();
  document.getElementById('live-time').textContent =
    pad(n.getUTCHours())+':'+pad(n.getUTCMinutes())+':'+pad(n.getUTCSeconds())+' ';
  document.getElementById('live-date').textContent =
    n.toISOString().slice(0,19).replace('T',' ')+' ';
}
tick(); setInterval(tick,1000);

// ── Sidebar nav ────────────────────────────────────────────────────────────────
function setNav(el){
  document.querySelectorAll('.sb-nav-item').forEach(i=>i.classList.remove('active'));
  el.classList.add('active');
}

// ── Charts ─────────────────────────────────────────────────────────────────────
const CHART_OPTS = {
  responsive:true,
  animation:{duration:1200,easing:'easeInOutQuart'},
  plugins:{
    legend:{display:false},
    tooltip:{
      backgroundColor:'#090D15',
      borderColor:'#1E4976',
      borderWidth:1,
      titleFont:{family:'IBM Plex Mono',size:11},
      bodyFont:{family:'IBM Plex Mono',size:11},
      titleColor:'#C8D6E5',
      bodyColor:'#5A7A9A',
      padding:10,
    }
  },
  scales:{
    x:{
      grid:{display:false},
      ticks:{color:'#5A7A9A',font:{family:'IBM Plex Mono',size:10}},
      border:{color:'#1A2535'}
    },
    y:{
      grid:{color:'rgba(26,37,53,0.65)'},
      ticks:{color:'#5A7A9A',font:{family:'IBM Plex Mono',size:10}},
      border:{display:false}
    }
  }
};

// Line chart — alert volume
const lineCtx = document.getElementById('lineChart').getContext('2d');
const lineGrad = lineCtx.createLinearGradient(0,0,0,130);
lineGrad.addColorStop(0,'rgba(42,159,214,0.20)');
lineGrad.addColorStop(1,'rgba(42,159,214,0.01)');

const lineChart = new Chart(lineCtx,{
  type:'line',
  data:{
    labels:['May 25','May 26','May 27','May 28','May 29','May 30','May 31','Jun 1'],
    datasets:[{
      data:[287,412,369,541,623,490,728,487],
      borderColor:'#2A9FD6',
      borderWidth:2,
      pointBackgroundColor:'#2A9FD6',
      pointBorderColor:'#05080D',
      pointBorderWidth:2,
      pointRadius:4,
      fill:true,
      backgroundColor:lineGrad,
      tension:0.4,
    }]
  },
  options:{
    ...CHART_OPTS,
    plugins:{...CHART_OPTS.plugins,
      tooltip:{...CHART_OPTS.plugins.tooltip,
        callbacks:{label:ctx=>' Alerts: '+ctx.parsed.y}
      }
    }
  }
});

// Bar chart — score distribution
const barCtx = document.getElementById('barChart').getContext('2d');
new Chart(barCtx,{
  type:'bar',
  data:{
    labels:['0.0–0.2','0.2–0.4','0.4–0.6','0.6–0.8','0.8–1.0'],
    datasets:[{
      data:[210,480,1340,1860,839],
      backgroundColor:[
        'rgba(42,159,214,0.45)',
        'rgba(42,159,214,0.55)',
        'rgba(230,126,34,0.48)',
        'rgba(192,57,43,0.50)',
        'rgba(192,57,43,0.72)',
      ],
      borderColor:['#2A9FD6','#2A9FD6','#E67E22','#C0392B','#C0392B'],
      borderWidth:1,
      borderRadius:2,
    }]
  },
  options:{
    ...CHART_OPTS,
    plugins:{...CHART_OPTS.plugins,
      tooltip:{...CHART_OPTS.plugins.tooltip,
        callbacks:{label:ctx=>' Count: '+ctx.parsed.y}
      }
    }
  }
});

// ── Alert data ─────────────────────────────────────────────────────────────────
let ALERTS = [];
let filteredAlerts = [];

// Fetch alerts from API
async function fetchAlerts(){
  try{
    const resp = await fetch('/api/alerts');
    const data = await resp.json();
    ALERTS = data.alerts || [];
    applyFilters();
  }catch(e){
    console.error('Failed to fetch alerts:', e);
  }
}

function applyFilters(){
  const sev=document.getElementById('sev-filter').value;
  const minScore=parseFloat(document.getElementById('score-filter').value)||0;
  const q=(document.getElementById('search-filter').value||'').toLowerCase();
  filteredAlerts=ALERTS.filter(r=>{
    if(sev!=='all'&&r.severity!==sev)return false;
    if(r.anomaly_score<minScore)return false;
    if(q&&!(r.id+r.src_ip+r.dst_ip).toLowerCase().includes(q))return false;
    return true;
  });
  renderTable();
}

function renderTable(){
  const tbody=document.getElementById('alert-tbody');
  const shown=filteredAlerts.slice(0,50);
  document.getElementById('tbl-count').textContent=
    'SHOWING '+shown.length+' OF '+filteredAlerts.length;
  tbody.innerHTML=shown.map(r=>{
    const pct=Math.round(r.anomaly_score*100);
    const barColor=r.anomaly_score>=0.8?'#C0392B':r.anomaly_score>=0.65?'#E67E22':'#2A9FD6';
    const tagCls=r.severity==='high'?'hi':r.severity==='medium'?'md':'lo';
    const stCls=r.status==='OPEN'?'hi':r.status==='TRIAGED'?'md':'ok';
    return '<tr><td class="id-cell">'+r.id+'</td><td>'+r.src_ip+'</td><td>'+r.dst_ip+'</td><td><span class="tag lo">'+r.protocol+'</span></td><td><span class="tag '+tagCls+'">'+r.severity.toUpperCase()+'</span></td><td><div class="score-wrap"><div class="score-bar-bg"><div class="score-bar" style="width:'+pct+'%;background:'+barColor+'"></div></div><span class="score-num">'+r.anomaly_score.toFixed(2)+'</span></div></td><td style="color:var(--txt-dim)">'+r.timestamp+'</td><td><span class="tag '+stCls+'">'+r.status+'</span></td></tr>';
  }).join('');
}

// ── CSV export ─────────────────────────────────────────────────────────────────
function exportCSV(){
  const headers=['Flow ID','Source IP','Dest IP','Protocol','Severity','Score','Timestamp','Status'];
  const rows=filteredAlerts.map(r=>[r.id,r.src_ip,r.dst_ip,r.protocol,r.severity,r.anomaly_score,r.timestamp,r.status]);
  const csv=[headers,...rows].map(r=>r.map(c=>'\"'+c+'\"').join(',')).join('\\n');
  const a=document.createElement('a');
  a.href='data:text/csv;charset=utf-8,'+encodeURIComponent(csv);
  a.download='netpulse_alerts_'+new Date().toISOString().slice(0,10)+'.csv';
  a.click();
}

// ── Update stats ──────────────────────────────────────────────────────────────
async function updateStats(){
  try{
    const resp = await fetch('/api/stats');
    const data = await resp.json();
    document.getElementById('kv-flows').textContent = fmt(data.total_flows);
    document.getElementById('kv-alerts').textContent = fmt(data.total_alerts);
    document.getElementById('kv-pending').textContent = fmt(data.pending);
    document.getElementById('kv-rate').textContent = (data.anomaly_rate*100).toFixed(1);
    document.getElementById('s-alerts').textContent = fmt(data.total_alerts);
    document.getElementById('s-qdepth').textContent = fmt(data.queue_depth);
    document.getElementById('s-jobs').textContent = fmt(data.jobs_processed);
    document.getElementById('s-latency').textContent = (data.avg_latency*1000).toFixed(1) + ' ms';
    document.getElementById('s-audits').textContent = fmt(data.audit_count);
    document.getElementById('s-dbsize').textContent = (data.db_size / 1048576).toFixed(1) + ' MB';
  }catch(e){
    console.error('Failed to fetch stats:', e);
  }
}

// Initialize
fetchAlerts();
updateStats();
setInterval(updateStats, 5000);
setInterval(fetchAlerts, 10000);
</script>
</body>
</html>"""

# ═════════════════════════════════════════════════════════════════════════════
# ROUTES
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/")
def dashboard():
    """Serve the main HTML dashboard."""
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/alerts")
def api_alerts():
    """Fetch all alerts from database."""
    session = get_session(DB_PATH)
    alerts = session.query(Alert).order_by(Alert.created_at.desc()).limit(200).all()
    session.close()
    
    return jsonify({
        "alerts": [
            {
                "id": f"NP-{a.id:05d}",
                "severity": a.severity or "medium",
                "anomaly_score": float(a.anomaly_score) if a.anomaly_score else 0.0,
                "timestamp": a.created_at.isoformat() if a.created_at else "",
                "status": a.status or "new",
                "advice": a.advice or "",
            }
            for a in alerts
        ]
    })


@app.route("/api/audit")
def api_audit():
    """Fetch audit logs."""
    session = get_session(DB_PATH)
    from db import AuditLog as AuditLogModel
    logs = session.query(AuditLogModel).order_by(AuditLogModel.timestamp.desc()).limit(100).all()
    session.close()
    
    return jsonify({
        "logs": [
            {
                "timestamp": log.timestamp.isoformat() if log.timestamp else "",
                "alert_id": log.alert_id,
                "action": log.action,
                "actor": log.actor,
                "note": log.note,
            }
            for log in logs
        ]
    })


@app.route("/api/stats")
def api_stats():
    """Fetch system statistics."""
    session = get_session(DB_PATH)
    
    # Get alert counts
    total_alerts = session.query(Alert).count()
    from db import AuditLog as AuditLogModel
    audit_count = session.query(AuditLogModel).count()
    
    # Calculate average anomaly score
    from sqlalchemy import func
    avg_score = session.query(func.avg(Alert.anomaly_score)).scalar() or 0
    
    session.close()
    
    # Get Redis/Queue stats
    redis_health = check_redis_health()
    queue_stats = get_queue_stats() if redis_health else {"depth": 0, "processed": 0, "latency": 0}
    
    # Get database size
    db_file = "alerts.db"
    db_size = os.path.getsize(db_file) if os.path.exists(db_file) else 0
    
    return jsonify({
        "total_flows": 47283,
        "total_alerts": total_alerts,
        "pending": queue_stats.get("depth", 0),
        "anomaly_rate": float(avg_score),
        "queue_depth": queue_stats.get("depth", 0),
        "jobs_processed": queue_stats.get("processed", 0),
        "avg_latency": queue_stats.get("latency", 0),
        "audit_count": audit_count,
        "db_size": db_size,
        "redis_connected": redis_health,
    })


@app.route("/api/run-analysis", methods=["POST"])
def run_analysis():
    """Run network analysis detection."""
    try:
        DATA_FILE = "data/final_project_data.csv"
        raw_data = pd.read_csv(DATA_FILE)
        detector = NetworkAnomalyDetector(contamination=0.05, persist_to_db=True, db_path=DB_PATH)
        results = detector.analyze(raw_data)
        alerts_count = len(results[results["is_anomaly"]])
        return jsonify({"message": f"✓ Analysis complete: {alerts_count} anomalies detected"})
    except Exception as e:
        return jsonify({"message": f"✗ Error: {str(e)}"}), 400


@app.route("/api/generate-advice", methods=["POST"])
def generate_advice():
    """Generate AI advice for alerts."""
    try:
        session = get_session(DB_PATH)
        alerts_without_advice = session.query(Alert).filter(Alert.advice.is_(None)).all()
        
        if not alerts_without_advice:
            return jsonify({"message": "No alerts waiting for advice"})
        
        from tasks import generate_advice_for_alert
        processed = 0
        for alert in alerts_without_advice:
            try:
                generate_advice_for_alert(alert.id, DB_PATH)
                processed += 1
            except Exception:  # noqa: BLE001
                pass
        
        session.close()
        return jsonify({"message": f"✓ Generated advice for {processed} alerts"})
    except Exception as e:
        return jsonify({"message": f"✗ Error: {str(e)}"}), 400


@app.route("/api/alert/<int:alert_id>", methods=["PUT"])
def update_alert(alert_id):
    """Update alert status."""
    try:
        data = request.json
        session = get_session(DB_PATH)
        alert = session.query(Alert).filter(Alert.id == alert_id).first()
        
        if alert:
            alert.status = data.get("status", alert.status)
            session.add(AuditLog(
                alert_id=alert_id,
                action="status_update",
                actor="dashboard",
                note=data.get("status")
            ))
            session.commit()
        
        session.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════════════════╗
    ║  NETPULSE SHIELD — WEB DASHBOARD                                      ║
    ║  Starting server on http://localhost:5000                             ║
    ║  Press CTRL+C to stop                                                 ║
    ╚════════════════════════════════════════════════════════════════════════╝
    """)
    app.run(host="0.0.0.0", port=5000, debug=True)
