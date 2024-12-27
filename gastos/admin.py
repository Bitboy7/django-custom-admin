from django.contrib import admin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin
# Register your models here.
from .models import CatGastos, Banco, Cuenta, Gastos, Compra
from catalogo.models import Sucursal

class CatGastoResource(resources.ModelResource):
    fields = ('id', 'nombre', 'fecha_registro')
    class Meta:
        model = CatGastos

@admin.register(CatGastos)
class CatGastosAdmin(ImportExportModelAdmin):
    resource_class = CatGastoResource
    list_display = ('id', 'nombre')
    search_fields = ('id', 'nombre', 'fecha_registro')
    list_filter = ('nombre', 'fecha_registro')
    list_per_page = 12
    fieldsets = (
        ('Datos del Registro', {
            'fields': ('nombre', 'fecha_registro')
        }),
    )

@admin.register(Banco)
class BancoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'telefono', 'direccion')
    search_fields = ('nombre', 'telefono', 'direccion')
    list_filter = ('nombre', 'telefono', 'direccion', 'fecha_registro')
    list_per_page = 12
    fieldsets = (
        ('Datos del Registro', {
            'fields': ('nombre', 'telefono', 'direccion', 'fecha_registro')
        }),
    )

@admin.register(Cuenta)
class CuentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'id_banco', 'id_sucursal',
                    'numero_cuenta', 'fecha_registro', 'numero_cliente', 'rfc', 'clabe')
    search_fields = ('numero_cuenta',
                     'fecha_registro', 'id_banco', 'id_sucursal')
    list_filter = ('id_banco', 'id_sucursal')
    list_per_page = 12
    fields = ('id_banco', 'id_sucursal',
              'numero_cuenta', 'fecha_registro', 'numero_cliente', 'rfc', 'clabe')

class GastosResource(resources.ModelResource):
    sucursal = fields.Field(
        column_name='sucursal',
        attribute='sucursal',
        widget=ForeignKeyWidget(Sucursal, field='nombre'))
    
    categoria = fields.Field(
        column_name='categoria',
        attribute='categoria',
        widget=ForeignKeyWidget(CatGastos, field='nombre'))
    
    cuenta = fields.Field(
        column_name='cuenta',
        attribute='cuenta',
        widget=ForeignKeyWidget(Cuenta, field='numero_cuenta'))
    
    class Meta:
        model = Gastos
        fields = ('id', 'sucursal', 'categoria', 'cuenta', 'monto', 'descripcion', 'fecha')

    def dehydrate_categoria(self, gasto):
        return gasto.id_cat_gastos.nombre
    
    def dehydrate_sucursal(self, gasto):
        return gasto.id_sucursal.nombre
    
    def dehydrate_cuenta(self, gasto):
        return gasto.id_cuenta_banco.numero_cuenta

@admin.register(Gastos)
class GastosAdmin(ImportExportModelAdmin):
    resource_class = GastosResource
    list_display = ('id', 'id_sucursal__nombre', 'id_cat_gastos__nombre',
                    'id_cuenta_banco', 'monto', 'descripcion', 'fecha')
    search_fields = ('monto', 'fecha_registro', 'id_sucursal', 'id_cat_gastos')
    list_filter = ('id_sucursal', 'id_cat_gastos', 'fecha')
    list_per_page = 20
    fieldsets = (
        ('Datos del Registro', {
            'fields': ('id_sucursal', 'id_cat_gastos', 'id_cuenta_banco', 'monto', 'descripcion', 'fecha')
        }),
    )
    
class ComprasResource(resources.ModelResource):
    productor = fields.Field(
            column_name='productor',
            attribute='productor',
            widget=ForeignKeyWidget(Sucursal, field='nombre'))
        
    producto = fields.Field(
            column_name='producto',
            attribute='producto',
            widget=ForeignKeyWidget(CatGastos, field='nombre'))
        
    cuenta = fields.Field(
            column_name='cuenta',
            attribute='cuenta',
            widget=ForeignKeyWidget(Cuenta, field='numero_cuenta'))
    
    class Meta:
         model = Compra
         fields = ('id', 'fecha_compra', 'productor', 'producto', 'cantidad', 'precio_unitario', 'monto_total', 'fecha_registro', 'cuenta')
         
    def dehydrate_productor(self, compra):
         return compra.productor.nombre
     
    def dehydrate_producto(self, compra):
         return compra.producto.nombre
     
    def dehydrate_cuenta(self, compra):
         return compra.cuenta.numero_cuenta    

@admin.register(Compra)
class ComprasAdmin(ImportExportModelAdmin):
        resource_class = ComprasResource
        list_display = ('id', 'fecha_compra', 'productor', 'producto', 'cantidad', 'precio_unitario', 'monto_total', 'cuenta')
        search_fields = ('fecha_compra',  'monto_total')
        list_filter = ('fecha_compra', 'productor', 'producto', 'monto_total')
        list_per_page = 20
        fieldsets = (
            ('Datos del Registro', {
                'fields': ('fecha_compra', 'productor', 'producto', 'cantidad', 'precio_unitario', 'monto_total', 'cuenta')
            }),
        )