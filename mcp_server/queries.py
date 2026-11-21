"""Curated, parameterized queries for the reporting tools.

All dates are ISO strings (YYYY-MM-DD). Money is grouped by its stored
currency so mixed-currency data is never silently added together.
"""

from __future__ import annotations

from datetime import date

GRANULARIDAD = {
    "dia": "%Y-%m-%d",
    "mes": "%Y-%m",
    "anio": "%Y",
}


def parse_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} debe tener formato YYYY-MM-DD") from exc


def parse_period(inicio: str, fin: str) -> tuple[date, date]:
    start = parse_date(inicio, "fecha_inicio")
    end = parse_date(fin, "fecha_fin")
    if start > end:
        raise ValueError("fecha_inicio no puede ser mayor que fecha_fin")
    return start, end


def clamp_limit(limite: int, max_rows: int) -> int:
    try:
        value = int(limite)
    except (TypeError, ValueError) as exc:
        raise ValueError("limite debe ser un entero") from exc
    return max(1, min(value, max_rows))


def _granularidad(value: str) -> str:
    key = (value or "mes").strip().lower()
    if key not in GRANULARIDAD:
        raise ValueError("agrupacion debe ser: dia, mes o anio")
    return GRANULARIDAD[key]


def resumen_ventas(inicio: str, fin: str, agrupacion: str = "mes", limite: int = 500):
    start, end = parse_period(inicio, fin)
    fmt = _granularidad(agrupacion)
    sql = f"""
        SELECT DATE_FORMAT(v.fecha_salida_manifiesto, '{fmt}') AS periodo,
               v.monto_currency AS moneda,
               COUNT(*) AS num_ventas,
               SUM(v.cantidad) AS cantidad_vendida,
               SUM(v.monto) AS monto_total,
               SUM(v.monto_pagado) AS monto_pagado
        FROM ventas_ventas v
        WHERE v.fecha_salida_manifiesto BETWEEN :inicio AND :fin
        GROUP BY periodo, moneda
        ORDER BY periodo
        LIMIT {clamp_limit(limite, 5000)}
    """
    return sql, {"inicio": start, "fin": end}


def ventas_por_cliente(inicio: str, fin: str, limite: int = 20):
    start, end = parse_period(inicio, fin)
    sql = f"""
        SELECT c.id AS cliente_id,
               c.nombre AS cliente,
               v.monto_currency AS moneda,
               COUNT(*) AS num_ventas,
               SUM(v.monto) AS monto_total,
               SUM(v.monto_pagado) AS monto_pagado,
               SUM(GREATEST(v.monto - v.monto_pagado, 0)) AS saldo_pendiente
        FROM ventas_ventas v
        JOIN ventas_cliente c ON c.id = v.cliente_id
        WHERE v.fecha_salida_manifiesto BETWEEN :inicio AND :fin
        GROUP BY c.id, c.nombre, moneda
        ORDER BY monto_total DESC
        LIMIT {clamp_limit(limite, 200)}
    """
    return sql, {"inicio": start, "fin": end}


def ventas_por_producto(inicio: str, fin: str, limite: int = 20):
    start, end = parse_period(inicio, fin)
    sql = f"""
        SELECT p.nombre AS producto,
               p.variedad AS variedad,
               v.monto_currency AS moneda,
               COUNT(*) AS num_ventas,
               SUM(v.cantidad) AS cantidad_vendida,
               SUM(v.monto) AS monto_total
        FROM ventas_ventas v
        JOIN catalogo_producto p ON p.id = v.producto_id
        WHERE v.fecha_salida_manifiesto BETWEEN :inicio AND :fin
        GROUP BY p.id, p.nombre, p.variedad, moneda
        ORDER BY monto_total DESC
        LIMIT {clamp_limit(limite, 200)}
    """
    return sql, {"inicio": start, "fin": end}


