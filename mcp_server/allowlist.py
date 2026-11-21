"""Tables and columns the read-only connector may expose.

Keep this list in sync with scripts/create_mcp_readonly_user.sql. The
database user is the real boundary; this list is the second barrier and
also drives the schema-discovery tools.
"""

from __future__ import annotations

ALLOWED_TABLES: dict[str, str] = {
    "ventas_ventas": "Ventas (ingresos, crédito, cobranza). Fechas: fecha_salida_manifiesto, fecha_vencimiento.",
    "ventas_pagoventa": "Pagos individuales de ventas a crédito.",
    "ventas_cliente": "Clientes y términos de crédito.",
    "gastos_gastos": "Gastos operativos. Fecha: fecha.",
    "gastos_compra": "Compras de producto a productores. Fecha: fecha_compra.",
    "gastos_catgastos": "Categorías de gasto.",
    "gastos_cuenta": "Cuentas bancarias.",
    "gastos_banco": "Bancos.",
    "gastos_saldomensual": "Saldos mensuales por cuenta bancaria.",
    "catalogo_producto": "Productos (nombre y variedad).",
    "catalogo_productor": "Productores.",
    "catalogo_sucursal": "Sucursales.",
    "catalogo_pais": "Países.",
    "catalogo_estado": "Estados / provincias.",
}

BLOCKED_COLUMNS: frozenset[str] = frozenset(
    {
        "rfc",
        "clabe",
        "clabe_interbancaria",
        "numero_cuenta",
        "num_cuenta",
        "correo",
        "telefono",
        "direccion",
        "numero_registro_fiscal",
        "codigo_postal_fiscal",
        "imagen",
        "logotipo",
    }
)

FORBIDDEN_SCHEMAS: frozenset[str] = frozenset(
    {"information_schema", "performance_schema", "mysql", "sys"}
)
