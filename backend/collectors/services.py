"""Systemd service status collector — process-presence check via /proc."""

import os
import logging

logger = logging.getLogger(__name__)

PROC_BASE = '/host/proc' if os.path.exists('/host/proc') else '/proc'

WATCHED_SERVICES = ('cloudflared', 'caddy', 'smbd', 'nmbd')


def collect_services_metrics() -> dict:
    """Check whether each watched service process is running via /proc/*/comm."""
    running: set = set()
    try:
        for entry in os.listdir(PROC_BASE):
            if not entry.isdigit():
                continue
            try:
                with open(f'{PROC_BASE}/{entry}/comm', 'r') as f:
                    name = f.read().strip()
                if name in WATCHED_SERVICES:
                    running.add(name)
            except (IOError, OSError):
                continue
    except Exception as e:
        logger.error(f"Error scanning proc for services: {e}")
        return {'error': str(e)}

    return {svc: {'running': svc in running} for svc in WATCHED_SERVICES}
