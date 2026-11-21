"""Server bootstrap for stdio and streamable HTTP transports."""

from __future__ import annotations

import hmac
import logging
from typing import Any

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .config import ConfigError, Settings
from .db import ReadOnlyDatabase
from .tools import register_tools

logger = logging.getLogger(__name__)

INSTRUCTIONS = """
Servidor de reportes de solo lectura para el ERP Agrícola de la Costa.
- Todas las consultas son SELECT sobre tablas permitidas; no hay escrituras.
- Usa primero las tools de reporte (resumen_financiero, resumen_ventas, cartera_*,
  resumen_gastos, compras_*) y consultar_sql solo para preguntas no cubiertas.
- Las fechas se reciben como YYYY-MM-DD.
- Los montos se devuelven agrupados por moneda; no sumes monedas distintas.
- Los saldos pendientes usan monto - monto_pagado de ventas_ventas.
- Si una tool devuelve {"error": ...}, corrige la consulta o pide más contexto.
""".strip()


def create_mcp(settings: Settings, db: ReadOnlyDatabase) -> FastMCP:
    mcp = FastMCP(
        name="agricola-reportes",
        instructions=INSTRUCTIONS,
        host=settings.http_host,
        port=settings.http_port,
        streamable_http_path=settings.http_path,
        stateless_http=True,
        json_response=True,
        log_level="INFO",
    )
    register_tools(mcp, db)
    return mcp


class BearerAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, token: str, allow_no_auth: bool = False) -> None:
        super().__init__(app)
        self.token = token
        self.allow_no_auth = allow_no_auth

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.url.path == "/health":
            return await call_next(request)
        if self.allow_no_auth:
            return await call_next(request)
        header = request.headers.get("authorization", "")
        scheme, _, value = header.partition(" ")
        if scheme.lower() != "bearer" or not hmac.compare_digest(value.strip(), self.token):
            logger.warning("Solicitud rechazada sin token válido desde %s", request.client)
            return JSONResponse(
                {"error": "unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await call_next(request)


def create_http_app(mcp: FastMCP, settings: Settings, db: ReadOnlyDatabase) -> Starlette:
    if not settings.http_token and not settings.allow_no_auth:
        raise ConfigError(
            "MCP_HTTP_TOKEN es obligatorio para HTTP. Define MCP_ALLOW_NO_AUTH=true solo en redes privadas."
        )

    app = mcp.streamable_http_app()

    async def health(_request: Request) -> JSONResponse:
        ok = db.ping()
        return JSONResponse({"status": "ok" if ok else "db_unavailable"}, status_code=200 if ok else 503)

    app.routes.append(Route("/health", health, methods=["GET"]))
    if settings.http_token:
        app.add_middleware(BearerAuthMiddleware, token=settings.http_token)
    return app


def run(settings: Settings, transport: str = "stdio") -> None:
    db = ReadOnlyDatabase(settings)
    mcp = create_mcp(settings, db)
    try:
        if transport == "stdio":
            logger.info("MCP escuchando por stdio")
            mcp.run("stdio")
            return
        if transport not in {"http", "streamable-http"}:
            raise ConfigError(f"Transporte no soportado: {transport}")
        app = create_http_app(mcp, settings, db)
        logger.info(
            "MCP HTTP en http://%s:%s%s",
            settings.http_host,
            settings.http_port,
            settings.http_path,
        )
        uvicorn.run(
            app,
            host=settings.http_host,
            port=settings.http_port,
            log_level="info",
        )
    finally:
        db.close()
