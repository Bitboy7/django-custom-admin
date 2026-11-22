"""Persistence for the in-ERP assistant conversations.

The server owns the conversation history: the browser only sends the
conversation id and the new question. Tool results are stored capped so a
single turn cannot grow the database without bound.
"""

from __future__ import annotations

import re
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction

from auditoria.models import (
    ConversacionAsistente,
    MensajeAsistente,
    TrazaHerramientaAsistente,
)
from app.services.mcp_chat_service import MAX_HISTORY_CHARS, MAX_HISTORY_MESSAGES

MAX_STORED_ROWS = 25
MAX_TITLE_CHARS = 80
MAX_ERROR_CHARS = 2000


class ConversacionNoEncontrada(Exception):
    """The conversation does not exist or belongs to another user."""


def _parse_uuid(raw: Any) -> uuid.UUID | None:
    if not raw:
        return None
    try:
        return uuid.UUID(str(raw))
    except (ValueError, AttributeError, TypeError):
        return None


def _title_from(question: str) -> str:
    title = re.sub(r"\s+", " ", (question or "").strip())
    if not title:
        return "Consulta"
    if len(title) <= MAX_TITLE_CHARS:
        return title
    return title[: MAX_TITLE_CHARS - 1].rstrip() + "…"


def resolve_conversation(
    user, conversation_id: Any, question: str
) -> ConversacionAsistente:
    """Load the user's conversation or create it (client-generated UUIDs allowed)."""
    parsed = _parse_uuid(conversation_id)
    if parsed is not None:
        existing = ConversacionAsistente.objects.filter(pk=parsed).first()
        if existing is not None:
            if existing.usuario_id != user.pk:
                raise ConversacionNoEncontrada(
                    "La conversación no existe o no tienes acceso a ella."
                )
            return existing

    return ConversacionAsistente.objects.create(
        id=parsed or uuid.uuid4(),
        usuario=user,
        titulo=_title_from(question),
    )


def load_history(
    conversation: ConversacionAsistente,
    limit: int = MAX_HISTORY_MESSAGES,
) -> list[dict[str, str]]:
    """Return the last usable turns, oldest first, for the language model."""
    messages = (
        conversation.mensajes.exclude(contenido="")
        .order_by("-orden")[:limit]
    )
    return [
        {"role": message.rol, "content": message.contenido[:MAX_HISTORY_CHARS]}
        for message in reversed(list(messages))
    ]


def _next_order(conversation: ConversacionAsistente) -> int:
    last = (
        conversation.mensajes.order_by("-orden")
        .values_list("orden", flat=True)
        .first()
    )
    return (last or 0) + 1


def _int(value: Any) -> int:
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def _decimal(value: Any) -> Decimal:
    try:
        return max(Decimal(str(value or 0)), Decimal("0"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _trace_payload(trace: dict[str, Any]) -> dict[str, Any]:
    table = trace.get("tabla")
    if not isinstance(table, dict):
        return {}
    rows = table.get("filas")
    if not isinstance(rows, list):
        rows = []
    truncated = bool(table.get("truncado")) or len(rows) > MAX_STORED_ROWS
    return {
        "columnas": table.get("columnas") or [],
        "filas": rows[:MAX_STORED_ROWS],
        "num_filas": _int(table.get("num_filas")) or len(rows),
        "truncado": truncated,
    }


def save_user_message(
    conversation: ConversacionAsistente, text: str
) -> MensajeAsistente:
    return MensajeAsistente.objects.create(
        conversacion=conversation,
        rol=MensajeAsistente.Rol.USUARIO,
        contenido=text,
        orden=_next_order(conversation),
    )


def save_assistant_message(
    conversation: ConversacionAsistente, result: dict[str, Any]
) -> MensajeAsistente:
    meta = result.get("meta") or {}
    traces = result.get("traza") or []
    with transaction.atomic():
        message = MensajeAsistente.objects.create(
            conversacion=conversation,
            rol=MensajeAsistente.Rol.ASISTENTE,
            contenido=result.get("respuesta") or "",
            orden=_next_order(conversation),
            modelo=str(meta.get("modelo") or "")[:80],
            tokens_entrada=_int(meta.get("tokens_entrada")),
            tokens_salida=_int(meta.get("tokens_salida")),
            tokens_razonamiento=_int(meta.get("tokens_razonamiento")),
            tokens_total=_int(meta.get("tokens_total")),
            costo_estimado_usd=_decimal(meta.get("costo_estimado_usd")),
            duracion_ms=_int(meta.get("duracion_ms")),
        )
        TrazaHerramientaAsistente.objects.bulk_create(
            [
                TrazaHerramientaAsistente(
                    mensaje=message,
                    herramienta=str(trace.get("herramienta") or "")[:80],
                    argumentos=trace.get("argumentos") or {},
                    num_filas=_int(trace.get("filas")),
                    columnas=trace.get("columnas") or [],
                    duracion_ms=_int(trace.get("duracion_ms")),
                    error=str(trace.get("error") or "")[:MAX_ERROR_CHARS],
                    resultado=_trace_payload(trace),
                )
                for trace in traces
                if isinstance(trace, dict)
            ]
        )
        conversation.save(update_fields=["actualizada_en"])
    return message


def save_error_message(
    conversation: ConversacionAsistente, error: str
) -> MensajeAsistente:
    message = MensajeAsistente.objects.create(
        conversacion=conversation,
        rol=MensajeAsistente.Rol.ASISTENTE,
        contenido="",
        orden=_next_order(conversation),
        error=(error or "Error desconocido")[:MAX_ERROR_CHARS],
    )
    conversation.save(update_fields=["actualizada_en"])
    return message
