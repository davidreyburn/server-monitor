"""Memory usage metrics collector."""

import os
import logging

logger = logging.getLogger(__name__)

# Support both native and Docker-mounted paths
PROC_BASE = '/host/proc' if os.path.exists('/host/proc') else '/proc'


def collect_memory_metrics() -> dict:
    """Collect memory usage from /proc/meminfo."""
    try:
        meminfo = {}
        with open(f'{PROC_BASE}/meminfo', 'r') as f:
            for line in f:
                parts = line.split(':')
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip().split()[0]
                    meminfo[key] = int(value)

        total_kb = meminfo.get('MemTotal', 0)
        free_kb = meminfo.get('MemFree', 0)
        available_kb = meminfo.get('MemAvailable', free_kb)
        buffers_kb = meminfo.get('Buffers', 0)
        cached_kb = meminfo.get('Cached', 0)
        swap_total_kb = meminfo.get('SwapTotal', 0)
        swap_free_kb = meminfo.get('SwapFree', 0)

        used_kb = total_kb - available_kb
        swap_used_kb = swap_total_kb - swap_free_kb

        return {
            'total_mb': round(total_kb / 1024, 1),
            'used_mb': round(used_kb / 1024, 1),
            'free_mb': round(free_kb / 1024, 1),
            'available_mb': round(available_kb / 1024, 1),
            'buffers_mb': round(buffers_kb / 1024, 1),
            'cached_mb': round(cached_kb / 1024, 1),
            'swap_total_mb': round(swap_total_kb / 1024, 1),
            'swap_used_mb': round(swap_used_kb / 1024, 1),
            'percent_used': round((used_kb / total_kb) * 100, 1) if total_kb > 0 else 0
        }

    except FileNotFoundError:
        logger.warning("/proc/meminfo not found")
        return {'error': 'meminfo not available'}
    except (IOError, KeyError, ValueError, ZeroDivisionError) as e:
        logger.error(f"Error reading memory info: {e}")
        return {'error': str(e)}
