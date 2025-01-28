from django.contrib import admin
from .models import Cliente, Agente, Ventas, Anticipo
from catalogo.models import Sucursal, Pais, Producto
from gastos.models import Cuenta
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget

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
class ClienteAdmin(ImportExportModelAdmin):
    resource_class = ClienteResource
    list_display = ('id', 'nombre', 'telefono', 'correo', 'direccion', 'get_pais', 'get_bandera', 'mostrar_logotipo', 'fecha_registro')
    list_per_page = 20
    list_display_links = ('nombre',)
    list_editable = ('telefono', 'correo', 'direccion')
    search_fields = ('nombre',)

    def get_pais(self, obj):
        return obj.pais.nombre
    get_pais.short_description = 'Pais'

    def get_bandera(self, obj):
        return obj.pais.mostrar_bandera()
    get_bandera.short_description = 'Bandera'
    
@admin.register(Agente)
class AgenteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha_registro', 'telefono', 'correo', 'mostrar_bandera_pais')
    list_editable = ('telefono', 'correo')
    list_per_page = 12

    def mostrar_bandera_pais(self, obj):
        return obj.pais.mostrar_bandera()
    mostrar_bandera_pais.short_description = 'Bandera del País'
   
class VentasResource(resources.ModelResource):
    agente = fields.Field(
        column_name='agente',
        attribute='agente',
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
        attribute='sucursal',
        widget=ForeignKeyWidget(Sucursal, field='nombre'))
    
    cuenta = fields.Field(
        column_name='cuenta',
        attribute='cuenta',
        widget=ForeignKeyWidget(Cuenta, field='numero_cuenta'))

    class Meta:
        model = Ventas
        fields = ('id', 'fecha_salida_manifiesto', 'agente', 'fecha_deposito', 'carga', 'PO', 'producto', 'cantidad', 'monto', 'descripcion', 'cliente', 'fecha_registro', 'sucursal','cuenta')
        
    def dehydrate_agente(self, ventas):
        return ventas.agente_id.nombre
    
    def dehydrate_producto(self, ventas):
        return ventas.producto.variedad
    
    def dehydrate_cliente(self, ventas):
        return ventas.cliente.nombre
    
    def dehydrate_sucursal(self, ventas):
        return ventas.sucursal_id.nombre
    
    def dehydrate_cuenta(self, ventas):
        return ventas.cuenta.numero_cuenta

    def before_import_row(self, row, **kwargs):
        # Asigna un ID específico basado en un rango disponible
        if not row['id']:
            last_ventas = Ventas.objects.order_by('-id').first()
            next_id = last_ventas.id + 1 if last_ventas else 1
            row['id'] = next_id
       
@admin.register(Ventas)
class VentasAdmin(ImportExportModelAdmin):
    resource_class = VentasResource
    list_display = ('fecha_salida_manifiesto', 'agente_id', 'fecha_deposito', 'carga', 'PO', 'producto', 'cantidad', 'monto', 'descripcion', 'cliente', 'fecha_registro', 'sucursal_id','cuenta')
    list_per_page = 30
    list_filter = ('fecha_salida_manifiesto', 'agente_id', 'fecha_deposito', 'carga', 'monto','cuenta')
    fiels = ('fecha_salida_manifiesto', 'agente_id', 'fecha_deposito', 'carga', 'PO', 'producto', 'cantidad', 'monto', 'descripcion', 'cliente', 'fecha_registro', 'sucursal_id','cuenta')
    
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
    
    class Meta:
        model = Anticipo
        fields = ('id', 'fecha', 'cliente', 'sucursal', 'cuenta', 'monto', 'descripcion','estado_anticipo')
        
    def dehydrate_cliente(self, anticipo):
        return anticipo.cliente.nombre
    
    def dehydrate_sucursal(self, anticipo):
        return anticipo.sucursal.nombre
    
    def dehydrate_cuenta(self, anticipo):
        return anticipo.cuenta.numero_cuenta

    def before_import_row(self, row, **kwargs):
        # Asigna un ID específico basado en un rango disponible
        if not row['id']:
            last_anticipo = Anticipo.objects.order_by('-id').first()
            next_id = last_anticipo.id + 1 if last_anticipo else 1
            row['id'] = next_id
     
@admin.register(Anticipo)
class AnticipoAdmin(ImportExportModelAdmin):
    resource_class = AnticiposResource
    list_display = ('fecha', 'cliente', 'sucursal', 'cuenta', 'monto', 'descripcion','estado_anticipo')
    list_per_page = 20
    list_filter = ('fecha', 'cliente', 'sucursal', 'cuenta', 'monto', 'estado_anticipo')
    fields = ('fecha', 'cliente', 'sucursal', 'cuenta', 'monto', 'descripcion', 'estado_anticipo')        
        


