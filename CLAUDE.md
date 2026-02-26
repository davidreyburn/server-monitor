# Claude Code Context

## Project Summary
Lightweight server monitoring dashboard deployed to Ubuntu server at 192.168.1.192.

## Current State (2026-02-26)
- **Status:** Deployed and running
- **Dashboard URL:** http://192.168.1.192:8081
- **Container:** `server-monitor` running via docker-compose
- **SSH User:** chives
- **GitHub Repository:** https://github.com/davidreyburn/server-monitor

## Tech Stack
- Backend: Python Flask + SQLite
- Frontend: Vanilla JS + canvas (arc gauge + waveforms), Share Tech Mono font
- Container: Alpine Linux, multi-stage build
- Resource limits: 256MB RAM, 0.5 CPU

## Key Files
- `backend/app.py` - Flask API server with APScheduler for data collection and alert checking
- `backend/collectors/` - Metric collectors: cpu, memory, disk, smart, drives, docker_containers, processes, network
- `backend/database.py` - SQLite helpers; `metrics` table + `alerts` table
- `frontend/` - Dashboard UI (index.html, style.css, app.js)
- `docker-compose.yml` - Container config (port 8081, volume mounts, Docker socket)

## Deployment Commands

### Option 1: Clone from GitHub (Recommended)
```bash
# Initial deployment
ssh chives@192.168.1.192
git clone https://github.com/davidreyburn/server-monitor.git
cd server-monitor
docker compose up -d --build

# Update existing deployment
ssh chives@192.168.1.192 "cd ~/server-monitor && git pull && docker compose up -d --build"
```

### Option 2: Copy via SCP
```bash
# Copy updates to server
scp -r . chives@192.168.1.192:~/server-monitor/

# Rebuild and restart
ssh chives@192.168.1.192 "cd ~/server-monitor && docker compose up -d --build"
```

### Common Commands
```bash
# View logs
ssh chives@192.168.1.192 "docker logs server-monitor"

# Check status
ssh chives@192.168.1.192 "docker ps --filter name=server-monitor"

# Check health status
ssh chives@192.168.1.192 "docker inspect server-monitor --format='{{.State.Health.Status}}'"
```

## Features
- **NGE-themed interface:** Neon Genesis Evangelion aesthetic — dark panels, electric green/cyan palette, scanlines, Share Tech Mono font, corner bracket decorations, boot animation
- **Layout:** Three-column dashboard — Left (CPU + RAM + Storage + Network) | Center (Docker) | Right (Processes + Alerts) — with MAGI system bottom bar
- **CPU Panel (Section 01):** Canvas arc gauge (temperature), scrolling canvas waveform with min/max °C labels, load average readout
- **Memory Panel (Section 02):** Chunky segmented bar gauge (green → yellow → red), used/total GB
- **Storage Panel (Section 03):** Hexagonal tiles per mount point, vertically filled by usage %; SMART health badge; long paths scroll as ticker
- **Docker Containers (Section 04):** Parallelogram bars color-coded by status; MEM stat turns amber >20% total RAM, red >40%
- **Process Monitor (Section 05):** Top 12 processes by RSS memory; memory values color-graded (amber >2% RAM, red >5%)
- **Network I/O Panel (Section 06):** Dual-line waveform (TX=green, RX=cyan), current MB/s readout; reads `/proc/net/dev` via module-level delta cache
- **Threshold Events Log (Section 07):** Persistent alert log in right column; alerts written by scheduler only (not on page load); 1-hour dedup cooldown per metric+level
- **MAGI Bar:** MELCHIOR=CPU temp, BALTHASAR=RAM, CASPER=worst disk; green/amber/red with blink on FAIL
- **Loading Spinners:** 8-segment green pulse wave shown in all dynamic content containers on page load
- **Historical Data:** 90-day retention; CPU temp and network waveforms support 24h/7d/30d views
- **Auto-refresh:** 60-second interval

## Pending / Future Work
- [ ] Email/push notification delivery for alerts
- [ ] Export data to CSV
- [ ] Set up automated database backups
- [ ] Per-container CPU usage history waveform

## Notes
- Port 8080 was already in use on server, using 8081 instead
- Added `coreutils` to Alpine image for `df` command
- Container needs SYS_RAWIO capability for SMART disk access
- Container needs Docker socket mount (`/var/run/docker.sock:ro`) for Docker monitoring
- External drive mounted at `/mnt/external-hdd:ro` for disk usage monitoring
- Database init and scheduler must run at module load (not in `__main__`) for gunicorn compatibility
- Disk collector filters out pseudo-filesystems (efivarfs, sysfs, tmpfs, etc.) and very small filesystems (<10 MB) to prevent dashboard clutter
- Drive collector uses `lsblk` to discover all block devices and reads `/host/proc/1/mounts` (host init process) to get mount info from host's mount namespace
- Docker monitoring uses Docker SDK (docker>=7.0.0) to collect comprehensive container metrics
- Process collector reads `/host/proc/[pid]/comm`, `/statm`, and `/stat` directly — no extra dependencies
- CPU collector also reads `/proc/uptime` and returns `uptime_seconds` in the load response
- Network collector uses module-level `_prev_bytes` / `_prev_time` cache to compute delta rates; first call returns `{_initializing: True}` and is not stored to DB
- Network collector skips loopback and virtual interfaces (docker*, br-*, veth*, virbr*, dummy*, tunl*, sit*)
- Alert checking runs only in `collect_all_metrics()` (scheduler), not in `/api/current` (which runs on every dashboard load) — prevents duplicate alerts on refresh
- Frontend uses canvas (not Chart.js) for arc gauge and all waveforms; Chart.js is loaded but not actively used
- `design-spec.md` and `reference/` directory (10 NGE reference images) exist locally but are not committed to the repo

## Resolved Issues
- **2026-02-01:** Fixed graphs not displaying - database wasn't initialized because `init_database()` was in `__main__` block which gunicorn doesn't execute. Moved to module-level initialization.
- **2026-02-03:** Fixed Docker health check IPv4/IPv6 issue - Changed health check from `localhost` to `127.0.0.1` to prevent false "unhealthy" status.
- **2026-02-03:** Published to GitHub - Created public repository at https://github.com/davidreyburn/server-monitor.
- **2026-02-04:** Added all connected drives and Docker container monitoring.
- **2026-02-04:** Fixed drives showing as unmounted - reads from `/host/proc/1/mounts` instead of `/host/proc/mounts`.
- **2026-02-26:** Full NGE interface redesign. Added process monitoring collector.
- **2026-02-26:** Storage hexagon improvements — honeycomb layout (row 2+ pulls up -28px), vertical fill by usage %, ticker scrolling for long mount/device paths.
- **2026-02-26:** Added network I/O panel, threshold alert log, dynamic MAGI status, process/docker memory color-grading, waveform y-axis labels, and page-load spinners.
