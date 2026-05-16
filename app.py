import json, os, sys, subprocess, uuid, threading, re
from pathlib import Path
from flask import Flask, jsonify, render_template, request
import pandas as pd
import numpy as np
import plotly.utils
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

app = Flask(__name__)

DATA_FILE = BASE_DIR / "data" / "processed" / "final_project_data.csv"
ALERTS_FILE = BASE_DIR / "data" / "outputs" / "alerts.csv"
REPORT_FILE = BASE_DIR / "data" / "outputs" / "Security_Report.txt"
ALERTS_FALLBACK = BASE_DIR / "alerts.csv"
REPORT_FALLBACK = BASE_DIR / "Security_Report.txt"

def find_alerts():
    if ALERTS_FILE.exists(): return ALERTS_FILE
    if ALERTS_FALLBACK.exists(): return ALERTS_FALLBACK
    return None

def find_report():
    if REPORT_FILE.exists(): return REPORT_FILE
    if REPORT_FALLBACK.exists(): return REPORT_FALLBACK
    return None

def load_csv(path):
    if path and Path(path).exists():
        return pd.read_csv(path)
    return None

def find_col(df, names):
    if df is None: return None
    norm = {c.lower(): c for c in df.columns}
    for n in names:
        if n.lower() in norm: return norm[n.lower()]
    return None

# start of flask routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def api_status():
    data = load_csv(str(DATA_FILE)) if DATA_FILE.exists() else None
    alerts = load_csv(find_alerts())
    total_rec = len(data) if data is not None else 0
    total_alt = len(alerts) if alerts is not None else 0
    report = find_report()
    sev_col = find_col(alerts, ["severity", "risk_level"])
    crit = 0
    if alerts is not None and sev_col:
        crit = int(alerts[sev_col].astype(str).str.lower().isin(["critical", "high"]).sum())
    return jsonify({
        "data_file": DATA_FILE.name if DATA_FILE.exists() else None,
        "alerts_file": find_alerts().name if find_alerts() else None,
        "report_exists": report is not None,
        "total_records": total_rec,
        "total_alerts": total_alt,
        "normal_traffic": max(total_rec - total_alt, 0),
        "critical_count": crit,
    })

@app.route("/api/alerts")
def api_alerts():
    alerts = load_csv(find_alerts())
    if alerts is None:
        return jsonify([])
    return jsonify(json.loads(alerts.to_json(orient="records", date_format="iso")))

@app.route("/api/globe")
def api_globe():
    from cyber_attack_map import create_attack_globe
    alerts = load_csv(find_alerts())
    if alerts is None or alerts.empty:
        return jsonify(None)
    fig = create_attack_globe(alerts)
    if fig is None:
        return jsonify(None)
    return app.response_class(
        json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder),
        mimetype="application/json"
    )

