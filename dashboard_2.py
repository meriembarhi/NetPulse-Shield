import streamlit as st
import streamlit.components.v1 as components

# Configure page — hide default Streamlit UI
st.set_page_config(
    page_title="NetPulse Shield — Control Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stDecoration"] { display: none; }
    .stApp { padding: 0; margin: 0; background: #05080D; }
    .main { padding: 0; margin: 0; }
    </style>
    """, unsafe_allow_html=True)

# HTML dashboard content
html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NetPulse Shield — Control Center</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;700&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}html,body{height:100%;overflow:hidden}
:root{--bg:#05080D;--surf:#090D15;--panel:#0C1118;--bdr:#1A2535;--bdr-hot:#1E4976;--acc:#2A9FD6;--acc-dim:rgba(42,159,214,0.12);--danger:#C0392B;--danger-dim:rgba(192,57,43,0.14);--warn:#E67E22;--warn-dim:rgba(230,126,34,0.12);--ok:#27AE60;--ok-dim:rgba(39,174,96,0.12);--txt:#C8D6E5;--txt-dim:#5A7A9A;--txt-faint:#1E3A5A;--mono:'IBM Plex Mono',monospace;--sans:'IBM Plex Sans',sans-serif;}
body{font-family:var(--sans);background:var(--bg);color:var(--txt);font-size:13px;}
body::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:9000;background-image:repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,0,0,0.055) 3px,rgba(0,0,0,0.055) 4px);}
.sweep-bar{position:fixed;top:0;left:0;right:0;height:2px;z-index:9001;background:linear-gradient(90deg,transparent 0%,var(--acc) 35%,#7FD8F5 50%,var(--acc) 65%,transparent 100%);background-size:200% 100%;animation:sweep 3.5s linear infinite;}
@keyframes sweep{0%{background-position:200% 0}100%{background-position:-200% 0}}
.shell{display:grid;grid-template-columns:210px 1fr;height:100vh;overflow:hidden;}
.sidebar{background:var(--surf);border-right:1px solid var(--bdr);display:flex;flex-direction:column;overflow:hidden;}
.sb-logo{padding:20px 18px 16px;border-bottom:1px solid var(--bdr);flex-shrink:0;}
.sb-logo-name{font-family:var(--mono);font-size:0.65rem;font-weight:700;letter-spacing:0.22em;color:var(--acc);line-height:1.5;}
.sb-logo-sub{font-family:var(--mono);font-size:0.46rem;letter-spacing:0.28em;color:var(--txt-faint);margin-top:4px;}
.sb-nav{padding:14px 0;flex:1;}
.sb-nav-label{font-family:var(--mono);font-size:0.46rem;letter-spacing:0.24em;color:var(--txt-faint);padding:0 18px 8px;}
.sb-nav-item{display:flex;align-items:center;gap:10px;padding:10px 18px;font-family:var(--mono);font-size:0.62rem;letter-spacing:0.06em;color:var(--txt-dim);cursor:pointer;border-left:2px solid transparent;transition:all 0.15s ease;user-select:none;}
.sb-nav-item:hover,.sb-nav-item.active{background:var(--acc-dim);color:var(--acc);border-left-color:var(--acc);}
.sb-nav-item svg{width:13px;height:13px;flex-shrink:0;opacity:0.7;}
.sb-nav-item.active svg{opacity:1;}
.sb-footer{padding:14px 18px;border-top:1px solid var(--bdr);flex-shrink:0;}
.sb-footer-time{font-family:var(--mono);font-size:0.56rem;color:var(--txt-faint);line-height:2.1;}
.sb-footer-time b{color:var(--txt-dim);display:block;font-size:0.62rem;}
.main{display:flex;flex-direction:column;overflow:hidden;min-width:0;}
.topbar{display:flex;align-items:center;justify-content:space-between;padding:14px 26px;border-bottom:1px solid var(--bdr);background:var(--surf);flex-shrink:0;}
.topbar-title{font-family:var(--mono);font-size:0.88rem;font-weight:700;letter-spacing:0.04em;display:flex;align-items:center;gap:8px;}
.topbar-title .acc{color:var(--acc);}
.topbar-title .dim{font-weight:300;color:var(--txt-dim);font-size:0.70rem;}
.cursor{animation:blink 1.1s step-end infinite;color:var(--acc);}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}
.topbar-right{display:flex;align-items:center;gap:16px;}
.topbar-ts{font-family:var(--mono);font-size:0.50rem;color:var(--txt-faint);text-align:right;line-height:2;letter-spacing:0.1em;}
.topbar-ts b{color:var(--txt-dim);display:block;font-size:0.60rem;}
.live-badge{font-family:var(--mono);font-size:0.46rem;letter-spacing:0.18em;background:var(--acc-dim);border:1px solid var(--bdr-hot);color:var(--acc);padding:3px 9px;border-radius:2px;display:flex;align-items:center;gap:5px;}
.live-badge::before{content:'';width:5px;height:5px;border-radius:50%;background:var(--acc);display:inline-block;animation:pdot 1.8s ease-in-out infinite;}
.content{flex:1;overflow-y:auto;padding:20px 26px 32px;display:flex;flex-direction:column;gap:20px;}
.content::-webkit-scrollbar{width:5px;}
.content::-webkit-scrollbar-track{background:var(--bg);}
.content::-webkit-scrollbar-thumb{background:#1E3A5A;border-radius:2px;}
.sec{font-family:var(--mono);font-size:0.50rem;letter-spacing:0.22em;color:var(--acc);border-bottom:1px solid var(--bdr);padding-bottom:6px;}
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;}
.kpi{background:var(--panel);border:1px solid var(--bdr);border-radius:3px;padding:15px 17px;position:relative;overflow:hidden;cursor:default;transition:border-color 0.2s,box-shadow 0.2s;}
.kpi::before{content:'';position:absolute;left:0;top:0;bottom:0;width:2px;border-radius:0;}
.kpi.c::before{background:var(--acc);}
.kpi.r::before{background:var(--danger);}
.kpi.a::before{background:var(--warn);}
.kpi.g::before{background:var(--ok);}
.kpi:hover{border-color:var(--bdr-hot);box-shadow:0 0 22px rgba(42,159,214,0.07);}
.kpi-label{font-family:var(--mono);font-size:0.48rem;letter-spacing:0.18em;color:var(--txt-dim);margin-bottom:9px;}
.kpi-val{font-family:var(--mono);font-size:1.6rem;font-weight:700;line-height:1;transition:color 0.3s;}
.kpi.c .kpi-val{color:var(--acc);}
.kpi.r .kpi-val{color:var(--danger);}
.kpi.a .kpi-val{color:var(--warn);}
.kpi.g .kpi-val{color:var(--ok);}
.kpi-sub{font-family:var(--mono);font-size:0.48rem;color:var(--txt-faint);margin-top:7px;}
.charts{display:grid;grid-template-columns:1.8fr 1fr;gap:12px;}
.chart-panel{background:var(--panel);border:1px solid var(--bdr);border-radius:3px;padding:15px 17px;}
.chart-eyebrow{font-family:var(--mono);font-size:0.48rem;letter-spacing:0.18em;color:var(--txt-dim);margin-bottom:12px;}
.filter-bar{display:flex;align-items:center;gap:10px;background:var(--panel);border:1px solid var(--bdr);border-radius:3px;padding:10px 14px;}
.filter-label{font-family:var(--mono);font-size:0.50rem;letter-spacing:0.14em;color:var(--txt-faint);flex-shrink:0;}
.filter-input{font-family:var(--mono);font-size:0.68rem;background:var(--surf);border:1px solid var(--bdr);border-radius:2px;color:var(--txt);padding:5px 10px;outline:none;transition:border-color 0.15s;}
.filter-input:focus{border-color:var(--acc);}
.filter-input::placeholder{color:var(--txt-faint);}
select.filter-input option{background:var(--panel);}
.filter-sep{width:1px;height:20px;background:var(--bdr);flex-shrink:0;}
.filter-btn{font-family:var(--mono);font-size:0.54rem;letter-spacing:0.12em;background:var(--acc-dim);border:1px solid var(--bdr-hot);color:var(--acc);padding:5px 14px;border-radius:2px;cursor:pointer;transition:all 0.15s;margin-left:auto;}
.filter-btn:hover{background:rgba(42,159,214,0.22);color:#fff;border-color:var(--acc);}
.tbl-wrap{background:var(--panel);border:1px solid var(--bdr);border-radius:3px;overflow:hidden;}
.tbl-header{display:flex;align-items:center;justify-content:space-between;padding:10px 14px;border-bottom:1px solid var(--bdr);background:var(--surf);}
.tbl-header-title{font-family:var(--mono);font-size:0.50rem;letter-spacing:0.16em;color:var(--txt-dim);}
.tbl-count{font-family:var(--mono);font-size:0.50rem;color:var(--txt-faint);letter-spacing:0.1em;}
table{width:100%;border-collapse:collapse;}
th{font-family:var(--mono);font-size:0.46rem;letter-spacing:0.16em;color:var(--txt-dim);background:rgba(9,13,21,0.6);padding:8px 12px;text-align:left;border-bottom:1px solid var(--bdr);white-space:nowrap;}
td{font-family:var(--mono);font-size:0.62rem;color:var(--txt);padding:7px 12px;border-bottom:1px solid rgba(26,37,53,0.5);white-space:nowrap;}
tr:last-child td{border-bottom:none;}
tr:hover td{background:rgba(42,159,214,0.04);}
.id-cell{color:var(--acc);}
.tag{display:inline-block;font-family:var(--mono);font-size:0.44rem;letter-spacing:0.1em;padding:2px 8px;border-radius:2px;}
.tag.hi{background:rgba(192,57,43,0.18);color:#E57373;border:1px solid rgba(192,57,43,0.3);}
.tag.md{background:rgba(230,126,34,0.15);color:#FFB74D;border:1px solid rgba(230,126,34,0.28);}
.tag.lo{background:rgba(42,159,214,0.12);color:#64B5F6;border:1px solid rgba(42,159,214,0.25);}
.tag.ok{background:rgba(39,174,96,0.12);color:#81C784;border:1px solid rgba(39,174,96,0.25);}
.score-wrap{display:flex;align-items:center;gap:8px;}
.score-bar-bg{width:72px;height:4px;background:var(--bdr);border-radius:2px;overflow:hidden;}
.score-bar{height:100%;border-radius:2px;}
.score-num{font-size:0.54rem;color:var(--txt-dim);}
.status-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.stat-panel{background:var(--panel);border:1px solid var(--bdr);border-radius:3px;padding:15px 17px;}
.stat-panel h4{font-family:var(--mono);font-size:0.50rem;letter-spacing:0.2em;color:var(--acc);margin-bottom:12px;padding-bottom:6px;border-bottom:1px solid var(--bdr);}
.stat-row{display:flex;align-items:center;font-family:var(--mono);font-size:0.60rem;color:var(--txt-dim);padding:6px 0;border-bottom:1px solid rgba(30,58,90,0.4);gap:6px;}
.stat-row:last-child{border-bottom:none;}
.stat-row .v{color:var(--txt);margin-left:auto;font-size:0.58rem;}
@keyframes pdot{0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.4;transform:scale(0.75)}}
.dot{display:inline-block;width:6px;height:6px;border-radius:50%;flex-shrink:0;animation:pdot 2s ease-in-out infinite;}
.dot.g{background:var(--ok);}
.dot.r{background:var(--danger);}
.dot.a{background:var(--warn);}
.app-footer{padding:9px 26px;border-top:1px solid var(--bdr);display:flex;justify-content:space-between;align-items:center;font-family:var(--mono);font-size:0.46rem;letter-spacing:0.14em;color:var(--txt-faint);flex-shrink:0;background:var(--surf);}
</style>
</head>
<body>
<div class="sweep-bar"></div>
<div class="shell">
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
  <div class="main">
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
    <div class="content">
      <div class="sec">// SYSTEM OVERVIEW</div>
      <div class="kpi-grid">
        <div class="kpi c">
          <div class="kpi-label">TOTAL FLOWS</div>
          <div class="kpi-val" id="kv-flows">47,283</div>
          <div class="kpi-sub">captured packets</div>
        </div>
        <div class="kpi r">
          <div class="kpi-label">TOTAL ALERTS</div>
          <div class="kpi-val" id="kv-alerts">4,729</div>
          <div class="kpi-sub">anomalies flagged</div>
        </div>
        <div class="kpi a">
          <div class="kpi-label">ADVICE PENDING</div>
          <div class="kpi-val" id="kv-pending">312</div>
          <div class="kpi-sub">awaiting triage</div>
        </div>
        <div class="kpi g">
          <div class="kpi-label">ANOMALY RATE</div>
          <div class="kpi-val" id="kv-rate">10.0<span style="font-size:1.1rem">%</span></div>
          <div class="kpi-sub">contamination factor</div>
        </div>
      </div>
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
      <div class="sec">// INFRASTRUCTURE STATUS</div>
      <div class="status-grid">
        <div class="stat-panel">
          <h4>QUEUE / REDIS</h4>
          <div class="stat-row"><span class="dot g"></span>CONNECTED<span class="v">redis://localhost:6379/0</span></div>
          <div class="stat-row">QUEUE DEPTH<span class="v" id="s-qdepth">312</span></div>
          <div class="stat-row">JOBS PROCESSED<span class="v">4,417</span></div>
          <div class="stat-row">AVG LATENCY<span class="v">4.2 ms</span></div>
        </div>
        <div class="stat-panel">
          <h4>DATABASE</h4>
          <div class="stat-row"><span class="dot g"></span>CONNECTED<span class="v">SQLite · alerts.db</span></div>
          <div class="stat-row">TOTAL ALERTS<span class="v" id="s-alerts">4,729</span></div>
          <div class="stat-row">AUDIT ENTRIES<span class="v">19,302</span></div>
          <div class="stat-row">DB SIZE<span class="v">14.2 MB</span></div>
        </div>
      </div>
    </div>
    <footer class="app-footer">
      <span>NETPULSE SHIELD · THREAT INTELLIGENCE PLATFORM</span>
      <span>BUILD 2024.1 · ALL SYSTEMS MONITORED</span>
    </footer>
  </div>
</div>
<script>
const fmt = n => Math.round(n).toLocaleString();
const pad = x => String(x).padStart(2,'0');
function tick(){
  const n = new Date();
  document.getElementById('live-time').textContent = pad(n.getUTCHours())+':'+pad(n.getUTCMinutes())+':'+pad(n.getUTCSeconds())+' ';
  document.getElementById('live-date').textContent = n.toISOString().slice(0,19).replace('T',' ')+' ';
}
tick(); setInterval(tick,1000);
function setNav(el){
  document.querySelectorAll('.sb-nav-item').forEach(i=>i.classList.remove('active'));
  el.classList.add('active');
}
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
  options:{...CHART_OPTS,plugins:{...CHART_OPTS.plugins,tooltip:{...CHART_OPTS.plugins.tooltip,callbacks:{label:ctx=>' Alerts: '+ctx.parsed.y}}}}
});
const barCtx = document.getElementById('barChart').getContext('2d');
new Chart(barCtx,{
  type:'bar',
  data:{
    labels:['0.0–0.2','0.2–0.4','0.4–0.6','0.6–0.8','0.8–1.0'],
    datasets:[{
      data:[210,480,1340,1860,839],
      backgroundColor:['rgba(42,159,214,0.45)','rgba(42,159,214,0.55)','rgba(230,126,34,0.48)','rgba(192,57,43,0.50)','rgba(192,57,43,0.72)'],
      borderColor:['#2A9FD6','#2A9FD6','#E67E22','#C0392B','#C0392B'],
      borderWidth:1,
      borderRadius:2,
    }]
  },
  options:{...CHART_OPTS,plugins:{...CHART_OPTS.plugins,tooltip:{...CHART_OPTS.plugins.tooltip,callbacks:{label:ctx=>' Count: '+ctx.parsed.y}}}}
});
const ALERTS = (()=>{
  const rows=[];
  const sips=['192.168.1.104','172.16.8.55','10.10.1.200','192.168.2.11','172.16.5.32','10.0.2.44','192.168.3.77','172.16.12.9','10.10.8.100','192.168.1.88'];
  const dips=['10.0.0.23','10.0.0.1','203.0.113.5','198.51.100.9','10.0.0.55','203.0.113.22','10.0.0.8','198.51.100.44','10.0.0.71','10.0.0.33'];
  const protos=['TCP','UDP','ICMP','HTTP','HTTPS'];
  const sevs=['high','high','medium','medium','low'];
  const stats=['OPEN','OPEN','TRIAGED','TRIAGED','CLOSED'];
  for(let i=0;i<40;i++){
    const score=parseFloat((Math.random()*0.6+0.4).toFixed(2));
    const sidx=score>=0.8?0:score>=0.65?2:4;
    rows.push({id:'NP-'+String(500-i).padStart(5,'0'),src:sips[i%sips.length],dst:dips[i%dips.length],proto:protos[i%protos.length],sev:sevs[sidx],score,ts:'2024-06-01 '+pad(14-Math.floor(i/4))+':'+pad((i*7)%60)+':'+pad((i*13)%60),status:stats[sidx+(i%2)>4?4:sidx+(i%2)]});
  }
  return rows.sort((a,b)=>b.score-a.score);
})();
let filteredAlerts=[...ALERTS];
function applyFilters(){
  const sev=document.getElementById('sev-filter').value;
  const minScore=parseFloat(document.getElementById('score-filter').value)||0;
  const q=(document.getElementById('search-filter').value||'').toLowerCase();
  filteredAlerts=ALERTS.filter(r=>{if(sev!=='all'&&r.sev!==sev)return false;if(r.score<minScore)return false;if(q&&!(r.id+r.src+r.dst).toLowerCase().includes(q))return false;return true;});
  renderTable();
}
function renderTable(){
  const tbody=document.getElementById('alert-tbody');
  const shown=filteredAlerts.slice(0,50);
  document.getElementById('tbl-count').textContent='SHOWING '+shown.length+' OF '+filteredAlerts.length;
  tbody.innerHTML=shown.map(r=>{const pct=Math.round(r.score*100);const barColor=r.score>=0.8?'#C0392B':r.score>=0.65?'#E67E22':'#2A9FD6';const tagCls=r.sev==='high'?'hi':r.sev==='medium'?'md':'lo';const stCls=r.status==='OPEN'?'hi':r.status==='TRIAGED'?'md':'ok';return `<tr><td class="id-cell">${r.id}</td><td>${r.src}</td><td>${r.dst}</td><td><span class="tag lo">${r.proto}</span></td><td><span class="tag ${tagCls}">${r.sev.toUpperCase()}</span></td><td><div class="score-wrap"><div class="score-bar-bg"><div class="score-bar" style="width:${pct}%;background:${barColor}"></div></div><span class="score-num">${r.score.toFixed(2)}</span></div></td><td style="color:var(--txt-dim)">${r.ts}</td><td><span class="tag ${stCls}">${r.status}</span></td></tr>`;}).join('');
}
renderTable();
function exportCSV(){
  const headers=['Flow ID','Source IP','Dest IP','Protocol','Severity','Score','Timestamp','Status'];
  const rows=filteredAlerts.map(r=>[r.id,r.src,r.dst,r.proto,r.sev,r.score,r.ts,r.status]);
  const csv=[headers,...rows].map(r=>r.join(',')).join('\n');
  const a=document.createElement('a');
  a.href='data:text/csv;charset=utf-8,'+encodeURIComponent(csv);
  a.download='netpulse_alerts_'+new Date().toISOString().slice(0,10)+'.csv';
  a.click();
}
let flows=47283,alerts=4729,pending=312;
setInterval(()=>{flows+=Math.floor(Math.random()*14+3);if(Math.random()>0.6)alerts++;pending=Math.max(0,pending+(Math.random()>0.8?1:Math.random()>0.5?-1:0));document.getElementById('kv-flows').textContent=fmt(flows);document.getElementById('kv-alerts').textContent=fmt(alerts);document.getElementById('kv-pending').textContent=fmt(pending);document.getElementById('s-alerts').textContent=fmt(alerts);document.getElementById('s-qdepth').textContent=fmt(pending);},2200);
</script>
</body>
</html>
"""

# Render the dashboard
components.html(html_content, height=1400, scrolling=True)
