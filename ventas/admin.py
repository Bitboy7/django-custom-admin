from django.contrib import admin
from .models import Producto, Cliente, Agente, Ventas

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'variedad')

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'telefono', 'correo', 'pais_id')
    
@admin.register(Agente)
class AgenteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha')
    
@admin.register(Ventas)
class VentasAdmin(admin.ModelAdmin):
    list_display = ('fecha_salida_manifiesto', 'agente_id', 'fecha_deposito', 'carga', 'PO', 'producto', 'caja', 'monto', 'descripcion', 'cliente', 'fecha_registro', 'sucursal_id')
    



