/* ===== STATE ===== */
let aiMode = 'rag';
let alertsData = [];
let refreshInterval = null;
let pipelineInterval = null;

/* ===== INIT ===== */
document.addEventListener('DOMContentLoaded', async () => {
    try {
        initTabs();
        initAIToggle();
        initRefresh();
        initAnalysisToggle();
        await initEmailConfig();
        await loadAll();
        startAutoRefresh();
    } catch (e) {
        console.error('Init error:', e);
        toast('Dashboard init failed: ' + e.message, 'error');
    }
});

/* ===== TOAST ===== */
function toast(msg, type = 'info') {
    const container = document.getElementById('toast-container');
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.innerHTML = `<span>${msg}</span><button class="toast-remove" onclick="this.parentElement.remove()">&times;</button>`;
    container.appendChild(el);
    setTimeout(() => { if (el.parentElement) el.remove(); }, 4000);
}

/* ===== MODAL ===== */
function showModal(title, body) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').textContent = body;
    document.getElementById('modal-overlay').style.display = 'flex';
}
function closeModal() {
    document.getElementById('modal-overlay').style.display = 'none';
}

/* ===== TABS ===== */
function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
            if (btn.dataset.tab === 'alerts') renderAlertsTable(alertsData);
            if (btn.dataset.tab === 'traffic') loadTrafficTab();
            if (btn.dataset.tab === 'report') loadReport();
            if (btn.dataset.tab === 'status') loadStatusTable();
        });
    });
}

/* ===== AI TOGGLE ===== */
function initAIToggle() {
    document.querySelectorAll('.toggle-group .toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.toggle-group .toggle-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            aiMode = btn.dataset.mode;
            document.getElementById('val-ai').textContent = aiMode.toUpperCase();
        });
    });
}

/* ===== REFRESH ===== */
function initRefresh() {
    document.getElementById('refresh-btn').addEventListener('click', () => {
        const btn = document.getElementById('refresh-btn');
        btn.classList.add('spinning');
        loadAll();
        setTimeout(() => btn.classList.remove('spinning'), 800);
    });
}

function startAutoRefresh() {
    if (refreshInterval) clearInterval(refreshInterval);
    refreshInterval = setInterval(loadAll, 30000);
}

function updateTimestamp() {
    document.getElementById('last-refresh').textContent = new Date().toLocaleTimeString();
}

/* ===== DATA LOADING ===== */
async function loadAll() {
    await Promise.allSettled([
        loadStatus(),
        loadAlerts(),
        loadGraph(),
        loadStats(),
        loadDataPreview(),
        loadTimeline(),
        loadLiveFeed(),
    ]);
    updateTimestamp();
}

function startAutoRefresh() {
    if (refreshInterval) clearInterval(refreshInterval);
    refreshInterval = setInterval(loadAll, 10000);
}

async function fetchJSON(url, options = {}, timeoutMs = 10000) {
    try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), timeoutMs);
        const r = await fetch(url, { ...options, signal: controller.signal });
        clearTimeout(timeout);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return await r.json();
    } catch (e) {
        if (e.name === 'AbortError') console.warn(`fetch ${url}: timeout (${timeoutMs}ms)`);
        else console.error(`fetch ${url}:`, e);
        return null;
    }
}

/* ===== STATUS ===== */
async function loadStatus() {
    const data = await fetchJSON('/api/status');
    if (!data) return;
    document.getElementById('stat-records').textContent = (data.total_records || 0).toLocaleString();
    document.getElementById('stat-alerts').textContent = (data.total_alerts || 0).toLocaleString();
    document.getElementById('stat-normal').textContent = (data.normal_traffic || 0).toLocaleString();
    document.getElementById('stat-critical').textContent = (data.critical_count || 0).toLocaleString();

    document.getElementById('val-data').textContent = data.data_file || 'N/A';
    document.getElementById('val-alerts').textContent = data.alerts_file || 'N/A';

    const dd = document.getElementById('dot-data');
    const da = document.getElementById('dot-alerts');
    dd.className = 'dot ' + (data.data_file ? 'dot-green' : 'dot-red');
    da.className = 'dot ' + (data.alerts_file ? 'dot-green' : 'dot-red');
}

/* ===== ALERTS ===== */
async function loadAlerts() {
    alertsData = await fetchJSON('/api/alerts') || [];
    // sort by anomaly_score ascending (most negative = most anomalous = highest priority)
    const scoreCol = findCol(alertsData, ['anomaly_score', 'score', 'decision_score']);
    if (scoreCol) {
        alertsData.sort((a, b) => (a[scoreCol] || 0) - (b[scoreCol] || 0));
    }
    renderAlertsTable(alertsData);
    renderRecentThreats(alertsData);
    populateFilters(alertsData);
    document.getElementById('alerts-count').textContent = `${alertsData.length} alerts`;
}

function renderAlertsTable(data) {
    const container = document.getElementById('alerts-table');
    if (!data || data.length === 0) {
        container.innerHTML = '<div class="empty-state">No alerts found. Run detection first.</div>';
        return;
    }
    const cols = ['label', 'anomaly_score', 'anomaly', 'is_anomaly', 'sttl', 'sbytes', 'dbytes'];
    const existing = cols.filter(c => c in data[0]);
    const sevCol = findCol(data, ['severity', 'risk_level']);
    if (sevCol && !existing.includes(sevCol)) existing.unshift(sevCol);

    let html = '<table><thead><tr>';
    existing.forEach(c => { html += `<th>${esc(c)}</th>`; });
    html += '</tr></thead><tbody>';
    data.slice(0, 50).forEach((row, idx) => {
        const realIdx = alertsData.indexOf(row);
        html += `<tr class="clickable" onclick="showAlertDetail(${realIdx})">`;
        existing.forEach(c => {
            let v = row[c];
            if (typeof v === 'number') v = v.toFixed ? v.toFixed(4) : v;
            html += `<td>${esc(String(v ?? ''))}</td>`;
        });
        html += '</tr>';
    });
    html += '</tbody></table>';
    container.innerHTML = html;
}