@app.route("/api/graph")
def api_graph():
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics.pairwise import euclidean_distances
    import numpy as np

    # Use full dataset: include alert-matched rows + supplement with normal
    df_raw = load_csv(str(DATA_FILE)) if DATA_FILE.exists() else None
    if df_raw is None or df_raw.empty:
        return jsonify({"nodes": [], "edges": []})

    feat_cols = [c for c in ["sttl", "sbytes", "dbytes", "sload", "dload"] if c in df_raw.columns]
    if not feat_cols:
        return jsonify({"nodes": [], "edges": []})

    # Find exact raw data rows that match alerts
    alerts_df = load_csv(find_alerts())
    alert_row_indices = set()
    alert_score_map = {}
    if alerts_df is not None and not alerts_df.empty and "anomaly_score" in alerts_df.columns:
        for _, ar in alerts_df.iterrows():
            mask = True
            for c in feat_cols:
                mask = mask & (df_raw[c].round(4) == round(ar[c], 4))
            matches = df_raw[mask].index.tolist()
            for m in matches:
                alert_row_indices.add(m)
                ascore = float(ar.get("anomaly_score", 0))
                if m not in alert_score_map or abs(ascore) > abs(alert_score_map[m]):
                    alert_score_map[m] = ascore

    n_extra = max(0, 200 - len(alert_row_indices))
    other_indices = list(set(df_raw.index) - alert_row_indices)
    import random
    extra = random.sample(other_indices, min(n_extra, len(other_indices)))
    selected = sorted(alert_row_indices | set(extra))[:200]
    df = df_raw.loc[selected].reset_index(drop=True)

    # Remap alert indices after reset_index
    alert_indices = set()
    alert_score_map_remapped = {}
    for new_idx, orig_idx in enumerate(selected):
        if orig_idx in alert_row_indices:
            alert_indices.add(new_idx)
            alert_score_map_remapped[new_idx] = alert_score_map.get(orig_idx, 0)
    alert_score_map = alert_score_map_remapped

    X = df[feat_cols].fillna(0).values
    X_scaled = StandardScaler().fit_transform(X)
    similarity = 1.0 / (1.0 + euclidean_distances(X_scaled))

    def sev_color(score, is_alert):
        if not is_alert: return "#1a2332"
        try: s = float(score)
        except: return "#78909c"
        if s <= 0.3: return "#00e676"
        if s <= 0.6: return "#ffc107"
        if s <= 0.8: return "#ff9100"
        return "#ff1744"

    nodes = []
    for idx, row in df.iterrows():
        is_alert = idx in alert_indices
        score = alert_score_map.get(idx, 0.0)
        display = f"Row {idx}" + (" [ANOMALY]" if is_alert else "")
        fvals = " | ".join(f"{c}={row.get(c, ''):.1f}" for c in feat_cols)

        nodes.append({
            "id": str(idx),
            "label": display[:30],
            "title": f"<b>Row #{idx}</b><br><b>Alert:</b> {('Yes' if is_alert else 'No')}<br><b>Score:</b> {score:.4f}<br><b>Features:</b> {fvals}",
            "color": {"background": sev_color(score, is_alert), "border": sev_color(score, is_alert),
                       "highlight": {"background": "#fff", "border": sev_color(score, is_alert)}},
            "value": max(5, (10 if is_alert else 3)),
            "group": "critical" if is_alert else "normal",
            "anomaly_score": score,
            "is_alert": is_alert,
            "features": fvals,
        })

    threshold = 0.6
    edges = []
    adj_counts = {str(i): 0 for i in range(len(df))}
    for i in range(len(df)):
        for j in range(i + 1, len(df)):
            sim = float(similarity[i][j])
            if sim > threshold:
                adj_counts[str(i)] += 1
                adj_counts[str(j)] += 1
                edges.append({
                    "from": str(i), "to": str(j),
                    "value": round(sim * 3, 2),
                    "title": f"Similarity: {sim:.2f}",
                    "color": {"color": "rgba(255,255,255,0.12)", "highlight": "#00bcd4", "hover": "#00bcd4",
                              "opacity": max(0.08, sim - 0.4)},
                    "width": max(0.3, sim * 1.5),
                })

    for node in nodes:
        node["value"] = max(3, adj_counts[node["id"]] * 3 + (5 if node["is_alert"] else 0))

    alert_count = sum(1 for n in nodes if n["is_alert"])
    return jsonify({
        "nodes": nodes[:200],
        "edges": edges[:3000],
        "stats": {"nodes": len(nodes), "edges": len(edges), "alerts": alert_count}
    })

@app.route("/api/stats")
def api_stats():
    from cyber_attack_map import create_attack_statistics
    alerts = load_csv(find_alerts())
    stats = create_attack_statistics(alerts)
    return jsonify(stats)

@app.route("/api/data")
def api_data():
    data = load_csv(str(DATA_FILE)) if DATA_FILE.exists() else None
    if data is None:
        return jsonify({"rows": 0, "cols": 0, "columns": [], "preview": []})
    cols = data.select_dtypes(include=["int64", "float64"]).columns.tolist()
    return jsonify({
        "rows": data.shape[0],
        "cols": data.shape[1],
        "columns": cols,
        "preview": json.loads(data.head(100).to_json(orient="records")),
    })

@app.route("/api/report")
def api_report():
    report = find_report()
    text = report.read_text(encoding="utf-8", errors="ignore") if report else None
    return jsonify({"report": text})

# === Async pipeline runner ===
pipeline_tasks = {}
def _run_pipeline_async(action, mode, task_id):
    try:
        pipeline_tasks[task_id] = {"status": "running", "output": "", "error": ""}
        from pipeline_runner import PipelineRunner
        runner = PipelineRunner()
        actions = {
            "clean": lambda: runner.run_clean_data(),
            "detect": lambda: runner.run_detector(),
            "solver": lambda: runner.run_solver(),
            "report": lambda: runner.run_report(mode),
            "run-all": lambda: runner.run_full_pipeline(mode),
        }
        func = actions.get(action)
        if not func:
            pipeline_tasks[task_id] = {"status": "failed", "output": "", "error": f"Unknown: {action}"}
            return
        success, out, err = func()
        pipeline_tasks[task_id] = {"status": "done" if success else "failed", "output": out or "", "error": err or ""}
    except Exception as e:
        pipeline_tasks[task_id] = {"status": "failed", "output": "", "error": str(e)}

