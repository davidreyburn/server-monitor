// Server Monitor Dashboard Application

const API_BASE = '';
let charts = {};
let thresholds = {};
let refreshInterval = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    loadData();
    setupEventListeners();
    startAutoRefresh();
});

function setupEventListeners() {
    document.getElementById('refresh-btn').addEventListener('click', loadData);
    document.getElementById('time-range').addEventListener('change', loadHistoricalData);
}

function startAutoRefresh() {
    // Refresh every 60 seconds
    refreshInterval = setInterval(loadData, 60000);
}

async function loadData() {
    try {
        const response = await fetch(`${API_BASE}/api/current`);
        if (!response.ok) throw new Error('Failed to fetch data');

        const data = await response.json();
        thresholds = data.thresholds || {};

        updateCpuDisplay(data.cpu);
        updateMemoryDisplay(data.memory);
        updateDiskDisplay(data.disk);
        updateSmartDisplay(data.smart);
        updateDrivesDisplay(data.drives);
        updateDockerDisplay(data.docker);

        document.getElementById('last-update').textContent =
            `Last update: ${new Date().toLocaleTimeString()}`;

        loadHistoricalData();
        loadStats();
    } catch (error) {
        console.error('Error loading data:', error);
    }
}

async function loadHistoricalData() {
    const hours = document.getElementById('time-range').value;

    try {
        const [cpuRes, memRes] = await Promise.all([
            fetch(`${API_BASE}/api/history/cpu?hours=${hours}`),
            fetch(`${API_BASE}/api/history/memory?hours=${hours}`)
        ]);

        const cpuData = await cpuRes.json();
        const memData = await memRes.json();

        updateTempChart(cpuData.data);
        updateLoadChart(cpuData.data);
        updateMemoryChart(memData.data);
    } catch (error) {
        console.error('Error loading historical data:', error);
    }
}

