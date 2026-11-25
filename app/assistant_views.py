"""Views for the in-ERP MCP data assistant."""

from __future__ import annotations

import json
import logging

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django_otp.decorators import otp_required

from app.services.asistente_history_service import (
    ConversacionNoEncontrada,
    load_history,
    resolve_conversation,
    save_assistant_message,
    save_error_message,
    save_user_message,
)
from app.services.mcp_chat_service import (
    ChatConfigurationError,
    ChatConnectionError,
    ChatModelError,
    ChatServiceError,
    estado_servicio,
    modelo_activo,
    preguntar,
)

logger = logging.getLogger(__name__)

RATE_LIMIT_REQUESTS = 30
RATE_LIMIT_WINDOW_SECONDS = 600


def _rate_key(user_id: int) -> str:
    return f"asistente:mcp:rate:{user_id}"


def _rate_limited(user_id: int) -> bool:
    key = _rate_key(user_id)
    try:
        current = cache.get(key, 0)
        if current >= RATE_LIMIT_REQUESTS:
            return True
        if current == 0:
            cache.set(key, 1, RATE_LIMIT_WINDOW_SECONDS)
        else:
            cache.incr(key)
        return False
    except Exception:
        # A cache outage must not take the assistant down.
        return False


def _retry_after_seconds(user_id: int) -> int:
    """Seconds until the rate-limit window resets (django-redis exposes ttl)."""
    ttl = getattr(cache, "ttl", None)
    if callable(ttl):
        try:
            remaining = ttl(_rate_key(user_id))
            if isinstance(remaining, int) and remaining > 0:
                return remaining
        except Exception:
            pass
    return RATE_LIMIT_WINDOW_SECONDS


def _safe_reverse(name: str) -> str | None:
    try:
        return reverse(name)
    except NoReverseMatch:
        return None


def _error(
    status: int,
    codigo: str,
    mensaje: str,
    *,
    reintentable: bool = False,
    detalle: str | None = None,
    accion: dict | None = None,
    reintentar_en: int | None = None,
) -> JsonResponse:
    """Uniform error payload for the chat UI.

    ``error`` is plain language for the person using the ERP; ``detalle`` keeps
    the technical cause (env vars, commands) for whoever administers it, and the
    UI shows it folded away. ``reintentable`` tells the UI whether retrying can
    help; ``accion`` is an optional link (label + url) that fixes the cause.
    """
    payload: dict = {"error": mensaje, "codigo": codigo, "reintentable": reintentable}
    if detalle:
        payload["detalle"] = detalle
    if accion and accion.get("url"):
        payload["accion"] = accion
    if reintentar_en:
        payload["reintentar_en"] = reintentar_en
    response = JsonResponse(payload, status=status)
    if reintentar_en:
        response["Retry-After"] = str(reintentar_en)
    return response


@login_required
@otp_required
@staff_member_required
def asistente_view(request):
    context = {
        **admin.site.each_context(request),
        "title": "Asistente de datos",
        "subtitle": "Consultas MCP de solo lectura",
        "estado_mcp": estado_servicio(),
        "modelo_ia": modelo_activo(),
        "sugerencias": [
            {
                "titulo": "Cartera vencida",
                "consulta": "¿Qué clientes me deben más y cuánto está vencido a más de 90 días?",
                "tipo": "Cartera",
            },
            {
                "titulo": "Cierre de ventas",
                "consulta": "Dame las ventas del mes actual por producto y moneda.",
                "tipo": "Ventas",
            },
            {
                "titulo": "Gastos por categoría",
                "consulta": "Compara los gastos por categoría de este año contra el año pasado.",
                "tipo": "Gastos",
            },
            {
                "titulo": "Compras por productor",
                "consulta": "¿Cuánto compramos a cada productor este año?",
                "tipo": "Compras",
            },
            {
                "titulo": "Saldos por banco",
                "consulta": "Muéstrame los saldos iniciales y finales por banco del último trimestre.",
                "tipo": "Bancos",
            },
            {
                "titulo": "Pagos recientes",
                "consulta": "¿Qué pagos recibimos en los últimos 30 días?",
                "tipo": "Cobranza",
            },
        ],
    }
    return render(request, "asistente/chat.html", context)