@app.route("/api/pipeline/<action>", methods=["POST"])
def api_pipeline(action):
    body = request.get_json(silent=True) or {}
    mode = body.get("mode", "rag")
    task_id = str(uuid.uuid4())
    t = threading.Thread(target=_run_pipeline_async, args=(action, mode, task_id), daemon=True)
    t.start()
    return jsonify({"task_id": task_id})

@app.route("/api/pipeline/status/<task_id>")
def api_pipeline_status(task_id):
    s = pipeline_tasks.get(task_id)
    if not s:
        # Clean up old tasks
        pipeline_tasks.pop(task_id, None)
        return jsonify({"status": "not_found"})
    # Clean up completed tasks after read
    if s["status"] in ("done", "failed"):
        result = dict(s)
        pipeline_tasks.pop(task_id, None)
        return jsonify(result)
    return jsonify(s)

@app.route("/api/timeline")
def api_timeline():
    from datetime import datetime, timedelta
    import random
    alerts = load_csv(find_alerts())
    n_alerts = len(alerts) if alerts is not None else 0
    now = datetime.now()
    hours = []
    seed = sum(ord(c) for c in str(datetime.now().minute))  # changes each minute
    rng = random.Random(seed)
    for i in range(24):
        t = now - timedelta(hours=23-i)
        base = n_alerts / 24.0
        noise = rng.uniform(-base * 0.5, base * 0.5)
        count = max(0, round(base + noise))
        hours.append({"hour": t.strftime("%H:00"), "count": count})
    return jsonify(hours)

@app.route("/api/alert/<int:alert_id>")
def api_alert_detail(alert_id):
    alerts = load_csv(find_alerts())
    if alerts is None or alert_id < 0 or alert_id >= len(alerts):
        return jsonify(None)
    row = alerts.iloc[alert_id].to_dict()
    for k, v in row.items():
        if isinstance(v, (pd.Timestamp, pd.Timestamp)):
            row[k] = str(v)
        elif isinstance(v, (np.floating,)):
            row[k] = float(v)
        elif isinstance(v, (np.integer,)):
            row[k] = int(v)
    return jsonify(row)

@app.route("/api/email/test", methods=["POST"])
def api_email_test():
    body = request.get_json(silent=True) or {}
    import smtplib
    try:
        s = smtplib.SMTP(body.get("server", "smtp.gmail.com"), int(body.get("port", 587)))
        s.starttls()
        s.login(body.get("email", ""), body.get("password", ""))
        s.quit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

