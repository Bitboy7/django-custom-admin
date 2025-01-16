from django.contrib import admin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin
from .models import CatGastos, Banco, Cuenta, Gastos, Compra, SaldoMensual
from django.utils.html import format_html
from catalogo.models import Sucursal
from django.contrib import admin

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
    list_display = ('id', 'nombre', 'telefono', 'direccion', 'fecha_registro', 'mostrar_logotipo')
    search_fields = ('nombre', 'telefono', 'direccion')
    list_filter = ('nombre', 'telefono', 'direccion', 'fecha_registro')
    list_per_page = 12
    fieldsets = (
        ('Información General', {
            'fields': ('nombre', 'telefono', 'direccion')
        }),
        ('Imagen', {
            'fields': ('logotipo',),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('fecha_registro',),
            'classes': ('collapse',)
        })
    )

@admin.register(Cuenta)
class CuentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'mostrar_logotipo_banco', 'id_sucursal', 'numero_cuenta', 'numero_cliente', 'rfc', 'clabe')
    search_fields = ('id_banco', 'id_sucursal', 'numero_cuenta', 'numero_cliente',)
    list_filter = ('id_banco', 'id_sucursal', 'numero_cuenta', 'numero_cliente', 'rfc')
    list_per_page = 12
    fieldsets = (
        ('Datos de la Cuenta', {
            'fields': ('id_banco', 'id_sucursal', 'numero_cuenta', 'numero_cliente', 'rfc', 'clabe')
        }),
        ('Metadatos', {
            'fields': ('fecha_registro',),
            'classes': ('collapse',)
        })
    )
    
    def mostrar_logotipo_banco(self, obj):
        return obj.id_banco.mostrar_logotipo()
    mostrar_logotipo_banco.short_description = 'Banco'
    
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
    list_display = ('id', 'id_sucursal', 'id_cat_gastos',
                    'id_cuenta_banco', 'monto', 'descripcion', 'fecha', 'fecha_registro')
    search_fields = ('id' ,'monto', 'fecha_registro', 'id_sucursal', 'id_cat_gastos', 'id_cuenta_banco')
    list_filter = ('id_sucursal', 'id_cat_gastos','id_cuenta_banco', 'fecha')
    list_per_page = 20
    fieldsets = (
        ('Datos del Registro', {
            'fields': ('id_sucursal', 'id_cat_gastos', 'id_cuenta_banco', 'monto', 'descripcion', 'fecha')
        }),
    )
    
    actions = ['export_to_excel']
    
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
        list_display = ('id', 'fecha_compra', 'productor', 'producto', 'cantidad', 'precio_unitario', 'monto_total', 'cuenta', 'tipo_pago')
        search_fields = ('fecha_compra',  'monto_total', 'productor', 'producto', 'cuenta','tipo_pago')
        list_filter = ('fecha_compra', 'productor', 'producto', 'monto_total')
        list_per_page = 20
        fieldsets = (
            ('Datos del Registro', {
                'fields': ('fecha_compra', 'productor', 'producto', 'cantidad', 'precio_unitario', 'monto_total', 'cuenta', 'tipo_pago')
            }),
        )
 
class SaldoMensualResource(resources.ModelResource):
    cuenta = fields.Field(
            column_name='cuenta',
            attribute='cuenta',
            widget=ForeignKeyWidget(Cuenta, field='numero_cuenta'))
    
    class Meta:
        model = SaldoMensual
        fields = ('id', 'cuenta', 'año', 'mes', 'saldo_inicial', 'saldo_final', 'fecha_registro', 'ultima_modificacion')
        
    def dehydrate_cuenta(self, saldo):
        return saldo.cuenta.numero_cuenta
          
@admin.register(SaldoMensual)
class SaldoMensualAdmin(ImportExportModelAdmin):
    list_display = ('cuenta', 'año', 'mes', 'saldo_inicial', 'saldo_final', 'fecha_registro', 'ultima_modificacion')
    search_fields = ('cuenta__numero_cuenta', 'año', 'mes')
    list_filter = ('cuenta', 'año', 'mes')
    list_per_page = 12
    fieldsets = (
        ('Datos del Registro', {
            'fields': ('cuenta', 'año', 'mes', 'saldo_inicial', 'saldo_final')
        }),
    )     
     