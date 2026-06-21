"""
Servicio de programacion de envios automaticos de reportes por WhatsApp.
Determina que reportes deben enviarse segun la configuracion y los procesa.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from whatsapp.models import ConfiguracionWhatsApp

logger = logging.getLogger(__name__)


def debe_ejecutarse_hoy(config: "ConfiguracionWhatsApp", fecha: date | None = None) -> bool:
    """
    Determina si una configuracion debe ejecutar su envio en la fecha dada.

    Args:
        config: ConfiguracionWhatsApp a evaluar.
        fecha: Fecha de referencia (default: hoy).

    Returns:
        True si corresponde envio hoy.
    """
    if not config.activo:
        return False

    hoy = fecha or date.today()

    if config.frecuencia_envio == config.FrecuenciaReporte.DIARIO:
        return True

    if config.frecuencia_envio == config.FrecuenciaReporte.SEMANAL:
        # 1=Lunes, 7=Domingo (ISO weekday: 1=Lunes, 7=Domingo)
        return hoy.isoweekday() == config.dia_semana

    if config.frecuencia_envio == config.FrecuenciaReporte.MENSUAL:
        dia = min(config.dia_mes, 28)
        return hoy.day == dia

    return False


def calcular_proxima_ejecucion(config: "ConfiguracionWhatsApp", desde: datetime | None = None) -> datetime:
    """
    Calcula la proxima fecha/hora de ejecucion para una configuracion.

    Args:
        config: ConfiguracionWhatsApp.
        desde: Fecha/hora de referencia (default: ahora).

    Returns:
        Datetime de la proxima ejecucion programada.
    """
    ahora = desde or timezone.now()
    hora = config.hora_envio
    hoy = ahora.date()

    hora_ejecucion = datetime.combine(hoy, hora, tzinfo=timezone.get_current_timezone())

    if config.frecuencia_envio == config.FrecuenciaReporte.DIARIO:
        if ahora >= hora_ejecucion:
            return hora_ejecucion + timedelta(days=1)
        return hora_ejecucion

    if config.frecuencia_envio == config.FrecuenciaReporte.SEMANAL:
        dia_actual = hoy.isoweekday()
        dias_hasta = (config.dia_semana - dia_actual) % 7
        if dias_hasta == 0 and ahora >= hora_ejecucion:
            dias_hasta = 7
        proxima_fecha = hoy + timedelta(days=dias_hasta)
        return datetime.combine(proxima_fecha, hora, tzinfo=timezone.get_current_timezone())

    if config.frecuencia_envio == config.FrecuenciaReporte.MENSUAL:
        dia = min(config.dia_mes, 28)
        proxima_fecha = hoy.replace(day=dia)

        if proxima_fecha <= hoy:
            if proxima_fecha.month == 12:
                proxima_fecha = proxima_fecha.replace(year=proxima_fecha.year + 1, month=1)
            else:
                proxima_fecha = proxima_fecha.replace(month=proxima_fecha.month + 1)

        return datetime.combine(proxima_fecha, hora, tzinfo=timezone.get_current_timezone())

    return ahora + timedelta(days=1)


def procesar_envios_pendientes() -> dict:
    """
    Revisa todas las configuraciones activas y envia reportes segun corresponda.

    Returns:
        Diccionario con resumen de la ejecucion.
    """
    from reportes.models import ConfiguracionReporte, ReporteEjecutivo
    from whatsapp.models import ConfiguracionWhatsApp, ProgramacionEnvio
    from whatsapp.services.whatsapp_notification import enviar_reporte_whatsapp

    resultado = {
        "configuraciones_evaluadas": 0,
        "reportes_generados": 0,
        "reportes_enviados": 0,
        "errores": 0,
        "detalles": [],
    }

    configs = ConfiguracionWhatsApp.objects.filter(
        activo=True,
        instancia__activo=True,
        enviar_reportes=True,
    ).exclude(frecuencia_envio="manual")

    for config in configs:
        resultado["configuraciones_evaluadas"] += 1

        if not debe_ejecutarse_hoy(config):
            continue

        try:
            config_reporte = ConfiguracionReporte.objects.filter(activo=True).first()
            if not config_reporte:
                logger.warning("No hay ConfiguracionReporte activa. Saltando configuracion WhatsApp %s", config)
                continue

            # Obtener fechas del periodo
            from reportes.admin import _get_periodo_dates
            try:
                fecha_inicio, fecha_fin = _get_periodo_dates(config_reporte)
            except Exception:
                from datetime import date as dt_date
                hoy = dt_date.today()
                fecha_inicio = hoy.replace(day=1)
                if hoy.month == 12:
                    fecha_fin = hoy.replace(year=hoy.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    fecha_fin = hoy.replace(month=hoy.month + 1, day=1) - timedelta(days=1)

            # Registrar programacion
            programacion = ProgramacionEnvio.objects.create(
                configuracion=config,
                estado=ProgramacionEnvio.EstadoEjecucion.EN_EJECUCION,
                programado_para=timezone.now(),
            )

            # Generar reporte
            from reportes.admin import _crear_y_guardar_reporte
            from django.contrib.auth.models import User

            admin_user = User.objects.filter(is_superuser=True).first()
            reporte = _crear_y_guardar_reporte(config_reporte, admin_user, fecha_inicio, fecha_fin)
            resultado["reportes_generados"] += 1

            programacion.reporte = reporte

            # Enviar por WhatsApp
            enviados = enviar_reporte_whatsapp(reporte, config)
            resultado["reportes_enviados"] += 1

            programacion.estado = ProgramacionEnvio.EstadoEjecucion.COMPLETADO
            programacion.ejecutado_en = timezone.now()
            programacion.save()

            resultado["detalles"].append({
                "configuracion": str(config),
                "reporte": reporte.titulo,
                "destinatarios": len(enviados),
                "estado": "completado",
            })

        except Exception as exc:
            resultado["errores"] += 1
            logger.exception("Error al procesar envio para configuracion %s", config)
            if "programacion" in locals():
                programacion.estado = ProgramacionEnvio.EstadoEjecucion.ERROR
                programacion.error_detalle = str(exc)
                programacion.ejecutado_en = timezone.now()
                programacion.save()
            resultado["detalles"].append({
                "configuracion": str(config),
                "error": str(exc),
                "estado": "error",
            })

    return resultado
