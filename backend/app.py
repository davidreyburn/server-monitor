"""Flask API server for server monitoring dashboard."""

import logging
import os
import atexit
from flask import Flask, jsonify, send_from_directory
from apscheduler.schedulers.background import BackgroundScheduler

from config import Config
from database import init_database, store_metrics, get_metrics, get_latest_metrics, cleanup_old_data, get_database_stats
from collectors import collect_cpu_metrics, collect_memory_metrics, collect_disk_metrics, collect_smart_metrics

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='../frontend', static_url_path='')


def collect_all_metrics():
    """Collect and store all system metrics."""
    logger.debug("Collecting metrics...")

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
        'thresholds': Config.get_thresholds()
    })


@app.route('/api/history/<metric_type>')
def get_metric_history(metric_type):
    """Get historical metrics by type."""
    from flask import request

    valid_types = ['cpu', 'memory', 'disk', 'smart']
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
    valid_types = ['cpu', 'memory', 'disk', 'smart']
    if metric_type not in valid_types:
        return jsonify({'error': f'Invalid metric type. Valid: {valid_types}'}), 400

    data = get_latest_metrics(metric_type)
    return jsonify(data or {'error': 'No data found'})


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


if __name__ == '__main__':
    # Initialize database
    init_database()

    # Collect initial metrics
    collect_all_metrics()

    # Start scheduler
    scheduler = start_scheduler()

    # Run Flask app
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
