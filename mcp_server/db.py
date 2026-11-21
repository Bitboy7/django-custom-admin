"""Read-only MySQL access layer."""

from __future__ import annotations

import datetime as _dt
import decimal
import logging
from typing import Any

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine

from .allowlist import ALLOWED_TABLES, BLOCKED_COLUMNS
from .config import Settings
from .guard import assert_allowlisted, validate_select

logger = logging.getLogger(__name__)


class ReadOnlyDatabase:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine: Engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_size=5,
            max_overflow=2,
            future=True,
        )
        self._configure_session(self.engine)

    def _configure_session(self, engine: Engine) -> None:
        timeout = int(self.settings.query_timeout_ms)

        @event.listens_for(engine, "connect")
        def _on_connect(dbapi_connection, _record):  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("SET SESSION TRANSACTION READ ONLY")
                cursor.execute(f"SET SESSION MAX_EXECUTION_TIME={timeout}")
            finally:
                cursor.close()

    def ping(self) -> bool:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception:
            logger.exception("No se pudo conectar a MySQL")
            return False

    def list_tables(self) -> list[dict[str, str]]:
        return [{"tabla": name, "descripcion": description} for name, description in ALLOWED_TABLES.items()]

    def describe_table(self, table: str) -> dict[str, Any]:
        name = table.strip().lower()
        if name not in ALLOWED_TABLES:
            raise ValueError(
                f"Tabla '{table}' no permitida. Usa listar_tablas para ver las disponibles."
            )
        columns = inspect(self.engine).get_columns(name)
        visible = [
            {
                "nombre": column["name"],
                "tipo": str(column["type"]),
                "nulo": bool(column["nullable"]),
            }
            for column in columns
            if column["name"].lower() not in BLOCKED_COLUMNS
        ]
        return {
            "tabla": name,
            "descripcion": ALLOWED_TABLES[name],
            "columnas": visible,
            "columnas_ocultas_por_privacidad": len(columns) - len(visible),
        }

    def run_select(self, sql: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        safe_sql = validate_select(sql, self.settings.max_rows)
        return self._execute(safe_sql, params)

    def run_trusted(self, sql: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        assert_allowlisted(sql)
        return self._execute(sql, params)

    def _execute(self, sql: str, params: dict[str, Any] | None) -> dict[str, Any]:
        max_rows = self.settings.max_rows
        logger.info("Ejecutando consulta de solo lectura (%s filas máx.)", max_rows)
        with self.engine.connect() as connection:
            result = connection.execute(text(sql), params or {})
            columns = list(result.keys())
            rows = result.fetchmany(max_rows + 1)
            truncated = len(rows) > max_rows
            rows = rows[:max_rows]
            return {
                "columnas": columns,
                "filas": [
                    {column: _jsonable(value) for column, value in zip(columns, row)}
                    for row in rows
                ],
                "num_filas": len(rows),
                "truncado": truncated,
            }

    def close(self) -> None:
        self.engine.dispose()


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, (_dt.datetime, _dt.date, _dt.time)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        return f"<{len(value)} bytes>"
    return str(value)
