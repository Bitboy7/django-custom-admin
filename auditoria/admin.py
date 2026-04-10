from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.utils.html import format_html
from .models import LogActividad, SiteConfiguration


@admin.register(LogActividad)
class LogActividadAdmin(ModelAdmin):
    """Configuración del admin para los logs de actividad"""
    
    list_display = ('fecha_hora', 'nombre_usuario', 'tipo_accion', 'modelo_afectado', 
                    'objeto_id', 'direccion_ip', 'descripcion_corta')
    
    list_filter = ('tipo_accion', 'fecha_hora', 'modelo_afectado', 'usuario')
    
    search_fields = ('nombre_usuario', 'descripcion', 'modelo_afectado', 
                     'objeto_id', 'direccion_ip')
    
    readonly_fields = ('usuario', 'nombre_usuario', 'tipo_accion', 'descripcion', 
                       'modelo_afectado', 'objeto_id', 'campos_modificados', 
                       'direccion_ip', 'navegador', 'fecha_hora')
    
    fieldsets = (
        ('Información del usuario', {
            'fields': ('usuario', 'nombre_usuario', 'direccion_ip', 'navegador')
        }),
        ('Detalles de la acción', {
            'fields': ('tipo_accion', 'descripcion', 'fecha_hora')
        }),
        ('Objeto afectado', {
            'fields': ('modelo_afectado', 'objeto_id', 'campos_modificados'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ('-fecha_hora',)
    
    # Eliminamos date_hierarchy para evitar problemas con zonas horarias
    # date_hierarchy = 'fecha_hora'
    
    # Deshabilitar acciones que modifican los logs
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def descripcion_corta(self, obj):
        """Muestra una versión corta de la descripción"""
        if len(obj.descripcion) > 100:
            return f"{obj.descripcion[:100]}..."
        return obj.descripcion
    
    descripcion_corta.short_description = 'Descripción'
    
    class Media:
        css = {
            'all': ('css/admin/auditoria.css',)
        }


_ACCION_ICONS = {
    ADDITION: ('fas fa-plus-circle', 'text-success', 'Creación'),
    CHANGE:   ('fas fa-edit',        'text-warning', 'Modificación'),
    DELETION: ('fas fa-trash-alt',   'text-danger',  'Eliminación'),
}


@admin.register(LogEntry)
class LogEntryAdmin(ModelAdmin):
    """Historial de cambios del admin de Django (LogEntry nativo)."""

    list_display = (
        'accion_badge', 'object_repr', 'content_type',
        'user', 'action_time',
    )
    list_filter  = ('action_flag', 'content_type', 'action_time')
    search_fields = ('object_repr', 'change_message', 'user__username')
    readonly_fields = (
        'action_time', 'user', 'content_type', 'object_id',
        'object_repr', 'action_flag', 'change_message',
    )
    ordering = ('-action_time',)

    fieldsets = (
        ('Quién y cuándo', {
            'fields': ('user', 'action_time'),
        }),
        ('Qué objeto', {
            'fields': ('content_type', 'object_id', 'object_repr'),
        }),
        ('Acción', {
            'fields': ('action_flag', 'change_message'),
        }),
    )

    def accion_badge(self, obj):
        icon_cls, color_cls, label = _ACCION_ICONS.get(
            obj.action_flag, ('fas fa-question', 'text-secondary', 'Desconocido')
        )
        return format_html(
            '<i class="{} {}" title="{}"></i> {}',
            icon_cls, color_cls, label, label
        )
    accion_badge.short_description = 'Acción'
    accion_badge.admin_order_field  = 'action_flag'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(ModelAdmin):
    """Admin singleton para la configuración global del sitio.
    Solo hay un registro; el listado redirige directamente al formulario.
    Acceso exclusivo para superusuarios.
    """

    fieldsets = (
        ('Logo e identidad', {
            'fields': ('company_logo',),
            'description': 'Imagen que aparece en la barra lateral y en la pantalla de login. '
                           'Usa PNG o SVG con fondo transparente (≥ 200 × 60 px recomendado).',
        }),
        ('Textos del sitio', {
            'fields': ('site_title', 'site_header', 'site_brand'),
            'description': 'Personaliza los textos que identifican tu empresa en el sistema.',
        }),
        ('Barra lateral', {
            'fields': ('navigation_expanded', 'show_ui_builder'),
        }),
        ('Estilos personalizados', {
            'fields': ('custom_topbar_css',),
            'description': 'CSS personalizado para la barra de navegación superior. '
                           'Ejemplo: .main-header { background-color: #ff0000; }',
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Aplicar el cambio en caliente sin reiniciar el servidor
        from django.conf import settings as django_settings
        jazzmin = getattr(django_settings, 'JAZZMIN_SETTINGS', {})
        jazzmin['show_ui_builder'] = obj.show_ui_builder

    def has_add_permission(self, request):
        return False  # Singleton: no se puede agregar otro.

    def has_delete_permission(self, request, obj=None):
        return False  # No se puede eliminar.

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def changelist_view(self, request, extra_context=None):
        """Redirige siempre al formulario del registro singleton."""
        obj = SiteConfiguration.load()
        return redirect(
            reverse('admin:auditoria_siteconfiguration_change', args=[obj.pk])
        )

    def response_change(self, request, obj):
        messages.success(request, 'Configuración del sitio actualizada correctamente.')
        return redirect(
            reverse('admin:auditoria_siteconfiguration_change', args=[obj.pk])
        )
