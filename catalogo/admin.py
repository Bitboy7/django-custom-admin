from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import Productor, Estado, Sucursal, Pais

@admin.register(Pais)
class PaisAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'siglas', 'moneda')

class ProductorResource(resources.ModelResource):
    fields = ('id', 'nombre_completo', 'num_cuenta', 'clabe_interbancaria', 'telefono', 'correo', 'id_sucursal', 'fecha_creacion')
    class Meta:
        model = Productor
        
@admin.register(Productor)
class ProductorAdmin(ImportExportModelAdmin):
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


 


