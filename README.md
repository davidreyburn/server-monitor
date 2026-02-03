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

## Health Check Configuration

The Docker health check uses an explicit IPv4 address (`127.0.0.1`) instead of `localhost`:

```yaml
healthcheck:
  test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://127.0.0.1:8080/health"]
```

**Why not use `localhost`?**

Docker's DNS resolution can cause issues:
1. `localhost` resolves to both IPv4 (`127.0.0.1`) and IPv6 (`::1`)
2. wget attempts IPv6 first: `[::1]:8080`
3. gunicorn binds to `0.0.0.0:8080` (IPv4 only)
4. IPv6 connection fails → health check fails → container shows "unhealthy"
5. Application works perfectly on IPv4 but Docker marks it unhealthy

**Solution**: Using `127.0.0.1` explicitly:
- Forces IPv4 connection (no DNS ambiguity)
- Connects directly to where gunicorn is listening
- Prevents false "unhealthy" status

**Verify health check is working:**
```bash
# Check container health status
docker ps --filter name=server-monitor

# View detailed health check logs
docker inspect server-monitor --format='{{json .State.Health}}' | jq .

# Manually test the health endpoint
curl http://127.0.0.1:8081/health
```

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

**Container shows as unhealthy:**
- Check health check logs: `docker inspect server-monitor --format='{{json .State.Health}}' | jq .`
- Verify the application is actually working: `curl http://localhost:8081`
- Ensure docker-compose.yml uses `127.0.0.1` (not `localhost`) in health check
- Test health endpoint inside container: `docker exec server-monitor wget -O- http://127.0.0.1:8080/health`

**Debug Docker health check:**
```bash
# View full container health status
docker inspect server-monitor --format='{{json .State.Health}}' | jq .

# Check last 5 health check results
docker inspect server-monitor --format='{{range .State.Health.Log}}{{.Output}}{{end}}'

# Manually run health check command inside container
docker exec server-monitor wget --no-verbose --tries=1 --spider http://127.0.0.1:8080/health

# Check if gunicorn is listening on the right port
docker exec server-monitor netstat -tlnp | grep 8080
```

**Restart container to reset health status:**
```bash
cd /path/to/server-monitor
docker compose restart
```
