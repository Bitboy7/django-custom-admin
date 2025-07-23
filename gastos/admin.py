from django.contrib import admin
from unfold.admin import ModelAdmin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm, SelectableFieldsExportForm
from .models import CatGastos, Banco, Cuenta, Gastos, Compra, SaldoMensual
from django.utils.html import format_html
from catalogo.models import Sucursal
from app.widgets import MoneyWidget

class CatGastoResource(resources.ModelResource):
    fields = ('id', 'nombre', 'fecha_registro')
    class Meta:
        model = CatGastos

@admin.register(CatGastos)
class CatGastosAdmin(ModelAdmin, ImportExportModelAdmin):
    resource_class = CatGastoResource
    import_form_class = ImportForm
    export_form_class = ExportForm
    list_display = ('id', 'nombre')
    search_fields = ('id', 'nombre', 'fecha_registro')
    list_filter = ('nombre', 'fecha_registro')
    list_per_page = 12
    fieldsets = (
        ('Datos del Registro', {
            'fields': ('nombre', 'fecha_registro')
        }),
    )


class BancoResource(resources.ModelResource):
    class Meta:
        model = Banco
        fields = ('id', 'nombre', 'telefono', 'direccion', 'logotipo', 'fecha_registro')

@admin.register(Banco)
class BancoAdmin(ModelAdmin, ImportExportModelAdmin):
    resource_class = BancoResource
    import_form_class = ImportForm
    export_form_class = ExportForm
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


class CuentaResource(resources.ModelResource):
    class Meta:
        model = Cuenta
        fields = ('id', 'id_banco', 'id_sucursal', 'numero_cuenta', 'numero_cliente', 'rfc', 'clabe', 'fecha_registro')

@admin.register(Cuenta)
class CuentaAdmin(ModelAdmin, ImportExportModelAdmin):
    resource_class = CuentaResource
    import_form_class = ImportForm
    export_form_class = ExportForm
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
        attribute='id_sucursal',
        widget=ForeignKeyWidget(Sucursal, field='nombre'))
    
    categoria = fields.Field(
        column_name='categoria',
        attribute='id_cat_gastos',
        widget=ForeignKeyWidget(CatGastos, field='nombre'))
    
    cuenta = fields.Field(
        column_name='cuenta',
        attribute='id_cuenta_banco',
        widget=ForeignKeyWidget(Cuenta, field='numero_cuenta'))
    
    monto = fields.Field(
        column_name='monto',
        attribute='monto',
        widget=MoneyWidget())
    
    class Meta:
        model = Gastos
        fields = ('id', 'sucursal', 'categoria', 'cuenta', 'monto', 'descripcion', 'fecha')
        import_id_fields = ('id',)

    def dehydrate_categoria(self, gasto):
        return gasto.id_cat_gastos.nombre
    
    def dehydrate_sucursal(self, gasto):
        return gasto.id_sucursal.nombre
    
    def dehydrate_cuenta(self, gasto):
        return gasto.id_cuenta_banco.numero_cuenta

@admin.register(Gastos)
class GastosAdmin(ModelAdmin, ImportExportModelAdmin):
    resource_class = GastosResource
    import_form_class = ImportForm
    export_form_class = ExportForm
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
    from catalogo.models import Productor, Producto  # Add this import at the top
    
    productor = fields.Field(
        column_name='productor',
        attribute='productor',
        widget=ForeignKeyWidget(Productor, field='nombre_completo'))
    
    producto = fields.Field(
        column_name='producto',
        attribute='producto',
        widget=ForeignKeyWidget(Producto, field='nombre'))
    
    cuenta = fields.Field(
        column_name='cuenta',
        attribute='cuenta',
        widget=ForeignKeyWidget(Cuenta, field='numero_cuenta'))
    
    precio_unitario = fields.Field(
        column_name='precio_unitario',
        attribute='precio_unitario',
        widget=MoneyWidget())
    
    monto_total = fields.Field(
        column_name='monto_total',
        attribute='monto_total',
        widget=MoneyWidget())
    
    class Meta:
        model = Compra
        fields = ('id', 'fecha_compra', 'productor', 'producto', 'cantidad', 'precio_unitario', 'monto_total', 'fecha_registro', 'cuenta', 'tipo_pago')
        import_id_fields = ('id',)
        
    def dehydrate_productor(self, compra):
        return compra.productor.nombre_completo
    
    def dehydrate_producto(self, compra):
        return compra.producto.nombre
    
    def dehydrate_cuenta(self, compra):
        return compra.cuenta.numero_cuenta if compra.cuenta else ""
    
@admin.register(Compra)
class ComprasAdmin(ModelAdmin, ImportExportModelAdmin):
        resource_class = ComprasResource
        import_form_class = ImportForm
        export_form_class = ExportForm
        list_display = ('id', 'fecha_compra','fecha_registro', 'productor', 'producto', 'cantidad', 'precio_unitario', 'monto_total', 'cuenta', 'tipo_pago')
        search_fields = ('fecha_compra',  'monto_total', 'productor', 'producto', 'cuenta','tipo_pago')
        list_filter = ('fecha_compra', 'productor', 'producto', 'monto_total')
        list_per_page = 20
        fieldsets = (
            ('Datos del Registro', {
                'fields': ('fecha_compra', 'productor', 'producto', 'cantidad', 'precio_unitario', 'monto_total', 'cuenta', 'tipo_pago')
            }),
        )
        
        class Media:
            js = (
                'js/compra_calculator.js',
                'js/scripts.js',
            )
            css = {
                'all': ('css/admin_custom.css',)
            }
 
class SaldoMensualResource(resources.ModelResource):
    cuenta = fields.Field(
            column_name='cuenta',
            attribute='cuenta',
            widget=ForeignKeyWidget(Cuenta, field='numero_cuenta'))
    
    saldo_inicial = fields.Field(
        column_name='saldo_inicial',
        attribute='saldo_inicial',
        widget=MoneyWidget())
    
    saldo_final = fields.Field(
        column_name='saldo_final',
        attribute='saldo_final',
        widget=MoneyWidget())
    
    class Meta:
        model = SaldoMensual
        fields = ('id', 'cuenta', 'año', 'mes', 'saldo_inicial', 'saldo_final', 'fecha_registro', 'ultima_modificacion')
        import_id_fields = ('id',)
        
    def dehydrate_cuenta(self, saldo):
        return saldo.cuenta.numero_cuenta
          
@admin.register(SaldoMensual)
class SaldoMensualAdmin(ModelAdmin, ImportExportModelAdmin):
    resource_class = SaldoMensualResource
    import_form_class = ImportForm
    export_form_class = ExportForm
    list_display = ('cuenta', 'año', 'mes', 'saldo_inicial', 'saldo_final', 'fecha_registro', 'ultima_modificacion')
    search_fields = ('cuenta__numero_cuenta', 'año', 'mes')
    list_filter = ('cuenta', 'año', 'mes')
    list_per_page = 12
    fieldsets = (
        ('Datos del Registro', {
            'fields': ('cuenta', 'año', 'mes', 'saldo_inicial', 'saldo_final')
        }),
    )     
     