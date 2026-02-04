# Claude Code Context

## Project Summary
Lightweight server monitoring dashboard deployed to Ubuntu server at 192.168.1.192.

## Current State (2026-02-04)
- **Status:** Deployed and running
- **Dashboard URL:** http://192.168.1.192:8081
- **Container:** `server-monitor` running via docker-compose
- **SSH User:** chives
- **GitHub Repository:** https://github.com/davidreyburn/server-monitor

## Tech Stack
- Backend: Python Flask + SQLite
- Frontend: Vanilla JS + Chart.js
- Container: Alpine Linux, multi-stage build
- Resource limits: 256MB RAM, 0.5 CPU

## Key Files
- `backend/app.py` - Flask API server with APScheduler for data collection
- `backend/collectors/` - Metric collectors (cpu, memory, disk, smart, drives, docker_containers)
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
- **System Monitoring:** CPU temperature, load average, memory usage
- **Disk Monitoring:** Usage stats with SMART health data
- **All Connected Drives:** Shows all physical drives (mounted and unmounted) with size and model
- **Docker Containers:** Comprehensive monitoring with status, health, CPU%, memory, network I/O, uptime, restart count
- **Historical Data:** 90-day retention with interactive charts
- **Auto-refresh:** 60-second interval, configurable time ranges

## Pending / Future Work
- [ ] Email/notification alerts for thresholds
- [ ] Network bandwidth monitoring
- [ ] Export data to CSV
- [ ] Set up automated database backups

## Notes
- Port 8080 was already in use on server, using 8081 instead
- Added `coreutils` to Alpine image for `df` command
- Container needs SYS_RAWIO capability for SMART disk access
- Container needs Docker socket mount (`/var/run/docker.sock:ro`) for Docker monitoring
- Database init and scheduler must run at module load (not in `__main__`) for gunicorn compatibility
- Disk collector filters out pseudo-filesystems (efivarfs, sysfs, tmpfs, etc.) and very small filesystems (<10 MB) to prevent dashboard clutter
- Drive collector uses `lsblk` to discover all block devices and cross-references with `df` for mount info
- Docker monitoring uses Docker SDK (docker>=7.0.0) to collect comprehensive container metrics

## Resolved Issues
- **2026-02-01:** Fixed graphs not displaying - database wasn't initialized because `init_database()` was in `__main__` block which gunicorn doesn't execute. Moved to module-level initialization.
- **2026-02-03:** Fixed Docker health check IPv4/IPv6 issue - Changed health check from `localhost` to `127.0.0.1` to prevent false "unhealthy" status. Docker's localhost resolves to both IPv4 and IPv6, but gunicorn only binds to IPv4, causing health check failures. Enhanced documentation with comprehensive troubleshooting guide.
- **2026-02-03:** Published to GitHub - Created public repository at https://github.com/davidreyburn/server-monitor with complete commit history.
- **2026-02-04:** Added all connected drives and Docker container monitoring - Implemented two new monitoring features: (1) All Connected Drives section showing all physical drives with mount status, size, and model; (2) Docker Containers section with comprehensive metrics including status, health, CPU%, memory, network I/O, uptime, and restart count. Performance impact minimal (~150ms per 5-minute collection cycle). Resource usage well within limits (43MB / 256MB memory, <0.1% CPU).
