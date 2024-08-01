from django.contrib import admin

# Register your models here.
from .models import CatGastos, Banco, Cuenta, Gastos

@admin.register(CatGastos)
class CatGastosAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)
    list_filter = ('nombre',)
    fieldsets = (
        ('Datos del Registro', {
            'fields': ('id','nombre',)
        }),
    )

@admin.register(Banco)
class BancoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'telefono', 'direccion')
    search_fields = ('nombre', 'telefono', 'direccion')
    list_filter = ('nombre', 'telefono', 'direccion', 'fecha_registro')
    fieldsets = (
        ('Datos del Registro', {
            'fields': ('nombre', 'telefono', 'direccion', 'fecha_registro')
        }),
    )

@admin.register(Cuenta)
class CuentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'id_banco', 'id_sucursal', 'numero_cuenta', 'saldo', 'fecha_registro')
    search_fields = ('numero_cuenta', 'saldo', 'fecha_registro', 'id_banco', 'id_sucursal')
    list_filter = ('id_banco', 'id_sucursal', 'saldo')
    fields = ('id_banco', 'id_sucursal', 'numero_cuenta', 'saldo', 'fecha_registro')

@admin.register(Gastos)
class GastosAdmin(admin.ModelAdmin):
    list_display = ('id', 'id_sucursal', 'id_cat_gastos', 'id_cuenta_banco', 'monto', 'descripcion', 'fecha')
    search_fields = ('monto', 'fecha_registro', 'id_sucursal', 'id_cat_gastos')
    list_filter = ('id_sucursal', 'id_cat_gastos', 'fecha_registro' , 'fecha')
    fieldsets = (
        ('Datos del Registro', {
            'fields': ('id_sucursal', 'id_cat_gastos', 'id_cuenta_banco', 'monto', 'descripcion', 'fecha')
        }),
    )

