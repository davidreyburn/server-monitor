// ═══════════════════════════════════════════════════════
//  NERV SYSTEM MONITOR — NGE Interface
// ═══════════════════════════════════════════════════════

const API_BASE = '';

let waveformBuffer = [];
const WAVEFORM_MAX = 60;

let thresholds = {};

// ─────────────────────────────────────────────────────
//  Init
// ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    runBootSequence();
    startClock();
    initHexScroll();
    loadData();
    setupEventListeners();
    setInterval(loadData, 60000);
});

// ─────────────────────────────────────────────────────
//  Boot sequence
// ─────────────────────────────────────────────────────
function runBootSequence() {
    const sl = document.getElementById('scanlines');
    sl.classList.add('boot-flash');
    setTimeout(() => sl.classList.remove('boot-flash'), 1000);
}

// ─────────────────────────────────────────────────────
//  Live clock
// ─────────────────────────────────────────────────────
function startClock() {
    function tick() {
        document.getElementById('live-clock').textContent =
            new Date().toTimeString().slice(0, 8);
    }
    tick();
    setInterval(tick, 1000);
}

// ─────────────────────────────────────────────────────
//  Event listeners
// ─────────────────────────────────────────────────────
function setupEventListeners() {
    document.getElementById('refresh-btn').addEventListener('click', loadData);
    document.getElementById('time-range').addEventListener('change', () => {
        loadHistoricalData();
        document.getElementById('waveform-range').textContent =
            document.getElementById('time-range').options[document.getElementById('time-range').selectedIndex].text;
    });
}

