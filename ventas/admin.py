from django.contrib import admin
from .models import Producto, Cliente, Agente, Ventas, Anticipo
from import_export import resources
from import_export.admin import ImportExportModelAdmin

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'variedad', )
    list_per_page = 12

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'telefono')
    list_per_page = 12
    search_fields = ('nombre',)
    
@admin.register(Agente)
class AgenteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha')
    list_per_page = 12
   
class VentasResource(resources.ModelResource):
    fields = ('fecha_salida_manifiesto', 'agente_id', 'fecha_deposito', 'carga', 'PO', 'producto', 'cantidad', 'monto', 'descripcion', 'cliente', 'fecha_registro', 'sucursal_id','cuenta')
    class Meta:
        model = Ventas
            
@admin.register(Ventas)
class VentasAdmin(ImportExportModelAdmin):
    list_display = ('fecha_salida_manifiesto', 'agente_id', 'fecha_deposito', 'carga', 'PO', 'producto', 'cantidad', 'monto', 'descripcion', 'cliente', 'fecha_registro', 'sucursal_id','cuenta')
    list_per_page = 20
    list_filter = ('fecha_salida_manifiesto', 'agente_id', 'fecha_deposito', 'carga', 'monto','cuenta')
    fiels = ('fecha_salida_manifiesto', 'agente_id', 'fecha_deposito', 'carga', 'PO', 'producto', 'cantidad', 'monto', 'descripcion', 'cliente', 'fecha_registro', 'sucursal_id','cuenta')
    
class AnticiposResource(resources.ModelResource):
    fields = ('fecha', 'cliente', 'sucursal', 'cuenta', 'monto', 'descripcion','estado_anticipo')
    class Meta:
        model = Anticipo
 
@admin.register(Anticipo)
class AnticipoAdmin(ImportExportModelAdmin):
    list_display = ('fecha', 'cliente', 'sucursal', 'cuenta', 'monto', 'descripcion','estado_anticipo')
    list_per_page = 20
    list_filter = ('fecha', 'cliente', 'sucursal', 'cuenta', 'monto', 'estado_anticipo')
    fields = ('fecha', 'cliente', 'sucursal', 'cuenta', 'monto', 'descripcion', 'estado_anticipo')        
        


