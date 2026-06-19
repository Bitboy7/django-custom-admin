from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib.admin import SimpleListFilter
from django.template.response import TemplateResponse
from django.urls import path
from django.http import HttpResponse
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin
from import_export.forms import ExportForm, ImportForm
from .models import CatGastos, Banco, Cuenta, Gastos, Compra, SaldoMensual
from django.utils.html import format_html
from django.utils import timezone
from catalogo.models import Sucursal, Productor, Producto
from app.widgets import MoneyWidget
from datetime import timedelta


class BancoGastoFilter(SimpleListFilter):
    title = 'Banco'
    parameter_name = 'banco'

    def lookups(self, request, model_admin):
        return [
            (str(banco.id), banco.nombre)
            for banco in Banco.objects.order_by('nombre')
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(id_cuenta_banco__id_banco_id=self.value())
        return queryset


class MontoGastoFilter(SimpleListFilter):
    title = 'Rango de monto'
    parameter_name = 'rango_monto'

    def lookups(self, request, model_admin):
        return [
            ('0-1000', '$0 - $1,000'),
            ('1000-5000', '$1,000 - $5,000'),
            ('5000-10000', '$5,000 - $10,000'),
            ('10000-50000', '$10,000 - $50,000'),
            ('50000+', '$50,000+'),
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if value == '0-1000':
            return queryset.filter(monto__amount__range=[0, 1000])
        if value == '1000-5000':
            return queryset.filter(monto__amount__range=[1000, 5000])
        if value == '5000-10000':
            return queryset.filter(monto__amount__range=[5000, 10000])
        if value == '10000-50000':
            return queryset.filter(monto__amount__range=[10000, 50000])
        if value == '50000+':
            return queryset.filter(monto__amount__gte=50000)
        return queryset


class PeriodoGastoFilter(SimpleListFilter):
    title = 'Periodo'
    parameter_name = 'periodo'

    def lookups(self, request, model_admin):
        return [
            ('hoy', 'Hoy'),
            ('semana', 'Ultimos 7 dias'),
            ('mes', 'Mes actual'),
            ('anio', 'Año actual'),
        ]

    def queryset(self, request, queryset):
        today = timezone.localdate()
        value = self.value()

        if value == 'hoy':
            return queryset.filter(fecha=today)
        if value == 'semana':
            return queryset.filter(fecha__gte=today - timedelta(days=7), fecha__lte=today)
        if value == 'mes':
            return queryset.filter(fecha__year=today.year, fecha__month=today.month)
        if value == 'anio':
            return queryset.filter(fecha__year=today.year)
        return queryset

class CatGastoResource(resources.ModelResource):
    fields = ('id', 'nombre', 'fecha_registro')
    class Meta:
        model = CatGastos

@admin.register(CatGastos)
class CatGastosAdmin(ImportExportModelAdmin, ModelAdmin):
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
class BancoAdmin(ImportExportModelAdmin, ModelAdmin):
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
class CuentaAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = CuentaResource
    import_form_class = ImportForm
    export_form_class = ExportForm
    list_display = ('id', 'mostrar_logotipo_banco', 'id_sucursal', 'numero_cuenta', 'numero_cliente', 'rfc', 'clabe')
    search_fields = ('id_banco__nombre', 'id_sucursal__nombre', 'numero_cuenta', 'numero_cliente')
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
class GastosAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = GastosResource
    import_form_class = ImportForm
    export_form_class = ExportForm
    list_display = ('id', 'id_sucursal', 'id_cat_gastos',
                    'id_cuenta_banco', 'monto', 'descripcion', 'fecha', 'fecha_registro')
    search_fields = ('descripcion', 'id_sucursal__nombre', 'id_cat_gastos__nombre', 'id_cuenta_banco__numero_cuenta', 'id_cuenta_banco__id_banco__nombre')
    list_filter = (BancoGastoFilter, 'id_sucursal', 'id_cat_gastos', 'id_cuenta_banco', MontoGastoFilter, PeriodoGastoFilter, 'fecha', 'fecha_registro')
    date_hierarchy = 'fecha'
    list_select_related = ('id_sucursal', 'id_cat_gastos', 'id_cuenta_banco', 'id_cuenta_banco__id_banco')
    list_per_page = 20
    fieldsets = (
        ('Datos del Registro', {
            'fields': ('id_sucursal', 'id_cat_gastos', 'id_cuenta_banco', 'monto', 'descripcion', 'fecha')
        }),
    )
    
    actions = ['export_to_excel']

    def export_to_excel(self, request, queryset):
        from django.http import HttpResponse
        import openpyxl
        import datetime
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter
        from openpyxl.worksheet.table import Table, TableStyleInfo
        from collections import defaultdict

        NAVY  = "1E3A5F"
        TEAL  = "1AADBC"
        LIGHT = "D6EAF8"
        WHITE = "FFFFFF"
        MONEY = '"$"#,##0.00'

        def _nav_hdr(cell, bg=NAVY):
            cell.font      = Font(bold=True, color=WHITE)
            cell.fill      = PatternFill("solid", fgColor=bg)
            cell.alignment = Alignment(horizontal="center", vertical="center")

        def _section_title(ws, row, col_start, col_end, text):
            cell = ws.cell(row=row, column=col_start, value=text)
            cell.font = Font(bold=True, color=WHITE, size=11)
            cell.fill = PatternFill("solid", fgColor=NAVY)
            cell.alignment = Alignment(horizontal="left", vertical="center")
            if col_end > col_start:
                ws.merge_cells(
                    start_row=row, start_column=col_start,
                    end_row=row,   end_column=col_end,
                )
            ws.row_dimensions[row].height = 20

        def _add_table(ws, name, hdr_row, data_end_row, col_end):
            if data_end_row < hdr_row + 1:
                return
            tab = Table(
                displayName=name,
                ref=f"A{hdr_row}:{get_column_letter(col_end)}{data_end_row}",
            )
            tab.tableStyleInfo = TableStyleInfo(
                name="TableStyleLight2",
                showFirstColumn=False, showLastColumn=False,
                showRowStripes=True,   showColumnStripes=False,
            )
            ws.add_table(tab)

        queryset = queryset.select_related(
            'id_sucursal', 'id_cat_gastos', 'id_cuenta_banco'
        ).order_by('fecha')
        data = list(queryset)

        wb = openpyxl.Workbook()

        # ── HOJA 1 — Detalle ─────────────────────────────────────────────────
        ws = wb.active
        ws.title = "Detalle"

        COLUMNS = [
            ("Fecha",        lambda g: g.fecha,                          14,  "DD/MM/YYYY"),
            ("Sucursal",     lambda g: g.id_sucursal.nombre,             22,  "@"),
            ("Categoría",    lambda g: g.id_cat_gastos.nombre,           22,  "@"),
            ("Cuenta",       lambda g: g.id_cuenta_banco.numero_cuenta,  22,  "@"),
            ("Monto",        lambda g: float(g.monto.amount),            16,  MONEY),
            ("Descripción",  lambda g: g.descripcion or "",              40,  "@"),
        ]

        for ci, (hdr, _, width, _) in enumerate(COLUMNS, 1):
            cell = ws.cell(row=1, column=ci, value=hdr)
            _nav_hdr(cell)
            ws.column_dimensions[get_column_letter(ci)].width = width

        for ri, gasto in enumerate(data, 2):
            for ci, (_, getter, _, fmt) in enumerate(COLUMNS, 1):
                cell = ws.cell(row=ri, column=ci, value=getter(gasto))
                cell.number_format = fmt
                cell.alignment = Alignment(vertical="center")

        last_data = len(data) + 1  # last row containing data

        # Tabla dinámica de Excel (activa filtros, ordenamiento y bandas)
        if data:
            tab_main = Table(
                displayName="TablaGastos",
                ref=f"A1:{get_column_letter(len(COLUMNS))}{last_data}",
            )
            tab_main.tableStyleInfo = TableStyleInfo(
                name="TableStyleMedium2",
                showFirstColumn=False, showLastColumn=False,
                showRowStripes=True,   showColumnStripes=False,
            )
            ws.add_table(tab_main)

        # Fila TOTAL fuera de la tabla
        total_r = last_data + 1
        mc = 5
        lbl = ws.cell(row=total_r, column=mc - 1, value="TOTAL")
        lbl.font = Font(bold=True)
        lbl.alignment = Alignment(horizontal="right")
        mc_ltr = get_column_letter(mc)
        tc = ws.cell(row=total_r, column=mc,
                     value=f"=SUM({mc_ltr}2:{mc_ltr}{last_data})")
        tc.number_format = MONEY
        tc.font = Font(bold=True)
        tc.fill = PatternFill("solid", fgColor=LIGHT)

        ws.freeze_panes = "A2"

        # ── HOJA 2 — Resumen ejecutivo ───────────────────────────────────────
        ws2 = wb.create_sheet("Resumen")

        if not data:
            ws2.cell(row=1, column=1, value="Sin datos seleccionados.")
        else:
            grand_total = sum(float(g.monto.amount) for g in data)
            dates = [g.fecha for g in data]
            fecha_min, fecha_max = min(dates), max(dates)
            avg = grand_total / len(data)

            by_cat   = defaultdict(lambda: {'count': 0, 'total': 0.0})
            by_suc   = defaultdict(lambda: {'count': 0, 'total': 0.0})
            by_month = defaultdict(lambda: {'count': 0, 'total': 0.0})

            for g in data:
                amt  = float(g.monto.amount)
                cat  = g.id_cat_gastos.nombre
                suc  = g.id_sucursal.nombre
                mkey = f"{g.fecha.year}-{g.fecha.month:02d}"
                by_cat[cat]['count']    += 1
                by_cat[cat]['total']    += amt
                by_suc[suc]['count']    += 1
                by_suc[suc]['total']    += amt
                by_month[mkey]['count'] += 1
                by_month[mkey]['total'] += amt

            # Anchos de columnas
            for col, w in zip('ABCD', [28, 14, 18, 14]):
                ws2.column_dimensions[col].width = w

            # ── Encabezado del reporte ────────────────────────────────────────
            r = 1
            hdr_cell = ws2.cell(row=r, column=1,
                                value="  REPORTE EJECUTIVO DE GASTOS")
            hdr_cell.font      = Font(bold=True, color=WHITE, size=14)
            hdr_cell.fill      = PatternFill("solid", fgColor=NAVY)
            hdr_cell.alignment = Alignment(horizontal="left", vertical="center")
            ws2.merge_cells(f"A{r}:D{r}")
            ws2.row_dimensions[r].height = 30
            r += 1

            sub = ws2.cell(
                row=r, column=1,
                value=(f"  Generado: {datetime.date.today().strftime('%d/%m/%Y')}"
                       f"   |   Período: {fecha_min.strftime('%d/%m/%Y')}"
                       f" – {fecha_max.strftime('%d/%m/%Y')}"),
            )
            sub.font = Font(italic=True, size=9, color="555555")
            sub.fill = PatternFill("solid", fgColor="EBF5FB")
            ws2.merge_cells(f"A{r}:D{r}")
            r += 2  # blank row separator

            # ── KPIs — (value, number_format) tuples so cells stay numeric ──
            kpis = [
                ("Total Gastos",       grand_total,     MONEY),
                ("N° de Registros",    len(data),       "0"),
                ("Promedio por Gasto", avg,             MONEY),
                ("Categorías",         len(by_cat),     "0"),
                ("Sucursales",         len(by_suc),     "0"),
                ("Meses con gastos",   len(by_month),   "0"),
            ]
            # 2 KPIs per row, 3 rows
            for i, (label, value, fmt) in enumerate(kpis):
                kpi_row = r + (i // 2)
                kpi_col = 1 + (i % 2) * 2
                lc = ws2.cell(row=kpi_row, column=kpi_col, value=label)
                lc.font      = Font(bold=True, size=9, color="666666")
                lc.alignment = Alignment(horizontal="left")
                lc.fill      = PatternFill("solid", fgColor="F8FBFD")
                vc = ws2.cell(row=kpi_row, column=kpi_col + 1, value=value)
                vc.number_format = fmt
                vc.font      = Font(bold=True, size=11, color=NAVY)
                vc.alignment = Alignment(horizontal="right")
                vc.fill      = PatternFill("solid", fgColor="F8FBFD")
            r += 3 + 1  # 3 KPI rows + blank separator

            # ── Sección: Por Categoría ────────────────────────────────────────
            _section_title(ws2, r, 1, 4, "  RESUMEN POR CATEGORÍA")
            r += 1
            for ci, h in enumerate(["Categoría", "N° Gastos", "Total", "% del Total"], 1):
                _nav_hdr(ws2.cell(row=r, column=ci, value=h), TEAL)
            cat_hdr = r
            r += 1
            cat_start = r
            for cat, v in sorted(by_cat.items(), key=lambda x: -x[1]['total']):
                pct = v['total'] / grand_total if grand_total else 0
                ws2.cell(row=r, column=1, value=cat)
                ws2.cell(row=r, column=2, value=v['count']).alignment = Alignment(horizontal="center")
                c3 = ws2.cell(row=r, column=3, value=v['total'])
                c3.number_format = MONEY
                c4 = ws2.cell(row=r, column=4, value=pct)
                c4.number_format = '0.00%'
                r += 1
            cat_end = r - 1
            # total row
            ws2.cell(row=r, column=1, value="TOTAL").font = Font(bold=True)
            ws2.cell(row=r, column=2, value=len(data)).font = Font(bold=True)
            ct = ws2.cell(row=r, column=3, value=grand_total)
            ct.number_format = MONEY
            ct.font = Font(bold=True)
            ct.fill = PatternFill("solid", fgColor=LIGHT)
            cp = ws2.cell(row=r, column=4, value=1.0)
            cp.number_format = '0.00%'
            cp.font = Font(bold=True)
            r += 2

            _add_table(ws2, "TablaCategorias", cat_hdr, cat_end, 4)

            # ── Sección: Por Sucursal ─────────────────────────────────────────
            _section_title(ws2, r, 1, 4, "  RESUMEN POR SUCURSAL")
            r += 1
            for ci, h in enumerate(["Sucursal", "N° Gastos", "Total", "% del Total"], 1):
                _nav_hdr(ws2.cell(row=r, column=ci, value=h), TEAL)
            suc_hdr = r
            r += 1
            suc_start = r
            for suc, v in sorted(by_suc.items(), key=lambda x: -x[1]['total']):
                pct = v['total'] / grand_total if grand_total else 0
                ws2.cell(row=r, column=1, value=suc)
                ws2.cell(row=r, column=2, value=v['count']).alignment = Alignment(horizontal="center")
                s3 = ws2.cell(row=r, column=3, value=v['total'])
                s3.number_format = MONEY
                s4 = ws2.cell(row=r, column=4, value=pct)
                s4.number_format = '0.00%'
                r += 1
            suc_end = r - 1
            ws2.cell(row=r, column=1, value="TOTAL").font = Font(bold=True)
            ws2.cell(row=r, column=2, value=len(data)).font = Font(bold=True)
            st = ws2.cell(row=r, column=3, value=grand_total)
            st.number_format = MONEY
            st.font = Font(bold=True)
            st.fill = PatternFill("solid", fgColor=LIGHT)
            sp = ws2.cell(row=r, column=4, value=1.0)
            sp.number_format = '0.00%'
            sp.font = Font(bold=True)
            r += 2

            _add_table(ws2, "TablaSucursales", suc_hdr, suc_end, 4)

            # ── Sección: Evolución Mensual ────────────────────────────────────
            _section_title(ws2, r, 1, 3, "  EVOLUCIÓN MENSUAL")
            r += 1
            for ci, h in enumerate(["Mes", "N° Gastos", "Total"], 1):
                _nav_hdr(ws2.cell(row=r, column=ci, value=h), TEAL)
            mon_hdr = r
            r += 1
            mon_start = r
            for mkey in sorted(by_month):
                v = by_month[mkey]
                ws2.cell(row=r, column=1, value=mkey)
                ws2.cell(row=r, column=2, value=v['count']).alignment = Alignment(horizontal="center")
                m3 = ws2.cell(row=r, column=3, value=v['total'])
                m3.number_format = MONEY
                r += 1
            mon_end = r - 1
            ws2.cell(row=r, column=1, value="TOTAL").font = Font(bold=True)
            ws2.cell(row=r, column=2, value=len(data)).font = Font(bold=True)
            mt = ws2.cell(row=r, column=3, value=grand_total)
            mt.number_format = MONEY
            mt.font = Font(bold=True)
            mt.fill = PatternFill("solid", fgColor=LIGHT)

            _add_table(ws2, "TablaMensual", mon_hdr, mon_end, 3)

            ws2.freeze_panes = "A4"

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="gastos.xlsx"'
        wb.save(response)
        return response

    export_to_excel.short_description = "Exportar a Excel (.xlsx)"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'balances/',
                self.admin_site.admin_view(self.balances_admin_view),
                name='gastos_gastos_balances',
            ),
        ]
        return custom_urls + urls

    def balances_admin_view(self, request):
        from app.services.balance_service import BalanceAnalysisService
        from django.http import JsonResponse
        from django.template.loader import render_to_string
        import json
        balance_service = BalanceAnalysisService()
        context = balance_service.get_full_context(request)
        context.update(self.admin_site.each_context(request))
        context.update({
            'title': 'Acumulado de Gastos',
            'subtitle': None,
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
        })

        is_htmx = request.headers.get('HX-Request') == 'true'

        if is_htmx:
            results_html = render_to_string(
                'admin/gastos/partials/balances_results.html',
                context,
                request=request,
            )
            response = HttpResponse(results_html)
            response['HX-Trigger'] = json.dumps({
                'showToast': {
                    'type': 'info',
                    'title': 'Filtros aplicados',
                    'message': 'La informaci&oacute;n ha sido filtrada seg&uacute;n los criterios seleccionados.'
                }
            })
            return response

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            table_html = render_to_string(
                'admin/gastos/partials/balances_table.html',
                context,
                request=request,
            )
            return JsonResponse({
                'kpis': {
                    'total_gastos': float(context.get('total_gastos') or 0),
                    'promedio_gastos': float(context.get('promedio_gastos') or 0),
                    'numero_transacciones': context.get('numero_transacciones', 0),
                    'gasto_maximo': float(context.get('gasto_maximo') or 0),
                    'gasto_minimo': float(context.get('gasto_minimo') or 0),
                    'gasto_mediano': float(context.get('gasto_mediano') or 0),
                    'categoria_gasto_maximo': context.get('categoria_gasto_maximo') or '',
                    'categoria_gasto_minimo': context.get('categoria_gasto_minimo') or '',
                },
                'table_html': table_html,
            })

        return TemplateResponse(request, 'admin/gastos/balances.html', context)
    
class ComprasResource(resources.ModelResource):
    
    productor = fields.Field(
        column_name='productor',
        attribute='productor',
        widget=ForeignKeyWidget(Productor, field='id'))
    
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
class ComprasAdmin(ImportExportModelAdmin, ModelAdmin):
        resource_class = ComprasResource
        import_form_class = ImportForm
        export_form_class = ExportForm
        list_display = ('id', 'fecha_compra','fecha_registro', 'productor', 'producto', 'cantidad', 'precio_unitario', 'monto_total', 'cuenta', 'tipo_pago')
        search_fields = ('tipo_pago', 'productor__nombre', 'producto__nombre', 'cuenta__numero_cuenta')
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
class SaldoMensualAdmin(ImportExportModelAdmin, ModelAdmin):
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
     