def cartera_por_cliente(solo_vencida: bool = False, limite: int = 50):
    filtro = "AND v.fecha_vencimiento < CURDATE()" if solo_vencida else ""
    sql = f"""
        SELECT c.id AS cliente_id,
               c.nombre AS cliente,
               v.monto_currency AS moneda,
               COUNT(*) AS ventas_pendientes,
               SUM(v.monto) AS monto_total,
               SUM(v.monto_pagado) AS monto_pagado,
               SUM(GREATEST(v.monto - v.monto_pagado, 0)) AS saldo_pendiente,
               SUM(CASE WHEN v.fecha_vencimiento < CURDATE()
                        THEN GREATEST(v.monto - v.monto_pagado, 0) ELSE 0 END) AS saldo_vencido
        FROM ventas_ventas v
        JOIN ventas_cliente c ON c.id = v.cliente_id
        WHERE v.estado_cobranza IN ('Pendiente', 'Parcial', 'Vencido')
          AND v.monto > v.monto_pagado
          {filtro}
        GROUP BY c.id, c.nombre, moneda
        HAVING saldo_pendiente > 0
        ORDER BY saldo_vencido DESC, saldo_pendiente DESC
        LIMIT {clamp_limit(limite, 500)}
    """
    return sql, {}


def cartera_vencida(fecha_corte: str | None = None, limite: int = 100):
    corte = parse_date(fecha_corte, "fecha_corte") if fecha_corte else date.today()
    sql = f"""
        SELECT c.nombre AS cliente,
               v.monto_currency AS moneda,
               SUM(CASE WHEN DATEDIFF(:corte, v.fecha_vencimiento) BETWEEN 1 AND 30
                        THEN GREATEST(v.monto - v.monto_pagado, 0) ELSE 0 END) AS dias_1_30,
               SUM(CASE WHEN DATEDIFF(:corte, v.fecha_vencimiento) BETWEEN 31 AND 60
                        THEN GREATEST(v.monto - v.monto_pagado, 0) ELSE 0 END) AS dias_31_60,
               SUM(CASE WHEN DATEDIFF(:corte, v.fecha_vencimiento) BETWEEN 61 AND 90
                        THEN GREATEST(v.monto - v.monto_pagado, 0) ELSE 0 END) AS dias_61_90,
               SUM(CASE WHEN DATEDIFF(:corte, v.fecha_vencimiento) > 90
                        THEN GREATEST(v.monto - v.monto_pagado, 0) ELSE 0 END) AS dias_mas_90,
               SUM(GREATEST(v.monto - v.monto_pagado, 0)) AS saldo_vencido_total
        FROM ventas_ventas v
        JOIN ventas_cliente c ON c.id = v.cliente_id
        WHERE v.estado_cobranza IN ('Pendiente', 'Parcial', 'Vencido')
          AND v.monto > v.monto_pagado
          AND v.fecha_vencimiento IS NOT NULL
          AND v.fecha_vencimiento < :corte
        GROUP BY c.id, c.nombre, moneda
        ORDER BY saldo_vencido_total DESC
        LIMIT {clamp_limit(limite, 500)}
    """
    return sql, {"corte": corte}


def pagos_recientes(inicio: str, fin: str, limite: int = 50):
    start, end = parse_period(inicio, fin)
    sql = f"""
        SELECT p.fecha_pago,
               c.nombre AS cliente,
               v.carga,
               v.pedimento,
               v.PO,
               p.monto_pago_currency AS moneda,
               p.monto_pago,
               p.metodo_pago,
               p.referencia
        FROM ventas_pagoventa p
        JOIN ventas_ventas v ON v.id = p.venta_id
        JOIN ventas_cliente c ON c.id = v.cliente_id
        WHERE p.fecha_pago BETWEEN :inicio AND :fin
        ORDER BY p.fecha_pago DESC, p.id DESC
        LIMIT {clamp_limit(limite, 500)}
    """
    return sql, {"inicio": start, "fin": end}


def resumen_gastos(inicio: str, fin: str, agrupacion: str = "mes", limite: int = 5000):
    start, end = parse_period(inicio, fin)
    fmt = _granularidad(agrupacion)
    sql = f"""
        SELECT DATE_FORMAT(g.fecha, '{fmt}') AS periodo,
               g.monto_currency AS moneda,
               COUNT(*) AS num_gastos,
               SUM(g.monto) AS monto_total
        FROM gastos_gastos g
        WHERE g.fecha BETWEEN :inicio AND :fin
        GROUP BY periodo, moneda
        ORDER BY periodo
        LIMIT {clamp_limit(limite, 5000)}
    """
    return sql, {"inicio": start, "fin": end}


