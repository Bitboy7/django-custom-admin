"""Read-only MCP chat client used by the in-ERP data assistant.

The assistant is a thin orchestration layer: the language model chooses MCP tools,
the tools are executed against the standalone ``mcp_server`` package over its
streamable HTTP transport, and every result is kept as an auditable trace.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 12
MAX_HISTORY_CHARS = 2400
MAX_TOOL_ROWS_FOR_LLM = 40
MAX_TOOL_CHARS_FOR_LLM = 14000

SYSTEM_PROMPT = """\
Eres Costa, el asistente de datos de Agrícola de la Costa San Luis, una empresa agrícola \
de Sinaloa, México. Hablas español (es-MX), con un tono preciso, cálido y directo, como un \
agrónomo experimentado que también domina las finanzas.

Hoy es {today}.

TU TRABAJO
- Responder preguntas sobre ventas, cartera, pagos, gastos, compras y saldos usando las \
herramientas del servidor MCP de solo lectura.
- Los datos se consultan primero con las herramientas curadas (resumen_financiero, \
resumen_ventas, ventas_por_cliente, cartera_vencida, resumen_gastos, compras_por_productor, \
pagos_recientes, saldo_mensual, etc.). Usa consultar_sql solo cuando ninguna herramienta curada \
cubra la pregunta.
- Antes de consultar_sql, si no conoces el esquema, usa listar_tablas o describir_tabla.

REGLAS DE DATOS
- Solo lectura. Nunca inventes cifras, clientes, folios ni fechas.
- Las fechas se envían como YYYY-MM-DD.
- Los montos vienen agrupados por moneda. No sumes MXN y USD; dilo explícitamente.
- El saldo pendiente es monto - monto_pagado.
- Si una herramienta devuelve un error, corrige la consulta o explica qué falta.
- Si no hay datos, dilo con claridad y sugiere un rango o filtro distinto.
- Cita el nombre de la herramienta que usaste entre paréntesis cuando aporte confianza.

