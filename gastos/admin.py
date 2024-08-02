from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
# Register your models here.
from .models import CatGastos, Banco, Cuenta, Gastos

@admin.register(CatGastos)
class CatGastosAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('id', 'nombre', 'fecha_registro')
    list_filter = ('nombre', 'fecha_registro')
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
    fieldsets = (
        ('Datos del Registro', {
            'fields': ('nombre', 'telefono', 'direccion', 'fecha_registro')
        }),
    )


@admin.register(Cuenta)
class CuentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'id_banco', 'id_sucursal',
                    'numero_cuenta', 'saldo', 'fecha_registro')
    search_fields = ('numero_cuenta', 'saldo',
                     'fecha_registro', 'id_banco', 'id_sucursal')
    list_filter = ('id_banco', 'id_sucursal', 'saldo')
    fields = ('id_banco', 'id_sucursal',
              'numero_cuenta', 'saldo', 'fecha_registro')

class GastosResource(resources.ModelResource):
    fields = ('id', 'id_sucursal', 'id_cat_gastos', 'id_cuenta_banco', 'monto', 'descripcion', 'fecha')
    class Meta:
        model = Gastos

@admin.register(Gastos)
class GastosAdmin(ImportExportModelAdmin):
    resorce_class = GastosResource
    list_display = ('id', 'id_sucursal', 'id_cat_gastos',
                    'id_cuenta_banco', 'monto', 'descripcion', 'fecha')
    search_fields = ('monto', 'fecha_registro', 'id_sucursal', 'id_cat_gastos')
    list_filter = ('id_sucursal', 'id_cat_gastos', 'fecha')
    fieldsets = (
        ('Datos del Registro', {
            'fields': ('id_sucursal', 'id_cat_gastos', 'id_cuenta_banco', 'monto', 'descripcion', 'fecha')
        }),
    )