function showAlertDetail(idx) {
    const row = alertsData[idx];
    if (!row) return;
    let html = '<div class="drill-grid">';
    for (const [k, v] of Object.entries(row)) {
        let val = typeof v === 'number' && v.toFixed ? v.toFixed(4) : String(v ?? '');
        html += `<div class="drill-item"><div class="drill-key">${esc(k)}</div><div class="drill-val">${esc(val)}</div></div>`;
    }
    html += '</div>';
    showModal(`Alert #${idx} — ${esc(row.label || 'Unknown')}`, '');
    document.getElementById('modal-body').innerHTML = html;
}

function renderRecentThreats(data) {
    const container = document.getElementById('recent-threats-table');
    if (!data || data.length === 0) {
        container.innerHTML = '<div class="empty-state">No alerts yet</div>';
        return;
    }
    const cols = ['label', 'anomaly_score'].filter(c => c in data[0]);
    if (cols.length === 0) cols.push(...Object.keys(data[0]).slice(0, 3));

    let html = '<table><thead><tr>';
    cols.forEach(c => { html += `<th>${esc(c)}</th>`; });
    html += '</tr></thead><tbody>';
    data.slice(0, 8).forEach(row => {
        html += '<tr>';
        cols.forEach(c => {
            let v = row[c];
            if (typeof v === 'number' && v.toFixed) v = v.toFixed(4);
            html += `<td>${esc(String(v ?? ''))}</td>`;
        });
        html += '</tr>';
    });
    html += '</tbody></table>';
    container.innerHTML = html;
}

function populateFilters(data) {
    if (!data || data.length === 0) return;
    const sevCol = findCol(data, ['severity', 'risk_level']);
    const typeCol = findCol(data, ['attack_category', 'attack_cat', 'predicted_attack', 'label']);

    const sf = document.getElementById('filter-severity');
    const tf = document.getElementById('filter-type');

    if (sevCol) {
        const vals = [...new Set(data.map(r => String(r[sevCol] || '').trim()).filter(Boolean))].sort();
        sf.innerHTML = '<option value="all">All Severities</option>' + vals.map(v => `<option>${esc(v)}</option>`).join('');
        sf.onchange = () => filterAlerts();
    }
    if (typeCol) {
        const vals = [...new Set(data.map(r => String(r[typeCol] || '').trim()).filter(Boolean))].sort();
        tf.innerHTML = '<option value="all">All Types</option>' + vals.map(v => `<option>${esc(v)}</option>`).join('');
        tf.onchange = () => filterAlerts();
    }
}

function filterAlerts() {
    let filtered = [...alertsData];
    const sv = document.getElementById('filter-severity').value;
    const tv = document.getElementById('filter-type').value;
    const sevCol = findCol(filtered, ['severity', 'risk_level']);
    const typeCol = findCol(filtered, ['attack_category', 'attack_cat', 'predicted_attack', 'label']);
    if (sv !== 'all' && sevCol) filtered = filtered.filter(r => String(r[sevCol]) === sv);
    if (tv !== 'all' && typeCol) filtered = filtered.filter(r => String(r[typeCol]) === tv);
    renderAlertsTable(filtered);
    document.getElementById('alerts-count').textContent = `${filtered.length} alerts`;
}

/* ===== ANALYSIS TOGGLE (Graph / Globe) ===== */
function initAnalysisToggle() {
    const toggles = document.querySelectorAll('#analysis-toggle .toggle-btn');
    toggles.forEach(btn => {
        btn.addEventListener('click', () => {
            toggles.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const view = btn.dataset.view;
            document.querySelectorAll('.analysis-view').forEach(v => v.classList.remove('active'));
            document.getElementById('view-' + view).classList.add('active');
            document.getElementById('analysis-legend-graph').style.display = view === 'graph' ? '' : 'none';
            document.getElementById('analysis-legend-globe').style.display = view === 'globe' ? '' : 'none';
            if (view === 'globe') loadGlobe();
        });
    });
}

/* ===== LINK ANALYSIS GRAPH (vis-network) ===== */
let graphNetwork = null;

