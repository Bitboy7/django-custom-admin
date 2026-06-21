"""
Manejador de webhooks entrantes desde Evolution API.
Recibe eventos de WhatsApp (mensajes, cambios de estado, etc.).

Las rutas son:
  - /whatsapp/webhook/                    -> webhook_receiver (generico)
  - /whatsapp/webhook/<instance_id>/     -> webhook_instance_receiver (por instancia)
"""

from __future__ import annotations

import json
import logging

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import DestinatarioWhatsApp, EvolutionInstance, MensajeWhatsApp, WebhookLog

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def webhook_instance_receiver(request: HttpRequest, instance_id: str) -> JsonResponse:
    """
    Recibe eventos de webhook de una instancia especifica de Evolution API.

    Evolution API envia POST con JSON:
    {
        "event": "messages.upsert",
        "instance": "ddcdaf19-...",
        "data": { ... }
    }
    """
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.warning("Webhook recibido con payload no-JSON para instancia %s", instance_id)
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    try:
        log_entry = WebhookLog.registrar(instance_id, payload)
        logger.info("Webhook registrado: id=%s, evento=%s, instancia=%s", log_entry.id, log_entry.tipo_evento, instance_id)

        if log_entry.tipo_evento == "messages.upsert" and log_entry.mensaje:
            procesar_mensaje_entrante(log_entry)

        return JsonResponse({"success": True, "log_id": log_entry.id})
    except Exception as exc:
        logger.exception("Error al procesar webhook de instancia %s", instance_id)
        return JsonResponse({"success": False, "error": str(exc)}, status=500)


@csrf_exempt
@require_POST
def webhook_receiver(request: HttpRequest) -> JsonResponse:
    """
    Recibe eventos de webhook generico (sin instance_id en la URL).
    El instance_id debe venir en el payload bajo el campo 'instance'.
    """
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    instance_id = payload.get("instance", "")

    try:
        log_entry = WebhookLog.registrar(instance_id, payload)
        logger.info("Webhook generico registrado: id=%s, evento=%s", log_entry.id, log_entry.tipo_evento)

        if log_entry.tipo_evento == "messages.upsert" and log_entry.mensaje:
            procesar_mensaje_entrante(log_entry)

        return JsonResponse({"success": True, "log_id": log_entry.id})
    except Exception as exc:
        logger.exception("Error al procesar webhook generico")
        return JsonResponse({"success": False, "error": str(exc)}, status=500)


def procesar_mensaje_entrante(log_entry: WebhookLog) -> None:
    """
    Procesa un mensaje entrante de WhatsApp.
    Aqui puedes agregar logica de respuesta automatica, comandos, etc.

    Por ahora solo registra el evento y lo marca como procesado.
    """
    telefono = log_entry.telefono_remitente
    mensaje = log_entry.mensaje

    if not telefono or not mensaje:
        return

    mensaje_lower = mensaje.strip().lower()

    respuestas_automaticas = {
        "hola": (
            "Hola! Este es el sistema automatizado de Agricola de la Costa San Luis. "
            "Para asistencia, contacta a tu gerente de cuenta."
        ),
        "reporte": (
            "Puedes solicitar reportes a traves del panel de administracion. "
            "Los reportes automaticos se envian segun la configuracion establecida."
        ),
        "ayuda": "Comandos disponibles: hola, reporte, ayuda.",
    }

    respuesta = None
    for clave, valor in respuestas_automaticas.items():
        if clave in mensaje_lower:
            respuesta = valor
            break

    if respuesta:
        from .services.evolution_api import get_evolution_service, EvolutionAPIError

        try:
            service = get_evolution_service(log_entry.instancia)
            service.send_text(telefono, respuesta)

            dest = DestinatarioWhatsApp.objects.filter(telefono=telefono).first()
            MensajeWhatsApp.objects.create(
                instancia=log_entry.instancia,
                destinatario=dest,
                tipo=MensajeWhatsApp.Tipo.MANUAL,
                contenido=respuesta,
                estado=MensajeWhatsApp.Estado.ENVIADO,
            )
            logger.info("Respuesta automatica enviada a %s", telefono)
        except EvolutionAPIError as exc:
            logger.error("Error al enviar respuesta automatica a %s: %s", telefono, exc)
        except Exception as exc:
            logger.exception("Error inesperado en respuesta automatica a %s", telefono)

    log_entry.procesado = True
    log_entry.save(update_fields=["procesado"])
