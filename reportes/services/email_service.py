"""
Servicio de envío de correos electrónicos para reportes ejecutivos.
Usa django.core.mail.EmailMultiAlternatives para enviar versión HTML + texto plano.
"""

from __future__ import annotations

import json
import logging
import smtplib
import socket

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def enviar_reporte_ejecutivo(
    reporte,  # ReporteEjecutivo model instance
    destinatarios: list[str],
    asunto: str | None = None,
) -> list[str]:
    """
    Envía el reporte ejecutivo por correo a la lista de destinatarios.

    Args:
        reporte: instancia de ReporteEjecutivo con los datos ya generados.
        destinatarios: lista de strings de correo electrónico.
        asunto: asunto personalizado (usa el título del reporte por defecto).

    Returns:
        Lista de correos a los que se envió exitosamente.

    Raises:
        RuntimeError: si no hay destinatarios activos o el envío falla.
    """
    if not destinatarios:
        raise RuntimeError("No hay destinatarios para enviar el reporte.")

    subject = asunto or f"Resumen Ejecutivo Financiero — {reporte.titulo}"

    # Parsear datos para la plantilla
    try:
        datos_financieros = json.loads(reporte.destinatarios_enviados or "{}")
    except (json.JSONDecodeError, AttributeError):
        datos_financieros = {}

    # Parsear resumen IA
    try:
        resumen_data = json.loads(reporte.resumen_ia)
    except (json.JSONDecodeError, TypeError):
        resumen_data = {
            "resumen_ejecutivo": reporte.resumen_ia or "",
            "alertas": [],
            "recomendaciones": [],
            "kpis": {},
        }

    context = {
        "reporte": reporte,
        "resumen_data": resumen_data,
        "site_name": getattr(settings, "JAZZMIN_SETTINGS", {}).get("site_title", "Sistema ERP"),
    }

    html_content = render_to_string("reportes/executive_summary_email.html", context)
    text_content = _html_to_text(resumen_data)

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@empresa.com")
    smtp_target = f"{getattr(settings, 'EMAIL_HOST', 'localhost')}:{getattr(settings, 'EMAIL_PORT', '')}"
    smtp_timeout = getattr(settings, "EMAIL_TIMEOUT", None)

    enviados = []
    errores = []

    connection = get_connection(fail_silently=False)

    try:
        connection.open()
    except smtplib.SMTPAuthenticationError as exc:
        raise RuntimeError(
            "El servidor SMTP rechazó la autenticación. "
            "Revisa EMAIL_HOST_USER y EMAIL_HOST_PASSWORD. "
            "Si usas Gmail, utiliza un App Password vigente."
        ) from exc
    except (socket.timeout, TimeoutError) as exc:
        raise RuntimeError(
            f"No se pudo conectar al servidor SMTP {smtp_target} dentro de {smtp_timeout}s. "
            "El proveedor de hosting probablemente está bloqueando la salida SMTP "
            "o el servidor no es alcanzable desde el contenedor."
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            f"No se pudo abrir conexión con el servidor SMTP {smtp_target}: {exc}"
        ) from exc

    try:
        for correo in destinatarios:
            try:
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=from_email,
                    to=[correo],
                    connection=connection,
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()
                enviados.append(correo)
                logger.info("Reporte enviado a %s", correo)
            except Exception as exc:
                logger.error("Error al enviar reporte a %s: %s", correo, exc, exc_info=True)
                errores.append(f"{correo}: {exc}")
    finally:
        try:
            connection.close()
        except Exception:
            logger.warning("No se pudo cerrar limpiamente la conexión SMTP.", exc_info=True)

    if errores and not enviados:
        raise RuntimeError(
            "El reporte no pudo enviarse a ningún destinatario: " + "; ".join(errores)
        )

    if errores:
        logger.warning("Algunos envíos fallaron: %s", "; ".join(errores))

    return enviados


def _html_to_text(resumen_data: dict) -> str:
    """Genera versión de texto plano del resumen para clientes de correo sin HTML."""
    lines = []
    lines.append("=== RESUMEN EJECUTIVO FINANCIERO ===\n")

    resumen = resumen_data.get("resumen_ejecutivo", "")
    if resumen:
        lines.append(resumen)
        lines.append("")

    alertas = resumen_data.get("alertas", [])
    if alertas:
        lines.append("ALERTAS:")
        for a in alertas:
            lines.append(f"  ⚠ {a}")
        lines.append("")

    recomendaciones = resumen_data.get("recomendaciones", [])
    if recomendaciones:
        lines.append("RECOMENDACIONES:")
        for r in recomendaciones:
            lines.append(f"  → {r}")
        lines.append("")

    kpis = resumen_data.get("kpis", {})
    semaforo = kpis.get("semaforo_financiero", "")
    if semaforo:
        lines.append(f"Estado financiero: {semaforo.upper()}")

    prioridad = kpis.get("prioridad", "")
    if prioridad:
        lines.append(f"Prioridad: {prioridad}")

    return "\n".join(lines)
