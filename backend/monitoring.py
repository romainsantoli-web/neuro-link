"""Neuro-Link — Lightweight monitoring & metrics.

Provides:
  - Request counter & latency tracking (per route)
  - System resource snapshot (CPU, memory, disk)
  - Structured JSON logging helper
  - /metrics endpoint for Prometheus-compatible scraping or dashboards

No external dependencies required — uses only the standard library.
"""
from __future__ import annotations

import logging
import os
import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ═══════════ Structured Logger ═══════════

class JsonFormatter(logging.Formatter):
    """Emit structured JSON log lines."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        log_entry = {
            'ts': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'msg': record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log_entry['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


def get_logger(name: str = 'neuro-link') -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(os.getenv('LOG_LEVEL', 'INFO').upper())
    return logger


logger = get_logger()


# ═══════════ Metrics Collector ═══════════

@dataclass
class RouteMetrics:
    count: int = 0
    total_ms: float = 0.0
    errors: int = 0
    min_ms: float = float('inf')
    max_ms: float = 0.0


_lock = threading.Lock()
_route_metrics: dict[str, RouteMetrics] = defaultdict(RouteMetrics)
_start_time = time.time()


def record_request(route: str, duration_ms: float, is_error: bool = False) -> None:
    """Record a request metric for a given route."""
    with _lock:
        m = _route_metrics[route]
        m.count += 1
        m.total_ms += duration_ms
        if is_error:
            m.errors += 1
        if duration_ms < m.min_ms:
            m.min_ms = duration_ms
        if duration_ms > m.max_ms:
            m.max_ms = duration_ms


def get_metrics_snapshot() -> dict[str, Any]:
    """Return a snapshot of all collected metrics."""
    uptime_s = time.time() - _start_time

    # System resources (best-effort, no psutil needed)
    system: dict[str, Any] = {'uptime_seconds': round(uptime_s, 1)}

    try:
        load1, load5, load15 = os.getloadavg()
        system['load_avg'] = {'1m': round(load1, 2), '5m': round(load5, 2), '15m': round(load15, 2)}
    except OSError:
        pass

    try:
        import resource
        rusage = resource.getrusage(resource.RUSAGE_SELF)
        system['memory_mb'] = round(rusage.ru_maxrss / (1024 * 1024), 1)  # macOS
    except Exception:
        pass

    # Routes
    routes_data: dict[str, Any] = {}
    with _lock:
        for route, m in _route_metrics.items():
            avg = m.total_ms / m.count if m.count > 0 else 0
            routes_data[route] = {
                'requests': m.count,
                'errors': m.errors,
                'avg_ms': round(avg, 2),
                'min_ms': round(m.min_ms, 2) if m.min_ms != float('inf') else 0,
                'max_ms': round(m.max_ms, 2),
            }

    total_requests = sum(m.count for m in _route_metrics.values())
    total_errors = sum(m.errors for m in _route_metrics.values())

    return {
        'service': 'neuro-link-api',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'system': system,
        'totals': {
            'requests': total_requests,
            'errors': total_errors,
            'error_rate': round(total_errors / total_requests, 4) if total_requests > 0 else 0,
        },
        'routes': routes_data,
    }