@require_POST
def asistente_chat_api(request):
    if not request.user.is_authenticated:
        return _error(
            401,
            "sesion_expirada",
            "Tu sesión expiró. Inicia sesión de nuevo; tu pregunta seguirá en pantalla.",
            accion={
                "etiqueta": "Iniciar sesión",
                "url": _safe_reverse("two_factor:login"),
                "nueva_pestana": True,
            },
        )
    if not request.user.is_staff:
        return _error(
            403,
            "sin_permiso",
            "Tu usuario no tiene acceso al asistente. Pide a un administrador que te lo habilite.",
        )
    if not request.user.is_verified():
        return _error(
            403,
            "requiere_2fa",
            "Para usar el asistente necesitas activar la verificación en dos pasos.",
            accion={"etiqueta": "Activar verificación", "url": _safe_reverse("two_factor:setup")},
        )
    if _rate_limited(request.user.pk):
        return _error(
            429,
            "limite_consultas",
            "Hiciste muchas preguntas seguidas. Podrás volver a preguntar cuando termine la cuenta regresiva.",
            reintentable=True,
            reintentar_en=_retry_after_seconds(request.user.pk),
        )

    try:
        payload = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = None

    if not isinstance(payload, dict):
        return _error(
            400,
            "solicitud_invalida",
            "No pude leer la consulta. Recarga la página e intenta de nuevo.",
        )

    message = payload.get("mensaje")
    if not isinstance(message, str) or not message.strip():
        return _error(400, "consulta_vacia", "Escribe una pregunta antes de enviarla.")

    try:
        conversation = resolve_conversation(
            request.user, payload.get("conversacion_id"), message
        )
        history = load_history(conversation)
        save_user_message(conversation, message)
    except ConversacionNoEncontrada as exc:
        return _error(
            404,
            "conversacion_no_encontrada",
            "Esa conversación ya no está disponible. Empieza una consulta nueva.",
            detalle=str(exc),
        )
    except Exception:
        logger.exception("No se pudo preparar la conversación del asistente")
        return _error(
            500,
            "error_guardado",
            "No pude guardar la conversación. Intenta de nuevo.",
            reintentable=True,
        )

    try:
        result = preguntar(message, history)
    except ChatConfigurationError as exc:
        save_error_message(conversation, str(exc))
        return _error(
            503,
            "no_configurado",
            "El asistente todavía no está listo en este servidor. Avisa al administrador del sistema.",
            detalle=str(exc),
        )
    except ChatConnectionError as exc:
        save_error_message(conversation, str(exc))
        return _error(
            502,
            "sin_conexion_datos",
            "No pude conectarme con el servicio de reportes. Intenta de nuevo en un momento.",
            reintentable=True,
            detalle=str(exc),
        )
    except ChatModelError as exc:
        save_error_message(conversation, str(exc))
        return _error(
            502,
            "ia_no_disponible",
            "El servicio de IA no respondió. Intenta de nuevo en un momento.",
            reintentable=True,
            detalle=str(exc),
        )
    except ChatServiceError as exc:
        save_error_message(conversation, str(exc))
        # The service's validation messages are already written for the user.
        return _error(400, "consulta_invalida", str(exc))
    except Exception:
        logger.exception("Error no controlado en el asistente MCP")
        save_error_message(conversation, "Error no controlado en el asistente MCP")
        return _error(
            500,
            "error_inesperado",
            "Ocurrió un error inesperado al consultar al asistente. Intenta de nuevo.",
            reintentable=True,
        )

    try:
        save_assistant_message(conversation, result)
    except Exception:
        logger.exception("No se pudo guardar la respuesta del asistente")

    meta = result.get("meta", {})
    logger.info(
        "Asistente MCP user=%s conversacion=%s costo_usd=%s tokens=%s herramientas=%s",
        request.user.pk,
        conversation.pk,
        meta.get("costo_estimado_usd"),
        meta.get("tokens_total"),
        meta.get("herramientas_usadas"),
    )
    result["conversacion_id"] = str(conversation.pk)
    result["titulo"] = conversation.titulo
    # Fecha de corte de los datos en la zona del ERP (no el reloj del navegador):
    # la UI la muestra como "saldos al ..." y la conserva al reabrir.
    result.setdefault("meta", {})["consultado_en"] = timezone.localdate().isoformat()
    return JsonResponse(result, json_dumps_params={"ensure_ascii": False})
