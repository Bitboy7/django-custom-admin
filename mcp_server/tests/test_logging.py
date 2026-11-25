import asyncio
import logging
from types import SimpleNamespace

import pytest
from mcp.server.fastmcp import FastMCP
from sqlalchemy.exc import OperationalError
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from mcp_server.config import ConfigError, log_level_from_env
from mcp_server.guard import SqlGuardError
from mcp_server.logutil import count_rows, logged_tool, sanitize_args, short_sql
from mcp_server.server import BearerAuthMiddleware, RequestLogMiddleware
from mcp_server.tools import register_tools

TOKEN = "t" * 40


# ---------------------------------------------------------------- helpers


def test_short_sql_collapses_whitespace():
    assert short_sql("SELECT  id\n  FROM\tventas_ventas") == "SELECT id FROM ventas_ventas"


def test_short_sql_truncates_with_ascii_ellipsis():
    out = short_sql("SELECT " + "x, " * 200 + "y FROM t", limit=50)
    assert len(out) == 50
    assert out.endswith("...")
    assert "…" not in out


def test_sanitize_args_masks_secrets_and_shortens():
    clean = sanitize_args(
        {
            "token": "secreto",
            "db_password": "secreto",
            "sql": "SELECT   id FROM ventas_ventas " + "WHERE id > 1 " * 100,
            "tabla": "x" * 500,
            "limite": 10,
            "solo_vencida": True,
            "fecha_corte": None,
            "filtros": {"a": 1},
        }
    )
    assert clean["token"] == "***"
    assert clean["db_password"] == "***"
    assert clean["sql"].startswith("SELECT id FROM ventas_ventas WHERE")
    assert len(clean["sql"]) <= 300
    assert len(clean["tabla"]) == 80 and clean["tabla"].endswith("...")
    assert clean["limite"] == 10
    assert clean["solo_vencida"] is True
    assert clean["fecha_corte"] is None
    assert clean["filtros"] == "<dict>"


@pytest.mark.parametrize(
    "result, expected",
    [
        ({"num_filas": 3, "filas": [1, 2, 3]}, 3),
        ([{"tabla": "a"}, {"tabla": "b"}], 2),
        ({"tabla": "x", "columnas": [1, 2]}, 2),
        ({"algo": 1}, None),
    ],
)
def test_count_rows(result, expected):
    assert count_rows(result) == expected


def test_log_level_from_env(monkeypatch):
    monkeypatch.delenv("MCP_LOG_LEVEL", raising=False)
    assert log_level_from_env() == "INFO"
    monkeypatch.setenv("MCP_LOG_LEVEL", " debug ")
    assert log_level_from_env() == "DEBUG"
    monkeypatch.setenv("MCP_LOG_LEVEL", "verbose")
    with pytest.raises(ConfigError):
        log_level_from_env()


# ---------------------------------------------------------- logged_tool


def test_logged_tool_success_logs_rows_and_duration(caplog):
    @logged_tool("demo")
    def demo(fecha_inicio: str, limite: int = 5):
        return {"num_filas": 2, "filas": [{"cliente": "ACME"}, {"cliente": "Otro"}]}

    with caplog.at_level(logging.INFO, logger="mcp_server.tools"):
        demo("2026-01-01")

    record = caplog.records[-1]
    assert record.levelno == logging.INFO
    msg = record.getMessage()
    assert "tool=demo ok" in msg
    assert "filas=2" in msg
    assert "ms" in msg
    assert "fecha_inicio='2026-01-01'" in msg
    assert "ACME" not in msg  # nunca el contenido de las filas


def test_logged_tool_error_result_is_warning(caplog):
    @logged_tool("demo")
    def demo():
        return {"error": "Fecha inválida"}

    with caplog.at_level(logging.INFO, logger="mcp_server.tools"):
        demo()

    record = caplog.records[-1]
    assert record.levelno == logging.WARNING
    assert "Fecha inválida" in record.getMessage()


def test_logged_tool_exception_logs_traceback_and_reraises(caplog):
    @logged_tool("demo")
    def demo():
        raise RuntimeError("boom")

    with caplog.at_level(logging.INFO, logger="mcp_server.tools"):
        with pytest.raises(RuntimeError):
            demo()

    record = caplog.records[-1]
    assert record.levelno == logging.ERROR
    assert record.exc_info is not None
    assert "tool=demo error" in record.getMessage()


# --------------------------------------------------- tools registradas


class FakeDB:
    def __init__(self):
        self.settings = SimpleNamespace(max_rows=500)
        self.fail_trusted = False

    def run_trusted(self, sql, params):
        if self.fail_trusted:
            raise OperationalError("SELECT 1", {}, Exception("conexión perdida"))
        return {"columnas": ["moneda"], "filas": [{"moneda": "MXN"}], "num_filas": 1, "truncado": False}

    def run_select(self, sql):
        if "DELETE" in sql.upper():
            raise SqlGuardError("Solo se permiten consultas SELECT")
        return {"columnas": ["id"], "filas": [{"id": 1}, {"id": 2}], "num_filas": 2, "truncado": False}

    def list_tables(self):
        return [{"tabla": "ventas_ventas", "descripcion": "Ventas"}]

    def describe_table(self, tabla):
        return {"tabla": tabla, "columnas": [{"nombre": "id", "tipo": "INT"}]}


