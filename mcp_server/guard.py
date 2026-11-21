"""SQL validation for the read-only connector.

The guard is intentionally conservative: one statement, SELECT only,
allowlisted tables, no `SELECT *`, no PII columns, an enforced LIMIT and
no dangerous functions. The MySQL user is still SELECT-only, so this is
defense in depth rather than the only protection.
"""

from __future__ import annotations

import re
from typing import Iterable

import sqlglot
from sqlglot import exp

from .allowlist import ALLOWED_TABLES, BLOCKED_COLUMNS, FORBIDDEN_SCHEMAS


class SqlGuardError(ValueError):
    """User-facing validation error. Safe to return to the MCP client."""


_FORBIDDEN_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\binto\s+outfile\b", re.I), "INTO OUTFILE no está permitido"),
    (re.compile(r"\binto\s+dumpfile\b", re.I), "INTO DUMPFILE no está permitido"),
    (re.compile(r"\bfor\s+update\b", re.I), "FOR UPDATE no está permitido"),
    (re.compile(r"\block\s+in\s+share\s+mode\b", re.I), "LOCK IN SHARE MODE no está permitido"),
    (re.compile(r"\bsleep\s*\(", re.I), "SLEEP() no está permitido"),
    (re.compile(r"\bbenchmark\s*\(", re.I), "BENCHMARK() no está permitido"),
    (re.compile(r"\bload_file\s*\(", re.I), "LOAD_FILE() no está permitido"),
    (re.compile(r"\bget_lock\s*\(", re.I), "GET_LOCK() no está permitido"),
    (re.compile(r"\binto\s+@", re.I), "Variables de sesión no están permitidas"),
    (re.compile(r"@@", re.I), "Variables del servidor no están permitidas"),
    (re.compile(r"\bprepare\b", re.I), "PREPARE no está permitido"),
    (re.compile(r"\bexecute\b", re.I), "EXECUTE no está permitido"),
    (re.compile(r"\bcall\b", re.I), "CALL no está permitido"),
    (re.compile(r"\bhandler\b", re.I), "HANDLER no está permitido"),
)

_ALLOWED_ROOTS = (exp.Select, exp.Union)


def _collect_cte_names(root: exp.Expression) -> set[str]:
    names: set[str] = set()
    for cte in root.find_all(exp.CTE):
        if cte.alias:
            names.add(cte.alias.lower())
    for subquery in root.find_all(exp.Subquery):
        if subquery.alias:
            names.add(subquery.alias.lower())
    return names


def _check_tables(root: exp.Expression, cte_names: set[str]) -> None:
    for table in root.find_all(exp.Table):
        name = (table.name or "").lower()
        schema = (table.db or "").lower()
        if schema and schema in FORBIDDEN_SCHEMAS:
            raise SqlGuardError(f"El esquema '{schema}' no está permitido")
        if schema and schema not in {""}:
            raise SqlGuardError("No se permiten nombres de esquema en las consultas")
        if not name or name in cte_names:
            continue
        if name not in ALLOWED_TABLES:
            raise SqlGuardError(
                f"Tabla '{table.name}' no permitida. Usa listar_tablas para ver las disponibles."
            )


def _check_columns(root: exp.Expression) -> None:
    for star in root.find_all(exp.Star):
        parent = star.parent
        if isinstance(parent, exp.Count):
            continue
        raise SqlGuardError("SELECT * no está permitido; enumera las columnas necesarias")
    for column in root.find_all(exp.Column):
        name = (column.name or "").lower()
        if name == "*":
            raise SqlGuardError("SELECT * no está permitido; enumera las columnas necesarias")
        if name in BLOCKED_COLUMNS:
            raise SqlGuardError(f"La columna '{column.name}' contiene datos personales y no está permitida")


def _check_root(root: exp.Expression) -> None:
    if not isinstance(root, _ALLOWED_ROOTS):
        kind = type(root).__name__
        raise SqlGuardError(f"Solo se permiten consultas SELECT (recibido: {kind})")
    for node in root.walk():
        if isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Alter, exp.Command)):
            raise SqlGuardError("Solo se permiten consultas SELECT")


def _enforce_limit(root: exp.Expression, max_rows: int) -> exp.Expression:
    limit = root.args.get("limit")
    if limit is None:
        return root.limit(max_rows)
    expression = limit.expression
    try:
        value = int(expression.name)
    except (AttributeError, TypeError, ValueError) as exc:
        raise SqlGuardError("LIMIT debe ser un número entero") from exc
    if value <= 0:
        raise SqlGuardError("LIMIT debe ser mayor que cero")
    return root if value <= max_rows else root.limit(max_rows)


def _scan_text(sql: str) -> None:
    for pattern, message in _FORBIDDEN_PATTERNS:
        if pattern.search(sql):
            raise SqlGuardError(message)


def validate_select(sql: str, max_rows: int = 500) -> str:
    """Validate and normalize a read-only query. Returns the safe SQL."""
    if not isinstance(sql, str) or not sql.strip():
        raise SqlGuardError("La consulta está vacía")
    if "\x00" in sql:
        raise SqlGuardError("La consulta contiene caracteres inválidos")

    _scan_text(sql)

    try:
        statements = sqlglot.parse(sql, read="mysql")
    except sqlglot.errors.ParseError as exc:
        raise SqlGuardError(f"No se pudo interpretar la consulta: {exc}") from exc

    statements = [statement for statement in statements if statement is not None]
    if len(statements) != 1:
        raise SqlGuardError("Solo se permite una consulta por llamada")

    root = statements[0]
    _check_root(root)
    _check_tables(root, _collect_cte_names(root))
    _check_columns(root)
    root = _enforce_limit(root, max_rows)
    return root.sql(dialect="mysql")


def assert_allowlisted(sql: str) -> None:
    """Validate trusted SQL built by this package without enforcing a LIMIT."""
    statements = [s for s in sqlglot.parse(sql, read="mysql") if s is not None]
    if len(statements) != 1:
        raise SqlGuardError("Solo se permite una consulta")
    root = statements[0]
    _check_root(root)
    _check_tables(root, _collect_cte_names(root))


def referenced_tables(sql: str) -> Iterable[str]:
    """Yield lower-case table names referenced by a query (for tests/debug)."""
    for statement in sqlglot.parse(sql, read="mysql"):
        if statement is None:
            continue
        for table in statement.find_all(exp.Table):
            if table.name:
                yield table.name.lower()
