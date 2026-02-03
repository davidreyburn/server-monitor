# Server Context: aleph

**Last Updated**: February 3, 2026
**Maintenance Status**: Production-ready with comprehensive monitoring

## System Overview
- **Hostname**: aleph
- **OS**: Ubuntu 24.04.3 LTS (Noble Numbat)
- **Kernel**: 6.8.0-94-generic (x86_64)
- **User**: chives (UID 1000)
- **SSH Access**: Key-only authentication (password auth disabled)

## Hardware
- **CPU**: Intel N95 (4 cores, 1 thread per core)
- **RAM**: 16GB total (13GB available)
- **Swap**: 4GB (swappiness optimized to 10 for low swap usage)
- **Primary Storage**: 98GB LVM volume (16% used, 79GB free)
- **External Storage**: 4.6TB HDD mounted at `/mnt/external-hdd` (73% used, 1.3TB free)
  - Largest usage: Video (2.7TB), MUSIC (334GB)

## Network Configuration
- **Primary Interface (Ethernet)**: enp1s0
  - Local IP: 192.168.1.192/24
  - MAC: 68:1d:ef:4f:d2:41
  - Status: Active

- **WiFi Interface**: wlp2s0
  - Status: **DISABLED** (Feb 1, 2026 - reduced attack surface)
  - Previous IP: 192.168.1.161/24
  - MAC: 1c:79:2d:e6:34:99

- **Docker Bridge**: docker0 (172.17.0.1/16)
- **Docker Custom Network**: br-9abbe3109f39 (172.18.0.1/16)
  - Used by server-monitor container

