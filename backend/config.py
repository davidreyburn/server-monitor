"""Configuration settings for server monitor."""

import os


class Config:
    """Application configuration."""

    # Data collection interval in seconds (default: 5 minutes)
    COLLECTION_INTERVAL = int(os.environ.get('COLLECTION_INTERVAL', 300))

    # Data retention period in days
    RETENTION_DAYS = int(os.environ.get('RETENTION_DAYS', 90))

    # Database path
    DB_PATH = os.environ.get('MONITOR_DB_PATH', '/app/data/metrics.db')

    # Web server settings
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 8080))
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'

    # Alert thresholds
    TEMP_WARNING_CELSIUS = int(os.environ.get('TEMP_WARNING', 70))
    TEMP_CRITICAL_CELSIUS = int(os.environ.get('TEMP_CRITICAL', 85))
    DISK_WARNING_PERCENT = int(os.environ.get('DISK_WARNING', 80))
    DISK_CRITICAL_PERCENT = int(os.environ.get('DISK_CRITICAL', 95))
    MEMORY_WARNING_PERCENT = int(os.environ.get('MEMORY_WARNING', 85))
    MEMORY_CRITICAL_PERCENT = int(os.environ.get('MEMORY_CRITICAL', 95))
    LOAD_WARNING_MULTIPLIER = float(os.environ.get('LOAD_WARNING', 1.0))
    LOAD_CRITICAL_MULTIPLIER = float(os.environ.get('LOAD_CRITICAL', 2.0))

    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'WARNING')

    @classmethod
    def get_thresholds(cls) -> dict:
        """Return all threshold values."""
        return {
            'temperature': {
                'warning': cls.TEMP_WARNING_CELSIUS,
                'critical': cls.TEMP_CRITICAL_CELSIUS
            },
            'disk': {
                'warning': cls.DISK_WARNING_PERCENT,
                'critical': cls.DISK_CRITICAL_PERCENT
            },
            'memory': {
                'warning': cls.MEMORY_WARNING_PERCENT,
                'critical': cls.MEMORY_CRITICAL_PERCENT
            },
            'load': {
                'warning': cls.LOAD_WARNING_MULTIPLIER,
                'critical': cls.LOAD_CRITICAL_MULTIPLIER
            }
        }