def _build_email_html(alerts_csv, report_text):
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    score_col = "anomaly_score"

    total = len(alerts_csv) if alerts_csv is not None else 0
    worst = f"{alerts_csv[score_col].min():.4f}" if alerts_csv is not None and score_col in alerts_csv.columns and not alerts_csv.empty else "N/A"
    types_dict = alerts_csv["label"].value_counts().to_dict() if alerts_csv is not None and "label" in alerts_csv.columns and not alerts_csv.empty else {}
    types_str = ", ".join(f"{k}={v}" for k, v in list(types_dict.items())[:5])

    all_cols = list(alerts_csv.columns) if alerts_csv is not None and not alerts_csv.empty else []

    # Alert table
    table_rows = ""
    if alerts_csv is not None and not alerts_csv.empty:
        for _, r in alerts_csv.head(10).iterrows():
            cells = ""
            for c in all_cols:
                v = r.get(c, "")
                if isinstance(v, float): v = f"{v:.4f}"
                cells += f'<td style="padding:6px 10px;border-bottom:1px solid #1a2332;font-size:0.72rem;color:#c8d6e5;font-family:monospace;">{v}</td>'
            table_rows += f"<tr>{cells}</tr>"
    cols_html = "".join(
        f'<th style="padding:8px 10px;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.5px;color:#00bcd4;border-bottom:1px solid #1a2332;background:#0d111c;text-align:left;font-weight:600;">{c}</th>'
        for c in all_cols
    )

    # Parse report text into threat cards
    threat_cards_html = ""
    if report_text and report_text.strip():
        lines = report_text.split("\n")
        in_threat = False
        threat_num = 0
        for i, line in enumerate(lines):
            t = line.strip()
            m = re.match(r"^THREAT\s*#(\d+)", t, re.IGNORECASE)
            if m:
                if in_threat:
                    threat_cards_html += "</td></tr></table></td></tr>"
                threat_num = int(m.group(1))
                sev = "critical" if threat_num <= 2 else ("high" if threat_num <= 4 else "medium")
                sev_colors = {"critical": {"border": "#ff1744", "bg": "rgba(255,23,68,0.12)", "text": "#ff1744", "dot": "#ff1744"},
                              "high": {"border": "#ff9100", "bg": "rgba(255,145,0,0.12)", "text": "#ff9100", "dot": "#ff9100"},
                              "medium": {"border": "#ffc107", "bg": "rgba(255,193,7,0.12)", "text": "#ffc107", "dot": "#ffc107"}}
                c = sev_colors[sev]
                threat_cards_html += f"""
<tr><td style="background:#0d111c;border:1px solid #1a2332;border-left:3px solid {c['border']};border-radius:10px;padding:16px 20px;margin-bottom:14px;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td style="padding-bottom:10px;">
<table width="100%"><tr>
<td><span style="display:inline-block;padding:3px 12px;border-radius:5px;font-size:0.7rem;font-weight:700;color:#fff;background:{c['border']};letter-spacing:0.5px;">THREAT #{threat_num}</span></td>
<td align="right"><span style="display:inline-block;padding:2px 10px;border-radius:20px;font-size:0.55rem;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;background:{c['bg']};color:{c['text']};border:1px solid {c['border']}33;">{sev.upper()}</span></td>
</tr></table>
</td></tr>"""
                in_threat = True
                continue
            if not in_threat:
                continue
            if re.match(r"^-{3,}$", t):
                continue
            if re.match(r"^Symptoms:", t, re.IGNORECASE):
                val = re.sub(r"^Symptoms:\s*", "", t, flags=re.IGNORECASE)
                threat_cards_html += f"""<tr><td style="padding:2px 0 4px;">
<div style="font-size:0.62rem;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#546e7a;margin:6px 0 3px;"><span style="color:#546e7a;">&#9881;</span> Symptoms</div>
<div style="background:#070b14;border:1px solid #1a2332;border-radius:6px;padding:8px 12px;font-family:monospace;font-size:0.7rem;color:#78909c;line-height:1.5;word-break:break-all;margin-top:2px;">{val}</div>
</td></tr>"""
                continue
            if re.match(r"^Remediation:\s*$", t, re.IGNORECASE):
                threat_cards_html += f"""<tr><td style="padding:4px 0 2px;"><div style="font-size:0.62rem;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#00bcd4;margin:8px 0 3px;"><span style="color:#00bcd4;">&#9724;</span> Remediation Steps</div></td></tr>"""
                continue
            if re.match(r"^Remediation:", t, re.IGNORECASE):
                val = re.sub(r"^Remediation:\s*", "", t, flags=re.IGNORECASE)
                if val:
                    threat_cards_html += f"""<tr><td style="padding:2px 0;"><div style="font-size:0.7rem;color:#78909c;">{val}</div></td></tr>"""
                continue
            gm = re.match(r"^\[Guidance\s*(\d+)\]", t, re.IGNORECASE)
            if gm:
                threat_cards_html += f"""<tr><td style="padding:4px 0 2px;"><span style="display:inline-flex;align-items:center;gap:5px;font-size:0.65rem;font-weight:600;color:#00bcd4;padding:3px 8px;border-radius:5px;background:rgba(0,188,212,0.06);">&#128214; Guidance {gm.group(1)}</span></td></tr>"""
                continue
            if re.match(r"^#\s+", t):
                topic = re.sub(r"^#\s*", "", t)
                threat_cards_html += f"""<tr><td style="background:rgba(0,0,0,0.2);border:1px solid #1a2332;border-radius:7px;padding:8px 12px;margin:4px 0;">
<div style="font-size:0.72rem;font-weight:600;color:#ff8a65;margin-bottom:3px;">&#128027; {topic}</div>"""
                j = i + 1
                while j < len(lines):
                    nj = lines[j].strip()
                    if re.match(r"^#\s+", nj) or re.match(r"^THREAT\s", nj, re.IGNORECASE) or re.match(r"^={3,}", nj):
                        break
                    if re.match(r"^Indicators:", nj, re.IGNORECASE):
                        ind_val = re.sub(r"^Indicators:\s*", "", nj, flags=re.IGNORECASE)
                        threat_cards_html += f"""<div style="font-size:0.68rem;color:#78909c;padding:2px 0;"><strong style="color:#e0e0e0;">Indicators:</strong> {ind_val}</div>"""
                    elif re.match(r"^\d+\.\s", nj):
                        step_text = re.sub(r"^\d+\.\s*", "", nj)
                        step_num = re.match(r"^\d+", nj).group()
                        threat_cards_html += f"""<div style="display:flex;align-items:flex-start;gap:6px;padding:2px 0;font-size:0.68rem;color:#b0bec5;"><span style="display:inline-flex;align-items:center;justify-content:center;width:17px;height:17px;border-radius:50%;background:rgba(0,188,212,0.12);color:#00bcd4;font-size:0.55rem;font-weight:700;flex-shrink:0;margin-top:2px;">{step_num}</span>{step_text}</div>"""
                    elif nj:
                        threat_cards_html += f"""<div style="font-size:0.7rem;color:#78909c;padding:1px 0;">{nj}</div>"""
                    j += 1
                threat_cards_html += "</td></tr>"
                i = j - 1
                continue
            if re.match(r"^Indicators:", t, re.IGNORECASE):
                ind_val = re.sub(r"^Indicators:\s*", "", t, flags=re.IGNORECASE)
                threat_cards_html += f"""<tr><td style="padding:2px 0;"><div style="font-size:0.68rem;color:#78909c;"><strong style="color:#e0e0e0;">Indicators:</strong> {ind_val}</div></td></tr>"""
                continue
            nm = re.match(r"^(\d+)\.\s(.+)", t)
            if nm:
                threat_cards_html += f"""<tr><td style="padding:2px 0;"><div style="display:flex;align-items:flex-start;gap:6px;font-size:0.68rem;color:#b0bec5;"><span style="display:inline-flex;align-items:center;justify-content:center;width:17px;height:17px;border-radius:50%;background:rgba(0,188,212,0.12);color:#00bcd4;font-size:0.55rem;font-weight:700;flex-shrink:0;margin-top:2px;">{nm.group(1)}</span>{nm.group(2)}</div></td></tr>"""
                continue
            if t:
                threat_cards_html += f"""<tr><td style="padding:2px 0;"><div style="font-size:0.7rem;color:#78909c;">{t}</div></td></tr>"""
        if in_threat:
            threat_cards_html += "</td></tr></table></td></tr>"

    # Sections spacer
    threat_section = ""
    if threat_cards_html:
        threat_section = f"""
<tr><td style="background:#0d111c;border:1px solid #1a2332;border-top:none;padding:0 28px 8px;">
<h3 style="font-size:0.8rem;font-weight:600;color:#e0e0e0;margin:0 0 6px;padding-top:8px;border-top:1px solid #1a2332;">&#9889; Threat Analysis</h3>
</td></tr>
{threat_cards_html}"""

    # Severity dot helper
    def sev_dot(score_val):
        try:
            s = float(score_val)
        except (ValueError, TypeError):
            return "#546e7a"
        if s <= 0.3: return "#00e676"
        if s <= 0.6: return "#ffc107"
        if s <= 0.8: return "#ff9100"
        return "#ff1744"

    alert_items_html = ""
    if alerts_csv is not None and not alerts_csv.empty:
        for _, r in alerts_csv.head(5).iterrows():
            sv = r.get(score_col, "")
            label = str(r.get("label", r.get("attack_cat", "Unknown")))
            dot = sev_dot(sv)
            alert_items_html += f"""<tr><td style="padding:4px 0;"><table width="100%"><tr>
<td width="8"><span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:{dot};margin-right:6px;"></span></td>
<td style="font-size:0.72rem;color:#c8d6e5;">{label}</td>
<td align="right" style="font-size:0.65rem;color:#78909c;font-family:monospace;">{sv}</td>
</tr></table></td></tr>"""

    threat_count = report_text.count("THREAT #") if report_text else 0

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>
  @media only screen and (max-width:600px) {{ .container {{ width:100% !important; }} .inner {{ padding:16px !important; }} .card-pad {{ padding:16px !important; }} .hide-mobile {{ display:none !important; }} }}
