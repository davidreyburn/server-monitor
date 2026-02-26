"""Network I/O rate metrics collector."""

import os
import time
import logging

logger = logging.getLogger(__name__)

PROC_BASE = '/host/proc' if os.path.exists('/host/proc') else '/proc'

_SKIP_IFACES = frozenset({'lo'})
_SKIP_PREFIXES = ('docker', 'br-', 'veth', 'virbr', 'dummy', 'tunl', 'sit')

_prev_bytes: dict = {}
_prev_time: float = 0.0


def _read_net_dev() -> dict:
    path = f'{PROC_BASE}/net/dev'
    stats = {}
    try:
        with open(path, 'r') as f:
            for line in f.readlines()[2:]:
                parts = line.split()
                if len(parts) < 10:
                    continue
                iface = parts[0].rstrip(':')
                if iface in _SKIP_IFACES or any(iface.startswith(p) for p in _SKIP_PREFIXES):
                    continue
                stats[iface] = (int(parts[1]), int(parts[9]))  # rx_bytes, tx_bytes
    except Exception as e:
        logger.error(f"Error reading {path}: {e}")
    return stats


def collect_network_metrics() -> dict:
    """Return per-interface and aggregate TX/RX rates in MB/s."""
    global _prev_bytes, _prev_time

    now = time.monotonic()
    current = _read_net_dev()

    if not current:
        return {'error': 'no network interfaces found'}

    if not _prev_bytes or _prev_time == 0.0:
        _prev_bytes = current
        _prev_time = now
        return {'_initializing': True}

    dt = now - _prev_time
    if dt <= 0:
        return {'_initializing': True}

    total_rx = 0.0
    total_tx = 0.0
    per_iface = {}

    for iface, (rx, tx) in current.items():
        if iface in _prev_bytes:
            prev_rx, prev_tx = _prev_bytes[iface]
            rx_rate = max(0.0, (rx - prev_rx) / dt)
            tx_rate = max(0.0, (tx - prev_tx) / dt)
            total_rx += rx_rate
            total_tx += tx_rate
            per_iface[iface] = {
                'rx_mb_per_sec': round(rx_rate / (1024 * 1024), 4),
                'tx_mb_per_sec': round(tx_rate / (1024 * 1024), 4),
            }

    _prev_bytes = current
    _prev_time = now

    result = dict(per_iface)
    result['_total'] = {
        'rx_mb_per_sec': round(total_rx / (1024 * 1024), 4),
        'tx_mb_per_sec': round(total_tx / (1024 * 1024), 4),
    }
    return result
