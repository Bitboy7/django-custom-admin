from django.contrib import admin
from django.http import HttpResponse
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin
# Register your models here.
from .models import CatGastos, Banco, Cuenta, Gastos, Compra
from catalogo.models import Sucursal
import openpyxl
from openpyxl.styles import NamedStyle, Font
from openpyxl.worksheet.table import Table, TableStyleInfo

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
    list_display = ('id', 'id_sucursal', 'id_cat_gastos',
                    'id_cuenta_banco', 'monto', 'descripcion', 'fecha')
    search_fields = ('monto', 'fecha_registro', 'id_sucursal', 'id_cat_gastos', 'id_cuenta_banco')
    list_filter = ('id_sucursal', 'id_cat_gastos','id_cuenta_banco', 'fecha')
    list_per_page = 20
    fieldsets = (
        ('Datos del Registro', {
            'fields': ('id_sucursal', 'id_cat_gastos', 'id_cuenta_banco', 'monto', 'descripcion', 'fecha')
        }),
    )
    
    actions = ['export_to_excel']

    def export_to_excel(self, request, queryset):
        # Crear un libro de trabajo y una hoja
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Reporte de Gastos"

        # Escribir encabezados
        headers = ["ID", "Sucursal", "Categoría", "Cuenta", "Monto", "Descripción", "Fecha"]
        ws.append(headers)

        # Escribir los datos en la hoja
        for gasto in queryset:
            ws.append([
                gasto.id,
                gasto.id_sucursal.nombre,
                gasto.id_cat_gastos.nombre,
                gasto.id_cuenta_banco.numero_cuenta,
                gasto.monto,
                gasto.descripcion,
                gasto.fecha.strftime('%Y-%m-%d')
            ])

        # Aplicar formato contable a la columna 'Monto'
        contable_style = NamedStyle(name="contable_style", number_format="#,##0.00")
        for row in ws.iter_rows(min_row=2, min_col=5, max_col=5):
            for cell in row:
                cell.style = contable_style

        # Calcular la suma de los montos y agregar una celda 'Total'
        total_monto = sum(gasto.monto for gasto in queryset)
        ws.append(["", "", "", "Total", total_monto])

        # Aplicar formato contable a la celda 'Total'
        total_cell = ws.cell(row=ws.max_row, column=5)
        total_cell.style = contable_style
        total_cell.font = Font(bold=True)

        # Aplicar formato de tabla
        tab = Table(displayName="GastosTable", ref=f"A1:G{ws.max_row}")
        style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False,
                               showLastColumn=False, showRowStripes=True, showColumnStripes=True)
        tab.tableStyleInfo = style
        ws.add_table(tab)

        # Crear una respuesta HTTP con el tipo de contenido Excel
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="reporte_gastos.xlsx"'

        # Guardar el libro de trabajo en la respuesta
        wb.save(response)

        return response

    export_to_excel.short_description = "Exportar a Excel"
    
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