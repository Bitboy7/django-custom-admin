from django.contrib import admin
from django.contrib.admin import ModelAdmin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin
from import_export.forms import ExportForm, ImportForm
from .models import Productor, Estado, Sucursal, Pais, Producto
from django.utils.html import format_html


class PaisResource(resources.ModelResource):
    class Meta:
        model = Pais
        fields = ('id', 'siglas', 'nombre', 'moneda', 'bandera')

@admin.register(Pais)
class PaisAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = PaisResource
    import_form_class = ImportForm
    export_form_class = ExportForm
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
    id_sucursal = fields.Field(
        column_name='id_sucursal',
        attribute='id_sucursal',
        widget=ForeignKeyWidget(Sucursal, field='nombre'))

    class Meta:
        model = Productor
        fields = ('id', 'nombre_completo', 'num_cuenta', 'clabe_interbancaria', 'telefono', 'correo', 'id_sucursal', 'fecha_creacion', 'nacimiento', 'nacionalidad')

    def dehydrate_id_sucursal(self, productor):
        return productor.id_sucursal.nombre

    def before_import_row(self, row, **kwargs):
        # Asigna un ID específico basado en un rango disponible
        if not row['id']:
            last_productor = Productor.objects.order_by('-id').first()
            next_id = last_productor.id + 1 if last_productor else 1
            row['id'] = next_id
    
@admin.register(Productor)
class ProductorAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = ProductorResource
    import_form_class = ImportForm
    export_form_class = ExportForm
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
    

class EstadoResource(resources.ModelResource):
    class Meta:
        model = Estado
        fields = ('id', 'nombre', 'pais')

@admin.register(Estado)
class EstadoAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = EstadoResource
    import_form_class = ImportForm
    export_form_class = ExportForm
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


class SucursalResource(resources.ModelResource):
    class Meta:
        model = Sucursal
        fields = ('id', 'nombre', 'direccion', 'telefono', 'id_estado')

@admin.register(Sucursal)
class SucursalAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = SucursalResource
    import_form_class = ImportForm
    export_form_class = ExportForm
    list_display = ('id', 'nombre', 'direccion', 'telefono', 'id_estado')
    search_fields = ('nombre', 'direccion', 'telefono')
    list_filter = ('id_estado',)
    fieldsets = (
        ('Datos de la Sucursal', {
            'fields': ('nombre', 'direccion', 'telefono', 'id_estado')
        }),
    )


class ProductoResource(resources.ModelResource):
    class Meta:
        model = Producto
        fields = ('id', 'nombre', 'variedad', 'precio_unitario', 'disponible', 'descripcion', 'imagen')

@admin.register(Producto)
class ProductoAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = ProductoResource
    import_form_class = ImportForm
    export_form_class = ExportForm
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