async function loadGraph() {
    const data = await fetchJSON('/api/graph');
    const placeholder = document.getElementById('graph-placeholder');
    const container = document.getElementById('graph-vis');

    if (!data || !data.nodes || data.nodes.length === 0) {
        placeholder.style.display = 'flex';
        placeholder.innerHTML = '<i class="fas fa-project-diagram" style="font-size:2rem;opacity:0.3;"></i><br>No alert data for graph';
        container.innerHTML = '';
        document.getElementById('g-nodes').textContent = '0';
        document.getElementById('g-edges').textContent = '0';
        document.getElementById('g-clusters').textContent = '0';
        document.getElementById('g-critical').textContent = '0';
        document.getElementById('g-avgscore').textContent = '0';
        return;
    }

    placeholder.style.display = 'none';

    const nodes = new vis.DataSet(data.nodes.map(n => ({
        id: n.id,
        label: n.label,
        title: n.title,
        color: n.color,
        value: n.value,
        group: n.group,
        shape: 'dot',
        font: { color: '#c8d6e5', size: 10, face: 'Inter', strokeWidth: 0 },
        borderWidth: 1,
        borderWidthSelected: 2,
        shadow: { color: 'rgba(0,0,0,0.4)', size: 4 },
    })));

    const edges = new vis.DataSet(data.edges.map(e => ({
        from: e.from,
        to: e.to,
        value: e.value,
        title: e.title,
        color: e.color,
        width: e.width || 0.3,
        smooth: { type: 'continuous' },
    })));

    const options = {
        nodes: { shape: 'dot', size: 10 },
        edges: { smooth: { type: 'continuous' } },
        physics: {
            solver: 'forceAtlas2Based',
            forceAtlas2Based: {
                gravitationalConstant: -60,
                centralGravity: 0.003,
                springLength: 140,
                springConstant: 0.05,
                damping: 0.5,
            },
            stabilization: { iterations: 200 },
            adaptiveTimestep: true,
        },
        interaction: {
            hover: true,
            tooltipDelay: 200,
            navigationButtons: true,
            keyboard: true,
            zoomView: true,
            dragView: true,
        },
        layout: { improvedLayout: true },
        groups: {
            critical: { color: { background: '#ff1744', border: '#ff1744' } },
            high: { color: { background: '#ff9100', border: '#ff9100' } },
            medium: { color: { background: '#ffc107', border: '#ffc107' } },
            low: { color: { background: '#00e676', border: '#00e676' } },
            normal: { color: { background: '#1a2332', border: '#2a3342' } },
            unknown: { color: { background: '#78909c', border: '#78909c' } },
        },
        background: '#020408',
    };

    // Destroy previous network if exists
    if (graphNetwork) graphNetwork.destroy();

    graphNetwork = new vis.Network(container, { nodes, edges }, options);

    // Stats
    const alertNodes = data.nodes.filter(n => n.is_alert);
    const scores = alertNodes.map(n => n.anomaly_score || 0);
    const avg = scores.length ? (scores.reduce((a, b) => a + b, 0) / scores.length) : 0;
    document.getElementById('g-nodes').textContent = data.nodes.length;
    document.getElementById('g-edges').textContent = data.edges.length;
    document.getElementById('g-clusters').textContent = alertNodes.length;
    document.getElementById('g-critical').textContent = alertNodes.length;
    document.getElementById('g-avgscore').textContent = avg.toFixed(3);

    // Click-to-drill-down: show node info
    graphNetwork.on('click', (params) => {
        if (params.nodes && params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const node = data.nodes.find(n => n.id === nodeId);
            if (!node) return;
            const body = document.getElementById('modal-body');
            if (node.is_alert) {
                // Try to find matching alert in alertsData
                const idx = parseInt(nodeId, 10);
                if (!isNaN(idx) && alertsData && alertsData[idx]) {
                    showAlertDetail(idx);
                    return;
                }
            }
            showModal('Node: Row #' + node.id, '');
            body.innerHTML = `<div class="drill-grid">
                <div class="drill-item"><div class="drill-key">Row</div><div class="drill-val">#${esc(node.id)}</div></div>
                <div class="drill-item"><div class="drill-key">Alert</div><div class="drill-val">${node.is_alert ? '<span style="color:var(--danger);">Yes</span>' : 'No'}</div></div>
                <div class="drill-item"><div class="drill-key">Anomaly Score</div><div class="drill-val">${node.anomaly_score?.toFixed(4) || 'N/A'}</div></div>
                <div class="drill-item"><div class="drill-key">Severity</div><div class="drill-val">${esc(node.group || 'normal')}</div></div>
                <div class="drill-item"><div class="drill-key">Features</div><div class="drill-val" style="word-break:break-all;">${esc(node.features || '')}</div></div>
            </div>`;
        }
    });

    // Hover tooltip enhancement
    graphNetwork.on('hoverNode', (params) => {
        document.getElementById('graph-vis').style.cursor = 'pointer';
    });
    graphNetwork.on('blurNode', () => {
        document.getElementById('graph-vis').style.cursor = 'default';
    });
}

/* ===== GLOBE (now a sub-view, lazy-loaded) ===== */
let globeLoaded = false;

async function loadGlobe() {
    if (globeLoaded) return;
    if (typeof Plotly === 'undefined') {
        document.getElementById('globe-placeholder').innerHTML = '<i class="fas fa-exclamation-triangle" style="font-size:1.2rem;opacity:0.5;"></i><br>Plotly library failed to load';
        return;
    }
    const fig = await fetchJSON('/api/globe');
    const placeholder = document.getElementById('globe-placeholder');
    const plotDiv = document.getElementById('globe-plot');

    if (fig) {
        placeholder.style.display = 'none';
        const layout = fig.layout || {};
        layout.dragmode = layout.dragmode || 'orbit';
        const config = {
            responsive: true,
            scrollZoom: true,
            displaylogo: false,
            modeBarButtonsToRemove: ['sendDataToCloud', 'lasso2d', 'select2d'],
        };
        Plotly.react(plotDiv, fig.data, layout, config);
        const resizeGlobe = () => Plotly.Plots.resize(plotDiv);
        window.addEventListener('resize', resizeGlobe);
        globeLoaded = true;
    } else {
        placeholder.innerHTML = '<i class="fas fa-globe-americas" style="font-size:2rem;opacity:0.3;"></i><br>No threat data';
        plotDiv.innerHTML = '';
    }
}

