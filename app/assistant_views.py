"""Views for the in-ERP MCP data assistant."""

from __future__ import annotations

import json
import logging
import os

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django_otp.decorators import otp_required

from app.services.mcp_chat_service import (
    ChatConfigurationError,
    ChatConnectionError,
    ChatModelError,
    ChatServiceError,
    estado_servicio,
    preguntar,
)

logger = logging.getLogger(__name__)

RATE_LIMIT_REQUESTS = 30
RATE_LIMIT_WINDOW_SECONDS = 600


def _rate_limited(user_id: int) -> bool:
    key = f"asistente:mcp:rate:{user_id}"
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


@login_required
@otp_required
@staff_member_required
def asistente_view(request):
    context = {
        **admin.site.each_context(request),
        "title": "Asistente de datos",
        "subtitle": "Consultas MCP de solo lectura",
        "estado_mcp": estado_servicio(),
        "modelo_ia": os.getenv("GOOGLE_API_MODEL")
        or os.getenv("OPENROUTER_API_MODEL")
        or "modelo predeterminado",
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
        return JsonResponse(
            {"error": "Tu sesión expiró. Vuelve a iniciar sesión."}, status=401
        )
    if not request.user.is_staff:
        return JsonResponse(
            {"error": "No tienes permiso para usar el asistente."}, status=403
        )
    if not request.user.is_verified():
        return JsonResponse(
            {"error": "Completa la verificación en dos pasos para usar el asistente."},
            status=403,
        )
    if _rate_limited(request.user.pk):
        return JsonResponse(
            {"error": "Demasiadas consultas seguidas. Espera unos minutos e intenta de nuevo."},
            status=429,
        )

    try:
        payload = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "La solicitud no es válida."}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({"error": "La solicitud no es válida."}, status=400)

    message = payload.get("mensaje")
    if not isinstance(message, str) or not message.strip():
        return JsonResponse({"error": "Escribe una consulta para el asistente."}, status=400)

    try:
        result = preguntar(message, payload.get("historial"))
    except ChatConfigurationError as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except ChatConnectionError as exc:
        return JsonResponse({"error": str(exc)}, status=502)
    except ChatModelError as exc:
        return JsonResponse({"error": str(exc)}, status=502)
    except ChatServiceError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except Exception:
        logger.exception("Error no controlado en el asistente MCP")
        return JsonResponse(
            {"error": "Ocurrió un error al consultar al asistente. Intenta de nuevo."},
            status=500,
        )

    return JsonResponse(result, json_dumps_params={"ensure_ascii": False})
