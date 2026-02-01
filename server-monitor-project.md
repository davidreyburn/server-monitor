# Server Monitoring Dashboard Project

## Project Overview
Build and deploy a lightweight web-based dashboard to monitor Ubuntu server stats (temperature, load, storage, disk health) with minimal performance impact on the host running Plex and other Docker containers.

**Target Server:** Ubuntu at 192.168.1.192  
**Deployment Method:** Docker container (to match existing infrastructure)  
**Performance Priority:** Minimal resource usage

---

## Technical Architecture

### Frontend
- Static HTML/CSS/JavaScript (no heavy frameworks)
- Chart.js or similar lightweight charting library
- Responsive design for desktop and mobile viewing
- Auto-refresh capability for real-time updates

### Backend
- Lightweight Python Flask or Node.js Express API
- Endpoints to serve system metrics
- Historical data storage (SQLite for minimal overhead)
- Data collection at configurable intervals (default: every 5 minutes)

### System Monitoring
- **CPU Temperature:** Read from `/sys/class/thermal/thermal_zone*/temp`
- **System Load:** Read from `/proc/loadavg`
- **Disk Usage:** Use `df` command or `/proc/mounts`
- **Disk Health:** Parse `smartctl` output (requires smartmontools)
- **Memory Usage:** Read from `/proc/meminfo`
- **Docker Stats:** Optional integration with Docker API

### Deployment
- Single Docker container with multi-stage build
- Volume mount for persistent data storage
- Minimal base image (Alpine Linux)
- Port mapping to host (e.g., 8080:80)
- Restart policy: unless-stopped

---

## File Structure
```
server-monitor/
├── Dockerfile
├── docker-compose.yml
├── backend/
│   ├── app.py (or server.js)
│   ├── requirements.txt (or package.json)
│   ├── database.py
│   └── collectors/
│       ├── cpu.py
│       ├── disk.py
│       ├── memory.py
│       └── smart.py
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── data/
    └── metrics.db (created at runtime)
```

---

## Features Checklist

### Core Features
- [x] Real-time system metrics display
- [x] Historical graphs (last 24 hours, 7 days, 30 days)
- [x] Disk health status with SMART data
- [x] Temperature monitoring with alerts
- [x] Storage usage by mount point
- [x] System load averages (1, 5, 15 min)

### Nice-to-Have Features
- [ ] Email/notification alerts for critical thresholds
- [ ] Docker container status overview
- [ ] Network bandwidth monitoring
- [x] Configurable refresh intervals
- [x] Dark theme (default)
- [ ] Export data to CSV

---

## Performance Considerations
- Data collection interval: 5 minutes (configurable)
- Database cleanup: Auto-purge data older than 90 days
- Container resource limits: 256MB RAM, 0.5 CPU
- Minimal logging to reduce I/O
- Efficient queries with proper indexing
- Static asset caching

---

## Deployment Steps
1. Build Docker image on development machine or directly on server
2. Create docker-compose.yml with volume mounts
3. Deploy to server at 192.168.1.192
4. Access dashboard at http://192.168.1.192:8081
5. Verify metrics collection is working
6. Set up automated backups of metrics database

---

## Security Considerations
- No authentication required (local network only)
- Optional: Add basic HTTP auth if desired
- Read-only access to system files
- No external network access required
- Restrict Docker container permissions (no privileged mode unless needed for SMART)

---

# Claude Code Prompt

```
I need you to build and deploy a lightweight server monitoring dashboard for my Ubuntu server at 192.168.1.192.

## Requirements:

**Server Context:**
- Ubuntu server running Docker containers (Plex and other services)
- Must have MINIMAL performance impact
- Deploy as a Docker container to match existing infrastructure

**Monitoring Metrics:**
1. CPU temperature (from /sys/class/thermal/)
2. System load (1, 5, 15 minute averages)
3. Disk usage by mount point (free space, total space, percentage)
4. Disk health using SMART data (requires smartmontools)
5. Memory usage (total, used, free, cached)

**Dashboard Features:**
- Clean, responsive web interface (HTML/CSS/JS, no heavy frameworks)
- Real-time metric display with auto-refresh
- Historical graphs showing data over time (24h, 7d, 30d views)
- Use Chart.js or similar lightweight charting library
- Display SMART status for each disk (health status, temperature, errors)

**Technical Stack:**
- Backend: Python Flask (preferred) or Node.js Express
- Database: SQLite for historical data (lightweight)
- Frontend: Vanilla JavaScript with Chart.js
- Container: Alpine Linux base image for minimal size
- Data collection: Every 5 minutes (configurable)
- Data retention: 90 days (auto-cleanup old data)

**Docker Configuration:**
- Create Dockerfile with multi-stage build for efficiency
- Create docker-compose.yml file
- Volume mount for persistent database storage
- Expose port 8080 for web access
- Resource limits: 256MB RAM max, 0.5 CPU max
- Restart policy: unless-stopped
- Container needs access to host metrics (volume mounts for /sys, /proc, /dev for SMART)

**Deployment Steps:**
1. Create all necessary files in a 'server-monitor' directory
2. Build the Docker image
3. Generate deployment instructions for 192.168.1.192
4. Include docker-compose.yml for easy deployment
5. Provide commands to deploy to the server via SSH/SCP

**Additional Requirements:**
- Efficient database queries with proper indexing
- Minimal logging to reduce disk I/O
- Error handling for missing sensors or permissions
- Configuration file for thresholds and intervals
- README with setup and deployment instructions

Please create the complete project structure, all code files, Docker configuration, and deployment instructions. Make it production-ready and optimized for minimal resource usage.
```

---

## Post-Deployment Testing

1. Verify web interface loads at http://192.168.1.192:8081
2. Confirm all metrics are being collected
3. Check Docker container resource usage: `docker stats server-monitor`
4. Verify database is growing appropriately
5. Test historical graphs after 24 hours of data collection
6. Monitor Plex performance to ensure no impact

---

## Maintenance Tasks

- Weekly: Check container logs for errors
- Monthly: Verify database size and cleanup
- Quarterly: Review and update SMART thresholds
- As needed: Adjust data retention period based on storage

---

## Troubleshooting

**SMART data not available:**
- Container may need `--privileged` flag or specific device access
- Ensure smartmontools is installed in container
- Check host has smartmontools: `sudo apt install smartmontools`

**High CPU usage:**
- Increase data collection interval
- Optimize database queries
- Check for infinite loops in monitoring scripts

**Missing metrics:**
- Verify volume mounts in docker-compose.yml
- Check file permissions on host
- Review container logs: `docker logs server-monitor`

---

## Deployment Log

### 2026-02-01 - Initial Deployment

**Completed:**
1. Created complete project structure with Python Flask backend and vanilla JS frontend
2. Built Docker image with multi-stage Alpine Linux build
3. Deployed to server at 192.168.1.192 via SCP/SSH (user: chives)
4. Container running on port 8081 (8080 was already in use)

**Dashboard URL:** http://192.168.1.192:8081

**Verified Working:**
| Metric | Status | Sample Value |
|--------|--------|--------------|
| CPU Temperature | Working | 48.0°C |
| System Load | Working | 0.11, 0.16, 0.11 |
| Memory Usage | Working | 9.7% of 15.7 GB |
| Disk Usage | Working | 17% of 97.87 GB |
| SMART Health | Working | sda, sdb - both healthy |

**Notes:**
- Had to add `coreutils` package to Alpine image for `df` command
- Port changed from 8080 to 8081 due to conflict on server
- Container configured with SYS_RAWIO capability for SMART access
- Data collection running every 5 minutes
