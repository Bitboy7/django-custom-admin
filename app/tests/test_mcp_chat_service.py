from types import SimpleNamespace

from app.services.mcp_chat_service import (
    UsageStats,
    _assistant_model_config,
    _sanitize_gemini_parameters,
    _tool_schema,
    default_prices_for_model,
    estimate_cost_usd,
)


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


def test_usage_stats_accumulates_thinking_tokens():
    stats = UsageStats()
    stats.add(
        SimpleNamespace(
            usage_metadata={"input_tokens": 1000, "output_tokens": 200, "total_tokens": 1500}
        )
    )
    stats.add(
        SimpleNamespace(
            usage_metadata={"input_tokens": 500, "output_tokens": 100, "total_tokens": 600}
        )
    )
    assert stats.llamadas == 2
    assert stats.entrada == 1500
    assert stats.salida == 300
    assert stats.razonamiento == 300
    assert stats.total == 2100


def test_usage_stats_ignores_missing_metadata():
    stats = UsageStats()
    stats.add(SimpleNamespace(usage_metadata=None))
    assert stats.llamadas == 0


def test_estimate_cost_uses_model_prices():
    stats = UsageStats(llamadas=1, entrada=1_000_000, salida=1_000_000, razonamiento=500_000)
    assert estimate_cost_usd(stats, 0.20, 1.20) == round(0.20 + 1.5 * 1.20, 8)


def test_default_prices_for_model():
    assert default_prices_for_model("gpt-5.6-luna") == (0.20, 1.20)
    assert default_prices_for_model("gpt-5.6-terra") == (2.00, 12.00)
    assert default_prices_for_model("gemini-2.5-flash") == (0.30, 2.50)
    assert default_prices_for_model("desconocido") == (0.30, 2.50)


def test_assistant_model_config_prefers_openai_when_key_present(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.6-luna")
    assert _assistant_model_config() == ("openai", "gpt-5.6-luna")


def test_assistant_model_config_respects_explicit_provider(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "google")
    monkeypatch.setenv("GOOGLE_API_MODEL", "gemini-2.5-flash")
    assert _assistant_model_config() == ("google", "gemini-2.5-flash")


def test_openai_factory_builds_reasoning_model(monkeypatch):
    import gastos.services.invoice_recognition_service as invoice

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_REASONING_EFFORT", "low")
    llm = invoice.get_llm_model("gpt-5.6-luna", provider="openai")
    assert type(llm).__name__ == "ChatOpenAI"
    assert llm.model_name == "gpt-5.6-luna"
    assert llm.temperature == 1
    assert llm.model_kwargs.get("reasoning_effort") == "low"


def test_openai_factory_for_tools_forces_reasoning_none(monkeypatch):
    import gastos.services.invoice_recognition_service as invoice

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_REASONING_EFFORT", "low")
    llm = invoice.get_llm_model("gpt-5.6-luna", provider="openai", for_tools=True)
    assert llm.model_kwargs.get("reasoning_effort") == "none"
