"""
Admin de Django para el modulo de WhatsApp / Evolution API.

Proporciona:
  - EvolutionInstanceAdmin: gestion de instancias con test de conexion, QR, webhook
  - DestinatarioWhatsAppAdmin: gestion de contactos
  - ConfiguracionWhatsAppAdmin: configuracion de notificaciones con envio manual
  - MensajeWhatsAppAdmin: historial de mensajes (solo lectura)
  - WebhookLogAdmin: registro de webhooks entrantes (solo lectura)
  - ProgramacionEnvioAdmin: historial de envios programados (solo lectura)
"""

from __future__ import annotations

import json
import logging

from django.contrib import admin, messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import (
    ConfiguracionWhatsApp,
    DestinatarioWhatsApp,
    EvolutionInstance,
    MensajeWhatsApp,
    ProgramacionEnvio,
    WebhookLog,
)

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────── #
# EvolutionInstanceAdmin                                                         #
# ────────────────────────────────────────────────────────────────────────────── #


@admin.register(EvolutionInstance)
class EvolutionInstanceAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "instance_id",
        "api_url",
        "estado_badge",
        "activo",
        "ultima_verificacion",
        "acciones_rapidas",
    )
    list_filter = ("activo", "estado")
    search_fields = ("nombre", "instance_id", "api_url")
    readonly_fields = ("estado", "ultima_verificacion", "webhook_url_display")
    ordering = ("nombre",)

    fieldsets = (
        (
            "Datos de conexion",
            {
                "fields": (
                    "nombre",
                    "instance_id",
                    "api_url",
                    "apikey",
                    "activo",
                ),
            },
        ),
        (
            "Webhook",
            {
                "fields": ("webhook_url", "webhook_url_display"),
                "description": "URL donde Evolution enviara los eventos entrantes. "
                "Si se deja en blanco, se genera automaticamente al configurar el webhook.",
            },
        ),
        (
            "Estado",
            {
                "fields": ("estado", "ultima_verificacion"),
            },
        ),
    )

    actions = [
        "action_verificar_conexion",
        "action_configurar_webhook",
    ]

    # ── Columna de estado ───────────────────────────────────────────────────── #

    def estado_badge(self, obj):
        colors = {
            "conectado": "#198754",
            "desconectado": "#6c757d",
            "error": "#dc3545",
        }
        color = colors.get(obj.estado, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            color,
            obj.get_estado_display(),
        )

    estado_badge.short_description = "Estado"

    # ── Columna de acciones rapidas ─────────────────────────────────────────── #

    def acciones_rapidas(self, obj):
        test_url = reverse("admin:whatsapp_test_connection", args=[obj.pk])
        qr_url = reverse("admin:whatsapp_qr_code", args=[obj.pk])
        return format_html(
            '<a class="btn btn-sm btn-info" href="{}">'
            '<i class="fas fa-plug"></i> Test</a>&nbsp;'
            '<a class="btn btn-sm btn-secondary" href="{}" target="_blank">'
            '<i class="fas fa-qrcode"></i> QR</a>',
            test_url,
            qr_url,
        )

    acciones_rapidas.short_description = "Acciones"
    acciones_rapidas.allow_tags = True

    # ── Campo webhook url ───────────────────────────────────────────────────── #

    def webhook_url_display(self, obj):
        if not obj.webhook_url:
            from whatsapp.services.evolution_api import _obtener_dominio_publico
            domain = _obtener_dominio_publico()
            es_local = domain in ("localhost", "127.0.0.1")
            protocol = "http" if es_local else "https"
            webhook_url = f"{protocol}://{domain}/whatsapp/webhook/{obj.instance_id}/"
            return format_html(
                '<code style="word-break:break-all">{}</code>'
                '<br><small class="text-muted">Copia esta URL y pegala en el Manager de Evolution > Webhook</small>',
                webhook_url,
            )
        return format_html(
            '<code style="word-break:break-all">{}</code>'
            '<br><small class="text-muted">Configurada. Si cambias, usa la accion "Configurar webhook".</small>',
            obj.webhook_url,
        )

    webhook_url_display.short_description = "URL del webhook (actual)"

    # ── Acciones del listado ────────────────────────────────────────────────── #

    @admin.action(description="Verificar conexion de instancias seleccionadas")
    def action_verificar_conexion(self, request, queryset):
        from .services.evolution_api import verificar_y_actualizar_estado

        for instancia in queryset:
            estado = verificar_y_actualizar_estado(instancia)
            if estado == "conectado":
                self.message_user(request, f"{instancia.nombre}: Conectado.", messages.SUCCESS)
            elif estado == "error":
                self.message_user(request, f"{instancia.nombre}: Error de conexion.", messages.ERROR)
            else:
                self.message_user(request, f"{instancia.nombre}: Desconectado.", messages.WARNING)

    @admin.action(description="Configurar webhook en Evolution")
    def action_configurar_webhook(self, request, queryset):
        from .services.evolution_api import configurar_webhook_instancia, EvolutionAPIError

        for instancia in queryset:
            try:
                result = configurar_webhook_instancia(instancia)
                self.message_user(
                    request,
                    f"Webhook configurado para {instancia.nombre}: {instancia.webhook_url}",
                    messages.SUCCESS,
                )
            except EvolutionAPIError as exc:
                self.message_user(
                    request,
                    f"Error al configurar webhook para {instancia.nombre}: {exc}",
                    messages.ERROR,
                )

    # ── URLs extra ──────────────────────────────────────────────────────────── #

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:instance_id>/test/",
                self.admin_site.admin_view(self.view_test_connection),
                name="whatsapp_test_connection",
            ),
            path(
                "<int:instance_id>/qr/",
                self.admin_site.admin_view(self.view_qr_code),
                name="whatsapp_qr_code",
            ),
            path(
                "<int:instance_id>/send-test/",
                self.admin_site.admin_view(self.view_send_test_message),
                name="whatsapp_send_test",
            ),
        ]
        return custom + urls

    # ── Vista: test de conexion ─────────────────────────────────────────────── #

    def view_test_connection(self, request, instance_id):
        instancia = get_object_or_404(EvolutionInstance, pk=instance_id)

        if request.method == "POST":
            from .services.evolution_api import verificar_y_actualizar_estado

            estado = verificar_y_actualizar_estado(instancia)
            if estado == "conectado":
                messages.success(request, f"Conexion exitosa a {instancia.nombre}.")
            else:
                messages.warning(request, f"{instancia.nombre}: {instancia.get_estado_display()}.")
            return redirect(reverse("admin:whatsapp_evolutioninstance_changelist"))

        api_url_display = instancia.api_url
        if api_url_display.startswith("http://"):
            api_url_display = "https://" + api_url_display[len("http://"):]

        context = {
            **self.admin_site.each_context(request),
            "title": f"Test de conexion — {instancia.nombre}",
            "instancia": instancia,
            "api_url_display": api_url_display,
            "opts": self.model._meta,
        }
        return TemplateResponse(request, "whatsapp/admin_test_connection.html", context)

    # ── Vista: QR code ──────────────────────────────────────────────────────── #

    def view_qr_code(self, request, instance_id):
        instancia = get_object_or_404(EvolutionInstance, pk=instance_id)

        qr_base64 = None
        error = None

        if request.method == "POST":
            from .services.evolution_api import get_evolution_service, EvolutionAPIError

            try:
                service = get_evolution_service(instancia)
                result = service.get_qr_code()
                qr_base64 = result.get("base64", "")
            except EvolutionAPIError as exc:
                error = str(exc)
        else:
            from .services.evolution_api import get_evolution_service, EvolutionAPIError

            try:
                service = get_evolution_service(instancia)
                result = service.get_qr_code()
                qr_base64 = result.get("base64", "")
            except EvolutionAPIError as exc:
                error = str(exc)

        context = {
            **self.admin_site.each_context(request),
            "title": f"QR Code — {instancia.nombre}",
            "instancia": instancia,
            "qr_base64": qr_base64,
            "error": error,
            "opts": self.model._meta,
        }
        return TemplateResponse(request, "whatsapp/admin_qr_code.html", context)

    # ── Vista: enviar mensaje de prueba ─────────────────────────────────────── #

    def view_send_test_message(self, request, instance_id):
        instancia = get_object_or_404(EvolutionInstance, pk=instance_id)

        destinatarios = DestinatarioWhatsApp.objects.filter(activo=True)

        if request.method == "POST":
            telefono = request.POST.get("telefono", "").strip()
            if not telefono:
                messages.error(request, "Debe ingresar un numero de telefono.")
                return redirect(reverse("admin:whatsapp_send_test", args=[instance_id]))

            from .services.whatsapp_notification import enviar_mensaje_prueba

            exito, detalle = enviar_mensaje_prueba(instancia, telefono)
            if exito:
                messages.success(request, f"Mensaje de prueba enviado correctamente a {telefono}. ID: {detalle}")
            else:
                messages.error(request, f"Error al enviar mensaje: {detalle}")
            return redirect(reverse("admin:whatsapp_evolutioninstance_change", args=[instance_id]))

        context = {
            **self.admin_site.each_context(request),
            "title": f"Enviar mensaje de prueba — {instancia.nombre}",
            "instancia": instancia,
            "destinatarios": destinatarios,
            "opts": self.model._meta,
        }
        return TemplateResponse(request, "whatsapp/admin_send_test.html", context)


