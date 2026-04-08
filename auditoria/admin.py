from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
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
            'fields': ('navigation_expanded',),
        }),
    )

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