/* ===== STATS ===== */
async function loadStats() {
    const stats = await fetchJSON('/api/stats');
    if (!stats) return;
    document.getElementById('g-total').textContent = (stats.total_attacks || 0).toLocaleString();
    document.getElementById('g-high').textContent = (stats.high_confidence || 0).toLocaleString();
    document.getElementById('g-blocked').textContent = (stats.blocked || 0).toLocaleString();
    document.getElementById('g-avg').textContent = (stats.avg_confidence || 0).toFixed(1) + '%';
    // Set globe's critical count (g-critical2) and graph's (g-critical)
    const critEl = document.getElementById('g-critical');
    const crit2El = document.getElementById('g-critical2');
    const cv = (stats.critical_count || 0).toLocaleString();
    if (critEl) critEl.textContent = cv;
    if (crit2El) crit2El.textContent = cv;

    renderAttackDist(stats.attack_types);
}

function renderAttackDist(types) {
    const container = document.getElementById('chart-dist');
    if (!types || Object.keys(types).length === 0) {
        container.innerHTML = '<div class="empty-state">No data</div>';
        return;
    }
    const entries = Object.entries(types).sort((a, b) => b[1] - a[1]);
    const labels = entries.map(e => e[0]);
    const values = entries.map(e => e[1]);
    const colors = labels.map(getColor);

    const trace = {
        x: values,
        y: labels,
        type: 'bar',
        orientation: 'h',
        marker: { color: colors, line: { width: 0 } },
        text: values.map(String),
        textposition: 'outside',
        textfont: { size: 10, color: '#78909c' },
    };
    const layout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#78909c', size: 9 },
        margin: { l: 90, r: 40, t: 10, b: 30 },
        height: 220,
        xaxis: { showgrid: true, gridcolor: '#1a2332', zeroline: false },
        yaxis: { showgrid: false, autorange: 'reversed' },
        bargap: 0.3,
    };
    Plotly.react(container, [trace], layout, { displayModeBar: false, responsive: true });
}

/* ===== TRAFFIC TAB ===== */
let trafficData = null;

async function loadDataPreview() {
    trafficData = await fetchJSON('/api/data');
}

async function loadTrafficTab() {
    if (!trafficData || trafficData.rows === 0) {
        await loadDataPreview();
    }
    if (!trafficData || trafficData.rows === 0) {
        document.getElementById('traffic-info').textContent = 'No data';
        return;
    }

    document.getElementById('traffic-info').textContent =
        `${trafficData.rows.toLocaleString()} rows \u00b7 ${trafficData.cols} cols`;

    // Render table
    const container = document.getElementById('traffic-table');
    if (trafficData.preview && trafficData.preview.length > 0) {
        const cols = Object.keys(trafficData.preview[0]);
        let html = '<table><thead><tr>';
        cols.forEach(c => { html += `<th>${esc(c)}</th>`; });
        html += '</tr></thead><tbody>';
        trafficData.preview.forEach(row => {
            html += '<tr>';
            cols.forEach(c => {
                let v = row[c];
                if (typeof v === 'number' && v.toFixed) v = v.toFixed(2);
                html += `<td>${esc(String(v ?? ''))}</td>`;
            });
            html += '</tr>';
        });
        html += '</tbody></table>';
        container.innerHTML = html;
    }

    // Feature selector
    const sel = document.getElementById('feature-select');
    if (trafficData.columns && trafficData.columns.length > 0) {
        sel.innerHTML = '<option value="">Select feature...</option>' +
            trafficData.columns.map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join('');
        sel.onchange = () => {
            const feat = sel.value;
            if (!feat) return;
            const values = trafficData.preview.map(r => r[feat]).filter(v => v !== null && v !== undefined);
            const trace = {
                x: values,
                type: 'histogram',
                nbinsx: 40,
                marker: { color: '#00bcd4', line: { color: '#0a0e17', width: 1 } },
            };
            const layout = {
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: { color: '#78909c', size: 9 },
                margin: { l: 40, r: 20, t: 30, b: 40 },
                title: { text: feat, font: { color: '#78909c', size: 11 } },
                xaxis: { gridcolor: '#1a2332' },
                yaxis: { gridcolor: '#1a2332' },
            };
            Plotly.react(document.getElementById('traffic-chart'), [trace], layout, { displayModeBar: false });
        };
    }
}

/* ===== STATUS TAB ===== */
function getStatusBadge(ok) {
    return ok
        ? '<span class="dot dot-green" style="display:inline-block;vertical-align:middle;margin-right:6px;"></span> OK'
        : '<span class="dot dot-red" style="display:inline-block;vertical-align:middle;margin-right:6px;"></span> Missing';
}

async function loadStatusTable() {
    const status = await fetchJSON('/api/status');
    const items = [
        { name: 'Processed Data', ok: !!(status && status.data_file), path: status?.data_file || '-' },
        { name: 'Alerts File', ok: !!(status && status.alerts_file), path: status?.alerts_file || '-' },
        { name: 'Security Report', ok: !!(status && status.report_exists), path: 'Security_Report.txt' },
        { name: 'clean_data.py', ok: true, path: 'src/clean_data.py' },
        { name: 'detector.py', ok: true, path: 'src/detector.py' },
        { name: 'solver.py', ok: true, path: 'src/solver.py' },
        { name: 'Server Status', ok: true, path: 'Running on port 5000' },
    ];

    let html = '<table><thead><tr><th>Component</th><th>Status</th><th>Path / Info</th></tr></thead><tbody>';
    items.forEach(item => {
        html += `<tr>
            <td>${esc(item.name)}</td>
            <td style="font-weight:600;">${getStatusBadge(item.ok)}</td>
            <td style="color:var(--text-muted);">${esc(item.path)}</td>
        </tr>`;
    });
    html += '</tbody></table>';
    document.getElementById('status-table').innerHTML = html;
}

/* ===== REPORT ===== */
let reportRawText = '';