# ────────────────────────────────────────────────────────────────────────────── #
# DestinatarioWhatsAppAdmin                                                      #
# ────────────────────────────────────────────────────────────────────────────── #


@admin.register(DestinatarioWhatsApp)
class DestinatarioWhatsAppAdmin(admin.ModelAdmin):
    list_display = ("nombre", "telefono", "activo", "fecha_registro")
    list_filter = ("activo",)
    search_fields = ("nombre", "telefono")
    list_editable = ("activo",)
    ordering = ("nombre",)


# ────────────────────────────────────────────────────────────────────────────── #
# ConfiguracionWhatsAppAdmin                                                     #
# ────────────────────────────────────────────────────────────────────────────── #


@admin.register(ConfiguracionWhatsApp)
class ConfiguracionWhatsAppAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "instancia",
        "frecuencia_envio",
        "hora_envio",
        "enviar_reportes",
        "enviar_alertas",
        "activo",
        "acciones_rapidas",
    )
    list_filter = ("activo", "frecuencia_envio", "instancia")
    filter_horizontal = ("destinatarios",)
    readonly_fields = ("fecha_actualizacion", "proxima_ejecucion_display")
    ordering = ("-fecha_actualizacion",)

    fieldsets = (
        (
            "General",
            {
                "fields": (
                    "usuario",
                    "instancia",
                    "activo",
                ),
            },
        ),
        (
            "Notificaciones",
            {
                "fields": ("enviar_reportes", "enviar_alertas"),
                "description": "Tipos de notificaciones a enviar por WhatsApp.",
            },
        ),
        (
            "Programacion",
            {
                "fields": (
                    "frecuencia_envio",
                    "hora_envio",
                    "dia_semana",
                    "dia_mes",
                    "proxima_ejecucion_display",
                ),
                "description": (
                    "Configura cuando se enviaran los reportes automaticamente. "
                    "Para solo envio manual, selecciona 'Solo manual'. "
                    "El comando 'enviar_reportes_whatsapp' debe ejecutarse via cron."
                ),
            },
        ),
        (
            "Destinatarios",
            {
                "fields": ("destinatarios",),
                "description": "Contactos que recibiran los reportes y alertas.",
            },
        ),
        (
            "Informacion",
            {
                "fields": ("fecha_actualizacion",),
            },
        ),
    )

    # ── Acciones ────────────────────────────────────────────────────────────── #

    actions = ["action_enviar_reporte_ahora", "action_probar_mensaje"]

    @admin.action(description="Enviar reporte ejecutivo ahora")
    def action_enviar_reporte_ahora(self, request, queryset):
        from reportes.models import ConfiguracionReporte
        from reportes.admin import _get_periodo_dates, _crear_y_guardar_reporte
        from .services.whatsapp_notification import enviar_reporte_whatsapp

        config_reporte = ConfiguracionReporte.objects.filter(activo=True).first()
        if not config_reporte:
            self.message_user(request, "No hay ConfiguracionReporte activa.", messages.ERROR)
            return

        fecha_inicio, fecha_fin = _get_periodo_dates(config_reporte)

        for config in queryset.filter(activo=True):
            try:
                reporte = _crear_y_guardar_reporte(config_reporte, request.user, fecha_inicio, fecha_fin)
                enviados = enviar_reporte_whatsapp(reporte, config)
                self.message_user(
                    request,
                    f"Reporte enviado a {len(enviados)} destinatarios via WhatsApp: {', '.join(enviados)}",
                    messages.SUCCESS,
                )
            except Exception as exc:
                self.message_user(
                    request,
                    f"Error al enviar reporte para {config}: {exc}",
                    messages.ERROR,
                )

    @admin.action(description="Probar envio de mensaje")
    def action_probar_mensaje(self, request, queryset):
        for config in queryset:
            request.session["whatsapp_probar_config_id"] = config.pk
            url = reverse("admin:whatsapp_configuracion_enviar_prueba", args=[config.pk])
            break
        return redirect(url)

    # ── Campos calculados ───────────────────────────────────────────────────── #

    def proxima_ejecucion_display(self, obj):
        from .services.report_scheduler import calcular_proxima_ejecucion

        if obj.frecuencia_envio == obj.FrecuenciaReporte.MANUAL:
            return "N/A (solo manual)"
        try:
            proxima = calcular_proxima_ejecucion(obj)
            return proxima.strftime("%d/%m/%Y %H:%M")
        except Exception:
            return "Error al calcular"

    proxima_ejecucion_display.short_description = "Proxima ejecucion"

    # ── Acciones rapidas ────────────────────────────────────────────────────── #

    def acciones_rapidas(self, obj):
        probar_url = reverse("admin:whatsapp_configuracion_enviar_prueba", args=[obj.pk])
        return format_html(
            '<a class="btn btn-sm btn-success" href="{}">'
            '<i class="fas fa-paper-plane"></i> Probar</a>',
            probar_url,
        )

    acciones_rapidas.short_description = "Acciones"
    acciones_rapidas.allow_tags = True

    # ── URLs extra ──────────────────────────────────────────────────────────── #

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:config_id>/probar/",
                self.admin_site.admin_view(self.view_enviar_prueba),
                name="whatsapp_configuracion_enviar_prueba",
            ),
        ]
        return custom + urls

    # ── Vista: enviar mensaje de prueba ─────────────────────────────────────── #

    def view_enviar_prueba(self, request, config_id):
        config = get_object_or_404(ConfiguracionWhatsApp, pk=config_id)
        destinatarios = config.destinatarios.filter(activo=True)

        if request.method == "POST":
            from datetime import date as dt_date
            from reportes.models import ConfiguracionReporte, ReporteEjecutivo
            from .services.whatsapp_notification import enviar_reporte_whatsapp, formatear_reporte_whatsapp

            accion = request.POST.get("accion", "reporte")

            if accion == "reporte":
                try:
                    config_reporte = ConfiguracionReporte.objects.filter(activo=True).first()
                    if not config_reporte:
                        messages.error(request, "No hay ConfiguracionReporte activa.")
                        return redirect(reverse("admin:whatsapp_configuracionwhatsapp_changelist"))

                    from reportes.admin import _get_periodo_dates, _crear_y_guardar_reporte
                    fecha_inicio, fecha_fin = _get_periodo_dates(config_reporte)
                    reporte = _crear_y_guardar_reporte(config_reporte, request.user, fecha_inicio, fecha_fin)
                    enviados = enviar_reporte_whatsapp(reporte, config)
                    messages.success(
                        request,
                        f"Reporte enviado a {len(enviados)} destinatarios: {', '.join(enviados)}",
                    )
                except Exception as exc:
                    messages.error(request, f"Error: {exc}")

            elif accion == "mensaje_personalizado":
                texto = request.POST.get("mensaje", "").strip()
                telefono = request.POST.get("telefono", "").strip()
                if texto and telefono:
                    from .services.evolution_api import get_evolution_service, EvolutionAPIError

                    try:
                        service = get_evolution_service(config.instancia)
                        service.send_text(telefono, texto)
                        messages.success(request, f"Mensaje enviado a {telefono}.")

                        MensajeWhatsApp.objects.create(
                            instancia=config.instancia,
                            destinatario=DestinatarioWhatsApp.objects.filter(telefono=telefono, activo=True).first(),
                            tipo=MensajeWhatsApp.Tipo.MANUAL,
                            contenido=texto,
                            estado=MensajeWhatsApp.Estado.ENVIADO,
                        )
                    except EvolutionAPIError as exc:
                        messages.error(request, f"Error al enviar: {exc}")
                else:
                    messages.error(request, "Debe ingresar un mensaje y un numero.")

            return redirect(reverse("admin:whatsapp_configuracionwhatsapp_changelist"))

        context = {
            **self.admin_site.each_context(request),
            "title": f"Enviar prueba — {config}",
            "config": config,
            "destinatarios": destinatarios,
            "opts": self.model._meta,
        }
        return TemplateResponse(request, "whatsapp/admin_enviar_prueba.html", context)


