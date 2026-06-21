"""
Servicio de notificaciones por WhatsApp.
Maneja el envio de reportes ejecutivos y alertas via WhatsApp.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.utils import timezone

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from reportes.models import ReporteEjecutivo
    from whatsapp.models import ConfiguracionWhatsApp, DestinatarioWhatsApp, EvolutionInstance

logger = logging.getLogger(__name__)


def formatear_reporte_whatsapp(reporte: "ReporteEjecutivo") -> str:
    """
    Formatea un ReporteEjecutivo como mensaje de WhatsApp.
    Usa el resumen de IA si esta disponible, o genera un resumen basico.
    """
    empresa = getattr(settings, "JAZZMIN_SETTINGS", {}).get("site_header", "Agrícola")

    lines = [
        f"*{empresa}*",
        f"Reporte: {reporte.titulo}",
        f"Periodo: {reporte.periodo_inicio.strftime('%d/%m/%Y')} — {reporte.periodo_fin.strftime('%d/%m/%Y')}",
        "",
    ]

    ventas_fmt = "${:,.2f}".format(float(reporte.total_ventas))
    gastos_fmt = "${:,.2f}".format(float(reporte.total_gastos))
    compras_fmt = "${:,.2f}".format(float(reporte.total_compras))
    balance_fmt = "${:,.2f}".format(float(reporte.margen_bruto))
    margen_fmt = "{:.1f}%".format(float(reporte.margen_porcentaje))

    lines.append("*KPIs Financieros:*")
    lines.append(f"Ventas: {ventas_fmt}")
    lines.append(f"Gastos: {gastos_fmt}")
    lines.append(f"Compras: {compras_fmt}")
    lines.append(f"Balance: {balance_fmt}")
    lines.append(f"Margen: {margen_fmt}")

    if reporte.resumen_ia:
        try:
            data = json.loads(reporte.resumen_ia)
            resumen = data.get("resumen_ejecutivo", "")
            alertas = data.get("alertas", [])
            recomendaciones = data.get("recomendaciones", [])
            kpis = data.get("kpis", {})
            semaforo = kpis.get("semaforo_financiero", "")

            if semaforo:
                emoji = {"verde": "🟢", "amarillo": "🟡", "rojo": "🔴"}.get(semaforo, "⚪")
                lines.append(f"\n{emoji} *Estado: {semaforo.upper()}*")

            if resumen:
                lines.append(f"\n*Resumen:*\n{resumen}")

            if alertas:
                lines.append("\n*Alertas:*")
                for a in alertas:
                    lines.append(f"⚠ {a}")

            if recomendaciones:
                lines.append("\n*Recomendaciones:*")
                for r in recomendaciones:
                    lines.append(f"→ {r}")
        except (json.JSONDecodeError, TypeError):
            pass

    return "\n".join(lines)


def formatear_alerta_cobranza(
    cliente_nombre: str,
    factura_numero: str,
    monto: str,
    vencimiento: str,
    dias_vencido: int = 0,
) -> str:
    """Formatea una alerta de cobranza como mensaje de WhatsApp."""
    empresa = getattr(settings, "JAZZMIN_SETTINGS", {}).get("site_header", "Agrícola")

    lines = [
        f"*{empresa} — Alerta de Cobranza*",
        "",
        f"Cliente: *{cliente_nombre}*",
        f"Factura: {factura_numero}",
        f"Monto: {monto}",
        f"Vencimiento: {vencimiento}",
    ]
    if dias_vencido > 0:
        lines.append(f"Vencida hace: {dias_vencido} dias")
    elif dias_vencido == 0:
        lines.append("Vence hoy")

    return "\n".join(lines)


def enviar_reporte_whatsapp(
    reporte: "ReporteEjecutivo",
    configuracion: "ConfiguracionWhatsApp",
) -> list[str]:
    """
    Envia un reporte ejecutivo por WhatsApp a los destinatarios configurados.

    Args:
        reporte: Instancia de ReporteEjecutivo con datos generados.
        configuracion: ConfiguracionWhatsApp con destinatarios e instancia.

    Returns:
        Lista de telefonos a los que se envio exitosamente.

    Raises:
        RuntimeError: Si no hay destinatarios o la instancia no esta activa.
    """
    from whatsapp.models import MensajeWhatsApp
    from whatsapp.services.evolution_api import EvolutionAPIError, get_evolution_service

    destinatarios = configuracion.destinatarios.filter(activo=True)
    if not destinatarios.exists():
        raise RuntimeError("No hay destinatarios WhatsApp activos.")

    if not configuracion.instancia.activo:
        raise RuntimeError(f"La instancia '{configuracion.instancia.nombre}' no esta activa.")

    mensaje_texto = formatear_reporte_whatsapp(reporte)
    service = get_evolution_service(configuracion.instancia)

    enviados = []
    errores = []

    for dest in destinatarios:
        try:
            result = service.send_text(dest.telefono, mensaje_texto)

            MensajeWhatsApp.objects.create(
                instancia=configuracion.instancia,
                destinatario=dest,
                tipo=MensajeWhatsApp.Tipo.REPORTE,
                contenido=mensaje_texto,
                estado=MensajeWhatsApp.Estado.ENVIADO,
                reporte=reporte,
                evolution_message_id=result.get("key", {}).get("id", ""),
            )
            enviados.append(dest.telefono)
            logger.info("Reporte WhatsApp enviado a %s (%s)", dest.nombre, dest.telefono)

        except EvolutionAPIError as exc:
            MensajeWhatsApp.objects.create(
                instancia=configuracion.instancia,
                destinatario=dest,
                tipo=MensajeWhatsApp.Tipo.REPORTE,
                contenido=mensaje_texto,
                estado=MensajeWhatsApp.Estado.ERROR,
                reporte=reporte,
                error_detalle=str(exc),
            )
            errores.append(f"{dest.telefono}: {exc}")
            logger.error("Error al enviar reporte WhatsApp a %s: %s", dest.telefono, exc)

    if errores and not enviados:
        raise RuntimeError("El reporte no pudo enviarse a ningun destinatario: " + "; ".join(errores))

    if errores:
        logger.warning("Algunos envios WhatsApp fallaron: %s", "; ".join(errores))

    return enviados


def enviar_mensaje_prueba(instance: "EvolutionInstance", telefono: str) -> tuple[bool, str]:
    """
    Envia un mensaje de prueba para verificar la conexion.

    Returns:
        (exito, mensaje_error_o_id)
    """
    from whatsapp.services.evolution_api import EvolutionAPIError, get_evolution_service

    try:
        service = get_evolution_service(instance)
        result = service.send_text(
            telefono,
            "Este es un mensaje de prueba desde el sistema ERP de Agrícola de la Costa San Luis. ✅",
        )
        msg_id = result.get("key", {}).get("id", "")
        return True, msg_id
    except EvolutionAPIError as exc:
        return False, str(exc)
