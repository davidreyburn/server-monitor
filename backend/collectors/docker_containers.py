"""
Collector for Docker container metrics.
"""
import logging
from datetime import datetime

try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False

logger = logging.getLogger(__name__)


def collect_docker_metrics() -> dict:
    """
    Collect comprehensive Docker container metrics.

    Returns:
        dict: Container metrics keyed by container name
    """
    if not DOCKER_AVAILABLE:
        return {'error': 'Docker SDK not installed'}

    try:
        client = docker.from_env(timeout=10)
        client.ping()
    except docker.errors.DockerException as e:
        logger.warning(f"Docker daemon unavailable: {e}")
        return {'error': 'Docker daemon unavailable'}
    except Exception as e:
        logger.error(f"Error connecting to Docker: {e}")
        return {'error': str(e)}

    containers_data = {}

    try:
        for container in client.containers.list(all=True):
            name = container.name

            info = {
                'id': container.short_id,
                'image': container.image.tags[0] if container.image.tags else container.image.short_id,
                'status': container.status,
                'health': _get_health_status(container),
                'created': container.attrs.get('Created', ''),
                'started': container.attrs.get('State', {}).get('StartedAt', ''),
                'restart_count': container.attrs.get('RestartCount', 0)
            }

            # Collect runtime stats only for running containers
            if container.status == 'running':
                try:
                    stats = _get_container_stats(container)
                    info.update(stats)
                    info['uptime_seconds'] = _calculate_uptime(info['started'])
                except Exception as e:
                    logger.warning(f"Error getting stats for {name}: {e}")
                    # Provide default values
                    info.update({
                        'cpu_percent': 0,
                        'memory_mb': 0,
                        'memory_percent': 0,
                        'network_rx_mb': 0,
                        'network_tx_mb': 0,
                        'uptime_seconds': 0
                    })
            else:
                # Not running - zero out stats
                info.update({
                    'cpu_percent': 0,
                    'memory_mb': 0,
                    'memory_percent': 0,
                    'network_rx_mb': 0,
                    'network_tx_mb': 0,
                    'uptime_seconds': 0
                })

            containers_data[name] = info

    except Exception as e:
        logger.error(f"Error listing containers: {e}")
        return {'error': str(e)}
    finally:
        try:
            client.close()
        except:
            pass

    return containers_data if containers_data else {'info': 'no containers'}


def _get_health_status(container) -> str:
    """
    Extract health status from container.

    Args:
        container: Docker container object

    Returns:
        str: Health status (healthy, unhealthy, starting, none)
    """
    try:
        health = container.attrs.get('State', {}).get('Health', {})
        return health.get('Status', 'none') if health else 'none'
    except Exception:
        return 'none'


def _get_container_stats(container) -> dict:
    """
    Get CPU, memory, and network stats for a running container.

    Args:
        container: Docker container object

    Returns:
        dict: Stats including cpu_percent, memory_mb, memory_percent,
              network_rx_mb, network_tx_mb
    """
    stats = container.stats(stream=False)

    # CPU calculation
    cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                stats['precpu_stats']['cpu_usage']['total_usage']
    system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                   stats['precpu_stats']['system_cpu_usage']
    num_cpus = stats['cpu_stats'].get('online_cpus', 1)

    if system_delta > 0 and cpu_delta > 0:
        cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0
    else:
        cpu_percent = 0.0

    # Memory calculation
    memory_usage = stats['memory_stats'].get('usage', 0)
    memory_limit = stats['memory_stats'].get('limit', 1)
    memory_mb = memory_usage / (1024 * 1024)
    memory_percent = (memory_usage / memory_limit) * 100 if memory_limit > 0 else 0

    # Network I/O (cumulative since container start)
    networks = stats.get('networks', {})
    rx_bytes = sum(net.get('rx_bytes', 0) for net in networks.values())
    tx_bytes = sum(net.get('tx_bytes', 0) for net in networks.values())

    return {
        'cpu_percent': round(cpu_percent, 2),
        'memory_mb': round(memory_mb, 1),
        'memory_percent': round(memory_percent, 1),
        'network_rx_mb': round(rx_bytes / (1024 * 1024), 2),
        'network_tx_mb': round(tx_bytes / (1024 * 1024), 2)
    }


def _calculate_uptime(started_at: str) -> int:
    """
    Calculate uptime in seconds from ISO timestamp.

    Args:
        started_at: ISO 8601 timestamp string

    Returns:
        int: Uptime in seconds
    """
    if not started_at:
        return 0

    try:
        # Handle both formats: with and without 'Z' suffix
        started_str = started_at.replace('Z', '+00:00')
        started = datetime.fromisoformat(started_str)

        # Calculate uptime
        now = datetime.now(started.tzinfo)
        uptime = (now - started).total_seconds()

        return int(uptime)
    except Exception as e:
        logger.warning(f"Error calculating uptime from {started_at}: {e}")
        return 0