async function loadReport() {
    const data = await fetchJSON('/api/report');
    const el = document.getElementById('report-rendered');
    if (data && data.report) {
        reportRawText = data.report;
        el.innerHTML = renderStyledReport(reportRawText);
    } else {
        reportRawText = '';
        el.innerHTML = '<div class="empty-state">No report generated yet. Run Report in pipeline.</div>';
    }
}

function renderStyledReport(text) {
    if (!text || text.trim().length === 0) {
        return '<div class="empty-state">No report generated yet.</div>';
    }

    const lines = text.split('\n');
    let html = '';
    let inThreatCard = false;
    let threatNum = 0;

    const openThreat = (n) => {
        const severity = n <= 2 ? 'critical' : n <= 4 ? 'high' : 'medium';
        const colors = { critical: '#ff1744', high: '#ff9100', medium: '#ffc107' };
        html += `<div class="rc-card rc-threat-${severity}">
            <div class="rc-threat-header">
                <span class="rc-threat-num" style="background:${colors[severity]};">THREAT #${n}</span>
                <span class="rc-severity-badge ${severity}">${severity.toUpperCase()}</span>
            </div>`;
    };

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const t = line.trim();

        // === MAIN HEADER ===
        if (/^={3,}\s*NETPULSE/.test(t)) {
            html += `<div class="rc-hero">
                <div class="rc-hero-icon"><i class="fas fa-shield-halved"></i></div>
                <div class="rc-hero-title">Security Assessment Report</div>
                <div class="rc-hero-sub">NetPulse-Shield &mdash; AI-Powered Threat Analysis</div>
            </div>`;
            continue;
        }
        if (/^={3,}/.test(t)) {
            continue;
        }

        // THREAT #N
        const threatMatch = t.match(/^THREAT\s*#(\d+)/i);
        if (threatMatch) {
            if (inThreatCard) { html += '</div>'; }
            threatNum = parseInt(threatMatch[1]);
            openThreat(threatNum);
            inThreatCard = true;
            continue;
        }

        // ---- divider
        if (/^-{3,}$/.test(t)) {
            if (inThreatCard) { html += '</div>'; inThreatCard = false; }
            html += '<div class="rc-divider"></div>';
            continue;
        }

        // Symptoms:
        if (/^Symptoms:/i.test(t)) {
            const val = t.replace(/^Symptoms:\s*/i, '');
            html += `<div class="rc-symptoms">
                <div class="rc-label"><i class="fas fa-microchip"></i> Symptoms</div>
                <div class="rc-symptom-data">${esc(val)}</div>
            </div>`;
            continue;
        }

        // Remediation:
        if (/^Remediation:\s*$/i.test(t)) {
            html += `<div class="rc-label rc-label-remediation"><i class="fas fa-shield"></i> Remediation Steps</div>`;
            continue;
        }
        if (/^Remediation:/i.test(t)) {
            html += `<div class="rc-label rc-label-remediation"><i class="fas fa-shield"></i> Remediation</div>`;
            const val = t.replace(/^Remediation:\s*/i, '');
            if (val) {
                html += `<div class="rc-body">${esc(val)}</div>`;
            }
            continue;
        }

        // [Guidance N]
        const guidMatch = t.match(/^\[Guidance\s*(\d+)\]/i);
        if (guidMatch) {
            html += `<div class="rc-guidance-tag"><i class="fas fa-book-open"></i> Guidance ${guidMatch[1]}</div>`;
            continue;
        }

        // # DDoS Attack Remediation (topic heading)
        if (/^#\s+/.test(t)) {
            const topic = t.replace(/^#\s*/, '');
            html += `<div class="rc-topic">
                <div class="rc-topic-title"><i class="fas fa-bug"></i> ${esc(topic)}</div>`;
            // collect following lines until next topic or threat
            let j = i + 1;
            while (j < lines.length) {
                const nj = lines[j].trim();
                if (/^#\s+/.test(nj) || /^THREAT\s/i.test(nj) || /^={3,}/.test(nj)) break;
                if (/^Indicators:/i.test(nj)) {
                    html += `<div class="rc-indicators"><strong>Indicators:</strong> ${esc(nj.replace(/^Indicators:\s*/i, ''))}</div>`;
                } else if (/^Remediation:\s*\d+\./i.test(nj) || /^\d+\.\s/.test(nj)) {
                    html += `<div class="rc-step">${esc(nj)}</div>`;
                } else if (/^Remediation:/i.test(nj)) {
                    // skip
                } else if (nj) {
                    html += `<div class="rc-body">${esc(nj)}</div>`;
                }
                j++;
            }
            html += '</div>';
            i = j - 1;
            continue;
        }

        // Indicators: standalone
        if (/^Indicators:/i.test(t)) {
            html += `<div class="rc-indicators"><strong>Indicators:</strong> ${esc(t.replace(/^Indicators:\s*/i, ''))}</div>`;
            continue;
        }

        // Numbered remediation step (1. 2. 3.)
        if (/^\d+\.\s/.test(t)) {
            html += `<div class="rc-step"><span class="rc-step-num">${t.match(/^\d+/)[0]}</span>${esc(t.replace(/^\d+\.\s*/, ''))}</div>`;
            continue;
        }

        // Blank line
        if (!t) {
            continue;
        }

        // Fallback: regular text
        html += `<div class="rc-body">${esc(t)}</div>`;
    }

    if (inThreatCard) html += '</div>';

    return html || '<div class="empty-state">No report content</div>';
}

function buildStyledHTML() {
    const date = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    const threatCount = (reportRawText.match(/THREAT\s*#\d+/gi) || []).length;
    let bodyContent = renderStyledReport(reportRawText);
    // Strip hero banner from rendered body (we use our own cover in the standalone HTML)
    bodyContent = bodyContent.replace(/<div class="rc-hero">[\s\S]*?<\/div>\s*/i, '');
    // Convert rc- classes to threat- for the HTML report style namespace
    bodyContent = bodyContent.replace(/rc-/g, 'threat-');
    return `<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8">
<title>NetPulse-Shield Security Report</title>
<style>
    @page { margin: 2cm 1.5cm; }
    * { box-sizing: border-box; }
    body { font-family: 'Inter', 'Segoe UI', system-ui, sans-serif; background: #070b14; color: #c8d6e5; margin: 0; padding: 0; line-height: 1.6; }
    .report-wrap { max-width: 860px; margin: 0 auto; padding: 30px 24px; }

    .cover { text-align: center; padding: 60px 20px 40px; border-bottom: 1px solid #1a2332; margin-bottom: 30px; }
    .cover-icon { font-size: 2.4rem; color: #00bcd4; margin-bottom: 12px; }
    .cover h1 { font-size: 1.6rem; font-weight: 700; color: #e0e0e0; margin: 0 0 6px; }
    .cover-sub { color: #78909c; font-size: 0.85rem; }
    .cover-meta { margin-top: 20px; display: flex; justify-content: center; gap: 30px; font-size: 0.7rem; color: #546e7a; }
    .cover-meta span { display: flex; align-items: center; gap: 6px; }
    .cover-badge { display: inline-block; padding: 3px 14px; border-radius: 20px; font-size: 0.65rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; background: rgba(255,23,68,0.15); color: #ff1744; border: 1px solid rgba(255,23,68,0.3); margin-top: 14px; }

    .threat-card { background: #0d111c; border: 1px solid #1a2332; border-radius: 12px; padding: 20px 24px; margin-bottom: 18px; }
    .threat-critical { border-left: 3px solid #ff1744; }
    .threat-high { border-left: 3px solid #ff9100; }
    .threat-medium { border-left: 3px solid #ffc107; }
    .threat-header { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
    .threat-num { display: inline-block; padding: 3px 12px; border-radius: 6px; font-size: 0.7rem; font-weight: 700; color: #fff; letter-spacing: 1px; }
    .sev-badge { font-size: 0.6rem; font-weight: 600; padding: 2px 10px; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.5px; }
    .sev-critical { background: rgba(255,23,68,0.15); color: #ff1744; border: 1px solid rgba(255,23,68,0.2); }
    .sev-high { background: rgba(255,145,0,0.15); color: #ff9100; border: 1px solid rgba(255,145,0,0.2); }
    .sev-medium { background: rgba(255,193,7,0.15); color: #ffc107; border: 1px solid rgba(255,193,7,0.2); }

    .section-label { font-size: 0.68rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: #546e7a; margin: 10px 0 6px; display: flex; align-items: center; gap: 6px; }
    .section-label i { width: 14px; text-align: center; }
    .section-remediation { color: #00bcd4; margin-top: 14px; }

    .symptom-data { background: #070b14; border: 1px solid #1a2332; border-radius: 8px; padding: 10px 14px; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #78909c; margin: 4px 0 10px; line-height: 1.5; word-break: break-all; }

    .guidance-tag { display: inline-flex; align-items: center; gap: 6px; font-size: 0.68rem; font-weight: 600; color: #00bcd4; padding: 4px 10px; border-radius: 6px; background: rgba(0,188,212,0.08); margin: 10px 0 6px; }

    .topic { background: #070b14; border: 1px solid #1a2332; border-radius: 8px; padding: 12px 16px; margin: 8px 0; }
    .topic-title { font-size: 0.78rem; font-weight: 600; color: #ff8a65; margin-bottom: 6px; display: flex; align-items: center; gap: 6px; }

    .indicators { font-size: 0.72rem; color: #78909c; padding: 4px 0; }
    .indicators strong { color: #e0e0e0; }

    .step { display: flex; align-items: flex-start; gap: 8px; padding: 4px 0 4px 4px; font-size: 0.72rem; color: #b0bec5; }
    .step-num { display: inline-flex; align-items: center; justify-content: center; width: 18px; height: 18px; border-radius: 50%; background: rgba(0,188,212,0.15); color: #00bcd4; font-size: 0.6rem; font-weight: 700; flex-shrink: 0; margin-top: 1px; }

    .body-text { font-size: 0.75rem; color: #78909c; padding: 2px 0; }

    .divider { height: 1px; background: #1a2332; margin: 16px 0; }

    .footer { text-align: center; padding: 24px 0 0; border-top: 1px solid #1a2332; margin-top: 30px; font-size: 0.6rem; color: #546e7a; }

    @media print {
        body { background: #fff; color: #000; }
        .report-wrap { max-width: 100%; padding: 0; }
        .threat-card { background: #fafafa; border-color: #ddd; }
        .cover { border-bottom-color: #ddd; }
        .cover h1 { color: #000; }
        .cover-sub { color: #555; }
        .cover-meta { color: #888; }
        .cover-badge { border-color: #d50000; color: #d50000; }
        .topic { background: #f5f5f5; border-color: #ddd; }
        .symptom-data { background: #f5f5f5; border-color: #ddd; color: #333; }
        .threat-card { background: #fafafa; border-color: #ddd; }
        .threat-critical { border-left-color: #d50000; }
        .threat-high { border-left-color: #e65100; }
        .threat-medium { border-left-color: #f9a825; }
        .footer { border-top-color: #ddd; color: #999; }
        .divider { background: #ddd; }
        .step { color: #333; }
        .indicators { color: #555; }
        .indicators strong { color: #000; }
        .body-text { color: #555; }
        @page { margin: 1.5cm; }
    }
</style></head>
<body>
<div class="report-wrap">
<div class="cover">
    <div class="cover-icon"><i class="fas fa-shield-halved"></i></div>
    <h1>Security Assessment Report</h1>
    <div class="cover-sub">NetPulse-Shield &mdash; AI-Powered Network Threat Analysis</div>
    <div class="cover-meta">
        <span><i class="far fa-calendar"></i> ${date}</span>
        <span><i class="fas fa-exclamation-triangle"></i> ${threatCount} Threats Identified</span>
    </div>
    <div class="cover-badge">Confidential &mdash; Security Team Only</div>
</div>
${bodyContent}
<div class="footer">
    Generated by NetPulse-Shield &bull; AI Network Security &bull; Local-First<br>
    This report is confidential and intended for the designated security team.
</div>
</div>
</body></html>`;
}

function downloadStyledHTML() {
    if (!reportRawText) { toast('No report to download', 'warning'); return; }
    const blob = new Blob([buildStyledHTML()], { type: 'text/html' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'Security_Report.html';
    a.click();
    URL.revokeObjectURL(a.href);
    toast('Professional HTML report downloaded', 'success');
}

function downloadReport() {
    if (!reportRawText) { toast('No report to download', 'warning'); return; }
    const blob = new Blob([reportRawText], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'Security_Report.txt';
    a.click();
    URL.revokeObjectURL(a.href);
    toast('Report downloaded (TXT)', 'success');
}

function printReport() {
    if (!reportRawText) { toast('No report to print', 'warning'); return; }
    const win = window.open('', '_blank');
    win.document.write(buildStyledHTML());
    win.document.close();
    win.focus();
    setTimeout(() => { win.print(); }, 400);
}

/* ===== PIPELINE ===== */
async function runPipeline(action) {
    const cleanAction = action.replace('run-', 'run-');
    const btn = document.getElementById('btn-' + cleanAction);
    if (btn) {
        btn.dataset.origHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Running...';
    }

    // Start pipeline asynchronously
    const startResult = await fetchJSON('/api/pipeline/' + action, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: aiMode }),
    });

    if (!startResult || !startResult.task_id) {
        toast('Failed to start pipeline', 'error');
        if (btn) { btn.disabled = false; btn.innerHTML = btn.dataset.origHtml || 'Run'; }
        return;
    }

    // Poll for completion
    const taskId = startResult.task_id;
    if (pipelineInterval) clearInterval(pipelineInterval);

    const poll = async () => {
        const status = await fetchJSON('/api/pipeline/status/' + taskId);
        if (!status || status.status === 'running') return;
        clearInterval(pipelineInterval);
        pipelineInterval = null;
        if (btn) { btn.disabled = false; btn.innerHTML = btn.dataset.origHtml || 'Run'; }
        if (status.status === 'done') {
            toast(`${action} completed`, 'success');
            if (status.output) showModal(`${action} Output`, status.output);
            loadAll();
            if (action === 'run-all' && document.getElementById('email-notify-chk').checked) {
                await sendAlertEmail();
            }
        } else {
            toast(`${action} failed`, 'error');
            showModal(`${action} Failed`, status.error || status.output || 'Unknown error');
        }
    };

    pipelineInterval = setInterval(poll, 2000);
}

/* ===== TIMELINE ===== */
async function loadTimeline() {
    const data = await fetchJSON('/api/timeline');
    const container = document.getElementById('chart-timeline');
    if (!data || data.length === 0) {
        container.innerHTML = '<div class="empty-state">No timeline data</div>';
        return;
    }
    const trace = {
        x: data.map(d => d.hour),
        y: data.map(d => d.count),
        type: 'scatter',
        mode: 'lines+markers',
        line: { color: '#00bcd4', width: 2, shape: 'spline' },
        marker: { color: '#00bcd4', size: 4 },
        fill: 'tozeroy',
        fillcolor: 'rgba(0,188,212,0.08)',
    };
    const layout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#78909c', size: 9 },
        margin: { l: 35, r: 10, t: 5, b: 30 },
        height: 160,
        xaxis: { showgrid: false, tickangle: -45, nticks: 12 },
        yaxis: { showgrid: true, gridcolor: '#1a2332', zeroline: false, title: 'Attacks' },
        hovermode: 'x',
    };
    Plotly.react(container, [trace], layout, { displayModeBar: false, responsive: true });
}

/* ===== LIVE FEED ===== */
async function loadLiveFeed() {
    const data = alertsData;
    const container = document.getElementById('live-feed');
    if (!data || data.length === 0) {
        container.innerHTML = '<div class="feed-empty">Waiting for alerts...</div>';
        return;
    }
    const scoreCol = findCol(data, ['anomaly_score', 'score', 'decision_score']);
    const labelCol = findCol(data, ['label', 'attack_category', 'attack_cat', 'type']);
    const top = data.slice(0, 4);
    let html = '';
    top.forEach((row, i) => {
        const score = scoreCol ? Math.abs(parseFloat(row[scoreCol]) || 0) : 0;
        const label = labelCol ? (row[labelCol] || '?') : '?';
        const color = score > 0.7 ? 'var(--danger)' : score > 0.4 ? 'var(--warning)' : 'var(--success)';
        const realIdx = alertsData.indexOf(row);
        html += `<div class="feed-item" onclick="showAlertDetail(${realIdx})" title="Click for details">
            <span class="feed-dot" style="background:${color};"></span>
            <span class="feed-label">${esc(String(label))}</span>
            <span class="feed-score">${(score*100).toFixed(0)}%</span>
        </div>`;
    });
    container.innerHTML = html;
}

async function sendAlertEmail() {
    const recipient = document.getElementById('email-recipient').value;
    const config = await fetchJSON('/api/email/config');
    const to = recipient || (config && config.RECEIVER_EMAIL);
    if (!to) { toast('No recipient configured (Email tab)', 'warning'); return false; }

    const result = await fetchJSON('/api/email/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            recipient: to,
            email: document.getElementById('email-addr').value || (config && config.EMAIL_SENDER),
            password: document.getElementById('email-pass').value || (config && config.EMAIL_PASSWORD),
            server: document.getElementById('email-server').value || (config && config.EMAIL_SMTP_SERVER),
            port: parseInt(document.getElementById('email-port').value) || parseInt(config && config.EMAIL_SMTP_PORT) || 587,
        }),
    });

    if (result && result.success) {
        toast('Alert email sent to ' + to, 'success');
        return true;
    } else {
        toast('Email send failed: ' + (result?.error || 'unknown'), 'error');
        return false;
    }
}

