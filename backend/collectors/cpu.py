"""CPU temperature and load metrics collector."""

import os
import logging

logger = logging.getLogger(__name__)

# Support both native and Docker-mounted paths
SYS_BASE = '/host/sys' if os.path.exists('/host/sys') else '/sys'
PROC_BASE = '/host/proc' if os.path.exists('/host/proc') else '/proc'


def collect_cpu_metrics() -> dict:
    """Collect CPU temperature and system load averages."""
    return {
        'temperature': _get_cpu_temperature(),
        'load': _get_load_averages()
    }


def _get_cpu_temperature() -> dict:
    """Read CPU temperature from thermal zones."""
    temps = {}
    thermal_base = f'{SYS_BASE}/class/thermal'

    try:
        if not os.path.exists(thermal_base):
            logger.warning("Thermal zone directory not found")
            return {'error': 'thermal zones not available'}

        for entry in os.listdir(thermal_base):
            if entry.startswith('thermal_zone'):
                zone_path = os.path.join(thermal_base, entry)
                temp_file = os.path.join(zone_path, 'temp')
                type_file = os.path.join(zone_path, 'type')

                if os.path.exists(temp_file):
                    try:
                        with open(temp_file, 'r') as f:
                            temp_raw = int(f.read().strip())
                            temp_celsius = temp_raw / 1000.0

                        zone_type = 'unknown'
                        if os.path.exists(type_file):
                            with open(type_file, 'r') as f:
                                zone_type = f.read().strip()

                        temps[entry] = {
                            'type': zone_type,
                            'temp_celsius': round(temp_celsius, 1)
                        }
                    except (IOError, ValueError) as e:
                        logger.debug(f"Could not read {entry}: {e}")

    except PermissionError:
        logger.warning("Permission denied reading thermal zones")
        return {'error': 'permission denied'}
    except Exception as e:
        logger.error(f"Error reading thermal zones: {e}")
        return {'error': str(e)}

    if not temps:
        return {'error': 'no thermal zones found'}

    return temps


def _get_load_averages() -> dict:
    """Read system load averages from /proc/loadavg."""
    try:
        with open(f'{PROC_BASE}/loadavg', 'r') as f:
            parts = f.read().strip().split()

        uptime_seconds = None
        try:
            with open(f'{PROC_BASE}/uptime', 'r') as f:
                uptime_seconds = int(float(f.read().split()[0]))
        except Exception:
            pass

        return {
            'load_1min': float(parts[0]),
            'load_5min': float(parts[1]),
            'load_15min': float(parts[2]),
            'running_processes': parts[3],
            'uptime_seconds': uptime_seconds,
        }
    except FileNotFoundError:
        logger.warning("/proc/loadavg not found")
        return {'error': 'loadavg not available'}
    except (IOError, IndexError, ValueError) as e:
        logger.error(f"Error reading load averages: {e}")
        return {'error': str(e)}
