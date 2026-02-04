"""
Collector for all connected drives (mounted and unmounted).
"""
import subprocess
import logging

logger = logging.getLogger(__name__)


def collect_drives_metrics() -> dict:
    """
    Collect information about all connected drives.

    Returns:
        dict: Drive information keyed by device path
              {'/dev/sda': {'size_gb', 'model', 'mounted', 'mount_point', 'fstype'}}
    """
    try:
        drives = _discover_all_drives()
        mount_info = _get_mount_info()

        # Cross-reference drives with mount information
        for device, data in drives.items():
            if device in mount_info:
                data['mounted'] = True
                data['mount_point'] = mount_info[device]['mount_point']
                data['fstype'] = mount_info[device]['fstype']
            else:
                data['mounted'] = False
                data['mount_point'] = None
                data['fstype'] = None

        return drives if drives else {'info': 'no drives found'}

    except Exception as e:
        logger.error(f"Error collecting drives metrics: {e}")
        return {'error': str(e)}


def _discover_all_drives() -> dict:
    """
    Use lsblk to discover all block devices.

    Returns:
        dict: Drive information keyed by device path
    """
    drives = {}

    try:
        # Use lsblk to get all block devices (disks only, no partitions)
        result = subprocess.run(
            ['lsblk', '-d', '-n', '-b', '-o', 'NAME,TYPE,SIZE,MODEL'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            logger.warning(f"lsblk command failed: {result.stderr}")
            return _fallback_drive_discovery()

        for line in result.stdout.strip().split('\n'):
            if not line:
                continue

            parts = line.split(maxsplit=3)
            if len(parts) < 3:
                continue

            name = parts[0]
            dev_type = parts[1]
            size_bytes = parts[2]
            model = parts[3].strip() if len(parts) > 3 else 'Unknown'

            # Only include actual disks (not partitions, loop devices, etc.)
            if dev_type != 'disk':
                continue

            device_path = f'/dev/{name}'

            try:
                size_gb = round(int(size_bytes) / (1024**3), 1)
            except ValueError:
                size_gb = 0

            drives[device_path] = {
                'size_gb': size_gb,
                'model': model if model else 'Unknown',
                'mounted': False,
                'mount_point': None,
                'fstype': None
            }

    except subprocess.TimeoutExpired:
        logger.error("lsblk command timed out")
        return _fallback_drive_discovery()
    except FileNotFoundError:
        logger.warning("lsblk command not found, using fallback")
        return _fallback_drive_discovery()
    except Exception as e:
        logger.error(f"Error running lsblk: {e}")
        return _fallback_drive_discovery()

    return drives


def _fallback_drive_discovery() -> dict:
    """
    Fallback method to discover drives by checking /dev directly.

    Returns:
        dict: Basic drive information
    """
    drives = {}

    try:
        import os

        # Check common device patterns
        for device in ['/dev/sda', '/dev/sdb', '/dev/sdc', '/dev/sdd',
                      '/dev/nvme0n1', '/dev/nvme1n1', '/dev/vda', '/dev/vdb']:
            if os.path.exists(device):
                drives[device] = {
                    'size_gb': 0,
                    'model': 'Unknown',
                    'mounted': False,
                    'mount_point': None,
                    'fstype': None
                }

    except Exception as e:
        logger.error(f"Fallback drive discovery failed: {e}")

    return drives


def _get_mount_info() -> dict:
    """
    Parse /host/proc/mounts to get mount point information from the host.

    Returns:
        dict: Mount info keyed by device path
              {'/dev/sda1': {'mount_point': '/', 'fstype': 'ext4'}}
    """
    mount_info = {}

    # Try to read from host's /proc/mounts (when running in container)
    mounts_paths = ['/host/proc/mounts', '/proc/mounts', '/etc/mtab']

    for mounts_path in mounts_paths:
        try:
            with open(mounts_path, 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) < 3:
                        continue

                    source = parts[0]
                    target = parts[1]
                    fstype = parts[2]

                    # Only track real devices (not tmpfs, overlay, etc.)
                    if not source.startswith('/dev/'):
                        continue

                    # Skip special devices
                    if source.startswith('/dev/loop') or source.startswith('/dev/mapper'):
                        continue

                    # Extract base device (e.g., /dev/sda from /dev/sda1)
                    # This helps match partitions to their parent drives
                    base_device = source

                    # Handle standard partitions (sda1, nvme0n1p1)
                    if 'nvme' in source and 'p' in source:
                        # For NVMe: /dev/nvme0n1p1 -> /dev/nvme0n1
                        base_device = source.rsplit('p', 1)[0]
                    elif any(source.endswith(str(i)) for i in range(10)):
                        # For standard: /dev/sda1 -> /dev/sda
                        base_device = source.rstrip('0123456789')

                    # Store info for both the specific partition and base device
                    # If multiple partitions are mounted, prefer showing the root/main partition
                    for device in [source, base_device]:
                        if device not in mount_info:
                            mount_info[device] = {
                                'mount_point': target,
                                'fstype': fstype
                            }
                        elif target == '/' and mount_info[device]['mount_point'] != '/':
                            # Prefer root mount point
                            mount_info[device] = {
                                'mount_point': target,
                                'fstype': fstype
                            }

                # Successfully read mounts, return
                logger.debug(f"Successfully read mount info from {mounts_path}")
                return mount_info

        except FileNotFoundError:
            logger.debug(f"Mount file not found: {mounts_path}")
            continue
        except Exception as e:
            logger.warning(f"Error reading {mounts_path}: {e}")
            continue

    logger.warning("Could not read mount information from any source")
    return mount_info