/* ===== EMAIL ===== */
async function initEmailConfig() {
    const config = await fetchJSON('/api/email/config');
    if (!config) return;
    if (config.EMAIL_SENDER) document.getElementById('email-addr').value = config.EMAIL_SENDER;
    if (config.EMAIL_PASSWORD) document.getElementById('email-pass').value = config.EMAIL_PASSWORD;
    if (config.EMAIL_SMTP_SERVER) document.getElementById('email-server').value = config.EMAIL_SMTP_SERVER;
    if (config.EMAIL_SMTP_PORT) document.getElementById('email-port').value = config.EMAIL_SMTP_PORT;
    if (config.RECEIVER_EMAIL) document.getElementById('email-recipient').value = config.RECEIVER_EMAIL;
    if (config.ATTACK_THRESHOLD_PERCENTAGE) {
        document.getElementById('email-threshold') &&
            (document.getElementById('email-threshold').value = config.ATTACK_THRESHOLD_PERCENTAGE);
    }
}

async function saveEmailConfig() {
    const btn = document.getElementById('btn-save-email');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

    const result = await fetchJSON('/api/email/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            EMAIL_SENDER: document.getElementById('email-addr').value,
            EMAIL_PASSWORD: document.getElementById('email-pass').value,
            EMAIL_SMTP_SERVER: document.getElementById('email-server').value,
            EMAIL_SMTP_PORT: document.getElementById('email-port').value,
            RECEIVER_EMAIL: document.getElementById('email-recipient').value,
        }),
    });

    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-floppy-disk"></i> Save Config';

    if (result && result.success) {
        toast('Email config saved', 'success');
    } else {
        toast('Save failed: ' + (result?.error || 'unknown'), 'error');
    }
}

