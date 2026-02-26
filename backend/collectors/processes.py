"""Process metrics collector — top processes by memory usage."""

import os
import logging

logger = logging.getLogger(__name__)

PROC_BASE = '/host/proc' if os.path.exists('/host/proc') else '/proc'


def collect_process_metrics() -> dict:
    """Collect top 12 processes by RSS memory from /proc."""
    try:
        # Get total memory (kB) for percent calculation
        mem_total_kb = 1
        try:
            with open(f'{PROC_BASE}/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal'):
                        mem_total_kb = int(line.split()[1])
                        break
        except Exception:
            pass

        processes = []

        for entry in os.listdir(PROC_BASE):
            if not entry.isdigit():
                continue
            pid = int(entry)
            try:
                with open(f'{PROC_BASE}/{pid}/comm', 'r') as f:
                    name = f.read().strip()

                # RSS in pages (each page = 4 kB on x86)
                with open(f'{PROC_BASE}/{pid}/statm', 'r') as f:
                    statm = f.read().split()
                rss_kb = int(statm[1]) * 4

                # Cumulative CPU jiffies (utime + stime) from /proc/[pid]/stat
                # Format after closing ')': state ppid pgrp session tty_nr tpgid flags
                #   minflt cminflt majflt cmajflt utime(11) stime(12) ...
                with open(f'{PROC_BASE}/{pid}/stat', 'r') as f:
                    stat = f.read()
                rparen = stat.rfind(')')
                stat_fields = stat[rparen + 2:].split()
                cpu_jiffies = int(stat_fields[11]) + int(stat_fields[12])

                processes.append({
                    'pid': pid,
                    'name': name,
                    'rss_kb': rss_kb,
                    'cpu_jiffies': cpu_jiffies,
                })

            except (IOError, OSError, ValueError, IndexError):
                continue

        # Sort by RSS descending, return top 12
        processes.sort(key=lambda x: x['rss_kb'], reverse=True)

        return {
            'processes': [
                {
                    'pid': p['pid'],
                    'name': p['name'],
                    'mem_mb': round(p['rss_kb'] / 1024, 1),
                    'mem_percent': round(p['rss_kb'] / mem_total_kb * 100, 1),
                    'cpu_jiffies': p['cpu_jiffies'],
                }
                for p in processes[:12]
            ]
        }

    except Exception as e:
        logger.error(f"Error collecting process metrics: {e}")
        return {'error': str(e)}
