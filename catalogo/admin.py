from django.contrib import admin

from .models import Productor, Estado, Sucursal

@admin.register(Productor)
class ProductorAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre_completo', 'num_cuenta', 'clabe_interbancaria', 'telefono', 'correo', 'id_sucursal', 'fecha_creacion')
    search_fields = ('nombre_completo', 'num_cuenta', 'clabe_interbancaria', 'telefono', 'correo', 'id_sucursal', 'fecha_creacion')
    list_filter = ('id_sucursal',)
    fieldsets = (
        ('Datos del Productor', {
            'fields': ('nombre_completo', 'num_cuenta', 'clabe_interbancaria', 'telefono', 'correo', 'id_sucursal', 'fecha_creacion')
        }),
    )
    
@admin.register(Estado)
class EstadoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)
    list_filter = ('nombre',)
    fieldsets = (
        ('Datos del Estado', {
            'fields': ('id', 'nombre',)
        }),
    )

@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'direccion', 'telefono', 'id_estado')
    search_fields = ('nombre', 'direccion', 'telefono')
    list_filter = ('id_estado',)
    fieldsets = (
        ('Datos de la Sucursal', {
            'fields': ('nombre', 'direccion', 'telefono', 'id_estado')
        }),
    )


 