</style>
</head>
<body style="margin:0;padding:0;background:#070b14;font-family:Inter,'Segoe UI',system-ui,sans-serif;-webkit-font-smoothing:antialiased;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#070b14;padding:30px 20px;">
<tr><td align="center">
<table class="container" width="640" cellpadding="0" cellspacing="0" style="max-width:640px;">

<!-- HERO -->
<tr><td style="background:linear-gradient(135deg,#0d111c,#141c2b);border-radius:14px 14px 0 0;border:1px solid #1a2332;border-bottom:none;padding:32px 28px 20px;text-align:center;">
<div style="font-size:2.2rem;margin-bottom:6px;">&#9724;</div>
<div style="font-size:1.3rem;font-weight:700;color:#e0e0e0;letter-spacing:-0.3px;">Security Assessment Report</div>
<div style="font-size:0.72rem;color:#78909c;margin-top:4px;">NetPulse-Shield &mdash; AI-Powered Network Threat Analysis</div>
<div style="margin-top:16px;display:flex;justify-content:center;gap:8px;">
<span style="background:rgba(255,23,68,0.10);border:1px solid rgba(255,23,68,0.15);border-radius:20px;padding:2px 12px;font-size:0.6rem;font-weight:600;color:#ff1744;text-transform:uppercase;letter-spacing:0.5px;">Confidential</span>
<span style="background:rgba(0,188,212,0.08);border:1px solid rgba(0,188,212,0.12);border-radius:20px;padding:2px 12px;font-size:0.6rem;font-weight:600;color:#00bcd4;text-transform:uppercase;letter-spacing:0.5px;">AI Analysis</span>
</div>
</td></tr>

