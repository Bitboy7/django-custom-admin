from django.contrib import admin
from unfold.admin import ModelAdmin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin
from .models import Productor, Estado, Sucursal, Pais, Producto
from django.utils.html import format_html

@admin.register(Pais)
class PaisAdmin(ModelAdmin):
    list_display = ('id', 'siglas', 'nombre', 'moneda', 'mostrar_bandera')
    search_fields = ('nombre', 'siglas')    
    fieldsets = (
        ('Datos del País', {
            'fields': ('siglas', 'nombre', 'moneda')
        }),
        ('Bandera', { 
            'fields': ('bandera',),
            'classes': ('collapse',)
        })
    )
    
class ProductorResource(resources.ModelResource):
    sucursal = fields.Field(
        column_name='sucursal',
        attribute='sucursal',
        widget=ForeignKeyWidget(Sucursal, field='nombre'))
    
    class Meta:
        model = Productor
        fields = ('id', 'nombre_completo', 'num_cuenta', 'clabe_interbancaria', 'telefono', 'correo', 'sucursal', 'fecha_creacion', 'nacimiento', 'nacionalidad')
        
    def dehydrate_sucursal(self, productor):
        return productor.sucursal.nombre   
    
    def before_import_row(self, row, **kwargs):
        # Asigna un ID específico basado en un rango disponible
        if not row['id']:
            last_productor = Productor.objects.order_by('-id').first()
            next_id = last_productor.id + 1 if last_productor else 1
            row['id'] = next_id
    
@admin.register(Productor)
class ProductorAdmin(ImportExportModelAdmin):
    resource_class = ProductorResource
    list_display = ('id', 'nombre_completo', 'num_cuenta', 'clabe_interbancaria', 'telefono', 'correo', 'id_sucursal', 'fecha_creacion', 'mostrar_imagen', 'nacimiento', 'mostrar_bandera_nacionalidad')
    search_fields = ('id', 'nombre_completo', 'num_cuenta', 'clabe_interbancaria', 'telefono', 'correo', 'id_sucursal__nombre', 'fecha_creacion')
    list_filter = ('id_sucursal', 'nombre_completo', 'nacionalidad')
    list_per_page = 30
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
            return format_html('<img src="{}" style="width: 57px; height: 57px;" />', obj.imagen.url)
        return "No Image"
    mostrar_imagen.short_description = 'Foto'

    def mostrar_bandera_nacionalidad(self, obj):
        return obj.nacionalidad.mostrar_bandera()
    mostrar_bandera_nacionalidad.short_description = 'Nacionalidad'
    
@admin.register(Estado)
class EstadoAdmin(ModelAdmin):
    list_display = ('id', 'nombre', 'mostrar_bandera_pais')
    search_fields = ('nombre',)
    list_filter = ('nombre',)
    fieldsets = (
        ('Datos del Estado', {
            'fields': ('id', 'nombre', 'pais')
        }),
    )

    def mostrar_bandera_pais(self, obj):
        return obj.pais.mostrar_bandera()
    mostrar_bandera_pais.short_description = 'Bandera del País'

@admin.register(Sucursal)
class SucursalAdmin(ModelAdmin):
    list_display = ('id', 'nombre', 'direccion', 'telefono', 'id_estado')
    search_fields = ('nombre', 'direccion', 'telefono')
    list_filter = ('id_estado',)
    fieldsets = (
        ('Datos de la Sucursal', {
            'fields': ('nombre', 'direccion', 'telefono', 'id_estado')
        }),
    )

@admin.register(Producto)
class ProductoAdmin(ModelAdmin):
    list_display = ('id', 'nombre', 'variedad', 'precio_unitario', 'disponible', 'mostrar_imagen', 'descripcion')
    search_fields = ('nombre', 'variedad', 'descripcion')
    list_filter = ('disponible', 'variedad')
    list_per_page = 12
    fieldsets = (
        ('Datos del Producto', {
            'fields': ('nombre', 'variedad', 'precio_unitario', 'disponible', 'descripcion', 'imagen')
        }),
    )
    
    def mostrar_imagen(self, obj):
        if obj.imagen:
            return format_html('<img src="{}" style="width: 60px; height: 58px;" />', obj.imagen.url)
        return "No Image"
    mostrar_imagen.short_description = 'Foto'
