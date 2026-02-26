"""SQLite database module for storing historical metrics."""

import sqlite3
import json
import logging
import os
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get('MONITOR_DB_PATH', '/app/data/metrics.db')


def init_database():
    """Initialize database with required tables and indexes."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                metric_type TEXT NOT NULL,
                data TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_metrics_timestamp
            ON metrics(timestamp)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_metrics_type_timestamp
            ON metrics(metric_type, timestamp)
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                level TEXT NOT NULL,
                metric TEXT NOT NULL,
                message TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_alerts_timestamp
            ON alerts(timestamp)
        ''')

        conn.commit()
        logger.info("Database initialized successfully")


@contextmanager
def get_connection():
    """Context manager for database connections."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def store_metrics(metric_type: str, data: dict):
    """Store a metric data point."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO metrics (metric_type, data) VALUES (?, ?)',
                (metric_type, json.dumps(data))
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error storing metrics: {e}")
        raise


def get_metrics(metric_type: str, hours: int = 24, limit: int = 1000) -> list:
    """Retrieve metrics for a given time period."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            since = datetime.utcnow() - timedelta(hours=hours)

            cursor.execute('''
                SELECT timestamp, data
                FROM metrics
                WHERE metric_type = ? AND timestamp > ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (metric_type, since.isoformat(), limit))

            results = []
            for row in cursor.fetchall():
                results.append({
                    'timestamp': row['timestamp'],
                    'data': json.loads(row['data'])
                })

            return list(reversed(results))
    except Exception as e:
        logger.error(f"Error retrieving metrics: {e}")
        return []


def get_latest_metrics(metric_type: str) -> Optional[dict]:
    """Get the most recent metric of a given type."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, data
                FROM metrics
                WHERE metric_type = ?
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (metric_type,))

            row = cursor.fetchone()
            if row:
                return {
                    'timestamp': row['timestamp'],
                    'data': json.loads(row['data'])
                }
            return None
    except Exception as e:
        logger.error(f"Error retrieving latest metrics: {e}")
        return None


def check_and_store_alert(level: str, metric: str, message: str) -> bool:
    """Store an alert only if an identical level+metric alert hasn't fired in the last hour."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM alerts
                WHERE metric = ? AND level = ?
                AND timestamp > datetime('now', '-1 hour')
                LIMIT 1
            ''', (metric, level))
            if cursor.fetchone():
                return False
            cursor.execute(
                'INSERT INTO alerts (level, metric, message) VALUES (?, ?, ?)',
                (level, metric, message)
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error storing alert: {e}")
        return False


def get_alerts(limit: int = 50) -> list:
    """Return recent alerts newest-first."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, level, metric, message
                FROM alerts
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return []


def cleanup_old_data(retention_days: int = 90):
    """Remove data older than retention period."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cutoff = datetime.utcnow() - timedelta(days=retention_days)

            cursor.execute(
                'DELETE FROM metrics WHERE timestamp < ?',
                (cutoff.isoformat(),)
            )
            deleted = cursor.rowcount
            cursor.execute(
                'DELETE FROM alerts WHERE timestamp < ?',
                (cutoff.isoformat(),)
            )
            conn.commit()

            if deleted > 0:
                cursor.execute('VACUUM')
                logger.info(f"Cleaned up {deleted} old metric records")

            return deleted
    except Exception as e:
        logger.error(f"Error cleaning up old data: {e}")
        return 0


def get_database_stats() -> dict:
    """Get database statistics."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) as count FROM metrics')
            total_records = cursor.fetchone()['count']

            cursor.execute('''
                SELECT metric_type, COUNT(*) as count
                FROM metrics
                GROUP BY metric_type
            ''')
            by_type = {row['metric_type']: row['count'] for row in cursor.fetchall()}

            cursor.execute('SELECT MIN(timestamp) as oldest FROM metrics')
            oldest = cursor.fetchone()['oldest']

            db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0

            return {
                'total_records': total_records,
                'records_by_type': by_type,
                'oldest_record': oldest,
                'database_size_mb': round(db_size / (1024 * 1024), 2)
            }
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {'error': str(e)}
