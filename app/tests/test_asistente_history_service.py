import uuid

from app.services.asistente_history_service import (
    MAX_STORED_ROWS,
    _parse_uuid,
    _title_from,
    _trace_payload,
)


def test_title_collapses_whitespace_and_truncates():
    assert _title_from("  ¿Cuánto   vendimos\n en 2025?  ") == "¿Cuánto vendimos en 2025?"
    title = _title_from("x" * 200)
    assert len(title) == 80
    assert title.endswith("…")


def test_title_falls_back_when_empty():
    assert _title_from("   ") == "Consulta"


def test_parse_uuid_accepts_valid_and_rejects_invalid():
    value = uuid.uuid4()
    assert _parse_uuid(str(value)) == value
    assert _parse_uuid("") is None
    assert _parse_uuid("c1699999999") is None
    assert _parse_uuid(None) is None


def test_trace_payload_caps_rows():
    rows = [{"id": index} for index in range(MAX_STORED_ROWS + 10)]
    payload = _trace_payload(
        {
            "tabla": {
                "columnas": ["id"],
                "filas": rows,
                "num_filas": len(rows),
                "truncado": False,
            }
        }
    )
    assert len(payload["filas"]) == MAX_STORED_ROWS
    assert payload["truncado"] is True
    assert payload["num_filas"] == len(rows)


def test_trace_payload_without_table_is_empty():
    assert _trace_payload({"herramienta": "listar_tablas", "tabla": None}) == {}
    assert _trace_payload({"herramienta": "listar_tablas"}) == {}