# ────────────────────────────────────────────────────────────────────────────── #
# MensajeWhatsAppAdmin (historial, solo lectura)                                 #
# ────────────────────────────────────────────────────────────────────────────── #


@admin.register(MensajeWhatsApp)
class MensajeWhatsAppAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "destinatario",
        "tipo_badge",
        "estado_badge",
        "fecha_envio",
        "resumen_contenido",
    )
    list_filter = ("tipo", "estado", "instancia", "fecha_envio")
    search_fields = ("destinatario__nombre", "destinatario__telefono", "contenido")
    readonly_fields = (
        "instancia",
        "destinatario",
        "tipo",
        "contenido",
        "estado",
        "reporte",
        "evolution_message_id",
        "error_detalle",
        "fecha_envio",
    )
    ordering = ("-fecha_envio",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def tipo_badge(self, obj):
        colors = {
            "reporte": "#0d6efd",
            "alerta": "#dc3545",
            "manual": "#6c757d",
            "prueba": "#198754",
        }
        color = colors.get(obj.tipo, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            color,
            obj.get_tipo_display(),
        )

    tipo_badge.short_description = "Tipo"

    def estado_badge(self, obj):
        colors = {
            "enviado": "#198754",
            "pendiente": "#ffc107",
            "error": "#dc3545",
        }
        color = colors.get(obj.estado, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            color,
            obj.get_estado_display(),
        )

    estado_badge.short_description = "Estado"

    def resumen_contenido(self, obj):
        if len(obj.contenido) > 100:
            return obj.contenido[:100] + "..."
        return obj.contenido

    resumen_contenido.short_description = "Contenido"

    fieldsets = (
        (
            "Informacion del mensaje",
            {
                "fields": (
                    "instancia",
                    "destinatario",
                    "tipo",
                    "estado",
                    "fecha_envio",
                ),
            },
        ),
        (
            "Contenido",
            {
                "fields": ("contenido",),
            },
        ),
        (
            "Referencias",
            {
                "fields": ("reporte", "evolution_message_id"),
            },
        ),
        (
            "Errores",
            {
                "fields": ("error_detalle",),
            },
        ),
    )


# ────────────────────────────────────────────────────────────────────────────── #
# WebhookLogAdmin (solo lectura)                                                 #
# ────────────────────────────────────────────────────────────────────────────── #


@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "instancia",
        "tipo_evento",
        "telefono_remitente",
        "resumen_mensaje",
        "procesado",
        "fecha_recepcion",
    )
    list_filter = ("tipo_evento", "procesado", "instancia", "fecha_recepcion")
    search_fields = ("telefono_remitente", "mensaje", "tipo_evento")
    readonly_fields = (
        "instancia",
        "tipo_evento",
        "payload_pretty",
        "telefono_remitente",
        "mensaje",
        "procesado",
        "fecha_recepcion",
    )
    ordering = ("-fecha_recepcion",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def resumen_mensaje(self, obj):
        if obj.mensaje:
            if len(obj.mensaje) > 80:
                return obj.mensaje[:80] + "..."
            return obj.mensaje
        return "-"

    resumen_mensaje.short_description = "Mensaje"

    def payload_pretty(self, obj):
        try:
            formatted = json.dumps(obj.payload, indent=2, ensure_ascii=False)
            return mark_safe(f"<pre style='max-height:400px;overflow:auto'>{formatted}</pre>")
        except Exception:
            return str(obj.payload)

    payload_pretty.short_description = "Payload"

    fieldsets = (
        (
            "Evento",
            {
                "fields": ("instancia", "tipo_evento", "fecha_recepcion", "procesado"),
            },
        ),
        (
            "Mensaje",
            {
                "fields": ("telefono_remitente", "mensaje"),
            },
        ),
        (
            "Payload completo",
            {
                "fields": ("payload_pretty",),
            },
        ),
    )


# ────────────────────────────────────────────────────────────────────────────── #
# ProgramacionEnvioAdmin (historial)                                             #
# ────────────────────────────────────────────────────────────────────────────── #


@admin.register(ProgramacionEnvio)
class ProgramacionEnvioAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "configuracion",
        "reporte",
        "estado_badge",
        "programado_para",
        "ejecutado_en",
    )
    list_filter = ("estado", "configuracion__instancia")
    readonly_fields = (
        "configuracion",
        "reporte",
        "estado",
        "programado_para",
        "ejecutado_en",
        "error_detalle",
        "fecha_creacion",
    )
    ordering = ("-programado_para",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def estado_badge(self, obj):
        colors = {
            "pendiente": "#ffc107",
            "en_ejecucion": "#0dcaf0",
            "completado": "#198754",
            "error": "#dc3545",
        }
        color = colors.get(obj.estado, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            color,
            obj.get_estado_display(),
        )

    estado_badge.short_description = "Estado"