// ─────────────────────────────────────────────────────
//  Data loading
// ─────────────────────────────────────────────────────
async function loadData() {
    try {
        const res = await fetch(`${API_BASE}/api/current`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        thresholds = data.thresholds || {};

        updateCpuDisplay(data.cpu);
        updateMemoryDisplay(data.memory);
        renderDiskHexes(data.disk, data.smart);
        renderDockerBars(data.docker);
        renderProcessList(data.processes);

        const uptime = data.cpu?.load?.uptime_seconds;
        if (uptime != null) {
            document.getElementById('top-uptime').textContent = formatUptime(uptime);
        }

        document.getElementById('last-update').textContent =
            new Date().toLocaleTimeString();

        const statusEl = document.getElementById('system-status');
        statusEl.textContent = '■ SYSTEM STATUS: NOMINAL';
        statusEl.className = 'status-nominal';

        loadHistoricalData();
        loadStats();

    } catch (err) {
        console.error('Data load error:', err);
        const statusEl = document.getElementById('system-status');
        statusEl.textContent = '■ SYSTEM STATUS: ERROR';
        statusEl.className = 'status-error';
    }
}

async function loadHistoricalData() {
    const hours = document.getElementById('time-range').value;
    try {
        const res = await fetch(`${API_BASE}/api/history/cpu?hours=${hours}`);
        const json = await res.json();
        if (json.data && json.data.length > 0) {
            populateWaveform(json.data);
        }
    } catch (err) {
        console.error('History error:', err);
    }
}

async function loadStats() {
    try {
        const res = await fetch(`${API_BASE}/api/stats`);
        const stats = await res.json();
        document.getElementById('db-stats').textContent =
            `// REC:${stats.total_records || 0} DB:${stats.database_size_mb || 0}MB`;
    } catch (_) {}
}

// ─────────────────────────────────────────────────────
//  CPU Display
// ─────────────────────────────────────────────────────
function updateCpuDisplay(cpu) {
    if (!cpu || cpu.error) return;

    // Temperature
    let mainTemp = null;
    const temps = cpu.temperature;
    if (temps && !temps.error) {
        for (const [, zone] of Object.entries(temps)) {
            if (zone.type && (zone.type.includes('cpu') || zone.type.includes('x86'))) {
                mainTemp = zone.temp_celsius;
                break;
            }
        }
        if (mainTemp === null) {
            const first = Object.values(temps)[0];
            mainTemp = first?.temp_celsius ?? null;
        }
    }

    if (mainTemp !== null) {
        const statusKey = getTempStatus(mainTemp);
        drawArcGauge(
            document.getElementById('cpu-gauge-canvas'),
            mainTemp, 100, statusKey
        );
        document.getElementById('cpu-temp-val').textContent = `${mainTemp}°C`;
    }

    // Load averages
    const load = cpu.load;
    if (load && !load.error) {
        document.getElementById('load-readout').textContent =
            `${load.load_1min?.toFixed(2)} / ${load.load_5min?.toFixed(2)} / ${load.load_15min?.toFixed(2)}`;
    }
}

// ─────────────────────────────────────────────────────
//  Arc Gauge (canvas)
// ─────────────────────────────────────────────────────
function drawArcGauge(canvas, value, max, statusKey) {
    const dpr    = window.devicePixelRatio || 1;
    const rect   = canvas.getBoundingClientRect();
    const cw     = rect.width  || 148;
    const ch     = rect.height || 106;

    canvas.width  = Math.round(cw * dpr);
    canvas.height = Math.round(ch * dpr);

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    const cx = cw / 2;
    const cy = ch * 0.60;
    const r  = Math.min(cw * 0.40, ch * 0.68);

    const startAngle = Math.PI * 0.75;   // 135°
    const endAngle   = Math.PI * 2.25;   // 405° (= 45°)
    const percent    = Math.min(Math.max(value / max, 0), 1);
    const fillAngle  = startAngle + (endAngle - startAngle) * percent;

    const valueColor =
        statusKey === 'status-critical' ? '#ff1a1a' :
        statusKey === 'status-warning'  ? '#ffcc00' : '#1eff00';

    // Track arc
    ctx.beginPath();
    ctx.arc(cx, cy, r, startAngle, endAngle);
    ctx.strokeStyle = '#0d3344';
    ctx.lineWidth   = 9;
    ctx.lineCap     = 'round';
    ctx.stroke();

    // Tick marks
    for (let i = 0; i <= 10; i++) {
        const a  = startAngle + (endAngle - startAngle) * (i / 10);
        const x1 = cx + Math.cos(a) * (r - 14);
        const y1 = cy + Math.sin(a) * (r - 14);
        const x2 = cx + Math.cos(a) * (r - 7);
        const y2 = cy + Math.sin(a) * (r - 7);
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.strokeStyle = '#1a4a5a';
        ctx.lineWidth   = 1.5;
        ctx.stroke();
    }

    // Value arc
    if (percent > 0) {
        ctx.beginPath();
        ctx.arc(cx, cy, r, startAngle, fillAngle);
        ctx.strokeStyle  = valueColor;
        ctx.lineWidth    = 9;
        ctx.lineCap      = 'round';
        ctx.shadowColor  = valueColor;
        ctx.shadowBlur   = 14;
        ctx.stroke();
        ctx.shadowBlur   = 0;
    }

    // Center number
    ctx.fillStyle    = valueColor;
    ctx.font         = `bold ${Math.round(r * 0.44)}px 'Share Tech Mono', monospace`;
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(`${Math.round(value)}`, cx, cy - r * 0.04);

    // Unit label
    ctx.fillStyle = '#1a4a5a';
    ctx.font      = `${Math.round(r * 0.22)}px 'Share Tech Mono', monospace`;
    ctx.fillText('°C', cx, cy + r * 0.36);
}

// ─────────────────────────────────────────────────────
//  Waveform (canvas)
// ─────────────────────────────────────────────────────
function populateWaveform(histData) {
    waveformBuffer = histData
        .map(d => {
            const t = d.data?.temperature;
            if (!t || t.error) return null;
            const first = Object.values(t)[0];
            return first?.temp_celsius ?? null;
        })
        .filter(v => v !== null);

    if (waveformBuffer.length > WAVEFORM_MAX) {
        waveformBuffer = waveformBuffer.slice(-WAVEFORM_MAX);
    }
    drawWaveform();
}

function drawWaveform() {
    const canvas = document.getElementById('cpu-waveform');
    if (!canvas) return;

    const dpr  = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const cw   = rect.width  || 240;
    const ch   = rect.height || 52;
    if (cw === 0 || ch === 0) return;

    canvas.width  = Math.round(cw * dpr);
    canvas.height = Math.round(ch * dpr);

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    const buf = waveformBuffer.length > 1 ? waveformBuffer : Array(10).fill(30);

    // Horizontal grid
    ctx.strokeStyle = 'rgba(0, 217, 255, 0.07)';
    ctx.lineWidth   = 0.5;
    for (let i = 0; i <= 4; i++) {
        const y = (ch / 4) * i;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(cw, y);
        ctx.stroke();
    }

    const maxV  = Math.max(...buf, 100);
    const minV  = Math.min(...buf, 20);
    const range = maxV - minV || 1;
    const step  = cw / Math.max(buf.length - 1, 1);

    // Fill path
    ctx.beginPath();
    buf.forEach((v, i) => {
        const x = i * step;
        const y = ch - ((v - minV) / range) * (ch * 0.82) - ch * 0.08;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.lineTo((buf.length - 1) * step, ch);
    ctx.lineTo(0, ch);
    ctx.closePath();
    ctx.fillStyle = 'rgba(30, 255, 0, 0.06)';
    ctx.fill();

    // Stroke path
    ctx.beginPath();
    buf.forEach((v, i) => {
        const x = i * step;
        const y = ch - ((v - minV) / range) * (ch * 0.82) - ch * 0.08;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.strokeStyle = '#1eff00';
    ctx.lineWidth   = 1.5;
    ctx.shadowColor = '#1eff00';
    ctx.shadowBlur  = 5;
    ctx.stroke();
    ctx.shadowBlur  = 0;
}

// ─────────────────────────────────────────────────────
//  Memory Display
// ─────────────────────────────────────────────────────
function updateMemoryDisplay(memory) {
    if (!memory || memory.error) return;

    const pct = memory.percent_used;
    document.getElementById('ram-percent-val').textContent = `${pct}%`;

    const usedGb  = (memory.used_mb  / 1024).toFixed(1);
    const totalGb = (memory.total_mb / 1024).toFixed(1);
    document.getElementById('ram-detail-val').textContent = `${usedGb} / ${totalGb} GB`;

    renderRamBar(pct, document.getElementById('ram-bar-wrap'));
}

function renderRamBar(percent, container) {
    const total  = 24;
    const filled = Math.round((percent / 100) * total);
    const segs   = [];
    for (let i = 0; i < total; i++) {
        const ratio = i / total;
        let cls = 'ram-seg';
        if (i < filled) {
            cls += ratio < 0.6  ? ' filled seg-green' :
                   ratio < 0.85 ? ' filled seg-yellow' : ' filled seg-red';
        }
        segs.push(`<div class="${cls}"></div>`);
    }
    container.innerHTML = segs.join('');
}

// ─────────────────────────────────────────────────────
//  Disk Hexagons
// ─────────────────────────────────────────────────────
function renderDiskHexes(disks, smart) {
    const container = document.getElementById('disk-hexes');

    if (!disks || disks.error) {
        container.innerHTML = '<div class="no-data">NO DISK DATA</div>';
        return;
    }

    // device base name → health boolean
    const healthMap = {};
    if (smart && !smart.error) {
        for (const [dev, data] of Object.entries(smart)) {
            healthMap[dev.replace('/dev/', '')] = data.health_passed;
        }
    }

    const fillColors = {
        'hex-ok':       { dark: 'rgba(1,8,5,0.98)',  fill: 'rgba(0,70,35,0.97)' },
        'hex-warn':     { dark: 'rgba(8,6,1,0.98)',  fill: 'rgba(75,52,0,0.97)' },
        'hex-critical': { dark: 'rgba(8,1,1,0.98)',  fill: 'rgba(75,8,8,0.97)'  },
    };

    container.innerHTML = Object.entries(disks).map(([mount, disk]) => {
        const pct      = disk.percent_used;
        const hexClass = pct >= 90 ? 'hex-critical' : pct >= 75 ? 'hex-warn' : 'hex-ok';
        const devShort = disk.device.replace('/dev/', '');
        const health   = healthMap[devShort];
        const smartBadge =
            health === false ? '<div class="hex-smart-fail">⚠ SMART</div>' :
            health === true  ? '<div class="hex-smart-ok">● OK</div>' : '';

        const { dark, fill } = fillColors[hexClass];
        const bgStyle = `linear-gradient(to top, ${fill} ${pct}%, ${dark} ${pct}%)`;
        const scrollClass = mount.length > 10 ? ' scrolling' : '';

        return `
        <div class="disk-hex ${hexClass}" style="background: ${bgStyle}" title="${mount} — ${disk.device}">
            <div class="hex-mount"><span class="hex-mount-text${scrollClass}">${mount}</span></div>
            <div class="hex-pct">${pct}%</div>
            <div class="hex-gb">${disk.used_gb}/${disk.total_gb}G</div>
            <div class="hex-dev">${disk.device}</div>
            ${smartBadge}
        </div>`;
    }).join('');
}

// ─────────────────────────────────────────────────────
//  Docker Bars
// ─────────────────────────────────────────────────────
function renderDockerBars(docker) {
    const container = document.getElementById('docker-list');

    if (!docker || docker.error || docker.info) {
        container.innerHTML = `<div class="no-data">${docker?.error || docker?.info || 'NO DATA'}</div>`;
        return;
    }

    const order = { running: 0, restarting: 1, paused: 2, exited: 3, dead: 4 };
    const entries = Object.entries(docker).sort(([, a], [, b]) =>
        (order[a.status] ?? 5) - (order[b.status] ?? 5)
    );

    container.innerHTML = entries.map(([name, data]) => {
        const st        = data.status || 'unknown';
        const indicator = st === 'running' ? '◆' : st === 'dead' ? '✕' : '◇';
        const uptime    = st === 'running' ? formatUptime(data.uptime_seconds) : '--';
        const healthBadge =
            (data.health && data.health !== 'none')
                ? `<span class="docker-health health-${data.health}">${data.health.toUpperCase()}</span>` : '';

        const stats = st === 'running' ? `
            <span class="docker-stats-inline">
                <span class="d-stat">CPU&nbsp;${data.cpu_percent}%</span>
                <span class="d-stat">MEM&nbsp;${data.memory_mb}MB</span>
                <span class="d-stat">UP&nbsp;${uptime}</span>
                <span class="d-stat">↑${data.network_tx_mb}&nbsp;↓${data.network_rx_mb}MB</span>
                ${data.restart_count > 0 ? `<span class="d-stat warn">RST:${data.restart_count}</span>` : ''}
            </span>` : '';

        return `
        <div class="docker-bar status-${st}" title="${data.image}">
            <span class="docker-indicator">${indicator}</span>
            <span class="docker-name">${name}</span>
            <span class="docker-status-tag">${st.toUpperCase()}</span>
            ${healthBadge}
            ${stats}
        </div>`;
    }).join('');
}

// ─────────────────────────────────────────────────────
//  Process List
// ─────────────────────────────────────────────────────
function renderProcessList(processes) {
    const container = document.getElementById('process-list');

    if (!processes || processes.error) {
        container.innerHTML = `<div class="no-data">${processes?.error || 'N/A'}</div>`;
        return;
    }

    const list = processes.processes || [];
    if (list.length === 0) {
        container.innerHTML = '<div class="no-data">NO PROCESS DATA</div>';
        return;
    }

    const rows = list.map(p => `
        <div class="proc-row ${p.mem_percent > 10 ? 'proc-high' : ''}">
            <span class="proc-pid">${p.pid}</span>
            <span class="proc-name" title="${p.name}">${p.name.slice(0, 14)}</span>
            <span class="proc-mem">${p.mem_mb}M</span>
            <span class="proc-pct">${p.mem_percent}%</span>
        </div>`
    ).join('');

    container.innerHTML = `
        <div class="proc-header">
            <span>PID</span>
            <span>PROCESS</span>
            <span style="text-align:right">MEM</span>
            <span style="text-align:right">%MEM</span>
        </div>
        ${rows}`;
}

// ─────────────────────────────────────────────────────
//  MAGI Hex Scroll
// ─────────────────────────────────────────────────────
function initHexScroll() {
    const el    = document.getElementById('hex-scroll');
    const chars = '0123456789ABCDEF';
    const rh    = n => Array.from({ length: n }, () => chars[Math.floor(Math.random() * 16)]).join('');
    const segs  = Array.from({ length: 48 }, () =>
        `${rh(4)}:${rh(4)}:${rh(4)}:${rh(8)}`
    ).join('  ·  ');
    el.textContent = segs;
}

// ─────────────────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────────────────
function getTempStatus(temp) {
    const t = thresholds.temperature || {};
    if (temp >= (t.critical || 85)) return 'status-critical';
    if (temp >= (t.warning  || 70)) return 'status-warning';
    return 'status-ok';
}

function formatUptime(seconds) {
    if (seconds == null || seconds < 0) return '--';
    if (seconds < 60)  return `${seconds}s`;
    const m = Math.floor(seconds / 60);
    if (m < 60)        return `${m}m`;
    const h = Math.floor(m / 60);
    if (h < 24)        return `${h}h ${m % 60}m`;
    const d = Math.floor(h / 24);
    return `${d}d ${h % 24}h`;
}
