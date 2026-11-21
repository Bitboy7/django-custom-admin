import pytest

from mcp_server.guard import SqlGuardError, validate_select


def test_simple_select_gets_limit():
    sql = validate_select("SELECT id, fecha FROM ventas_ventas", max_rows=100)
    assert "LIMIT 100" in sql.upper()


def test_existing_limit_is_clamped():
    sql = validate_select("SELECT id FROM ventas_ventas LIMIT 5000", max_rows=50)
    assert "LIMIT 50" in sql.upper()


def test_small_limit_is_kept():
    sql = validate_select("SELECT id FROM ventas_ventas LIMIT 10", max_rows=50)
    assert "LIMIT 10" in sql.upper()


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE ventas_ventas SET monto = 0",
        "DELETE FROM ventas_ventas",
        "DROP TABLE ventas_ventas",
        "INSERT INTO ventas_ventas (id) VALUES (1)",
        "ALTER TABLE ventas_ventas ADD COLUMN x INT",
        "CREATE TABLE x (id INT)",
        "TRUNCATE TABLE ventas_ventas",
    ],
)
def test_write_statements_rejected(sql):
    with pytest.raises(SqlGuardError):
        validate_select(sql)


def test_multiple_statements_rejected():
    with pytest.raises(SqlGuardError):
        validate_select("SELECT id FROM ventas_ventas; SELECT id FROM gastos_gastos")


@pytest.mark.parametrize(
    "table",
    ["auth_user", "django_session", "axes_accessattempt", "auditoria_logactividad"],
)
def test_non_allowlisted_tables_rejected(table):
    with pytest.raises(SqlGuardError):
        validate_select(f"SELECT id FROM {table}")


def test_select_star_rejected():
    with pytest.raises(SqlGuardError):
        validate_select("SELECT * FROM ventas_ventas")


def test_count_star_allowed():
    sql = validate_select("SELECT COUNT(*) AS total FROM ventas_ventas", max_rows=10)
    assert "COUNT(*)" in sql.upper()


def test_pii_column_rejected():
    with pytest.raises(SqlGuardError):
        validate_select("SELECT rfc FROM ventas_cliente")


def test_information_schema_rejected():
    with pytest.raises(SqlGuardError):
        validate_select("SELECT table_name FROM information_schema.tables")


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT id FROM ventas_ventas INTO OUTFILE '/tmp/x'",
        "SELECT SLEEP(10) FROM ventas_ventas",
        "SELECT BENCHMARK(1000000, MD5('x')) FROM ventas_ventas",
        "SELECT @@version FROM ventas_ventas",
    ],
)
def test_dangerous_constructs_rejected(sql):
    with pytest.raises(SqlGuardError):
        validate_select(sql)


def test_cte_allowed():
    sql = validate_select(
        "WITH total AS (SELECT cliente_id, SUM(monto) AS m FROM ventas_ventas GROUP BY cliente_id) "
        "SELECT cliente_id, m FROM total",
        max_rows=10,
    )
    assert "WITH" in sql.upper()


def test_union_allowed():
    sql = validate_select(
        "SELECT id FROM ventas_ventas UNION ALL SELECT id FROM gastos_gastos",
        max_rows=10,
    )
    assert "UNION ALL" in sql.upper()


def test_empty_query_rejected():
    with pytest.raises(SqlGuardError):
        validate_select("   ")
