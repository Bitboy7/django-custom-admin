from django.contrib import admin
from django.contrib.admin import ModelAdmin
from .models import Cliente, Agente, Ventas, Anticipo, TerminoCredito, MercadoDestino, PagoVenta
from catalogo.models import Sucursal, Pais, Producto
from gastos.models import Cuenta
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.forms import ExportForm, ImportForm
from app.widgets import MoneyWidget
from django.utils.html import format_html

class ClienteResource(resources.ModelResource):
    pais = fields.Field(    
        column_name='pais',
        attribute='pais',
        widget=ForeignKeyWidget(Pais, field='nombre'))
    
    class Meta:
        model = Cliente
        fields = ('id', 'nombre', 'telefono', 'correo', 'direccion', 'pais', 'fecha_registro')
    
    def dehydrate_pais(self, cliente):
        return cliente.pais.nombre
    
    def before_import_row(self, row, **kwargs):
        # Asigna un ID específico basado en un rango disponible
        if not row['id']:
            last_cliente = Cliente.objects.order_by('-id').first()
            next_id = last_cliente.id + 1 if last_cliente else 1
            row['id'] = next_id
        

@admin.register(Cliente)
class ClienteAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = ClienteResource
    import_form_class = ImportForm
    export_form_class = ExportForm
    
    list_display = (
        'nombre', 'get_pais', 'tipo_cliente', 'limite_credito', 
        'calificacion_credito', 'get_credito_disponible', 'activo'
    )
    
    list_filter = ('tipo_cliente', 'calificacion_credito', 'mercado_destino', 'activo', 'pais')
    search_fields = ('nombre', 'correo')
    list_per_page = 20
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'telefono', 'correo', 'direccion', 'imagen')
        }),
        ('Ubicación y Mercado', {
            'fields': ('pais', 'mercado_destino')
        }),
        ('Configuración de Crédito', {
            'fields': ('tipo_cliente', 'limite_credito', 'termino_credito_predeterminado', 
                      'calificacion_credito')
        }),
        ('Estado', {
            'fields': ('activo', 'fecha_registro'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('fecha_registro',)

    def get_pais(self, obj):
        return obj.pais.nombre
    get_pais.short_description = 'País'

    def get_bandera(self, obj):
        return obj.pais.mostrar_bandera()
    get_bandera.short_description = 'Bandera'
    
    def get_credito_disponible(self, obj):
        if obj.tipo_cliente == 'Contado':
            return 'N/A'
        disponible = obj.credito_disponible()
        color = 'green' if disponible > 0 else 'red'
        return format_html(
            '<span style="color: {};">${:,.2f}</span>',
            color, disponible
        )
    get_credito_disponible.short_description = 'Crédito Disponible'

# Inline para PagoVenta - debe definirse antes de VentasAdmin
class PagoVentaInline(admin.TabularInline):
    model = PagoVenta
    extra = 0
    readonly_fields = ('fecha_registro',)
    fields = ('fecha_pago', 'monto_pago', 'cuenta_destino', 'metodo_pago', 'referencia', 'notas')
    
@admin.register(Agente)
class AgenteAdmin(ModelAdmin):
    list_display = ('nombre', 'fecha_registro')
    list_per_page = 12
   
class VentasResource(resources.ModelResource):
    agente = fields.Field(
        column_name='agente',
        attribute='agente_id',
        widget=ForeignKeyWidget(Agente, field='nombre'))
    
    producto = fields.Field(    
        column_name='producto',
        attribute='producto',
        widget=ForeignKeyWidget(Producto, field='variedad'))
    
    cliente = fields.Field(
        column_name='cliente',
        attribute='cliente',
        widget=ForeignKeyWidget(Cliente, field='nombre'))
    
    sucursal = fields.Field(
        column_name='sucursal',
        attribute='sucursal_id',
        widget=ForeignKeyWidget(Sucursal, field='nombre'))
    
    cuenta = fields.Field(
        column_name='cuenta',
        attribute='cuenta',
        widget=ForeignKeyWidget(Cuenta, field='numero_cuenta'))
    
    monto = fields.Field(
        column_name='monto',
        attribute='monto',
        widget=MoneyWidget())

    class Meta:
        model = Ventas
        fields = ('id', 'fecha_salida_manifiesto', 'agente', 'fecha_deposito', 'carga', 'PO', 'producto', 'cantidad', 'monto', 'descripcion', 'cliente', 'fecha_registro', 'sucursal','cuenta')
        import_id_fields = ('id',)
        
    def dehydrate_agente(self, ventas):
        return ventas.agente_id.nombre
    
    def dehydrate_producto(self, ventas):
        return ventas.producto.variedad
    
    def dehydrate_cliente(self, ventas):
        return ventas.cliente.nombre
    
    def dehydrate_sucursal(self, ventas):
        return ventas.sucursal_id.nombre
    
    def dehydrate_cuenta(self, ventas):
        return ventas.cuenta.numero_cuenta if ventas.cuenta else ""

    def before_import_row(self, row, **kwargs):
        # Asigna un ID específico basado en un rango disponible
        if not row['id']:
            last_ventas = Ventas.objects.order_by('-id').first()
            next_id = last_ventas.id + 1 if last_ventas else 1
            row['id'] = next_id
       
@admin.register(Ventas)
class VentasAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = VentasResource
    import_form_class = ImportForm
    export_form_class = ExportForm
    
    list_display = (
        'fecha_salida_manifiesto', 'carga', 'cliente', 'monto', 
        'modalidad_pago', 'get_estado_cobranza', 'get_dias_vencimiento', 
        'tipo_venta', 'get_mercado_destino'
    )
    
    list_filter = (
        'modalidad_pago', 'estado_cobranza', 'tipo_venta', 
        'fecha_salida_manifiesto', 'mercado_destino', 'termino_credito'
    )
    
    search_fields = ('carga', 'cliente__nombre', 'producto__variedad', 'PO')
    
    list_per_page = 30
    
    inlines = [PagoVentaInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('fecha_salida_manifiesto', 'agente_id', 'fecha_deposito', 
                      'carga', 'PO', 'pedimento')
        }),
        ('Producto y Cliente', {
            'fields': ('producto', 'cantidad', 'monto', 'cliente', 
                      'sucursal_id', 'descripcion')
        }),
        ('Modalidad de Pago', {
            'fields': ('modalidad_pago', 'termino_credito', 'fecha_vencimiento',
                      'estado_cobranza', 'monto_pagado')
        }),
        ('Mercado y Exportación', {
            'fields': ('tipo_venta', 'mercado_destino', 'incoterm', 
                      'moneda_venta', 'tipo_cambio')
        }),
        ('Contabilidad', {
            'fields': ('cuenta', 'anticipo'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('fecha_registro', 'monto_pagado')
    
    def get_estado_cobranza(self, obj):
        colors = {
            'Pagado': 'green',
            'Pendiente': 'orange', 
            'Parcial': 'blue',
            'Vencido': 'red',
            'Incobrable': 'darkred'
        }
        color = colors.get(obj.estado_cobranza, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_estado_cobranza_display()
        )
    get_estado_cobranza.short_description = 'Estado Cobranza'
    
    def get_dias_vencimiento(self, obj):
        if obj.modalidad_pago == 'Contado':
            return '-'
        dias = obj.dias_vencido()
        if dias > 0:
            return format_html('<span style="color: red;">+{} días</span>', dias)
        elif dias < 0:
            return format_html('<span style="color: green;">{} días</span>', abs(dias))
        else:
            return 'Vence hoy'
    get_dias_vencimiento.short_description = 'Vencimiento'
    
    def get_mercado_destino(self, obj):
        return obj.mercado_destino.nombre if obj.mercado_destino else obj.tipo_venta
    get_mercado_destino.short_description = 'Mercado'

# Administración para PagoVenta
class PagoVentaResource(resources.ModelResource):
    venta = fields.Field(
        column_name='venta',
        attribute='venta',
        widget=ForeignKeyWidget(Ventas, field='carga'))
    
    cuenta_destino = fields.Field(
        column_name='cuenta_destino',
        attribute='cuenta_destino',
        widget=ForeignKeyWidget(Cuenta, field='numero_cuenta'))
    
    monto_pago = fields.Field(
        column_name='monto_pago',
        attribute='monto_pago',
        widget=MoneyWidget())

    class Meta:
        model = PagoVenta
        fields = ('id', 'fecha_pago', 'venta', 'monto_pago', 'cuenta_destino', 'metodo_pago', 'referencia')
        import_id_fields = ('id',)

@admin.register(PagoVenta)
class PagoVentaAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = PagoVentaResource
    list_display = ('fecha_pago', 'get_venta_info', 'monto_pago', 'metodo_pago', 'referencia', 'fecha_registro')
    list_filter = ('fecha_pago', 'metodo_pago', 'venta__cliente')
    search_fields = ('venta__carga', 'venta__cliente__nombre', 'referencia')
    date_hierarchy = 'fecha_pago'
    
    def get_venta_info(self, obj):
        return f"{obj.venta.carga} - {obj.venta.cliente.nombre}"
    get_venta_info.short_description = 'Venta - Cliente'
    
class AnticiposResource(resources.ModelResource):
    cliente = fields.Field(
        column_name='cliente',
        attribute='cliente',
        widget=ForeignKeyWidget(Cliente, field='nombre'))
    
    sucursal = fields.Field(
        column_name='sucursal',
        attribute='sucursal',
        widget=ForeignKeyWidget(Sucursal, field='nombre'))
    
    cuenta = fields.Field(
        column_name='cuenta',
        attribute='cuenta',
        widget=ForeignKeyWidget(Cuenta, field='numero_cuenta'))
    
    monto = fields.Field(
        column_name='monto',
        attribute='monto',
        widget=MoneyWidget())
    
    class Meta:
        model = Anticipo
        fields = ('id', 'fecha', 'cliente', 'sucursal', 'cuenta', 'monto', 'descripcion','estado_anticipo')
        import_id_fields = ('id',)
        
    def dehydrate_cliente(self, anticipo):
        return anticipo.cliente.nombre
    
    def dehydrate_sucursal(self, anticipo):
        return anticipo.sucursal.nombre
    
    def dehydrate_cuenta(self, anticipo):
        return anticipo.cuenta.numero_cuenta if anticipo.cuenta else ""

    def before_import_row(self, row, **kwargs):
        # Asigna un ID específico basado en un rango disponible
        if not row['id']:
            last_anticipo = Anticipo.objects.order_by('-id').first()
            next_id = last_anticipo.id + 1 if last_anticipo else 1
            row['id'] = next_id
     
@admin.register(Anticipo)
class AnticipoAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = AnticiposResource
    import_form_class = ImportForm
    export_form_class = ExportForm
    list_display = ('fecha', 'cliente', 'sucursal', 'cuenta', 'monto', 'descripcion','estado_anticipo')
    list_per_page = 20
    list_filter = ('fecha', 'cliente', 'sucursal', 'cuenta', 'monto', 'estado_anticipo')
    fields = ('fecha', 'cliente', 'sucursal', 'cuenta', 'monto', 'descripcion', 'estado_anticipo')        

# Administración para TerminoCredito
@admin.register(TerminoCredito)
class TerminoCreditoAdmin(ModelAdmin):
    list_display = ('nombre', 'dias_credito', 'tasa_interes_mensual', 'activo', 'fecha_creacion')
    list_filter = ('activo', 'dias_credito')
    search_fields = ('nombre',)
    list_editable = ('activo',)
    ordering = ['dias_credito']

# Administración para MercadoDestino
class PaisInline(admin.TabularInline):
    model = MercadoDestino.paises.through
list_editable = ('activo',)
inlines = [PaisInline]
exclude = ('paises',)

# Inline para PagoVenta - debe definirse antes de VentasAdmin
class PagoVentaInline(admin.TabularInline):
    model = PagoVenta
    extra = 0
    readonly_fields = ('fecha_registro',)
    fields = ('fecha_pago', 'monto_pago', 'cuenta_destino', 'metodo_pago', 'referencia', 'notas')