<!-- META BAR -->
<tr><td style="background:#0d111c;border:1px solid #1a2332;border-top:none;border-bottom:none;padding:4px 28px;">
<table width="100%"><tr>
<td style="font-size:0.6rem;color:#546e7a;padding:6px 0;"><span style="color:#78909c;">&#128197;</span> {now}</td>
<td align="center" style="font-size:0.6rem;color:#546e7a;padding:6px 0;"><span style="color:#78909c;">&#9888;</span> {total} Alerts</td>
<td align="right" style="font-size:0.6rem;color:#546e7a;padding:6px 0;"><span style="color:#78909c;">&#128520;</span> {threat_count} Threats</td>
</tr></table>
</td></tr>

<!-- SUMMARY CARDS ROW -->
<tr><td style="background:#0d111c;border:1px solid #1a2332;border-top:none;border-bottom:none;padding:12px 28px;">
<table width="100%"><tr>
<td align="center" style="background:#070b14;border-radius:10px;padding:12px 8px;border:1px solid #1a2332;width:33%;">
<div style="font-size:1.6rem;font-weight:700;color:#00bcd4;font-family:monospace;">{total}</div>
<div style="font-size:0.55rem;color:#546e7a;text-transform:uppercase;letter-spacing:0.8px;margin-top:2px;">Total Alerts</div>
</td>
<td align="center" style="background:#070b14;border-radius:10px;padding:12px 8px;border:1px solid #1a2332;width:33%;">
<div style="font-size:1.6rem;font-weight:700;color:#ff1744;font-family:monospace;">{worst}</div>
<div style="font-size:0.55rem;color:#546e7a;text-transform:uppercase;letter-spacing:0.8px;margin-top:2px;">Worst Score</div>
</td>
<td align="center" style="background:#070b14;border-radius:10px;padding:12px 8px;border:1px solid #1a2332;width:33%;">
<div style="font-size:0.7rem;font-weight:600;color:#ffc107;font-family:monospace;word-break:break-all;">{types_str}</div>
<div style="font-size:0.55rem;color:#546e7a;text-transform:uppercase;letter-spacing:0.8px;margin-top:2px;">Types</div>
</td>
</tr></table>
</td></tr>

<!-- ALERTS SECTION -->
<tr><td style="background:#0d111c;border:1px solid #1a2332;border-top:none;border-bottom:none;padding:16px 28px 4px;">
<h3 style="font-size:0.75rem;font-weight:600;color:#e0e0e0;margin:0 0 8px;display:flex;align-items:center;gap:6px;"><span style="color:#00bcd4;">&#9881;</span> Top Alerts</h3>
<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
<thead><tr>{cols_html}</tr></thead>
<tbody>{table_rows}</tbody>
</table>
</td></tr>