@pytest.fixture
def mcp_and_db():
    db = FakeDB()
    mcp = FastMCP(name="test")
    register_tools(mcp, db)
    return mcp, db


def _call(mcp, name, args):
    return asyncio.run(mcp.call_tool(name, args))


def test_wrapped_tools_keep_their_input_schema(mcp_and_db):
    mcp, _ = mcp_and_db
    tools = {tool.name: tool for tool in asyncio.run(mcp.list_tools())}
    assert len(tools) == 15
    schema = tools["resumen_ventas"].inputSchema
    assert set(schema["properties"]) == {"fecha_inicio", "fecha_fin", "agrupacion"}
    assert set(schema["required"]) == {"fecha_inicio", "fecha_fin"}
    assert tools["saldo_mensual"].inputSchema.get("required", []) == []


def test_tool_call_is_logged(mcp_and_db, caplog):
    mcp, _ = mcp_and_db
    with caplog.at_level(logging.INFO, logger="mcp_server.tools"):
        _call(mcp, "resumen_ventas", {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-01-31"})

    messages = [r.getMessage() for r in caplog.records if r.name == "mcp_server.tools"]
    assert any(
        "tool=resumen_ventas ok" in m and "filas=1" in m and "fecha_fin='2026-01-31'" in m
        for m in messages
    )


def test_consultar_sql_logs_short_sql_only(mcp_and_db, caplog):
    mcp, _ = mcp_and_db
    sql = "SELECT   id\nFROM ventas_ventas WHERE " + " OR ".join(f"id = {i}" for i in range(300))
    with caplog.at_level(logging.INFO, logger="mcp_server.tools"):
        _call(mcp, "consultar_sql", {"sql": sql})

    msg = next(r.getMessage() for r in caplog.records if "tool=consultar_sql" in r.getMessage())
    assert "sql='SELECT id FROM ventas_ventas WHERE id = 0" in msg
    assert "...'" in msg
    assert "id = 299" not in msg
    assert "filas=2" in msg


def test_consultar_sql_guard_rejection_is_warning(mcp_and_db, caplog):
    mcp, _ = mcp_and_db
    with caplog.at_level(logging.INFO, logger="mcp_server.tools"):
        _call(mcp, "consultar_sql", {"sql": "DELETE FROM ventas_ventas"})

    record = next(r for r in caplog.records if "tool=consultar_sql" in r.getMessage())
    assert record.levelno == logging.WARNING
    assert "Solo se permiten consultas SELECT" in record.getMessage()


def test_db_error_logs_traceback(mcp_and_db, caplog):
    mcp, db = mcp_and_db
    db.fail_trusted = True
    with caplog.at_level(logging.INFO, logger="mcp_server.tools"):
        _call(mcp, "resumen_gastos", {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-01-31"})

    assert any(r.levelno == logging.ERROR and r.exc_info for r in caplog.records)
    assert any(
        r.levelno == logging.WARNING and "tool=resumen_gastos rechazada" in r.getMessage()
        for r in caplog.records
    )


# -------------------------------------------------------- HTTP middleware


def _http_app():
    async def ok(_request):
        return JSONResponse({"ok": True})

    async def boom(_request):
        return JSONResponse({"error": "x"}, status_code=503)

    async def health(_request):
        return JSONResponse({"status": "ok"})

    app = Starlette(
        routes=[
            Route("/mcp", ok, methods=["POST"]),
            Route("/fail", boom, methods=["POST"]),
            Route("/health", health),
        ]
    )
    app.add_middleware(BearerAuthMiddleware, token=TOKEN)
    app.add_middleware(RequestLogMiddleware)
    return TestClient(app)


def _http_records(caplog):
    return [r for r in caplog.records if r.name == "mcp_server.server" and r.getMessage().startswith("HTTP ")]


def test_http_request_logged_with_status_and_duration(caplog):
    client = _http_app()
    with caplog.at_level(logging.INFO, logger="mcp_server.server"):
        client.post("/mcp?secreto=1", headers={"Authorization": f"Bearer {TOKEN}"})

    record = _http_records(caplog)[-1]
    msg = record.getMessage()
    assert record.levelno == logging.INFO
    assert msg.startswith("HTTP POST /mcp -> 200 en ")
    assert "cliente=testclient" in msg
    assert "secreto" not in msg


def test_http_401_is_warning_without_token(caplog):
    client = _http_app()
    with caplog.at_level(logging.DEBUG, logger="mcp_server.server"):
        response = client.post("/mcp", headers={"Authorization": "Bearer token-incorrecto"})

    assert response.status_code == 401
    record = _http_records(caplog)[-1]
    assert record.levelno == logging.WARNING
    assert "-> 401" in record.getMessage()
    full_log = caplog.text
    assert "token-incorrecto" not in full_log
    assert TOKEN not in full_log


def test_http_5xx_is_error(caplog):
    client = _http_app()
    with caplog.at_level(logging.INFO, logger="mcp_server.server"):
        client.post("/fail", headers={"Authorization": f"Bearer {TOKEN}"})

    record = _http_records(caplog)[-1]
    assert record.levelno == logging.ERROR
    assert "-> 503" in record.getMessage()


def test_http_health_ok_is_debug_only(caplog):
    client = _http_app()
    with caplog.at_level(logging.INFO, logger="mcp_server.server"):
        client.get("/health")
    assert _http_records(caplog) == []
