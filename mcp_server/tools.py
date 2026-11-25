"""MCP tools exposed to the language model."""

from __future__ import annotations

import logging
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP
from sqlalchemy.exc import SQLAlchemyError

from . import queries
from .db import ReadOnlyDatabase
from .guard import SqlGuardError
from .logutil import logged_tool

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP, db: ReadOnlyDatabase) -> None:
    max_rows = db.settings.max_rows

    def tool(name: str, description: str) -> Callable[[Callable[..., Any]], Any]:
        """``mcp.tool`` + logging (nombre, args saneados, filas, duración, errores)."""

        def decorator(func: Callable[..., Any]) -> Any:
            return mcp.tool(name=name, description=description)(logged_tool(name)(func))

        return decorator

    def _run(builder: Callable[[], tuple[str, dict[str, Any]]]) -> dict[str, Any]:
        try:
            sql, params = builder()
            return db.run_trusted(sql, params)
        except (ValueError, SqlGuardError) as exc:
            return {"error": str(exc)}
        except SQLAlchemyError:
            logger.exception("Error de base de datos en una tool curada")
            return {"error": "No se pudo ejecutar la consulta en la base de datos"}

    @tool(
        name="listar_tablas",
        description=(
            "Lista las tablas de solo lectura disponibles para reportes, con una breve descripción. "
            "Úsala antes de consultar_sql si no conoces el esquema."
        ),
    )
    def listar_tablas() -> list[dict[str, str]]:
        return db.list_tables()

    @tool(
        name="describir_tabla",
        description=(
            "Devuelve las columnas y tipos de una tabla permitida. Omite columnas con datos personales."
        ),
    )
    def describir_tabla(tabla: str) -> dict[str, Any]:
        try:
            return db.describe_table(tabla)
        except ValueError as exc:
            return {"error": str(exc)}
        except SQLAlchemyError as exc:
            logger.exception("Error de base de datos en describir_tabla")
            return {"error": str(exc)}

    @tool(
        name="resumen_ventas",
        description=(
            "Totales de ventas por periodo (dia, mes o anio) y moneda dentro de un rango de fechas. "
            "Fechas en formato YYYY-MM-DD."
        ),
    )
    def resumen_ventas(fecha_inicio: str, fecha_fin: str, agrupacion: str = "mes") -> dict[str, Any]:
        return _run(lambda: queries.resumen_ventas(fecha_inicio, fecha_fin, agrupacion))

    @tool(
        name="ventas_por_cliente",
        description=(
            "Ventas del periodo agrupadas por cliente, con monto total, pagado y saldo pendiente. "
            "Ordenado de mayor a menor monto."
        ),
    )
    def ventas_por_cliente(fecha_inicio: str, fecha_fin: str, limite: int = 20) -> dict[str, Any]:
        return _run(lambda: queries.ventas_por_cliente(fecha_inicio, fecha_fin, limite))

    @tool(
        name="ventas_por_producto",
        description=(
            "Ventas del periodo agrupadas por producto y variedad, con cantidad y monto. "
            "Ordenado de mayor a menor monto."
        ),
    )
    def ventas_por_producto(fecha_inicio: str, fecha_fin: str, limite: int = 20) -> dict[str, Any]:
        return _run(lambda: queries.ventas_por_producto(fecha_inicio, fecha_fin, limite))

    @tool(
        name="cartera_por_cliente",
        description=(
            "Saldo pendiente y vencido por cliente (cuentas por cobrar), opcionalmente solo vencidas. "
            "No requiere fechas."
        ),
    )
    def cartera_por_cliente(solo_vencida: bool = False, limite: int = 50) -> dict[str, Any]:
        return _run(lambda: queries.cartera_por_cliente(solo_vencida, limite))

    @tool(
        name="cartera_vencida",
        description=(
            "Antigüedad de saldos vencidos por cliente en tramos de 1-30, 31-60, 61-90 y más de 90 días. "
            "fecha_corte es opcional (YYYY-MM-DD); por defecto hoy."
        ),
    )
    def cartera_vencida(fecha_corte: str | None = None, limite: int = 100) -> dict[str, Any]:
        return _run(lambda: queries.cartera_vencida(fecha_corte, limite))

    @tool(
        name="pagos_recientes",
        description="Pagos recibidos en un rango de fechas, con cliente, venta, método y monto.",
    )
    def pagos_recientes(fecha_inicio: str, fecha_fin: str, limite: int = 50) -> dict[str, Any]:
        return _run(lambda: queries.pagos_recientes(fecha_inicio, fecha_fin, limite))

    @tool(
        name="resumen_gastos",
        description="Totales de gastos por periodo (dia, mes o anio) y moneda dentro de un rango de fechas.",
    )
    def resumen_gastos(fecha_inicio: str, fecha_fin: str, agrupacion: str = "mes") -> dict[str, Any]:
        return _run(lambda: queries.resumen_gastos(fecha_inicio, fecha_fin, agrupacion))

    @tool(
        name="gastos_por_categoria",
        description="Gastos del periodo agrupados por categoría, ordenados de mayor a menor monto.",
    )
    def gastos_por_categoria(fecha_inicio: str, fecha_fin: str, limite: int = 30) -> dict[str, Any]:
        return _run(lambda: queries.gastos_por_categoria(fecha_inicio, fecha_fin, limite))

    @tool(
        name="compras_por_producto",
        description="Compras del periodo agrupadas por producto y variedad, con cantidad y monto.",
    )
    def compras_por_producto(fecha_inicio: str, fecha_fin: str, limite: int = 30) -> dict[str, Any]:
        return _run(lambda: queries.compras_por_producto(fecha_inicio, fecha_fin, limite))

    @tool(
        name="compras_por_productor",
        description="Compras del periodo agrupadas por productor, con cantidad y monto total.",
    )
    def compras_por_productor(fecha_inicio: str, fecha_fin: str, limite: int = 30) -> dict[str, Any]:
        return _run(lambda: queries.compras_por_productor(fecha_inicio, fecha_fin, limite))

    @tool(
        name="saldo_mensual",
        description="Saldos inicial y final por banco y mes. Filtros opcionales: anio y mes.",
    )
    def saldo_mensual(anio: int | None = None, mes: int | None = None, limite: int = 100) -> dict[str, Any]:
        return _run(lambda: queries.saldo_mensual(anio, mes, limite))

    @tool(
        name="resumen_financiero",
        description=(
            "Resumen del periodo con ventas, gastos, compras y cartera pendiente por moneda. "
            "Ideal para una vista general antes de pedir detalle."
        ),
    )
    def resumen_financiero(fecha_inicio: str, fecha_fin: str) -> dict[str, Any]:
        return _run(lambda: queries.resumen_financiero(fecha_inicio, fecha_fin))

    @tool(
        name="consultar_sql",
        description=(
            "Ejecuta una consulta SELECT ad-hoc de solo lectura sobre tablas permitidas. "
            "Reglas: una sola sentencia, sin SELECT *, sin columnas personales, LIMIT máximo "
            f"{max_rows}. Úsala solo cuando las tools de reporte no cubran la pregunta."
        ),
    )
    def consultar_sql(sql: str) -> dict[str, Any]:
        try:
            return db.run_select(sql)
        except (ValueError, SqlGuardError) as exc:
            return {"error": str(exc)}
        except SQLAlchemyError:
            logger.exception("Error de base de datos en consultar_sql")
            return {"error": "No se pudo ejecutar la consulta en la base de datos"}
