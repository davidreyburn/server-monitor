# Claude Code Context

## Project Summary
Lightweight server monitoring dashboard deployed to Ubuntu server at 192.168.1.192.

## Current State (2026-02-01)
- **Status:** Deployed and running
- **Dashboard URL:** http://192.168.1.192:8081
- **Container:** `server-monitor` running via docker-compose
- **SSH User:** chives

## Tech Stack
- Backend: Python Flask + SQLite
- Frontend: Vanilla JS + Chart.js
- Container: Alpine Linux, multi-stage build
- Resource limits: 256MB RAM, 0.5 CPU

## Key Files
- `backend/app.py` - Flask API server with APScheduler for data collection
- `backend/collectors/` - Metric collectors (cpu, memory, disk, smart)
- `frontend/` - Dashboard UI (index.html, style.css, app.js)
- `docker-compose.yml` - Container config (port 8081, volume mounts)

## Deployment Commands
```bash
# Copy updates to server
scp -r . chives@192.168.1.192:~/server-monitor/

# Rebuild and restart
ssh chives@192.168.1.192 "cd ~/server-monitor && docker compose up -d --build"

# View logs
ssh chives@192.168.1.192 "docker logs server-monitor"

# Check status
ssh chives@192.168.1.192 "docker ps --filter name=server-monitor"
```

## Pending / Future Work
- [ ] Push to GitHub (gh CLI not installed)
- [ ] Email/notification alerts for thresholds
- [ ] Docker container status overview
- [ ] Network bandwidth monitoring
- [ ] Export data to CSV
- [ ] Set up automated database backups

## Notes
- Port 8080 was already in use on server, using 8081 instead
- Added `coreutils` to Alpine image for `df` command
- Container needs SYS_RAWIO capability for SMART disk access
- Database init and scheduler must run at module load (not in `__main__`) for gunicorn compatibility

## Resolved Issues
- **2026-02-01:** Fixed graphs not displaying - database wasn't initialized because `init_database()` was in `__main__` block which gunicorn doesn't execute. Moved to module-level initialization.