### Open Ports & Services
- **SSH**: Port 22 (all interfaces) - **Key-only auth, fail2ban protected**
- **HTTPS/Caddy**: Port 443 (reverse proxy for all web services)
- **Samba**: Ports 139, 445 (file sharing)
- **Plex**: Port 32400 (also via https://plex.aleph.local)
- **Server Monitor**: Port 8081 (also via https://monitor.aleph.local)
- **Wekan**: Port 8080 (also via https://wekan.aleph.local)
- **MQTT**: Port 1883 (localhost only)
- **OpenClaw Gateway**: Multiple internal ports (18789, 18792)
- **DNS**: Port 53 (localhost via systemd-resolved)
- **Caddy Admin**: Port 2019 (localhost only)

## Running Services

### Core Infrastructure
- Docker (with containerd)
- SSH server (OpenSSH with ED25519 key auth)
- **Caddy** (reverse proxy and web server) - **NEW**
- **fail2ban** (SSH brute-force protection) - **NEW**
- Samba (file sharing - nmbd & smbd)
- Systemd services (networkd, resolved, timesyncd)

### Applications
- **Plex Media Server** (Docker container)
  - Container ID: 24a9d1801615
  - Image: lscr.io/linuxserver/plex:latest
  - Running for 23+ hours
  
- **Server Monitor** (Docker container)
  - Container ID: a1434c3d3532 (updated Feb 1, 2026)
  - Image: server-monitor-server-monitor (custom)
  - Port: 8081->8080 (HTTP)
  - Status: Running (**healthy** - IPv4/IPv6 fix applied Feb 3, 2026)
  - Command: gunicorn web server
  - Access: https://monitor.aleph.local or http://192.168.1.192:8081
  - GitHub: https://github.com/davidreyburn/server-monitor
  
- **Wekan** (Kanban board via snap)
  - MongoDB service
  - Wekan web service
  
- **Mosquitto** (MQTT broker via snap)

- **OpenClaw Gateway** (custom service)

### Background Services
- cron (scheduled tasks)
- thermald (thermal management)
- smartmontools (disk monitoring)
- unattended-upgrades (automatic security updates)
- systemd-journald (log management with 100MB limit, 7-day retention)

## Development Environment
- **Python**: 3.12.3
- **Node.js**: v22.22.0
- **Caddy**: 2.10.2 (web server and reverse proxy)
- **No databases** directly installed (MongoDB runs in snap for Wekan)
- **No traditional web servers** (nginx/apache) - Using Caddy for reverse proxy

## Storage Layout
```
/boot/efi     - 1.1GB (EFI partition)
/boot         - 2.0GB
/             - 98GB LVM (root filesystem)
/mnt/external-hdd - 4.6TB external HDD
```

## Network Topology Notes
- **Single-homed** (Ethernet only - WiFi disabled Feb 1, 2026)
- Part of 192.168.1.0/24 network
- IPv6 enabled with both global and ULA addresses
- Docker default bridge network: 172.17.0.0/16
- Docker custom network (server-monitor): 172.18.0.0/16

### Reverse Proxy Configuration
- **Base Domain**: aleph.local
- **Services**:
  - https://aleph.local - Welcome page
  - https://plex.aleph.local - Plex Media Server
  - https://monitor.aleph.local - Server Monitor Dashboard
  - https://wekan.aleph.local - Wekan Kanban Board
- **Certificates**: Self-signed via Caddy internal CA
- **Security**: TLS 1.2+, strong ciphers, security headers

## Use Cases & Context
This is a home media/productivity server running:
1. **Media streaming** (Plex) - 2.7TB of video content
2. **File sharing** (Samba)
3. **Project management** (Wekan)
4. **IoT/automation** (MQTT broker, OpenClaw)
5. **Remote access** (SSH with key-only authentication)
6. **System monitoring** (Server Monitor web dashboard)
7. **Reverse proxy** (Caddy for unified HTTPS access)

The large external HDD (4.6TB, 73% full) stores media content for Plex. The server is accessed locally via HTTPS (*.aleph.local) and remotely via SSH with ED25519 keys.

## Quick Reference Commands

### SSH Access (⚠️ PASSWORD AUTH DISABLED)
```bash
# Connect with SSH key
ssh -i /path/to/aleph_ssh_key chives@192.168.1.192

# Or if configured in ~/.ssh/config as "aleph"
ssh aleph
```

### Service Management
```bash
# Check all services
systemctl status ssh caddy fail2ban docker

# Check fail2ban status
sudo fail2ban-client status sshd

# Check Caddy status
systemctl status caddy
sudo caddy validate --config /etc/caddy/Caddyfile

# View service logs
sudo journalctl -u caddy -n 50
sudo journalctl -u ssh -n 50
sudo journalctl -u fail2ban -n 50
```

### Container Management
```bash
# Access Plex container
docker exec -it plex /bin/bash

# Access Server Monitor container
docker exec -it server-monitor /bin/bash

# View Server Monitor logs
docker logs server-monitor

# Restart Server Monitor
cd /home/chives/server-monitor
docker compose restart
```

### Web Services
```bash
# Check services via reverse proxy
curl -k https://aleph.local
curl -k https://monitor.aleph.local
curl -k https://plex.aleph.local
curl -k https://wekan.aleph.local

# Direct access (fallback)
curl http://localhost:8081
curl http://localhost:32400
curl http://localhost:8080
```

### System Monitoring
```bash
# Check disk space
df -h
du -sh /var/* | sort -h | tail -10

# Check external HDD
df -h /mnt/external-hdd

# Check memory and swap
free -h
cat /proc/sys/vm/swappiness  # Should be 10

# Check journal size
journalctl --disk-usage  # Should be <100MB

# View Wekan logs
snap logs wekan

# Check MQTT broker status
snap services mosquitto

# Monitor system resources
htop
```

### Security
```bash
# Check recent SSH attempts
sudo grep 'sshd' /var/log/auth.log | tail -20

# Check fail2ban bans
sudo fail2ban-client status sshd

# View current connections
who
ss -tn
```

## Important Paths

### Configuration Files
- **SSH**: `/etc/ssh/sshd_config`, `/etc/ssh/sshd_config.d/99-hardening.conf`
- **Caddy**: `/etc/caddy/Caddyfile`
- **fail2ban**: `/etc/fail2ban/jail.local`
- **Network**: `/etc/netplan/50-cloud-init.yaml`
- **Journal**: `/etc/systemd/journald.conf.d/size-limit.conf`
- **Sysctl**: `/etc/sysctl.d/99-swappiness.conf`

### Data Directories
- **External HDD**: `/mnt/external-hdd`
- **Docker data**: `/var/lib/docker`
- **Caddy data**: `/var/lib/caddy`
- **Server Monitor**: `/home/chives/server-monitor`
- **Snap apps**: `/snap/` (wekan, mosquitto)
- **Home**: `/home/chives`

### Backup Files (Created Feb 1, 2026)
- `/etc/ssh/sshd_config.backup-*`
- `/etc/netplan/50-cloud-init.yaml.backup-*`
- `/etc/caddy/Caddyfile.backup-*` (if existed)
- `/home/chives/server-monitor/docker-compose.yml.backup-*`
- `/home/chives/ssh-rollback.sh` (emergency SSH rollback script)

### Certificates
- **Caddy CA**: `/var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt`
- **Service certs**: Auto-generated by Caddy in same directory

## Security Hardening (Applied Feb 1, 2026)

### SSH Security
- ✅ Password authentication disabled
- ✅ Key-only authentication (ED25519)
- ✅ Root login disabled
- ✅ Max authentication tries: 3
- ✅ Strong ciphers and MACs configured
- ✅ fail2ban active (3 attempts = 1 hour ban)

### Network Security
- ✅ WiFi interface disabled (single network path)
- ✅ HTTPS for all web services via Caddy
- ✅ Self-signed certificates (trusted on client)
- ✅ Security headers enabled

### System Optimization
- ✅ Swappiness reduced to 10 (from 60)
- ✅ Journal logs limited to 100MB, 7-day retention
- ✅ APT cache cleaned regularly
- ✅ Container health monitoring fixed

## Maintenance History

### February 1, 2026 - Major Security & Optimization Update
**Performed by**: Claude Code (Anthropic)
**Duration**: ~1 hour

**Changes**:
1. Fixed unhealthy server-monitor container (IPv4/IPv6 health check issue)
2. Hardened SSH security (key-only auth, fail2ban, strong encryption)
3. Disabled WiFi interface (kept Ethernet only)
4. Installed and configured Caddy reverse proxy
5. Cleaned up root disk (~104MB freed)
6. Optimized swap configuration (swappiness 60→10)
7. Configured log rotation limits

**Documentation Created**:
- `instructions.md` - Quick access guide
- `MAINTENANCE_SUMMARY.md` - Overview of changes
- `claude.md` - Detailed technical log
- `REVERSE_PROXY_SETUP.md` - Reverse proxy setup guide

**Files Exported**:
- `aleph_ssh_key` - Private SSH key (required for access)
- `caddy-ca-certificate.crt` - CA certificate for HTTPS trust

**Next Maintenance**: TBD
**Recommended**: Monthly security updates, quarterly system review

### February 3, 2026 - Server Monitor Health Check Fix & GitHub Publication
**Performed by**: Claude Code (Anthropic)
**Duration**: ~15 minutes

**Changes**:
1. Fixed Docker health check IPv4/IPv6 issue in docker-compose.yml
   - Changed health check URL from `localhost` to `127.0.0.1`
   - Added comprehensive explanatory comments
2. Enhanced README.md documentation
   - Added "Health Check Configuration" section with technical explanation
   - Expanded troubleshooting guide with debugging procedures
3. Published project to GitHub
   - Authenticated with gh CLI as davidreyburn
   - Created public repository: https://github.com/davidreyburn/server-monitor
   - Pushed all commits with full history
4. Updated project documentation (CLAUDE.md, server_context.md)

**Root Cause of Health Check Issue**:
- Docker's `localhost` resolves to both IPv4 (127.0.0.1) and IPv6 (::1)
- wget attempts IPv6 first, connecting to [::1]:8080
- gunicorn only binds to IPv4 (0.0.0.0:8080), not IPv6
- IPv6 connection fails → health check fails → false "unhealthy" status
- Application was working perfectly, but Docker marked container unhealthy

**Solution**:
- Explicit 127.0.0.1 forces IPv4 connection, bypassing DNS ambiguity
- Health check now consistently passes

**Files Modified**:
- `docker-compose.yml` - Health check configuration
- `README.md` - Documentation enhancements
- `CLAUDE.md` - Project status updates
- `server_context.md` - Server documentation updates

**Next Steps**:
- Deploy updated configuration to production server (optional - already fixed manually on Feb 1)
- Configuration change is committed to repository for future deployments

**Repository Details**:
- URL: https://github.com/davidreyburn/server-monitor
- Visibility: Public
- Branch: master
- Commits: 6 total (including health check fix)

## Troubleshooting

### Can't SSH to Server
- Ensure using SSH key: `ssh -i aleph_ssh_key chives@192.168.1.192`
- Password authentication is disabled
- If locked out, need physical console access to run `~/ssh-rollback.sh`

### Can't Access Web Services
- Check if Caddy is running: `systemctl status caddy`
- Verify DNS entries in client's hosts file
- Use direct URLs as fallback (http://192.168.1.192:PORT)

### Container Issues
- Check status: `docker ps -a`
- View logs: `docker logs <container-name>`
- Restart: `docker restart <container-name>`

### System Performance
- Check swap usage: `free -h` (should be minimal with swappiness=10)
- Check disk space: `df -h` (should have 75GB+ free on root)
- Check journal size: `journalctl --disk-usage` (should be <100MB)

## Additional Notes

- **Uptime Goal**: 24/7 availability
- **Backup Strategy**: Configuration backups created, data backup TBD
- **Update Policy**: Unattended security updates enabled
- **Monitoring**: Server Monitor dashboard, fail2ban alerts
- **Access**: Local HTTPS (*.aleph.local) and remote SSH (key-only)

---

**For detailed instructions, see `instructions.md`**
**For maintenance log, see `claude.md`**
**For rollback procedures, see `MAINTENANCE_SUMMARY.md`**