def gastos_por_categoria(inicio: str, fin: str, limite: int = 30):
    start, end = parse_period(inicio, fin)
    sql = f"""
        SELECT cg.nombre AS categoria,
               g.monto_currency AS moneda,
               COUNT(*) AS num_registros,
               SUM(g.monto) AS monto_total
        FROM gastos_gastos g
        JOIN gastos_catgastos cg ON cg.id = g.id_cat_gastos_id
        WHERE g.fecha BETWEEN :inicio AND :fin
        GROUP BY cg.id, cg.nombre, moneda
        ORDER BY monto_total DESC
        LIMIT {clamp_limit(limite, 200)}
    """
    return sql, {"inicio": start, "fin": end}


def compras_por_producto(inicio: str, fin: str, limite: int = 30):
    start, end = parse_period(inicio, fin)
    sql = f"""
        SELECT p.nombre AS producto,
               p.variedad AS variedad,
               c.monto_total_currency AS moneda,
               COUNT(*) AS num_compras,
               SUM(c.cantidad) AS cantidad_comprada,
               SUM(c.monto_total) AS monto_total
        FROM gastos_compra c
        JOIN catalogo_producto p ON p.id = c.producto_id
        WHERE c.fecha_compra BETWEEN :inicio AND :fin
        GROUP BY p.id, p.nombre, p.variedad, moneda
        ORDER BY monto_total DESC
        LIMIT {clamp_limit(limite, 200)}
    """
    return sql, {"inicio": start, "fin": end}


def compras_por_productor(inicio: str, fin: str, limite: int = 30):
    start, end = parse_period(inicio, fin)
    sql = f"""
        SELECT pr.id AS productor_id,
               pr.nombre_completo AS productor,
               c.monto_total_currency AS moneda,
               COUNT(*) AS num_compras,
               SUM(c.cantidad) AS cantidad_comprada,
               SUM(c.monto_total) AS monto_total
        FROM gastos_compra c
        JOIN catalogo_productor pr ON pr.id = c.productor_id
        WHERE c.fecha_compra BETWEEN :inicio AND :fin
        GROUP BY pr.id, pr.nombre_completo, moneda
        ORDER BY monto_total DESC
        LIMIT {clamp_limit(limite, 200)}
    """
    return sql, {"inicio": start, "fin": end}


def saldo_mensual(anio: int | None = None, mes: int | None = None, limite: int = 100):
    if mes is not None and not 1 <= int(mes) <= 12:
        raise ValueError("mes debe estar entre 1 y 12")
    if anio is not None and not 1999 <= int(anio) <= 2100:
        raise ValueError("anio fuera de rango")
    sql = f"""
        SELECT b.nombre AS banco,
               s.año AS anio,
               s.mes,
               s.saldo_inicial_currency AS moneda,
               s.saldo_inicial,
               s.saldo_final
        FROM gastos_saldomensual s
        JOIN gastos_cuenta cu ON cu.id = s.cuenta_id
        JOIN gastos_banco b ON b.id = cu.id_banco_id
        WHERE (:anio IS NULL OR s.año = :anio)
          AND (:mes IS NULL OR s.mes = :mes)
        ORDER BY s.año DESC, s.mes DESC, b.nombre
        LIMIT {clamp_limit(limite, 500)}
    """
    return sql, {"anio": anio, "mes": mes}


def resumen_financiero(inicio: str, fin: str):
    start, end = parse_period(inicio, fin)
    sql = """
        SELECT 'ventas' AS concepto, v.monto_currency AS moneda, SUM(v.monto) AS total
        FROM ventas_ventas v
        WHERE v.fecha_salida_manifiesto BETWEEN :inicio AND :fin
        GROUP BY moneda
        UNION ALL
        SELECT 'gastos' AS concepto, g.monto_currency AS moneda, SUM(g.monto) AS total
        FROM gastos_gastos g
        WHERE g.fecha BETWEEN :inicio AND :fin
        GROUP BY moneda
        UNION ALL
        SELECT 'compras' AS concepto, c.monto_total_currency AS moneda, SUM(c.monto_total) AS total
        FROM gastos_compra c
        WHERE c.fecha_compra BETWEEN :inicio AND :fin
        GROUP BY moneda
        UNION ALL
        SELECT 'cartera_pendiente' AS concepto, v.monto_currency AS moneda,
               SUM(GREATEST(v.monto - v.monto_pagado, 0)) AS total
        FROM ventas_ventas v
        WHERE v.estado_cobranza IN ('Pendiente', 'Parcial', 'Vencido')
          AND v.monto > v.monto_pagado
        GROUP BY moneda
        ORDER BY concepto, moneda
    """
    return sql, {"inicio": start, "fin": end}
