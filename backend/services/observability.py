from __future__ import annotations

import contextvars
import json
import logging
import time
from collections import defaultdict
from threading import Lock
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in {"args", "msg", "exc_info", "exc_text", "stack_info", "lineno", "pathname", "filename", "module", "funcName", "created", "msecs", "relativeCreated", "thread", "threadName", "processName", "process", "name", "levelname", "levelno"}:
                continue
            if key not in payload:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


_request_state: contextvars.ContextVar[dict[str, float] | None] = contextvars.ContextVar(
    "crb_request_observability_state",
    default=None,
)

_metrics_lock = Lock()
_metrics_totals: dict[str, float] = defaultdict(float)


def configure_json_logging() -> None:
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(level=logging.INFO)
    for handler in root_logger.handlers:
        if not isinstance(handler.formatter, JsonFormatter):
            handler.setFormatter(JsonFormatter())


def start_request_observation() -> contextvars.Token:
    return _request_state.set({"db_query_count": 0.0, "db_query_ms": 0.0})


def record_db_query(duration_ms: float) -> None:
    state = _request_state.get()
    if state is None:
        return
    state["db_query_count"] = float(state.get("db_query_count", 0.0)) + 1.0
    state["db_query_ms"] = float(state.get("db_query_ms", 0.0)) + max(duration_ms, 0.0)


def finish_request_observation(token: contextvars.Token) -> dict[str, float]:
    state = _request_state.get() or {"db_query_count": 0.0, "db_query_ms": 0.0}
    _request_state.reset(token)
    return {
        "db_query_count": float(state.get("db_query_count", 0.0)),
        "db_query_ms": float(state.get("db_query_ms", 0.0)),
    }


def record_request_metrics(
    *,
    status_code: int,
    duration_ms: float,
    db_query_count: float,
    db_query_ms: float,
) -> None:
    with _metrics_lock:
        _metrics_totals["requests_total"] += 1.0
        _metrics_totals["requests_5xx"] += 1.0 if status_code >= 500 else 0.0
        _metrics_totals["latency_ms_total"] += max(duration_ms, 0.0)
        _metrics_totals["db_query_count_total"] += max(db_query_count, 0.0)
        _metrics_totals["db_query_ms_total"] += max(db_query_ms, 0.0)


def metrics_snapshot() -> dict[str, float]:
    with _metrics_lock:
        requests_total = max(_metrics_totals["requests_total"], 0.0)
        requests_5xx = max(_metrics_totals["requests_5xx"], 0.0)
        latency_total = max(_metrics_totals["latency_ms_total"], 0.0)
        db_query_count_total = max(_metrics_totals["db_query_count_total"], 0.0)
        db_query_ms_total = max(_metrics_totals["db_query_ms_total"], 0.0)

    return {
        "requests_total": requests_total,
        "requests_5xx": requests_5xx,
        "error_rate_5xx": round((requests_5xx / requests_total) if requests_total else 0.0, 6),
        "avg_latency_ms": round((latency_total / requests_total) if requests_total else 0.0, 3),
        "db_queries_total": db_query_count_total,
        "db_query_avg_ms": round((db_query_ms_total / db_query_count_total) if db_query_count_total else 0.0, 3),
    }


def monotonic_ms() -> float:
    return time.perf_counter() * 1000.0
