"""
Admin de Django para el módulo de Reportes Ejecutivos.

Proporciona:
  - ConfiguracionReporteAdmin: gestión de la configuración + acción para generar/enviar reporte
  - DestinatarioReporteAdmin: gestión de destinatarios
  - ReporteEjecutivoAdmin: historial de reportes (solo lectura) con vista de preview
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime

from django.contrib import admin, messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import ConfiguracionReporte, DestinatarioReporte, ReporteEjecutivo

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────── #
# Helpers                                                                        #
# ────────────────────────────────────────────────────────────────────────────── #


def _get_periodo_dates(config: ConfiguracionReporte) -> tuple[date, date]:
    """Devuelve (inicio, fin) según el período configurado."""
    from reportes.services.executive_summary_service import (
        get_periodo_anual_actual,
        get_periodo_mensual_actual,
        get_periodo_trimestral_actual,
    )

    mapping = {
        ConfiguracionReporte.Periodo.MENSUAL: get_periodo_mensual_actual,
        ConfiguracionReporte.Periodo.TRIMESTRAL: get_periodo_trimestral_actual,
        ConfiguracionReporte.Periodo.ANUAL: get_periodo_anual_actual,
    }
    fn = mapping.get(config.periodo_default, get_periodo_mensual_actual)
    return fn()


def _crear_y_guardar_reporte(config: ConfiguracionReporte, user, fecha_inicio: date, fecha_fin: date) -> ReporteEjecutivo:
    """
    Crea un registro ReporteEjecutivo, llama a la IA y lo guarda.
    """
    from django.conf import settings

    from reportes.services.executive_summary_service import generar_resumen_ejecutivo

    empresa_nombre = getattr(settings, "JAZZMIN_SETTINGS", {}).get("site_header", "Empresa")

    periodo_str = f"{fecha_inicio.strftime('%B %Y').capitalize()}"
    titulo = f"Resumen Ejecutivo — {periodo_str}"

    reporte = ReporteEjecutivo.objects.create(
        titulo=titulo,
        periodo_inicio=fecha_inicio,
        periodo_fin=fecha_fin,
        estado=ReporteEjecutivo.Estado.GENERANDO,
        generado_por=user,
    )

    try:
        resultado = generar_resumen_ejecutivo(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            modelo_ia=config.modelo_ia or None,
            empresa_nombre=empresa_nombre,
        )

        datos = resultado.get("datos_financieros", {})
        margen = datos.get("margen_bruto_pct", 0)
        balance = datos.get("balance_neto", 0)

        reporte.resumen_ia = json.dumps(resultado, ensure_ascii=False)
        reporte.total_ventas = datos.get("total_ventas", 0)
        reporte.total_gastos = datos.get("total_gastos", 0)
        reporte.total_compras = datos.get("total_compras", 0)
        reporte.margen_bruto = balance
        reporte.margen_porcentaje = margen
        reporte.modelo_ia_usado = resultado.get("modelo_usado", "")
        reporte.estado = ReporteEjecutivo.Estado.GENERADO
        reporte.save()

    except Exception as exc:
        reporte.error_detalle = str(exc)
        reporte.estado = ReporteEjecutivo.Estado.ERROR
        reporte.save()
        raise

    return reporte


def _enviar_reporte(config: ConfiguracionReporte, reporte: ReporteEjecutivo) -> list[str]:
    """Envía el reporte a todos los destinatarios activos de la configuración."""
    from reportes.services.email_service import enviar_reporte_ejecutivo

    destinatarios_activos = [
        d.correo for d in config.destinatarios.filter(activo=True)
    ]

    reporte.estado = ReporteEjecutivo.Estado.ENVIANDO
    reporte.save(update_fields=["estado"])

    try:
        asunto = config.asunto_email.replace(
            "{periodo}",
            f"{reporte.periodo_inicio.strftime('%B %Y').capitalize()}",
        )
        enviados = enviar_reporte_ejecutivo(reporte, destinatarios_activos, asunto=asunto)
        reporte.destinatarios_enviados = json.dumps(enviados, ensure_ascii=False)
        reporte.estado = ReporteEjecutivo.Estado.ENVIADO
        reporte.save(update_fields=["destinatarios_enviados", "estado"])
        return enviados
    except Exception as exc:
        reporte.error_detalle = str(exc)
        reporte.estado = ReporteEjecutivo.Estado.ERROR
        reporte.save(update_fields=["error_detalle", "estado"])
        raise


# ────────────────────────────────────────────────────────────────────────────── #
# DestinatarioReporteAdmin                                                       #
# ────────────────────────────────────────────────────────────────────────────── #


@admin.register(DestinatarioReporte)
class DestinatarioReporteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "correo", "activo", "fecha_registro")
    list_filter = ("activo",)
    search_fields = ("nombre", "correo")
    list_editable = ("activo",)
    ordering = ("nombre",)


# ────────────────────────────────────────────────────────────────────────────── #
# ConfiguracionReporteAdmin                                                      #
# ────────────────────────────────────────────────────────────────────────────── #


@admin.register(ConfiguracionReporte)
class ConfiguracionReporteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "periodo_default", "modelo_ia", "activo", "fecha_actualizacion", "acciones_rapidas")
    list_filter = ("activo", "periodo_default")
    filter_horizontal = ("destinatarios",)
    readonly_fields = ("fecha_actualizacion",)
    ordering = ("nombre",)

    fieldsets = (
        (
            "Configuración general",
            {
                "fields": ("nombre", "activo", "periodo_default", "modelo_ia"),
            },
        ),
        (
            "Correo electrónico",
            {
                "fields": ("asunto_email", "destinatarios"),
                "description": "Configura el asunto y los destinatarios del reporte.",
            },
        ),
        (
            "Información",
            {
                "fields": ("fecha_actualizacion",),
                "classes": ("collapse",),
            },
        ),
    )

    # ── Acciones del listado ─────────────────────────────────────────────────── #

    actions = ["action_generar_y_enviar"]

    @admin.action(description="Generar y enviar reporte ahora")
    def action_generar_y_enviar(self, request, queryset):
        generados = 0
        for config in queryset.filter(activo=True):
            try:
                fecha_inicio, fecha_fin = _get_periodo_dates(config)
                reporte = _crear_y_guardar_reporte(config, request.user, fecha_inicio, fecha_fin)
                _enviar_reporte(config, reporte)
                generados += 1
                self.message_user(
                    request,
                    f"Reporte «{reporte.titulo}» generado y enviado correctamente.",
                    messages.SUCCESS,
                )
            except Exception as exc:
                self.message_user(
                    request,
                    f"Error al generar reporte para «{config.nombre}»: {exc}",
                    messages.ERROR,
                )

    # ── Columna con botones de acción rápida ─────────────────────────────────── #

    def acciones_rapidas(self, obj):
        generar_url = reverse("admin:reportes_generar_reporte", args=[obj.pk])
        preview_url = reverse("admin:reportes_preview_reporte", args=[obj.pk])
        return format_html(
            '<a class="btn btn-sm btn-primary" href="{}">'
            '<i class="fas fa-robot"></i> Generar</a>&nbsp;'
            '<a class="btn btn-sm btn-info" href="{}" target="_blank">'
            '<i class="fas fa-eye"></i> Preview</a>',
            generar_url,
            preview_url,
        )

    acciones_rapidas.short_description = "Acciones"
    acciones_rapidas.allow_tags = True

    # ── URLs extra ────────────────────────────────────────────────────────────── #

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:config_id>/generar/",
                self.admin_site.admin_view(self.view_generar_reporte),
                name="reportes_generar_reporte",
            ),
            path(
                "<int:config_id>/preview/",
                self.admin_site.admin_view(self.view_preview_reporte),
                name="reportes_preview_reporte",
            ),
        ]
        return custom + urls

    # ── Vista: generar y enviar ───────────────────────────────────────────────── #

    def view_generar_reporte(self, request, config_id):
        config = ConfiguracionReporte.objects.get(pk=config_id)

        if request.method == "POST":
            fecha_inicio_str = request.POST.get("fecha_inicio")
            fecha_fin_str = request.POST.get("fecha_fin")
            solo_preview = request.POST.get("solo_preview") == "1"
            enviar = request.POST.get("enviar") == "1"

            try:
                fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
                fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                fecha_inicio, fecha_fin = _get_periodo_dates(config)

            try:
                reporte = _crear_y_guardar_reporte(config, request.user, fecha_inicio, fecha_fin)

                if enviar:
                    enviados = _enviar_reporte(config, reporte)
                    messages.success(
                        request,
                        f"Reporte generado y enviado a: {', '.join(enviados)}",
                    )
                else:
                    messages.success(request, "Reporte generado correctamente (no enviado).")

                return redirect(
                    reverse("admin:reportes_reporteejecutivo_change", args=[reporte.pk])
                )

            except Exception as exc:
                messages.error(request, f"Error: {exc}")
                return redirect(reverse("admin:reportes_configuracionreporte_changelist"))

        # GET → mostrar formulario
        fecha_inicio, fecha_fin = _get_periodo_dates(config)
        context = {
            **self.admin_site.each_context(request),
            "title": f"Generar reporte — {config.nombre}",
            "config": config,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "opts": self.model._meta,
        }
        return TemplateResponse(request, "reportes/admin_generar_reporte.html", context)

    # ── Vista: preview ────────────────────────────────────────────────────────── #

    def view_preview_reporte(self, request, config_id):
        """
        Genera el resumen en tiempo real (sin guardar) y lo muestra como HTML.
        Útil para validar el contenido antes de enviar.
        """
        from django.conf import settings

        from reportes.services.executive_summary_service import (
            generar_resumen_ejecutivo,
        )

        config = ConfiguracionReporte.objects.get(pk=config_id)
        fecha_inicio, fecha_fin = _get_periodo_dates(config)
        empresa_nombre = getattr(settings, "JAZZMIN_SETTINGS", {}).get(
            "site_header", "Empresa"
        )

        try:
            resultado = generar_resumen_ejecutivo(
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                modelo_ia=config.modelo_ia or None,
                empresa_nombre=empresa_nombre,
            )
        except Exception as exc:
            messages.error(request, f"Error al generar preview: {exc}")
            return redirect(reverse("admin:reportes_configuracionreporte_changelist"))

        # Crear objeto temporal (no guardado) para la plantilla
        reporte_preview = ReporteEjecutivo(
            titulo=f"PREVIEW — {empresa_nombre}",
            periodo_inicio=fecha_inicio,
            periodo_fin=fecha_fin,
            total_ventas=resultado["datos_financieros"]["total_ventas"],
            total_gastos=resultado["datos_financieros"]["total_gastos"],
            total_compras=resultado["datos_financieros"]["total_compras"],
            margen_bruto=resultado["datos_financieros"]["balance_neto"],
            margen_porcentaje=resultado["datos_financieros"]["margen_bruto_pct"],
            modelo_ia_usado=resultado.get("modelo_usado", ""),
        )

        context = {
            **self.admin_site.each_context(request),
            "title": "Preview del reporte ejecutivo",
            "config": config,
            "reporte": reporte_preview,
            "resumen_data": resultado,
            "opts": self.model._meta,
            "is_preview": True,
        }
        return TemplateResponse(request, "reportes/admin_preview_reporte.html", context)


# ────────────────────────────────────────────────────────────────────────────── #
# ReporteEjecutivoAdmin (historial, solo lectura)                                #
# ────────────────────────────────────────────────────────────────────────────── #


@admin.register(ReporteEjecutivo)
class ReporteEjecutivoAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "periodo_inicio",
        "periodo_fin",
        "estado_badge",
        "total_ventas_fmt",
        "balance_fmt",
        "margen_pct_fmt",
        "modelo_ia_usado",
        "generado_por",
        "fecha_generacion",
    )
    list_filter = ("estado", "periodo_inicio", "generado_por")
    search_fields = ("titulo", "modelo_ia_usado")
    readonly_fields = (
        "titulo",
        "periodo_inicio",
        "periodo_fin",
        "total_ventas",
        "total_gastos",
        "total_compras",
        "margen_bruto",
        "margen_porcentaje",
        "modelo_ia_usado",
        "estado",
        "error_detalle",
        "generado_por",
        "fecha_generacion",
        "destinatarios_enviados",
        "resumen_ia_renderizado",
    )
    ordering = ("-fecha_generacion",)

    fieldsets = (
        (
            "Información del reporte",
            {
                "fields": (
                    "titulo",
                    "estado",
                    "periodo_inicio",
                    "periodo_fin",
                    "generado_por",
                    "fecha_generacion",
                    "modelo_ia_usado",
                ),
            },
        ),
        (
            "KPIs financieros",
            {
                "fields": (
                    "total_ventas",
                    "total_gastos",
                    "total_compras",
                    "margen_bruto",
                    "margen_porcentaje",
                ),
            },
        ),
        (
            "Contenido generado",
            {
                "fields": ("resumen_ia_renderizado",),
            },
        ),
        (
            "Envío",
            {
                "fields": ("destinatarios_enviados", "error_detalle"),
                "classes": ("collapse",),
            },
        ),
    )

    # No permitir agregar/editar manualmente
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    # ── Campos calculados ─────────────────────────────────────────────────────── #

    def estado_badge(self, obj):
        colors = {
            ReporteEjecutivo.Estado.GENERANDO: "#6c757d",
            ReporteEjecutivo.Estado.GENERADO: "#0dcaf0",
            ReporteEjecutivo.Estado.ENVIANDO: "#ffc107",
            ReporteEjecutivo.Estado.ENVIADO: "#198754",
            ReporteEjecutivo.Estado.ERROR: "#dc3545",
        }
        color = colors.get(obj.estado, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            color,
            obj.get_estado_display(),
        )

    estado_badge.short_description = "Estado"

    def total_ventas_fmt(self, obj):
        return f"${obj.total_ventas:,.2f}"

    total_ventas_fmt.short_description = "Ventas"

    def balance_fmt(self, obj):
        color = "green" if obj.margen_bruto >= 0 else "red"
        formatted = "${:,.2f}".format(float(obj.margen_bruto))
        return format_html('<span style="color:{}">{}</span>', color, formatted)

    balance_fmt.short_description = "Balance"

    def margen_pct_fmt(self, obj):
        color = "green" if obj.margen_porcentaje >= 0 else "red"
        formatted = "{:.1f}%".format(float(obj.margen_porcentaje))
        return format_html('<span style="color:{}">{}</span>', color, formatted)

    margen_pct_fmt.short_description = "Margen"

    def resumen_ia_renderizado(self, obj):
        """Renderiza el JSON del resumen IA como HTML legible en el admin."""
        if not obj.resumen_ia:
            return "Sin contenido"

        try:
            data = json.loads(obj.resumen_ia)
        except (json.JSONDecodeError, TypeError):
            return mark_safe(f"<pre>{obj.resumen_ia}</pre>")

        resumen = data.get("resumen_ejecutivo", "")
        alertas = data.get("alertas", [])
        recomendaciones = data.get("recomendaciones", [])
        kpis = data.get("kpis", {})
        semaforo = kpis.get("semaforo_financiero", "")

        semaforo_colors = {"verde": "#198754", "amarillo": "#ffc107", "rojo": "#dc3545"}
        semaforo_color = semaforo_colors.get(semaforo, "#6c757d")

        html_parts = []

        if semaforo:
            html_parts.append(
                f'<p><strong>Estado financiero:</strong> '
                f'<span style="background:{semaforo_color};color:#fff;padding:2px 10px;border-radius:4px">'
                f'{semaforo.upper()}</span></p>'
            )

        if resumen:
            html_parts.append(f"<h4>Resumen ejecutivo</h4><p>{resumen}</p>")

        if alertas:
            items = "".join(f"<li>⚠ {a}</li>" for a in alertas)
            html_parts.append(f"<h4>Alertas</h4><ul>{items}</ul>")

        if recomendaciones:
            items = "".join(f"<li>→ {r}</li>" for r in recomendaciones)
            html_parts.append(f"<h4>Recomendaciones</h4><ul>{items}</ul>")

        prioridad = kpis.get("prioridad", "")
        if prioridad:
            html_parts.append(f"<p><strong>Prioridad:</strong> {prioridad}</p>")

        return mark_safe("".join(html_parts))

    resumen_ia_renderizado.short_description = "Resumen generado por IA"