FORMATO
- Responde en 2 a 5 oraciones y, si ayuda, hasta 4 viñetas cortas.
- No uses tablas Markdown: la interfaz muestra las tablas de datos citadas al costado.
- Destaca cifras clave en **negritas**. No uses encabezados ni bloques de código.
- Si la pregunta es ambigua, elige el rango más razonable, dilo en una frase y responde.
"""


class ChatServiceError(Exception):
    """Base error with a user-safe message."""


class ChatConfigurationError(ChatServiceError):
    pass


class ChatConnectionError(ChatServiceError):
    pass


class ChatModelError(ChatServiceError):
    pass


@dataclass
class ToolTrace:
    herramienta: str
    argumentos: dict[str, Any]
    duracion_ms: int
    filas: int = 0
    columnas: list[str] = field(default_factory=list)
    tabla: dict[str, Any] | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "herramienta": self.herramienta,
            "argumentos": self.argumentos,
            "duracion_ms": self.duracion_ms,
            "filas": self.filas,
            "columnas": self.columnas,
            "tabla": self.tabla,
            "error": self.error,
        }


def mcp_url() -> str:
    url = os.getenv("MCP_HTTP_URL")
    if url:
        return url
    host = os.getenv("MCP_HTTP_HOST", "127.0.0.1")
    port = os.getenv("MCP_HTTP_PORT", "8765")
    path = os.getenv("MCP_HTTP_PATH", "/mcp")
    if not path.startswith("/"):
        path = "/" + path
    return f"http://{host}:{port}{path}"


def mcp_headers() -> dict[str, str]:
    token = (os.getenv("MCP_HTTP_TOKEN") or "").strip()
    if token:
        return {"Authorization": f"Bearer {token}"}
    allow_no_auth = (os.getenv("MCP_ALLOW_NO_AUTH") or "").strip().lower() in {"1", "true", "yes"}
    if allow_no_auth:
        return {}
    raise ChatConfigurationError(
        "Falta MCP_HTTP_TOKEN. Configúralo en el .env o habilita MCP_ALLOW_NO_AUTH "
        "solo en una red privada."
    )


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            text = getattr(block, "text", None)
            if text is not None:
                parts.append(str(text))
            else:
                parts.append(str(block))
        return "\n".join(parts)
    return "" if content is None else str(content)


def _normalize_table(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    if "columnas" not in payload or "filas" not in payload:
        return None
    rows = payload.get("filas")
    if not isinstance(rows, list):
        return None
    columns = payload.get("columnas") or []
    if not isinstance(columns, list):
        columns = list(columns)
    return {
        "columnas": [str(column) for column in columns],
        "filas": rows,
        "num_filas": payload.get("num_filas", len(rows)),
        "truncado": bool(payload.get("truncado")),
    }


def _unwrap_result(result: Any) -> Any:
    structured = getattr(result, "structuredContent", None)
    if structured:
        if isinstance(structured, dict) and set(structured.keys()) == {"result"}:
            return structured["result"]
        return structured

    texts: list[str] = []
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text is not None:
            texts.append(str(text))
    raw = "\n".join(texts).strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {"texto": raw}


def _compact_for_llm(payload: Any) -> str:
    """Serialize a tool result for the model without blowing the context window."""
    if isinstance(payload, dict) and "columnas" in payload and "filas" in payload:
        rows = payload.get("filas") or []
        compact = {
            "columnas": payload.get("columnas"),
            "filas": rows[:MAX_TOOL_ROWS_FOR_LLM],
            "num_filas": payload.get("num_filas", len(rows)),
            "truncado": bool(payload.get("truncado")),
        }
        if len(rows) > MAX_TOOL_ROWS_FOR_LLM:
            compact["nota"] = (
                f"Se muestran {MAX_TOOL_ROWS_FOR_LLM} de {len(rows)} filas; "
                "la interfaz muestra el resto."
            )
        return json.dumps(compact, ensure_ascii=False, default=str)

    raw = json.dumps(payload, ensure_ascii=False, default=str)
    if len(raw) > MAX_TOOL_CHARS_FOR_LLM:
        raw = raw[:MAX_TOOL_CHARS_FOR_LLM] + "…"
    return raw


_GEMINI_UNSUPPORTED_SCHEMA_KEYS = frozenset(
    {
        "$schema",
        "$defs",
        "definitions",
        "title",
        "default",
        "examples",
        "const",
        "additionalProperties",
        "patternProperties",
        "oneOf",
        "allOf",
    }
)


def _sanitize_gemini_parameters(schema: Any) -> Any:
    """Drop JSON Schema keys the Gemini SDK ignores and flatten nullable anyOf."""
    if not isinstance(schema, dict):
        return schema

    any_of = schema.get("anyOf")
    if isinstance(any_of, list):
        non_null = [
            option
            for option in any_of
            if not (isinstance(option, dict) and option.get("type") == "null")
        ]
        base = {key: value for key, value in schema.items() if key != "anyOf"}
        if len(non_null) == 1 and isinstance(non_null[0], dict):
            merged = _sanitize_gemini_parameters({**base, **non_null[0]})
            merged["nullable"] = True
            return merged

    cleaned: dict[str, Any] = {}
    for key, value in schema.items():
        if key in _GEMINI_UNSUPPORTED_SCHEMA_KEYS:
            continue
        if key == "properties" and isinstance(value, dict):
            cleaned[key] = {
                name: _sanitize_gemini_parameters(definition)
                for name, definition in value.items()
            }
        elif key == "items":
            cleaned[key] = _sanitize_gemini_parameters(value)
        else:
            cleaned[key] = value
    return cleaned


def _tool_schema(tools: list[Any], *, gemini: bool = False) -> list[dict[str, Any]]:
    """Convert MCP tools to the schema format expected by the chat model.

    Gemini's ``bind_tools`` (langchain-google-genai 1.x) does not understand the
    OpenAI ``{"type": "function", "function": ...}`` wrapper and silently builds
    declarations with an empty name. Gemini gets the flat declaration instead.
    """
    schemas: list[dict[str, Any]] = []
    for tool in tools:
        parameters = getattr(tool, "inputSchema", None) or {
            "type": "object",
            "properties": {},
        }
        name = str(tool.name)
        description = getattr(tool, "description", "") or ""
        if gemini:
            schemas.append(
                {
                    "name": name,
                    "description": description,
                    "parameters": _sanitize_gemini_parameters(parameters),
                }
            )
        else:
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description,
                        "parameters": parameters,
                    },
                }
            )
    return schemas


def _clean_history(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    cleaned: list[dict[str, str]] = []
    for item in raw[-MAX_HISTORY_MESSAGES:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            continue
        content = content.strip()
        if not content:
            continue
        cleaned.append({"role": role, "content": content[:MAX_HISTORY_CHARS]})
    return cleaned


def _fallback_answer(traces: list[ToolTrace]) -> str:
    successful = [trace for trace in traces if not trace.error]
    if not successful:
        return (
            "No pude obtener datos del servidor MCP. Revisa que el servicio esté activo y "
            "vuelve a intentarlo."
        )
    last = successful[-1]
    return (
        f"Consulté {last.herramienta} y obtuve {last.filas} fila(s). "
        "Revisa la tabla de datos citados al costado para el detalle."
    )


async def _ask_async(question: str, history: list[dict[str, str]]) -> dict[str, Any]:
    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise ChatConfigurationError(
            "Faltan dependencias del cliente MCP o de LangChain. "
            "Instala requirements-mcp.txt y requirements.txt."
        ) from exc

    from gastos.services.invoice_recognition_service import get_llm_model

    url = mcp_url()
    headers = mcp_headers()
    timeout_seconds = float(getattr(settings, "MCP_CHAT_TIMEOUT", 45))
    max_steps = int(getattr(settings, "MCP_CHAT_MAX_STEPS", 5))
    model_id = os.getenv("GOOGLE_API_MODEL") or os.getenv("OPENROUTER_API_MODEL")

    system = SystemMessage(
        content=SYSTEM_PROMPT.format(today=timezone.localdate().isoformat())
    )
    messages: list[Any] = [system]
    for item in history:
        if item["role"] == "user":
            messages.append(HumanMessage(content=item["content"]))
        else:
            messages.append(AIMessage(content=item["content"]))
    messages.append(HumanMessage(content=question))

    traces: list[ToolTrace] = []
    started = time.perf_counter()
    answer = ""

    timeout = timedelta(seconds=timeout_seconds)
    async with streamablehttp_client(url, headers=headers, timeout=timeout) as (
        read,
        write,
        _get_session_id,
    ):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            tools = list(getattr(listed, "tools", []) or [])
            if not tools:
                raise ChatConnectionError(
                    "El servidor MCP no expuso herramientas. Revisa su configuración."
                )

            try:
                llm = get_llm_model(model_id)
                try:
                    from langchain_google_genai import ChatGoogleGenerativeAI

                    gemini_model = isinstance(llm, ChatGoogleGenerativeAI)
                except ImportError:  # pragma: no cover - optional dependency
                    gemini_model = False
                bound = llm.bind_tools(_tool_schema(tools, gemini=gemini_model))
            except Exception as exc:
                logger.exception("No se pudo preparar el modelo de lenguaje")
                raise ChatModelError(
                    "No se pudo preparar el modelo de IA. Revisa GOOGLE_API_KEY u OPENROUTER_API_KEY."
                ) from exc

            for _step in range(max_steps):
                try:
                    response = await asyncio.to_thread(bound.invoke, messages)
                except Exception as exc:
                    logger.exception("Error al invocar el modelo de lenguaje")
                    text = str(exc)
                    if "429" in text or "quota" in text.lower() or "ResourceExhausted" in type(exc).__name__:
                        raise ChatModelError(
                            "La cuota de la API de IA está agotada. Revisa tu plan y facturación."
                        ) from exc
                    raise ChatModelError(
                        "El modelo de IA no respondió. Intenta de nuevo en un momento."
                    ) from exc

                messages.append(response)
                tool_calls = list(getattr(response, "tool_calls", None) or [])
                if not tool_calls:
                    answer = _content_text(response.content).strip()
                    break

                for call in tool_calls:
                    name = call.get("name") or ""
                    arguments = call.get("args") or {}
                    if not isinstance(arguments, dict):
                        arguments = {}
                    call_started = time.perf_counter()
                    trace = ToolTrace(
                        herramienta=name,
                        argumentos=arguments,
                        duracion_ms=0,
                    )
                    try:
                        result = await session.call_tool(
                            name,
                            arguments,
                            read_timeout_seconds=timeout,
                        )
                        payload = _unwrap_result(result)
                        if getattr(result, "isError", False):
                            message = payload.get("error") if isinstance(payload, dict) else None
                            trace.error = str(message or "La herramienta devolvió un error.")
                        elif isinstance(payload, dict) and payload.get("error"):
                            trace.error = str(payload["error"])
                        else:
                            table = _normalize_table(payload)
                            if table:
                                trace.tabla = table
                                trace.columnas = table["columnas"]
                                trace.filas = int(table.get("num_filas") or 0)
                        llm_payload = payload
                        if trace.error:
                            llm_payload = {"error": trace.error}
                    except Exception as exc:
                        logger.warning("Fallo la herramienta MCP %s: %s", name, exc)
                        trace.error = "No se pudo ejecutar la consulta en el servidor MCP."
                        llm_payload = {"error": trace.error}
                    finally:
                        trace.duracion_ms = int(
                            (time.perf_counter() - call_started) * 1000
                        )

                    traces.append(trace)
                    messages.append(
                        ToolMessage(
                            content=_compact_for_llm(llm_payload),
                            tool_call_id=call.get("id") or f"call_{name}_{len(traces)}",
                            name=name,
                        )
                    )
            else:
                # Tool budget exhausted: ask for a final answer without tools.
                try:
                    final = await asyncio.to_thread(llm.invoke, messages)
                    answer = _content_text(final.content).strip()
                except Exception:
                    logger.exception("Error al cerrar la conversación con el modelo")
                    answer = ""

    if not answer:
        answer = _fallback_answer(traces)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "respuesta": answer,
        "traza": [trace.as_dict() for trace in traces],
        "meta": {
            "modelo": model_id or "",
            "duracion_ms": elapsed_ms,
            "herramientas_usadas": len(traces),
            "servidor": url,
        },
    }


def preguntar(question: str, history: Any = None) -> dict[str, Any]:
    """Ask the MCP assistant a question. Safe to call from a synchronous view."""
    question = (question or "").strip()
    if not question:
        raise ChatServiceError("Escribe una consulta para el asistente.")
    if len(question) > 2000:
        raise ChatServiceError("La consulta es demasiado larga (máximo 2,000 caracteres).")

    clean_history = _clean_history(history)
    try:
        return asyncio.run(_ask_async(question, clean_history))
    except ChatServiceError:
        raise
    except OSError as exc:
        logger.exception("No se pudo abrir la conexión MCP")
        raise ChatConnectionError(
            "No se pudo conectar al servidor MCP. Inícialo con "
            "`python -m mcp_server --transport http` y verifica MCP_HTTP_TOKEN."
        ) from exc
    except Exception as exc:
        logger.exception("Error inesperado en el asistente MCP")
        text = str(exc).lower()
        if "401" in text or "unauthorized" in text:
            raise ChatConnectionError(
                "El servidor MCP rechazó el token (401). Verifica que MCP_HTTP_TOKEN sea el "
                "mismo en el .env y reinicia el servidor MCP."
            ) from exc
        if "connect" in text or "refused" in text or "timeout" in text:
            raise ChatConnectionError(
                "No se pudo conectar al servidor MCP. Verifica que esté activo y que la URL "
                "MCP_HTTP_URL sea correcta."
            ) from exc
        raise ChatServiceError(
            "Ocurrió un error al consultar al asistente. Intenta de nuevo."
        ) from exc


def estado_servicio() -> dict[str, Any]:
    """Cheap configuration-only status for the page (no network call)."""
    try:
        headers = mcp_headers()
    except ChatConfigurationError as exc:
        return {"configurado": False, "detalle": str(exc), "url": mcp_url()}
    return {
        "configurado": True,
        "detalle": "Servidor MCP de solo lectura configurado.",
        "url": mcp_url(),
        "autenticado": bool(headers.get("Authorization")),
    }