async function testEmail() {
    const btn = document.querySelector('#tab-email .btn:not(#btn-save-email)');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';

    const result = await fetchJSON('/api/email/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            email: document.getElementById('email-addr').value,
            password: document.getElementById('email-pass').value,
            server: document.getElementById('email-server').value,
            port: parseInt(document.getElementById('email-port').value) || 587,
        }),
    });

    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-plug"></i> Test Connection';

    if (result && result.success) {
        toast('SMTP connection OK', 'success');
    } else {
        toast('SMTP failed: ' + (result?.error || 'unknown'), 'error');
    }
}

async function sendTestEmail() {
    const recipient = document.getElementById('email-recipient').value;
    if (!recipient) { toast('Enter recipient email', 'warning'); return; }

    const btn = document.querySelector('#tab-email .btn-primary');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';

    const result = await fetchJSON('/api/email/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            recipient,
            email: document.getElementById('email-addr').value,
            password: document.getElementById('email-pass').value,
            server: document.getElementById('email-server').value,
            port: parseInt(document.getElementById('email-port').value) || 587,
        }),
    });

    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-paper-plane"></i> Send Alert Email';

    if (result && result.success) {
        document.getElementById('email-result').className = 'email-result success';
        document.getElementById('email-result').textContent = 'Alert email sent with top alerts ordered by severity!';
        toast('Alert email sent to ' + recipient, 'success');
    } else {
        document.getElementById('email-result').className = 'email-result error';
        document.getElementById('email-result').textContent = 'Failed: ' + (result?.error || 'unknown');
        toast('Email send failed', 'error');
    }
}

/* ===== UTILITY ===== */
function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

function findCol(data, names) {
    if (!data || data.length === 0) return null;
    const cols = Object.keys(data[0]).map(c => c.toLowerCase());
    for (const n of names) {
        const idx = cols.indexOf(n.toLowerCase());
        if (idx !== -1) return Object.keys(data[0])[idx];
    }
    return null;
}

function getColor(label) {
    const map = {
        'backdoor': '#ff1744', 'exploits': '#d50000', 'dos': '#b71c1c',
        'ddos': '#ff0000', 'fuzzers': '#ffc107', 'analysis': '#ff9100',
        'reconnaissance': '#2196f3', 'shellcode': '#9c27b0', 'worms': '#e91e63',
        'generic': '#9e9e9e', 'brute force': '#ff9100', 'port scan': '#2196f3',
        'normal': '#00e676', '1': '#ff1744', '0': '#00e676',
    };
    const s = String(label).toLowerCase();
    for (const [k, v] of Object.entries(map)) {
        if (s.includes(k)) return v;
    }
    return '#9e9e9e';
}

/* ===== KEYBOARD SHORTCUTS ===== */
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
    if (e.key === 'r' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        document.getElementById('refresh-btn').click();
    }
});
