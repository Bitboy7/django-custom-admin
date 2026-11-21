from types import SimpleNamespace

from app.services.mcp_chat_service import _sanitize_gemini_parameters, _tool_schema


def _tool(name="resumen_ventas", schema=None):
    return SimpleNamespace(
        name=name,
        description="Descripción",
        inputSchema=schema
        or {
            "type": "object",
            "properties": {"fecha_inicio": {"type": "string", "title": "Fecha Inicio"}},
            "required": ["fecha_inicio"],
        },
    )


def test_gemini_schema_uses_flat_declarations():
    schema = _tool_schema([_tool()], gemini=True)
    assert schema == [
        {
            "name": "resumen_ventas",
            "description": "Descripción",
            "parameters": {
                "type": "object",
                "properties": {"fecha_inicio": {"type": "string"}},
                "required": ["fecha_inicio"],
            },
        }
    ]


def test_openai_schema_keeps_function_wrapper():
    schema = _tool_schema([_tool()])
    assert schema[0]["type"] == "function"
    assert schema[0]["function"]["name"] == "resumen_ventas"


def test_gemini_optional_field_becomes_nullable():
    schema = {
        "type": "object",
        "properties": {
            "fecha_corte": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "default": None,
                "title": "Fecha Corte",
            }
        },
    }
    sanitized = _sanitize_gemini_parameters(schema)
    prop = sanitized["properties"]["fecha_corte"]
    assert prop["type"] == "string"
    assert prop["nullable"] is True
    assert "anyOf" not in prop
    assert "title" not in prop
    assert "default" not in prop


def test_gemini_schema_has_no_unsupported_keys():
    schema = {
        "type": "object",
        "properties": {
            "filtro": {
                "type": "object",
                "title": "Filtro",
                "default": {},
                "properties": {"valor": {"type": "string", "title": "Valor"}},
            },
            "lista": {"type": "array", "items": {"type": "string", "title": "Item"}},
        },
    }
    sanitized = _sanitize_gemini_parameters(schema)

    def keys(node):
        if isinstance(node, dict):
            for key, value in node.items():
                yield key
                yield from keys(value)
        elif isinstance(node, list):
            for item in node:
                yield from keys(item)

    found = set(keys(sanitized))
    assert not {"title", "default", "additionalProperties"} & found
