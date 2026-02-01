"""SMART disk health metrics collector."""

import subprocess
import re
import logging
import os

logger = logging.getLogger(__name__)


def collect_smart_metrics() -> dict:
    """Collect SMART health data for all disks."""
    disks = _get_block_devices()

    if not disks:
        return {'error': 'no block devices found'}

    smart_data = {}
    for disk in disks:
        data = _get_smart_data(disk)
        if data and 'error' not in data:
            smart_data[disk] = data

    return smart_data if smart_data else {'error': 'no SMART data available'}


def _get_block_devices() -> list:
    """Get list of block devices that might support SMART."""
    devices = []

    try:
        result = subprocess.run(
            ['lsblk', '-d', '-n', '-o', 'NAME,TYPE'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 2 and parts[1] == 'disk':
                    devices.append(f"/dev/{parts[0]}")
    except Exception as e:
        logger.debug(f"lsblk failed: {e}")

    if not devices:
        for dev in ['sda', 'sdb', 'sdc', 'sdd', 'nvme0n1', 'nvme1n1']:
            path = f"/dev/{dev}"
            if os.path.exists(path):
                devices.append(path)

    return devices


def _get_smart_data(device: str) -> dict:
    """Get SMART data for a specific device."""
    try:
        result = subprocess.run(
            ['smartctl', '-a', '-j', device],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode in (0, 4):
            import json
            try:
                data = json.loads(result.stdout)
                return _parse_smart_json(data, device)
            except json.JSONDecodeError:
                return _parse_smart_text(result.stdout, device)
        else:
            return _parse_smart_text(result.stdout + result.stderr, device)

    except subprocess.TimeoutExpired:
        logger.warning(f"SMART query timed out for {device}")
        return {'error': 'timeout'}
    except FileNotFoundError:
        logger.warning("smartctl not found - install smartmontools")
        return {'error': 'smartctl not available'}
    except Exception as e:
        logger.error(f"Error getting SMART data for {device}: {e}")
        return {'error': str(e)}


def _parse_smart_json(data: dict, device: str) -> dict:
    """Parse JSON output from smartctl."""
    result = {
        'device': device,
        'model': data.get('model_name', 'Unknown'),
        'serial': data.get('serial_number', 'Unknown'),
        'health_passed': True,
        'temperature_celsius': None,
        'power_on_hours': None,
        'attributes': {}
    }

    smart_status = data.get('smart_status', {})
    if isinstance(smart_status, dict):
        result['health_passed'] = smart_status.get('passed', True)

    temp_data = data.get('temperature', {})
    if isinstance(temp_data, dict):
        result['temperature_celsius'] = temp_data.get('current')

    power_on = data.get('power_on_time', {})
    if isinstance(power_on, dict):
        result['power_on_hours'] = power_on.get('hours')

    ata_attrs = data.get('ata_smart_attributes', {})
    if isinstance(ata_attrs, dict):
        for attr in ata_attrs.get('table', []):
            name = attr.get('name', '')
            if name in ['Temperature_Celsius', 'Reallocated_Sector_Ct',
                       'Current_Pending_Sector', 'Offline_Uncorrectable',
                       'Power_On_Hours', 'Wear_Leveling_Count']:
                result['attributes'][name] = {
                    'value': attr.get('value'),
                    'raw': attr.get('raw', {}).get('value')
                }

    return result


def _parse_smart_text(output: str, device: str) -> dict:
    """Parse text output from smartctl as fallback."""
    result = {
        'device': device,
        'model': 'Unknown',
        'serial': 'Unknown',
        'health_passed': None,
        'temperature_celsius': None,
        'power_on_hours': None,
        'attributes': {}
    }

    for line in output.split('\n'):
        line = line.strip()

        if 'Device Model:' in line or 'Model Number:' in line:
            result['model'] = line.split(':', 1)[-1].strip()
        elif 'Serial Number:' in line:
            result['serial'] = line.split(':', 1)[-1].strip()
        elif 'SMART overall-health' in line:
            result['health_passed'] = 'PASSED' in line
        elif 'Temperature_Celsius' in line or 'Temperature:' in line:
            match = re.search(r'(\d+)\s*(?:Celsius|C|\()', line)
            if match:
                result['temperature_celsius'] = int(match.group(1))
        elif 'Power_On_Hours' in line:
            match = re.search(r'(\d+)$', line)
            if match:
                result['power_on_hours'] = int(match.group(1))
        elif 'Reallocated_Sector_Ct' in line:
            match = re.search(r'(\d+)$', line)
            if match:
                result['attributes']['Reallocated_Sector_Ct'] = {
                    'raw': int(match.group(1))
                }

    return result
