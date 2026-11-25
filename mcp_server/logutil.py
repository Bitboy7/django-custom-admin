"""Logging helpers: uniform format, safe argument summaries and tool timing.

Nothing logged here may contain secrets (tokens, passwords) or row data.
Only tool names, sanitized arguments, row counts and durations.
"""

from __future__ import annotations

import functools
import inspect
import logging
import sys
import time
from typing import Any, Callable, TypeVar

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
VALID_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

# ASCII ellipsis on purpose: Windows consoles (cp1252) mangle "…".
ELLIPSIS = "..."
SQL_LOG_LIMIT = 300
ARG_STR_LIMIT = 80
SENSITIVE_KEYS = ("token", "password", "passwd", "secret", "authorization", "api_key", "apikey")

F = TypeVar("F", bound=Callable[..., Any])

tool_logger = logging.getLogger("mcp_server.tools")


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger once with the uniform format on stderr.

    stderr keeps stdout clean for the stdio transport. ``force`` replaces any
    handler a library installed earlier (FastMCP's basicConfig is then a no-op).
    """
    logging.basicConfig(
        level=level,
        stream=sys.stderr,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        force=True,
    )
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "mcp", "httpx"):
        lib_logger = logging.getLogger(name)
        lib_logger.handlers.clear()
        lib_logger.propagate = True
    # The SDK logs "Processing request of type ..." at INFO for every call;
    # the tool wrapper already covers that, so keep it only in DEBUG.
    logging.getLogger("mcp.server.lowlevel.server").setLevel(
        logging.NOTSET if level == "DEBUG" else logging.WARNING
    )


def short_sql(sql: str, limit: int = SQL_LOG_LIMIT) -> str:
    """Collapse whitespace and cap a SQL string for logging."""
    compact = " ".join((sql or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: max(0, limit - len(ELLIPSIS))] + ELLIPSIS


def _short_value(value: Any, limit: int = ARG_STR_LIMIT) -> Any:
    if isinstance(value, str):
        if len(value) <= limit:
            return value
        return value[: limit - len(ELLIPSIS)] + ELLIPSIS
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return f"<{type(value).__name__}>"


def sanitize_args(args: dict[str, Any]) -> dict[str, Any]:
    """Return a log-safe copy of tool arguments.

    Sensitive keys are masked, ``sql`` is compacted with :func:`short_sql`,
    long strings are truncated and complex values are replaced by their type.
    """
    clean: dict[str, Any] = {}
    for key, value in args.items():
        lowered = key.lower()
        if any(marker in lowered for marker in SENSITIVE_KEYS):
            clean[key] = "***"
        elif lowered == "sql" and isinstance(value, str):
            clean[key] = short_sql(value)
        else:
            clean[key] = _short_value(value)
    return clean


def count_rows(result: Any) -> int | None:
    """Best-effort row count of a tool result (never inspects row content)."""
    if isinstance(result, list):
        return len(result)
    if isinstance(result, dict):
        if isinstance(result.get("num_filas"), int):
            return result["num_filas"]
        for key in ("filas", "columnas"):
            if isinstance(result.get(key), list):
                return len(result[key])
    return None


def _format_args(args: dict[str, Any]) -> str:
    return ", ".join(f"{key}={value!r}" for key, value in sanitize_args(args).items())


def logged_tool(name: str) -> Callable[[F], F]:
    """Decorator that logs a tool call: name, args, rows, duration and errors.

    ``functools.wraps`` keeps ``__wrapped__`` so FastMCP still reads the real
    signature to build the tool's input schema.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                bound = inspect.signature(func).bind_partial(*args, **kwargs)
                call_args = dict(bound.arguments)
            except TypeError:
                call_args = dict(kwargs)
            arg_text = _format_args(call_args)
            started = time.perf_counter()
            try:
                result = func(*args, **kwargs)
            except Exception:
                elapsed = (time.perf_counter() - started) * 1000
                tool_logger.exception("tool=%s error tras %.0f ms args={%s}", name, elapsed, arg_text)
                raise
            elapsed = (time.perf_counter() - started) * 1000
            if isinstance(result, dict) and "error" in result:
                tool_logger.warning(
                    "tool=%s rechazada en %.0f ms args={%s} error=%r",
                    name,
                    elapsed,
                    arg_text,
                    _short_value(str(result["error"]), 200),
                )
            else:
                rows = count_rows(result)
                tool_logger.info(
                    "tool=%s ok en %.0f ms filas=%s args={%s}",
                    name,
                    elapsed,
                    "?" if rows is None else rows,
                    arg_text,
                )
            return result

        return wrapper  # type: ignore[return-value]

    return decorator