async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/api/stats`);
        const stats = await response.json();

        document.getElementById('db-stats').textContent =
            `Records: ${stats.total_records || 0} | DB Size: ${stats.database_size_mb || 0} MB`;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

function updateCpuDisplay(cpu) {
    if (!cpu || cpu.error) {
        document.getElementById('cpu-temp').textContent = 'N/A';
        return;
    }

    const temps = cpu.temperature;
    if (temps && !temps.error) {
        // Find the primary CPU temperature
        let mainTemp = null;
        for (const [zone, data] of Object.entries(temps)) {
            if (data.type && (data.type.includes('cpu') || data.type.includes('x86'))) {
                mainTemp = data.temp_celsius;
                break;
            }
        }
        // Fallback to first available
        if (mainTemp === null) {
            const firstZone = Object.values(temps)[0];
            mainTemp = firstZone?.temp_celsius;
        }

        if (mainTemp !== null) {
            const tempEl = document.getElementById('cpu-temp');
            tempEl.textContent = `${mainTemp}°C`;
            tempEl.className = 'metric-value ' + getTempStatus(mainTemp);
        }
    }

    const load = cpu.load;
    if (load && !load.error) {
        document.getElementById('load-1').textContent = load.load_1min?.toFixed(2) || '--';
        document.getElementById('load-5').textContent = load.load_5min?.toFixed(2) || '--';
        document.getElementById('load-15').textContent = load.load_15min?.toFixed(2) || '--';
    }
}

function updateMemoryDisplay(memory) {
    if (!memory || memory.error) {
        document.getElementById('memory-percent').textContent = 'N/A';
        return;
    }

    const percent = memory.percent_used;
    const percentEl = document.getElementById('memory-percent');
    percentEl.textContent = `${percent}%`;
    percentEl.className = 'metric-value ' + getMemoryStatus(percent);

    const usedGb = (memory.used_mb / 1024).toFixed(1);
    const totalGb = (memory.total_mb / 1024).toFixed(1);
    document.getElementById('memory-detail').textContent = `${usedGb} / ${totalGb} GB`;
}

function updateDiskDisplay(disks) {
    const container = document.getElementById('disk-list');

    if (!disks || disks.error) {
        container.innerHTML = '<div class="error-message">Unable to retrieve disk information</div>';
        return;
    }

    container.innerHTML = Object.entries(disks).map(([mount, disk]) => {
        const statusClass = getDiskStatus(disk.percent_used);
        return `
            <div class="disk-item">
                <div class="mount">${mount}</div>
                <div class="device">${disk.device} (${disk.fstype})</div>
                <div class="progress-bar">
                    <div class="progress-fill ${statusClass}" style="width: ${disk.percent_used}%"></div>
                </div>
                <div class="usage-text">
                    <span>${disk.used_gb} / ${disk.total_gb} GB</span>
                    <span class="${'status-' + statusClass}">${disk.percent_used}%</span>
                </div>
            </div>
        `;
    }).join('');
}

function updateSmartDisplay(smart) {
    const container = document.getElementById('smart-list');

    if (!smart || smart.error) {
        container.innerHTML = `<div class="error-message">SMART data unavailable: ${smart?.error || 'Unknown error'}</div>`;
        return;
    }

    container.innerHTML = Object.entries(smart).map(([device, data]) => {
        const healthClass = data.health_passed === true ? 'passed' :
                          data.health_passed === false ? 'failed' : 'unknown';
        const healthText = data.health_passed === true ? 'Healthy' :
                          data.health_passed === false ? 'Failed' : 'Unknown';

        return `
            <div class="smart-item">
                <div class="model">${data.model || 'Unknown Model'}</div>
                <div class="device">${device} | S/N: ${data.serial || 'N/A'}</div>
                <span class="health ${healthClass}">${healthText}</span>
                <div class="details">
                    ${data.temperature_celsius ? `Temp: ${data.temperature_celsius}°C` : ''}
                    ${data.power_on_hours ? ` | Power-on: ${(data.power_on_hours / 24).toFixed(0)} days` : ''}
                </div>
            </div>
        `;
    }).join('');
}

function initCharts() {
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false }
        },
        scales: {
            x: {
                display: true,
                grid: { color: 'rgba(255,255,255,0.1)' },
                ticks: { color: '#aaa', maxTicksLimit: 6 }
            },
            y: {
                display: true,
                grid: { color: 'rgba(255,255,255,0.1)' },
                ticks: { color: '#aaa' }
            }
        }
    };

    charts.temp = new Chart(document.getElementById('temp-chart'), {
        type: 'line',
        data: { labels: [], datasets: [{ data: [], borderColor: '#e94560', tension: 0.3, fill: false }] },
        options: { ...chartOptions, scales: { ...chartOptions.scales, y: { ...chartOptions.scales.y, min: 20, max: 100 } } }
    });

    charts.load = new Chart(document.getElementById('load-chart'), {
        type: 'line',
        data: { labels: [], datasets: [
            { label: '1m', data: [], borderColor: '#4ade80', tension: 0.3, fill: false },
            { label: '5m', data: [], borderColor: '#fbbf24', tension: 0.3, fill: false },
            { label: '15m', data: [], borderColor: '#e94560', tension: 0.3, fill: false }
        ] },
        options: { ...chartOptions, plugins: { legend: { display: true, labels: { color: '#aaa' } } } }
    });

    charts.memory = new Chart(document.getElementById('memory-chart'), {
        type: 'line',
        data: { labels: [], datasets: [{ data: [], borderColor: '#60a5fa', tension: 0.3, fill: true, backgroundColor: 'rgba(96,165,250,0.1)' }] },
        options: { ...chartOptions, scales: { ...chartOptions.scales, y: { ...chartOptions.scales.y, min: 0, max: 100 } } }
    });
}

function updateTempChart(data) {
    if (!data || data.length === 0) return;

    const labels = data.map(d => formatTime(d.timestamp));
    const temps = data.map(d => {
        const tempData = d.data?.temperature;
        if (!tempData || tempData.error) return null;
        const firstZone = Object.values(tempData)[0];
        return firstZone?.temp_celsius || null;
    });

    charts.temp.data.labels = labels;
    charts.temp.data.datasets[0].data = temps;
    charts.temp.update('none');
}

function updateLoadChart(data) {
    if (!data || data.length === 0) return;

    const labels = data.map(d => formatTime(d.timestamp));
    const load1 = data.map(d => d.data?.load?.load_1min || null);
    const load5 = data.map(d => d.data?.load?.load_5min || null);
    const load15 = data.map(d => d.data?.load?.load_15min || null);

    charts.load.data.labels = labels;
    charts.load.data.datasets[0].data = load1;
    charts.load.data.datasets[1].data = load5;
    charts.load.data.datasets[2].data = load15;
    charts.load.update('none');
}

function updateMemoryChart(data) {
    if (!data || data.length === 0) return;

    const labels = data.map(d => formatTime(d.timestamp));
    const percentages = data.map(d => d.data?.percent_used || null);

    charts.memory.data.labels = labels;
    charts.memory.data.datasets[0].data = percentages;
    charts.memory.update('none');
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    const hours = document.getElementById('time-range').value;

    if (hours <= 24) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else {
        return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
}

function getTempStatus(temp) {
    const t = thresholds.temperature || {};
    if (temp >= (t.critical || 85)) return 'status-critical';
    if (temp >= (t.warning || 70)) return 'status-warning';
    return 'status-ok';
}

function getMemoryStatus(percent) {
    const m = thresholds.memory || {};
    if (percent >= (m.critical || 95)) return 'danger';
    if (percent >= (m.warning || 85)) return 'warning';
    return 'success';
}

function getDiskStatus(percent) {
    const d = thresholds.disk || {};
    if (percent >= (d.critical || 95)) return 'danger';
    if (percent >= (d.warning || 80)) return 'warning';
    return 'success';
}

function updateDrivesDisplay(drives) {
    const container = document.getElementById('drives-list');

    if (!drives || drives.error) {
        container.innerHTML = '<div class="error-message">Unable to retrieve drives information</div>';
        return;
    }

    if (drives.info) {
        container.innerHTML = `<div class="info-message">${drives.info}</div>`;
        return;
    }

    container.innerHTML = Object.entries(drives).map(([device, data]) => {
        const statusClass = data.mounted ? 'mounted' : 'unmounted';
        const statusText = data.mounted ? `Mounted at ${data.mount_point}` : 'Unmounted';

        return `
            <div class="drive-item ${statusClass}">
                <div class="device-name">${device}</div>
                <div class="device-model">${data.model || 'Unknown'}</div>
                <div class="device-info">
                    <span>${data.size_gb} GB</span>
                    <span class="status-badge ${statusClass}">${statusText}</span>
                    ${data.fstype ? `<span class="fstype">${data.fstype}</span>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

function updateDockerDisplay(docker) {
    const container = document.getElementById('docker-list');

    if (!docker || docker.error) {
        container.innerHTML = `<div class="info-message">Docker monitoring unavailable: ${docker?.error || 'unknown error'}</div>`;
        return;
    }

    if (docker.info) {
        container.innerHTML = `<div class="info-message">${docker.info}</div>`;
        return;
    }

    // Sort: running first, then by name
    const entries = Object.entries(docker).sort(([nameA, dataA], [nameB, dataB]) => {
        if (dataA.status === 'running' && dataB.status !== 'running') return -1;
        if (dataA.status !== 'running' && dataB.status === 'running') return 1;
        return nameA.localeCompare(nameB);
    });

    container.innerHTML = entries.map(([name, data]) => {
        const statusClass = getDockerStatusClass(data.status);
        const healthClass = getDockerHealthClass(data.health);
        const uptime = formatUptime(data.uptime_seconds);

        return `
            <div class="docker-item ${statusClass}">
                <div class="docker-header">
                    <div>
                        <div class="container-name">${name}</div>
                        <div class="container-image">${data.image}</div>
                    </div>
                    <div class="docker-badges">
                        <span class="status-badge ${statusClass}">${data.status}</span>
                        ${data.health !== 'none' ? `<span class="health-badge ${healthClass}">${data.health}</span>` : ''}
                    </div>
                </div>
                ${data.status === 'running' ? `
                    <div class="docker-stats">
                        <div class="stat">
                            <span class="stat-label">CPU</span>
                            <span class="stat-value">${data.cpu_percent}%</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">Memory</span>
                            <span class="stat-value">${data.memory_mb} MB (${data.memory_percent}%)</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">Network RX</span>
                            <span class="stat-value">${data.network_rx_mb} MB</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">Network TX</span>
                            <span class="stat-value">${data.network_tx_mb} MB</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">Uptime</span>
                            <span class="stat-value">${uptime}</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">Restarts</span>
                            <span class="stat-value">${data.restart_count}</span>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

function getDockerStatusClass(status) {
    const map = {
        'running': 'status-running',
        'exited': 'status-exited',
        'paused': 'status-paused',
        'restarting': 'status-restarting',
        'dead': 'status-dead'
    };
    return map[status] || 'status-unknown';
}

function getDockerHealthClass(health) {
    const map = {
        'healthy': 'health-healthy',
        'unhealthy': 'health-unhealthy',
        'starting': 'health-starting'
    };
    return map[health] || '';
}

function formatUptime(seconds) {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ${minutes % 60}m`;
    const days = Math.floor(hours / 24);
    return `${days}d ${hours % 24}h`;
}
