"""Disk usage metrics collector."""

import subprocess
import logging

logger = logging.getLogger(__name__)


def collect_disk_metrics() -> dict:
    """Collect disk usage for all mounted filesystems."""
    try:
        result = subprocess.run(
            ['df', '-B1', '--output=source,fstype,size,used,avail,pcent,target'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            logger.error(f"df command failed: {result.stderr}")
            return {'error': 'df command failed'}

        disks = {}
        lines = result.stdout.strip().split('\n')

        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 7:
                source = parts[0]
                fstype = parts[1]

                if fstype in ('tmpfs', 'devtmpfs', 'squashfs', 'overlay'):
                    continue
                if source.startswith('/dev/loop'):
                    continue

                try:
                    size_bytes = int(parts[2])
                    used_bytes = int(parts[3])
                    avail_bytes = int(parts[4])
                    percent_str = parts[5].rstrip('%')
                    mount_point = ' '.join(parts[6:])

                    if size_bytes == 0:
                        continue

                    disks[mount_point] = {
                        'device': source,
                        'fstype': fstype,
                        'total_gb': round(size_bytes / (1024**3), 2),
                        'used_gb': round(used_bytes / (1024**3), 2),
                        'available_gb': round(avail_bytes / (1024**3), 2),
                        'percent_used': int(percent_str) if percent_str.isdigit() else 0
                    }
                except (ValueError, IndexError) as e:
                    logger.debug(f"Could not parse disk line: {line}, error: {e}")
                    continue

        return disks if disks else {'error': 'no disks found'}

    except subprocess.TimeoutExpired:
        logger.error("df command timed out")
        return {'error': 'timeout'}
    except FileNotFoundError:
        logger.error("df command not found")
        return {'error': 'df not available'}
    except Exception as e:
        logger.error(f"Error collecting disk metrics: {e}")
        return {'error': str(e)}
