"""Flask API server for server monitoring dashboard."""

import logging
import os
import atexit
from flask import Flask, jsonify, send_from_directory
from apscheduler.schedulers.background import BackgroundScheduler

from config import Config
from database import init_database, store_metrics, get_metrics, get_latest_metrics, cleanup_old_data, get_database_stats, check_and_store_alert, get_alerts
from collectors import collect_cpu_metrics, collect_memory_metrics, collect_disk_metrics, collect_smart_metrics, collect_drives_metrics, collect_docker_metrics, collect_process_metrics, collect_network_metrics

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='../frontend', static_url_path='')


def _check_alerts(cpu_data: dict, memory_data: dict, disk_data: dict):
    """Check collected metrics against thresholds and log new alerts."""
    t = Config.get_thresholds()

    # CPU temperature — find first valid zone
    try:
        temps = cpu_data.get('temperature', {})
        if not isinstance(temps, dict) or temps.get('error'):
            raise ValueError('no temp data')
        temp = None
        for zone in temps.values():
            if isinstance(zone, dict) and 'temp_celsius' in zone:
                if zone.get('type', '').lower() in ('x86_pkg_temp', 'cpu-thermal', 'cpu'):
                    temp = zone['temp_celsius']
                    break
        if temp is None:
            first = next((v for v in temps.values() if isinstance(v, dict) and 'temp_celsius' in v), None)
            if first:
                temp = first['temp_celsius']
        if temp is not None:
            if temp >= t['temperature']['critical']:
                check_and_store_alert('critical', 'cpu_temp',
                    f'CPU temp {temp}°C — critical threshold {t["temperature"]["critical"]}°C')
            elif temp >= t['temperature']['warning']:
                check_and_store_alert('warning', 'cpu_temp',
                    f'CPU temp {temp}°C — warning threshold {t["temperature"]["warning"]}°C')
    except Exception as e:
        logger.debug(f"Alert check (cpu): {e}")

    # RAM
    try:
        if not memory_data.get('error'):
            pct = memory_data.get('percent_used', 0)
            if pct >= t['memory']['critical']:
                check_and_store_alert('critical', 'memory',
                    f'RAM {pct}% — critical threshold {t["memory"]["critical"]}%')
            elif pct >= t['memory']['warning']:
                check_and_store_alert('warning', 'memory',
                    f'RAM {pct}% — warning threshold {t["memory"]["warning"]}%')
    except Exception as e:
        logger.debug(f"Alert check (memory): {e}")

    # Disk — check each mount point
    try:
        if not disk_data.get('error'):
            for mount, disk in disk_data.items():
                pct = disk.get('percent_used', 0)
                if pct >= t['disk']['critical']:
                    check_and_store_alert('critical', f'disk:{mount}',
                        f'Disk {mount} at {pct}% — critical threshold {t["disk"]["critical"]}%')
                elif pct >= t['disk']['warning']:
                    check_and_store_alert('warning', f'disk:{mount}',
                        f'Disk {mount} at {pct}% — warning threshold {t["disk"]["warning"]}%')
    except Exception as e:
        logger.debug(f"Alert check (disk): {e}")


def collect_all_metrics():
    """Collect and store all system metrics."""
    logger.debug("Collecting metrics...")

    cpu_data = memory_data = disk_data = {}

    try:
        cpu_data = collect_cpu_metrics()
        store_metrics('cpu', cpu_data)
    except Exception as e:
        logger.error(f"Error collecting CPU metrics: {e}")

    try:
        memory_data = collect_memory_metrics()
        store_metrics('memory', memory_data)
    except Exception as e:
        logger.error(f"Error collecting memory metrics: {e}")

    try:
        disk_data = collect_disk_metrics()
        store_metrics('disk', disk_data)
    except Exception as e:
        logger.error(f"Error collecting disk metrics: {e}")

    try:
        smart_data = collect_smart_metrics()
        store_metrics('smart', smart_data)
    except Exception as e:
        logger.error(f"Error collecting SMART metrics: {e}")

    try:
        drives_data = collect_drives_metrics()
        store_metrics('drives', drives_data)
    except Exception as e:
        logger.error(f"Error collecting drives metrics: {e}")

    try:
        docker_data = collect_docker_metrics()
        store_metrics('docker', docker_data)
    except Exception as e:
        logger.error(f"Error collecting Docker metrics: {e}")

    try:
        process_data = collect_process_metrics()
        store_metrics('processes', process_data)
    except Exception as e:
        logger.error(f"Error collecting process metrics: {e}")

    try:
        network_data = collect_network_metrics()
        if not network_data.get('_initializing'):
            store_metrics('network', network_data)
    except Exception as e:
        logger.error(f"Error collecting network metrics: {e}")

    try:
        _check_alerts(cpu_data, memory_data, disk_data)
    except Exception as e:
        logger.error(f"Error checking alerts: {e}")

    logger.debug("Metrics collection complete")


