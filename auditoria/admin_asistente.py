"""Read-only admin views for the assistant conversations and their cost."""

from __future__ import annotations

from django.contrib import admin
from django.db.models import Count, Sum
from django.utils.html import format_html

from .models import (
    ConversacionAsistente,
    MensajeAsistente,
    TrazaHerramientaAsistente,
)


class TrazaHerramientaInline(admin.TabularInline):
    model = TrazaHerramientaAsistente
    extra = 0
    can_delete = False
    fields = ("herramienta", "argumentos", "num_filas", "duracion_ms", "error")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class MensajeAsistenteInline(admin.TabularInline):
    model = MensajeAsistente
    extra = 0
    can_delete = False
    fields = (
        "orden",
        "rol",
        "contenido_resumen",
        "modelo",
        "tokens_total",
        "costo_estimado_usd",
        "duracion_ms",
        "error",
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Contenido")
    def contenido_resumen(self, obj):
        text = (obj.contenido or "").strip()
        if len(text) <= 110:
            return text
        return text[:110].rstrip() + "…"


@admin.register(ConversacionAsistente)
class ConversacionAsistenteAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "usuario",
        "mensajes_count",
        "costo_total",
        "actualizada_en",
        "archivada",
    )
    list_filter = ("archivada", "actualizada_en", "usuario")
    search_fields = ("titulo", "usuario__username", "usuario__email")
    readonly_fields = ("id", "usuario", "titulo", "creada_en", "actualizada_en")
    inlines = (MensajeAsistenteInline,)
    date_hierarchy = "actualizada_en"
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _mensajes_count=Count("mensajes", distinct=True),
            _costo_total=Sum("mensajes__costo_estimado_usd"),
        )

    @admin.display(description="Mensajes", ordering="_mensajes_count")
    def mensajes_count(self, obj):
        return obj._mensajes_count

    @admin.display(description="Costo USD", ordering="_costo_total")
    def costo_total(self, obj):
        value = obj._costo_total or 0
        return format_html("<strong>${}</strong>", f"{value:.6f}")


@admin.register(MensajeAsistente)
class MensajeAsistenteAdmin(admin.ModelAdmin):
    list_display = (
        "creado_en",
        "conversacion",
        "rol",
        "modelo",
        "tokens_total",
        "costo_estimado_usd",
        "duracion_ms",
        "tuvo_error",
    )
    list_filter = ("rol", "modelo", "creado_en")
    search_fields = ("conversacion__titulo", "contenido")
    inlines = (TrazaHerramientaInline,)
    list_per_page = 50

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    @admin.display(boolean=True, description="Error")
    def tuvo_error(self, obj):
        return bool(obj.error)


@admin.register(TrazaHerramientaAsistente)
class TrazaHerramientaAsistenteAdmin(admin.ModelAdmin):
    list_display = (
        "herramienta",
        "mensaje",
        "num_filas",
        "duracion_ms",
        "creado_en",
        "tuvo_error",
    )
    list_filter = ("herramienta", "creado_en")
    search_fields = ("herramienta", "mensaje__conversacion__titulo")
    list_per_page = 50

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    @admin.display(boolean=True, description="Error")
    def tuvo_error(self, obj):
        return bool(obj.error)
