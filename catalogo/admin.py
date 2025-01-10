from django.contrib import admin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin
from .models import Productor, Estado, Sucursal, Pais, Producto
from django.utils.html import format_html

@admin.register(Pais)
class PaisAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'siglas', 'moneda')
    search_fields = ('nombre', 'siglas', 'moneda')

class ProductorResource(resources.ModelResource):
    sucursal = fields.Field(
        column_name='sucursal',
        attribute='sucursal',
        widget=ForeignKeyWidget(Sucursal, field='nombre'))
    
    class Meta:
        model = Productor
        fields = ('id', 'nombre_completo', 'num_cuenta', 'clabe_interbancaria', 'telefono', 'correo', 'sucursal', 'fecha_creacion')
        
    def dehydrate_sucursal(self, productor):
        return productor.sucursal.nombre   
    
@admin.register(Productor)
class ProductorAdmin(ImportExportModelAdmin):
    resource_class = ProductorResource
    list_display = ('id', 'nombre_completo', 'num_cuenta', 'clabe_interbancaria', 'telefono', 'correo', 'id_sucursal', 'fecha_creacion', 'mostrar_imagen', 'nacimiento', 'nacionalidad')
    search_fields = ('nombre_completo', 'num_cuenta', 'clabe_interbancaria', 'telefono', 'correo', 'id_sucursal', 'fecha_creacion')
    list_filter = ('id_sucursal', 'fecha_creacion')
    list_per_page = 12
    fieldsets = (
        ('Datos del Productor', {
            'fields': ('nombre_completo', 'num_cuenta', 'clabe_interbancaria', 'telefono', 'correo', 'id_sucursal')
        }),
        ('Imagen', {
            'fields': ('imagen',),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('fecha_creacion', 'nacimiento', 'nacionalidad'),
            'classes': ('collapse',)
        })
    )

    def mostrar_imagen(self, obj):
        if obj.imagen:
            return format_html('<img src="{}" style="width: 70px; height: 70px;" />', obj.imagen.url)
        return "No Image"
    mostrar_imagen.short_description = 'Imagen del Productor'
    
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

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'variedad', 'precio_unitario', 'disponible', 'mostrar_imagen')
    search_fields = ('nombre', 'variedad', 'descripcion')
    list_filter = ('disponible', 'variedad')
    list_per_page = 12
    fieldsets = (
        ('Datos del Producto', {
            'fields': ('nombre', 'variedad', 'precio_unitario', 'disponible', 'descripcion')
        }),
        ('Imagen', {
            'fields': ('imagen',),
            'classes': ('collapse',)
        }),
    )
    
    def mostrar_imagen(self, obj):
        if obj.imagen:
            return format_html('<img src="{}" style="width: 70px; height: 70px;" />', obj.imagen.url)
        return "No Image"
    mostrar_imagen.short_description = 'Imagen del Producto'
