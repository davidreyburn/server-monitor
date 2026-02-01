# Server Monitor

Lightweight server monitoring dashboard for Ubuntu servers running Docker.

## Features

- CPU temperature monitoring
- System load averages (1, 5, 15 min)
- Memory usage tracking
- Disk usage by mount point
- SMART disk health status
- Historical graphs (24h, 7d, 30d views)
- Responsive web interface

## Quick Start

### Build and Run with Docker Compose

```bash
# Clone/copy to your server
scp -r server-monitor/ user@192.168.1.192:~/

# SSH to server
ssh user@192.168.1.192

# Build and start
cd server-monitor
docker-compose up -d --build
```

Access the dashboard at: http://192.168.1.192:8080

### Configuration

Environment variables (set in docker-compose.yml):

| Variable | Default | Description |
|----------|---------|-------------|
| COLLECTION_INTERVAL | 300 | Data collection interval (seconds) |
| RETENTION_DAYS | 90 | How long to keep historical data |
| LOG_LEVEL | WARNING | Logging level |
| TEMP_WARNING | 70 | Temperature warning threshold (°C) |
| TEMP_CRITICAL | 85 | Temperature critical threshold (°C) |
| DISK_WARNING | 80 | Disk usage warning threshold (%) |
| DISK_CRITICAL | 95 | Disk usage critical threshold (%) |
| MEMORY_WARNING | 85 | Memory usage warning threshold (%) |
| MEMORY_CRITICAL | 95 | Memory usage critical threshold (%) |

## Deployment to Server

### Option 1: Build on Server

```bash
# Copy files to server
scp -r server-monitor/ user@192.168.1.192:~/

# SSH and run
ssh user@192.168.1.192
cd server-monitor
docker-compose up -d --build
```

### Option 2: Build Locally, Transfer Image

```bash
# Build locally
docker build -t server-monitor:latest .

# Save image
docker save server-monitor:latest | gzip > server-monitor.tar.gz

# Transfer to server
scp server-monitor.tar.gz user@192.168.1.192:~/
scp docker-compose.yml user@192.168.1.192:~/server-monitor/

# Load and run on server
ssh user@192.168.1.192
docker load < server-monitor.tar.gz
cd server-monitor
docker-compose up -d
```

## SMART Monitoring

For SMART disk health monitoring to work:

1. Install smartmontools on the host: `sudo apt install smartmontools`
2. The container needs access to disk devices

Edit docker-compose.yml to list your disks:
```yaml
devices:
  - /dev/sda:/dev/sda
  - /dev/sdb:/dev/sdb
```

If SMART still doesn't work, try enabling privileged mode (less secure):
```yaml
privileged: true
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| GET / | Dashboard web interface |
| GET /api/current | Current system metrics |
| GET /api/history/{type}?hours=24 | Historical data (cpu, memory, disk, smart) |
| GET /api/latest/{type} | Latest metric of a type |
| GET /api/stats | Database statistics |
| GET /api/config | Current configuration |
| GET /health | Health check |

## Resource Usage

Container limits (configurable in docker-compose.yml):
- CPU: 0.5 cores max
- Memory: 256MB max

## Troubleshooting

**No temperature data:**
- Some systems don't expose thermal zones
- Check `/sys/class/thermal/` exists on host

**SMART data unavailable:**
- Ensure smartmontools is installed on host
- Verify disk devices are mounted in container
- May need privileged mode for some systems

**High resource usage:**
- Increase COLLECTION_INTERVAL
- Reduce RETENTION_DAYS

**View logs:**
```bash
docker logs server-monitor
docker logs -f server-monitor  # follow
```