def daily_cleanup():
    """Run daily database cleanup."""
    logger.info("Running daily cleanup...")
    cleanup_old_data(Config.RETENTION_DAYS)


# API Routes
@app.route('/')
def index():
    """Serve the main dashboard."""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/current')
def get_current_metrics():
    """Get current system metrics."""
    return jsonify({
        'cpu': collect_cpu_metrics(),
        'memory': collect_memory_metrics(),
        'disk': collect_disk_metrics(),
        'smart': collect_smart_metrics(),
        'drives': collect_drives_metrics(),
        'docker': collect_docker_metrics(),
        'processes': collect_process_metrics(),
        'network': collect_network_metrics(),
        'thresholds': Config.get_thresholds()
    })


@app.route('/api/history/<metric_type>')
def get_metric_history(metric_type):
    """Get historical metrics by type."""
    from flask import request

    valid_types = ['cpu', 'memory', 'disk', 'smart', 'drives', 'docker', 'processes', 'network']
    if metric_type not in valid_types:
        return jsonify({'error': f'Invalid metric type. Valid: {valid_types}'}), 400

    hours = request.args.get('hours', 24, type=int)
    hours = min(max(hours, 1), 2160)  # 1 hour to 90 days

    data = get_metrics(metric_type, hours=hours)
    return jsonify({
        'metric_type': metric_type,
        'hours': hours,
        'data': data
    })


@app.route('/api/latest/<metric_type>')
def get_latest(metric_type):
    """Get latest metric of a type."""
    valid_types = ['cpu', 'memory', 'disk', 'smart', 'drives', 'docker', 'processes', 'network']
    if metric_type not in valid_types:
        return jsonify({'error': f'Invalid metric type. Valid: {valid_types}'}), 400

    data = get_latest_metrics(metric_type)
    return jsonify(data or {'error': 'No data found'})


@app.route('/api/alerts')
def get_alerts_route():
    """Get recent threshold alert events."""
    return jsonify(get_alerts(limit=50))


@app.route('/api/stats')
def get_stats():
    """Get database statistics."""
    return jsonify(get_database_stats())


@app.route('/api/config')
def get_config():
    """Get current configuration."""
    return jsonify({
        'collection_interval_seconds': Config.COLLECTION_INTERVAL,
        'retention_days': Config.RETENTION_DAYS,
        'thresholds': Config.get_thresholds()
    })


@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})


def start_scheduler():
    """Start the background scheduler for metric collection."""
    scheduler = BackgroundScheduler()

    # Collect metrics at configured interval
    scheduler.add_job(
        collect_all_metrics,
        'interval',
        seconds=Config.COLLECTION_INTERVAL,
        id='collect_metrics',
        replace_existing=True
    )

    # Daily cleanup at 3 AM
    scheduler.add_job(
        daily_cleanup,
        'cron',
        hour=3,
        id='daily_cleanup',
        replace_existing=True
    )

    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())

    return scheduler


# Initialize on module load (runs with gunicorn)
init_database()
collect_all_metrics()
scheduler = start_scheduler()
logger.info("Server monitor initialized")


if __name__ == '__main__':
    # Run Flask development server
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
