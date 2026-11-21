import pytest

from mcp_server import queries
from mcp_server.allowlist import ALLOWED_TABLES
from mcp_server.guard import SqlGuardError, assert_allowlisted, referenced_tables

PERIOD = ("2025-01-01", "2025-12-31")

BUILDERS = {
    "resumen_ventas": lambda: queries.resumen_ventas(*PERIOD),
    "ventas_por_cliente": lambda: queries.ventas_por_cliente(*PERIOD),
    "ventas_por_producto": lambda: queries.ventas_por_producto(*PERIOD),
    "cartera_por_cliente": lambda: queries.cartera_por_cliente(),
    "cartera_por_cliente_vencida": lambda: queries.cartera_por_cliente(True),
    "cartera_vencida": lambda: queries.cartera_vencida(),
    "pagos_recientes": lambda: queries.pagos_recientes(*PERIOD),
    "resumen_gastos": lambda: queries.resumen_gastos(*PERIOD),
    "gastos_por_categoria": lambda: queries.gastos_por_categoria(*PERIOD),
    "compras_por_producto": lambda: queries.compras_por_producto(*PERIOD),
    "compras_por_productor": lambda: queries.compras_por_productor(*PERIOD),
    "saldo_mensual": lambda: queries.saldo_mensual(2025, 1),
    "resumen_financiero": lambda: queries.resumen_financiero(*PERIOD),
}


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_curated_sql_is_select_and_allowlisted(name):
    sql, _params = BUILDERS[name]()
    assert_allowlisted(sql)
    tables = set(referenced_tables(sql))
    assert tables
    assert tables <= set(ALLOWED_TABLES), f"{name} usa tablas no permitidas: {tables - set(ALLOWED_TABLES)}"


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_curated_sql_has_no_pii_columns(name):
    sql, _params = BUILDERS[name]()
    lowered = sql.lower()
    for column in ("rfc", "clabe", "correo", "telefono", "direccion"):
        assert column not in lowered, f"{name} referencia {column}"


def test_invalid_date_rejected():
    with pytest.raises(ValueError):
        queries.resumen_ventas("2025-13-01", "2025-12-31")
    with pytest.raises(ValueError):
        queries.resumen_ventas("2025-12-31", "2025-01-01")
    with pytest.raises(ValueError):
        queries.resumen_ventas(*PERIOD, agrupacion="semana")


def test_limit_is_clamped():
    assert queries.clamp_limit(0, 100) == 1
    assert queries.clamp_limit(10_000, 100) == 100
    assert queries.clamp_limit("25", 100) == 25
    with pytest.raises(ValueError):
        queries.clamp_limit("abc", 100)


def test_saldo_mensual_validates_ranges():
    with pytest.raises(ValueError):
        queries.saldo_mensual(2025, 13)
    with pytest.raises(ValueError):
        queries.saldo_mensual(1800, 1)


def test_guard_still_rejects_curated_pii_if_changed():
    with pytest.raises(SqlGuardError):
        assert_allowlisted("SELECT id FROM auth_user")
