"""
Trace ids, structured logs, and per-stage timing.

Every HTTP request gets a trace_id (taken from the X-Trace-Id header or
generated). It is kept in a context variable, written on every log line,
copied into Kafka message headers, and picked up again by the workers,
so one id follows a request through the API, Kafka, and the workers.

Stage timings (model inference, database, tool execution, queue wait,
worker processing) are stored in the `traces` collection.
"""

import contextvars
import json
import logging
import os
import sys
import time
from contextlib import contextmanager
from uuid import uuid4

from .database import get_database, utcnow


SERVICE_NAME = os.getenv("SERVICE_NAME", "handshake")

_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)
# Stage timings are stored only for sampled traces (every assistant
# request, plus any request sent with "X-Trace-Sample: 1"), so load tests
# of the CRUD endpoints do not also load-test the traces collection.
_sampled: contextvars.ContextVar[bool] = contextvars.ContextVar("trace_sampled", default=False)


def new_trace_id() -> str:
    return uuid4().hex


def current_trace_id() -> str | None:
    return _trace_id.get()


def is_sampled() -> bool:
    return _sampled.get()


def set_trace_id(trace_id: str | None, sampled: bool = False):
    return (_trace_id.set(trace_id), _sampled.set(sampled))


def reset_trace_id(tokens) -> None:
    trace_token, sampled_token = tokens
    _trace_id.reset(trace_token)
    _sampled.reset(sampled_token)


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        line = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "trace_id": getattr(record, "trace_id", None) or current_trace_id(),
            "msg": record.getMessage(),
        }
        extra = getattr(record, "fields", None)
        if extra:
            line.update(extra)
        return json.dumps(line, default=str)


def get_logger(name: str = "handshake") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
        logger.propagate = False
    return logger


log = get_logger()


def log_event(message: str, **fields) -> None:
    log.info(message, extra={"fields": fields})


def record_stage(
    stage: str,
    ms: float,
    trace_id: str | None = None,
    ok: bool = True,
    **details,
) -> None:
    """
    Saves one stage timing for a trace. Failures here never break the
    request being traced.
    """

    if trace_id is None:
        if not is_sampled():
            return
        trace_id = current_trace_id()
    if not trace_id:
        return

    try:
        get_database().traces.insert_one({
            "trace_id": trace_id,
            "service": SERVICE_NAME,
            "stage": stage,
            "ms": round(ms, 2),
            "ok": ok,
            "details": details,
            "started_at": utcnow(),
        })
    except Exception:  # pragma: no cover - tracing must never fail a request
        pass


@contextmanager
def stage_timer(stage: str, trace_id: str | None = None, **details):
    """
    with stage_timer("db.find_jobs"): ...
    Records the elapsed time even if the block raises.
    """

    started = time.perf_counter()
    ok = True
    try:
        yield
    except Exception:
        ok = False
        raise
    finally:
        record_stage(stage, (time.perf_counter() - started) * 1000, trace_id, ok, **details)