<!-- THREAT ANALYSIS -->
{threat_section}

<!-- FOOTER -->
<tr><td style="background:linear-gradient(135deg,#0d111c,#141c2b);border:1px solid #1a2332;border-top:none;border-radius:0 0 14px 14px;padding:18px 28px;text-align:center;">
<div style="font-size:0.55rem;color:#546e7a;letter-spacing:0.3px;line-height:1.6;">This is an automated report from NetPulse-Shield &bull; AI Network Security &bull; Local-First</div>
<div style="font-size:0.5rem;color:#37474f;margin-top:4px;">Confidential — intended for the designated security team only</div>
</td></tr>

</table>
</td></tr></table>
</body></html>"""

@app.route("/api/email/send", methods=["POST"])
def api_email_send():
    body = request.get_json(silent=True) or {}
    try:
        email = body.get("email") or os.getenv("EMAIL_SENDER", "")
        password = body.get("password") or os.getenv("EMAIL_PASSWORD", "")
        server = body.get("server") or os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
        port = int(body.get("port") or os.getenv("EMAIL_SMTP_PORT", "587"))

        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from datetime import datetime

        alerts_csv = load_csv(find_alerts())
        score_col = "anomaly_score"
        if alerts_csv is not None and not alerts_csv.empty and score_col in alerts_csv.columns:
            alerts_csv = alerts_csv.sort_values(score_col, ascending=True)

        total = len(alerts_csv) if alerts_csv is not None else 0
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Load report text
        report_path = find_report()
        report_text = ""
        if report_path:
            try:
                report_text = report_path.read_text(encoding="utf-8")
            except Exception:
                pass

        # Build HTML
        html = _build_email_html(alerts_csv, report_text)

        msg = MIMEMultipart("alternative")
        msg["From"] = email
        msg["To"] = body.get("recipient", "")
        msg["Subject"] = f"NetPulse-Shield Security Report ({total} alerts, {now})"

        # Plain text fallback
        worst = f"{alerts_csv[score_col].min():.4f}" if alerts_csv is not None and score_col in alerts_csv.columns and not alerts_csv.empty else "N/A"
        text_plain = f"NetPulse-Shield Security Report\n{now}\nTotal alerts: {total}\nWorst score: {worst}\n"
        if alerts_csv is not None and not alerts_csv.empty:
            text_plain += "\nTop 10 Alerts:\n"
            for _, r in alerts_csv.head(10).iterrows():
                parts = [f"{c}={r.get(c, '')}" for c in list(alerts_csv.columns)[:6]]
                text_plain += "  " + " | ".join(parts) + "\n"
        msg.attach(MIMEText(text_plain, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(server, port) as s:
            s.starttls()
            s.login(email, password)
            s.send_message(msg)

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/email/config", methods=["GET", "POST"])
def api_email_config():
    if request.method == "GET":
        return jsonify({
            "EMAIL_SENDER": os.getenv("EMAIL_SENDER", ""),
            "EMAIL_PASSWORD": os.getenv("EMAIL_PASSWORD", ""),
            "EMAIL_SMTP_SERVER": os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com"),
            "EMAIL_SMTP_PORT": os.getenv("EMAIL_SMTP_PORT", "587"),
            "RECEIVER_EMAIL": os.getenv("RECEIVER_EMAIL", ""),
            "WEEKLY_REPORT_DAY": os.getenv("WEEKLY_REPORT_DAY", "0"),
            "WEEKLY_REPORT_TIME": os.getenv("WEEKLY_REPORT_TIME", "09:00"),
            "ATTACK_THRESHOLD_PERCENTAGE": os.getenv("ATTACK_THRESHOLD_PERCENTAGE", "80"),
        })
    body = request.get_json(silent=True) or {}
    try:
        env_path = BASE_DIR / ".env"
        # Read existing .env lines
        existing = {}
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if "=" in line:
                    k, v = line.split("=", 1)
                    existing[k.strip()] = v.strip()
        # Update with new values
        for k, v in body.items():
            if v is not None:
                existing[k.upper()] = str(v)
        # Write back
        with open(env_path, "w", encoding="utf-8") as f:
            for k, v in existing.items():
                f.write(f"{k}={v}\n")
        # Reload env
        load_dotenv(override=True)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    import webbrowser
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        webbrowser.open("http://localhost:5000")
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=5000)
