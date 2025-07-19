from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import LogActividad


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
