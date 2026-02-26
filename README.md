# Server Monitor

A Neon Genesis Evangelion–themed server monitoring dashboard for Ubuntu servers running Docker. Displays real-time system metrics in a dark, angular interface styled after NERV computer interfaces from the anime.

## Features

- **CPU** — Arc gauge (temperature), scrolling waveform history with min/max °C labels, load average (1/5/15 min)
- **Memory** — Chunky segmented bar gauge with green → yellow → red gradient
- **Storage** — Hexagonal tiles per mount point, vertically filled by usage %, with SMART health indicators and scrolling path labels
- **Network I/O** — Dual waveform (TX green, RX cyan) with current MB/s readout; history supports 24h / 7d / 30d views
- **Docker Containers** — Parallelogram bars color-coded by status (running/paused/exited/dead), with CPU%, memory (amber/red when high), uptime, network I/O, restart count
- **Processes** — Top 12 processes by RSS memory; memory values color-graded (amber >2% RAM, red >5% RAM)
- **MAGI System Bottom Bar** — MELCHIOR (CPU temp) / BALTHASAR (RAM) / CASPER (disk) — live status: green OK, amber WARN, red FAIL with blink
- **Threshold Event Log** — Persistent alert history for CPU temp, RAM, and disk threshold crossings, logged with 1-hour deduplication cooldown
- **Loading Spinners** — Sequential green segment pulse shown in every panel on page load until data arrives
- **Historical Data** — 90-day retention; waveform views support 24h / 7d / 30d
- **Auto-refresh** — 60-second interval

## Quick Start

```bash
# SSH to your server and clone
ssh user@your-server
git clone https://github.com/davidreyburn/server-monitor.git
cd server-monitor
docker compose up -d --build
```

Access the dashboard at: **http://your-server:8081**

## Update Existing Deployment

```bash
ssh user@your-server "cd ~/server-monitor && git pull && docker compose up -d --build"
```

## Configuration

Environment variables (set in `docker-compose.yml`):

| Variable | Default | Description |
|---|---|---|
| `COLLECTION_INTERVAL` | `300` | Data collection interval (seconds) |
| `RETENTION_DAYS` | `90` | Historical data retention |
| `LOG_LEVEL` | `WARNING` | Logging verbosity |
| `TEMP_WARNING` | `70` | CPU temperature warning threshold (°C) |
| `TEMP_CRITICAL` | `85` | CPU temperature critical threshold (°C) |
| `DISK_WARNING` | `80` | Disk usage warning threshold (%) |
| `DISK_CRITICAL` | `95` | Disk usage critical threshold (%) |
| `MEMORY_WARNING` | `85` | Memory usage warning threshold (%) |
| `MEMORY_CRITICAL` | `95` | Memory usage critical threshold (%) |

## Volume Mounts

The container requires several host paths to be mounted:

```yaml
volumes:
  - ./data:/app/data              # SQLite database persistence
  - /sys:/host/sys:ro             # CPU temperature (thermal zones)
  - /proc:/host/proc:ro           # Load avg, memory, process info, network stats, uptime
  - /dev:/dev:ro                  # SMART disk access
  - /var/run/docker.sock:/var/run/docker.sock:ro  # Docker monitoring
```

Optionally mount external/additional drives to include them in disk usage monitoring:
```yaml
  - /mnt/external-hdd:/mnt/external-hdd:ro
  - /mnt/internal-ssd:/mnt/internal-ssd:ro
```

## SMART Monitoring

1. Install smartmontools on the host: `sudo apt install smartmontools`
2. List your disk devices in `docker-compose.yml`:
   ```yaml
   devices:
     - /dev/sda:/dev/sda
     - /dev/sdb:/dev/sdb
   ```
3. The container uses `SYS_RAWIO` capability for SMART access. If that's insufficient, enable privileged mode (less secure):
   ```yaml
   privileged: true
   ```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Dashboard web interface |
| `GET /api/current` | All current metrics (cpu, memory, disk, smart, drives, docker, processes, network) |
| `GET /api/history/{type}?hours=24` | Historical data — valid types: `cpu`, `memory`, `disk`, `smart`, `drives`, `docker`, `processes`, `network` |
| `GET /api/latest/{type}` | Latest stored metric of a given type |
| `GET /api/alerts` | Recent threshold alert events (newest first, max 50) |
| `GET /api/stats` | Database record count and size |
| `GET /api/config` | Active configuration and thresholds |
| `GET /health` | Health check (used by Docker) |

## Resource Usage

Container limits (configurable in `docker-compose.yml`):
- CPU: 0.5 cores max
- Memory: 256MB max

Typical observed usage: ~43MB RAM, <0.1% CPU between collection cycles.

## Troubleshooting

**No temperature data**
- Some systems don't expose thermal zones. Check `/sys/class/thermal/` on the host.

**Network I/O shows `--` or initializing**
- The network collector requires two collection cycles to compute a rate delta. Rates will appear after the first scheduled collection (~5 minutes after start). Virtual interfaces (docker*, br-*, veth*) are excluded automatically.

**SMART data unavailable**
- Ensure `smartmontools` is installed on the host.
- Verify disk devices are listed under `devices:` in `docker-compose.yml`.

**Disks not showing / wrong mount info**
- The disk collector reads from `/host/proc/1/mounts` (the host's init process) to bypass the container's mount namespace. Ensure `/proc:/host/proc:ro` is mounted.

**Process list empty or erroring**
- Requires `/proc:/host/proc:ro` mount. The collector reads `/host/proc/[pid]/comm`, `/statm`, and `/stat` directly.

**Disk mount points not appearing**
- The collector filters out pseudo-filesystems (tmpfs, efivarfs, sysfs, cgroup, etc.) and filesystems smaller than 10MB. This is intentional.

**No alerts appearing**
- Alerts are only logged by the background scheduler, not by dashboard refreshes. They will appear once a threshold is crossed during a scheduled collection cycle. The same alert won't repeat within 1 hour.

**Container shows as unhealthy**
- The health check uses `127.0.0.1` (not `localhost`) to avoid IPv6/IPv4 ambiguity with gunicorn's IPv4-only binding.
- Verify: `docker inspect server-monitor --format='{{json .State.Health}}' | jq .`
- Manual test: `docker exec server-monitor wget -O- http://127.0.0.1:8080/health`

**View logs**
```bash
docker logs server-monitor
docker logs -f server-monitor   # follow
```

**Restart container**
```bash
docker compose restart
```
