from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Sum, Avg, Max, Min
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from gastos.models import Gastos, Cuenta, Compra
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics import renderPDF
from reportlab.graphics.charts.barcharts import VerticalBarChart
import openpyxl
from openpyxl.styles import PatternFill, NamedStyle, Font
from openpyxl import Workbook
import pandas as pd
import numpy as np
from datetime import datetime
import decimal
from django.contrib.auth.decorators import user_passes_test

def is_admin(user):
    return user.is_superuser

@user_passes_test(is_admin)
def export_to_excel(request):
    # Obtener parámetros de filtro
    categoria_id = request.GET.get('categoria_id')
    mes = request.GET.get('mes')
    
    # Crear un libro de trabajo y una hoja
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte de Gastos"

    # Escribir encabezados con nueva columna de suma acumulada
    headers = ["Cuenta", "Categoría", "Mes", "Total Gastos", "Suma Acumulada"]
    ws.append(headers)

    # Construir el query base
    query = Gastos.objects.values(
        'id_cuenta_banco__id', 
        'id_cuenta_banco__numero_cuenta',
        'id_cat_gastos__nombre'
    )

    # Aplicar filtros si existen
    if categoria_id:
        query = query.filter(categoria_id=categoria_id)
    if mes:
        query = query.filter(fecha__month=mes)

    # Agrupar y agregar
    balances = query.annotate(
        month=TruncMonth('fecha'),
        total_gastos=Sum('monto')
    ).order_by('id_cuenta_banco__id', 'id_cat_gastos__nombre', 'month')

    # Escribir los datos y calcular suma acumulada
    accumulated_sum = 0
    for balance in balances:
        accumulated_sum += balance['total_gastos']
        ws.append([
            balance['id_cuenta_banco__numero_cuenta'],
            balance['id_cat_gastos__nombre'],
            balance['month'].strftime('%B %Y'),
            balance['total_gastos'],
            accumulated_sum
        ])

    # Aplicar formato contable a totales y suma acumulada
    contable_style = NamedStyle(name="contable_style", number_format="$#,##0.00")
    for row in ws.iter_rows(min_row=2, min_col=4, max_col=5):
        for cell in row:
            cell.style = contable_style

    # Calcular totales por cuenta
    totales_cuenta = query.values('id_cuenta_banco__numero_cuenta').annotate(
        total=Sum('monto')
    ).order_by('id_cuenta_banco__numero_cuenta')

    # Agregar espacio y encabezado de resumen
    ws.append([])
    ws.append(["Resumen por Cuenta"])
    ws.append(["Cuenta", "", "", "Total", ""])

    # Agregar totales por cuenta con formato
    grand_total = 0
    for total in totales_cuenta:
        grand_total += total['total']
        ws.append([
            total['id_cuenta_banco__numero_cuenta'],
            "",
            "",
            total['total'],
            grand_total
        ])
        for cell in ws[ws.max_row][3:5]:
            cell.style = contable_style
            cell.font = Font(bold=True)

    # Crear una tabla dinámica
    unique_table_name = f"GastosTableStyled_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    tab = openpyxl.worksheet.table.Table(
        displayName=unique_table_name, 
        ref=f"A1:E{ws.max_row-totales_cuenta.count()-3}",
        tableStyleInfo=openpyxl.worksheet.table.TableStyleInfo(
            name="TableStyleLight13",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=True
        )
    )
    
    ws.add_table(tab)

    # Ajustar el ancho de las columnas
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column].width = adjusted_width

    # Create purchases sheet
    ws_purchases = wb.create_sheet("Reporte de Compras")
    
    # Headers for purchases
    purchase_headers = ["Fecha", "Productor", "Producto", "Cantidad", "Precio Unitario", "Monto Total", "Cuenta"]
    ws_purchases.append(purchase_headers)

    # Get purchases data
    purchases = Compra.objects.all().order_by('fecha_compra')
    
    # Write purchases data
    for purchase in purchases:
        ws_purchases.append([
            purchase.fecha_compra,
            str(purchase.productor),
            str(purchase.producto),
            purchase.cantidad,
            purchase.precio_unitario,
            purchase.monto_total,
            str(purchase.cuenta)
        ])

    # Format purchases table
    for row in ws_purchases.iter_rows(min_row=2, min_col=5, max_col=6):
        for cell in row:
            cell.style = contable_style

    # Crear una tabla dinámica para compras
    purchases_table_name = f"PurchasesTableStyled_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    purchases_tab = openpyxl.worksheet.table.Table(
        displayName=purchases_table_name, 
        ref=f"A1:G{ws_purchases.max_row}",
        tableStyleInfo=openpyxl.worksheet.table.TableStyleInfo(
            name="TableStyleLight1",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=True
        )
    )
    
    ws_purchases.add_table(purchases_tab)

    # Ajustar el ancho de las columnas en la hoja de compras
    for col in ws_purchases.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = (max_length + 2)
        ws_purchases.column_dimensions[column].width = adjusted_width

    # Modify monthly summary sheet to include both expenses and purchases
    ws_monthly = wb.create_sheet("Resumen Mensual")
    
    # Get monthly totals for both expenses and purchases
    monthly_totals = (Gastos.objects
        .annotate(month=TruncMonth('fecha'))
        .values('month')
        .annotate(gastos_total=Sum('monto'))
        .order_by('month'))

    monthly_purchases = (Compra.objects
        .annotate(month=TruncMonth('fecha_compra'))
        .values('month')
        .annotate(compras_total=Sum('monto_total'))
        .order_by('month'))

    # Combine data by month
    monthly_combined = {}
    for entry in monthly_totals:
        month = entry['month']
        monthly_combined[month] = {
            'gastos': entry['gastos_total'],
            'compras': 0,
            'total': 0
        }

    for entry in monthly_purchases:
        month = entry['month']
        if month not in monthly_combined:
            monthly_combined[month] = {
                'gastos': 0,
                'compras': entry['compras_total'],
                'total': 0
            }
        else:
            monthly_combined[month]['compras'] = entry['compras_total']

    # Calculate totals
    for month in monthly_combined:
        # Convert gastos to Decimal if it's a float
        gastos = decimal.Decimal(str(monthly_combined[month]['gastos'])) if monthly_combined[month]['gastos'] else decimal.Decimal('0')
        compras = decimal.Decimal(str(monthly_combined[month]['compras'])) if monthly_combined[month]['compras'] else decimal.Decimal('0')
        
        monthly_combined[month]['total'] = compras - gastos

    # Write headers
    ws_monthly.append(["Mes", "Gastos", "Compras", "Balance", "Acumulado", "Saldo Inicial"])

    # Write monthly data
    accumulated = decimal.Decimal('0')
    saldo_inicial = decimal.Decimal('0')
    monthly_data = []
    for month, data in sorted(monthly_combined.items()):
        accumulated += data['total']
        month_str = month.strftime('%B %Y')
        ws_monthly.append([
            month_str,
            data['gastos'],
            data['compras'], 
            data['total'],
            accumulated,
            saldo_inicial
        ])
        saldo_inicial = accumulated
        monthly_data.append([month_str, data['total']])

    # Apply accounting format
    for row in ws_monthly.iter_rows(min_row=2, min_col=2, max_col=6):
        for cell in row:
            cell.style = contable_style

    # Add total accumulated sum at the end
    total_accumulated_sum = sum(row[0] for row in ws_monthly.iter_rows(min_row=2, min_col=5, max_col=5, values_only=True))
    ws_monthly.append(["", "", "", "Total Acumulado", total_accumulated_sum, ""])
    for cell in ws_monthly[ws_monthly.max_row][4:5]:
        cell.style = contable_style
        cell.font = Font(bold=True)

    # Crear una tabla dinámica para el resumen mensual
    monthly_table_name = f"MonthlySummaryTableStyled_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    monthly_tab = openpyxl.worksheet.table.Table(
        displayName=monthly_table_name, 
        ref=f"A1:F{ws_monthly.max_row}",
        tableStyleInfo=openpyxl.worksheet.table.TableStyleInfo(
            name="TableStyleLight13",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=True
        )
    )
    
    ws_monthly.add_table(monthly_tab)

    # Ajustar el ancho de las columnas en la hoja de resumen mensual
    for col in ws_monthly.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = (max_length + 2)
        ws_monthly.column_dimensions[column].width = adjusted_width

    # Crear gráfica de gastos por categoría
    ws_chart = wb.create_sheet("Gráfica de Gastos por Categoría")
    
    # Obtener datos de gastos por categoría
    gastos_por_categoria = (Gastos.objects
        .values('id_cat_gastos__nombre')
        .annotate(total_gastos=Sum('monto'))
        .order_by('-total_gastos'))

    # Escribir encabezados
    ws_chart.append(["Categoría", "Total Gastos"])

    # Escribir datos
    for gasto in gastos_por_categoria:
        ws_chart.append([gasto['id_cat_gastos__nombre'], gasto['total_gastos']])

    # Crear gráfica de barras
    bar_chart = openpyxl.chart.BarChart()
    bar_chart.title = "Gastos por Categoría"
    bar_chart.x_axis.title = "Categoría"
    bar_chart.y_axis.title = "Total Gastos"
    
    data = openpyxl.chart.Reference(ws_chart, min_col=2, min_row=1, max_row=ws_chart.max_row)
    categories = openpyxl.chart.Reference(ws_chart, min_col=1, min_row=2, max_row=ws_chart.max_row)
    bar_chart.add_data(data, titles_from_data=True)
    bar_chart.set_categories(categories)
    
    ws_chart.add_chart(bar_chart, "E5")

    current_date = datetime.now().strftime("%Y%m%d")
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="reporte_gastos_{current_date}.xlsx"'

    # Save workbook
    wb.save(response)
    return response
    
@user_passes_test(is_admin)    
def balances_view(request):
    cuenta_id = request.GET.get('cuenta_id', '')
    year = request.GET.get('year', datetime.now().year)
    month = request.GET.get('month', datetime.now().month)
    periodo = request.GET.get('periodo', 'diario')  # 'diario', 'semanal' o 'mensual'
    dia = request.GET.get('dia', datetime.now().strftime('%Y-%m-%d'))
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')

    # Obtener los años disponibles
    available_years = Gastos.objects.dates('fecha', 'year')

    # Lista de meses
    months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

    # Filtrar y agrupar los datos de los gastos según el periodo seleccionado
    filters = {'fecha__year': year}
    if cuenta_id:
        filters['id_cuenta_banco_id'] = cuenta_id
    if month:
        filters['fecha__month'] = month

    if periodo == 'diario':
        if dia:
            filters['fecha'] = dia
        elif fecha_inicio and fecha_fin:
            filters['fecha__range'] = [fecha_inicio, fecha_fin]
        balances = Gastos.objects.filter(**filters).values(
            'id_cuenta_banco__id', 
            'id_cuenta_banco__numero_cuenta',
            'id_cuenta_banco__id_banco__nombre',
            'id_cuenta_banco__id_sucursal__nombre',
            'id_cat_gastos__nombre',
            'fecha'
        ).annotate(
            total_gastos=Sum('monto')
        ).order_by('id_cuenta_banco__id', 'fecha')
    elif periodo == 'semanal':
        balances = Gastos.objects.filter(**filters).annotate(
            semana=TruncWeek('fecha')
        ).values(
            'id_cuenta_banco__id', 
            'id_cuenta_banco__numero_cuenta',
            'id_cuenta_banco__id_banco__nombre',
            'id_cuenta_banco__id_sucursal__nombre',
            'id_cat_gastos__nombre',
            'semana'
        ).annotate(
            total_gastos=Sum('monto')
        ).order_by('id_cuenta_banco__id', 'semana')
    elif periodo == 'mensual':
        balances = Gastos.objects.filter(**filters).annotate(
            mes=TruncMonth('fecha')
        ).values(
            'id_cuenta_banco__id', 
            'id_cuenta_banco__numero_cuenta',
            'id_cuenta_banco__id_banco__nombre',
            'id_cuenta_banco__id_sucursal__nombre',
            'id_cat_gastos__nombre',
            'mes'
        ).annotate(
            total_gastos=Sum('monto')
        ).order_by('id_cuenta_banco__id', 'mes')
    else:
        balances = []

    # Calcular el acumulado de la suma de montos
    acumulado = 0
    for balance in balances:
        acumulado += balance['total_gastos']
        balance['acumulado'] = acumulado

    total_gastos = sum(balance['total_gastos'] for balance in balances)
    promedio_gastos = Gastos.objects.filter(**filters).aggregate(promedio=Avg('monto'))['promedio']
    numero_transacciones = Gastos.objects.filter(**filters).count()
    gasto_maximo = Gastos.objects.filter(**filters).aggregate(maximo=Max('monto'))['maximo']
    gasto_minimo = Gastos.objects.filter(**filters).aggregate(minimo=Min('monto'))['minimo']
    gastos = list(Gastos.objects.filter(**filters).values_list('monto', flat=True))
    gasto_mediano = np.median(gastos) if gastos else 0

    # Obtener las categorías de gasto máximo y mínimo
    categoria_gasto_maximo = Gastos.objects.filter(monto=gasto_maximo).values('id_cat_gastos__nombre').first()
    categoria_gasto_minimo = Gastos.objects.filter(monto=gasto_minimo).values('id_cat_gastos__nombre').first()

    cuentas = Cuenta.objects.all()
    context = {
        'balances': balances,
        'cuentas': cuentas,
        'selected_cuenta_id': cuenta_id,
        'selected_year': year,
        'selected_month': month,
        'selected_periodo': periodo,
        'selected_dia': dia,
        'selected_fecha_inicio': fecha_inicio,
        'selected_fecha_fin': fecha_fin,
        'available_years': available_years,
        'months': months,
        'total_gastos': total_gastos,
        'promedio_gastos': promedio_gastos,
        'numero_transacciones': numero_transacciones,
        'gasto_maximo': gasto_maximo,
        'gasto_minimo': gasto_minimo,
        'gasto_mediano': gasto_mediano,
        'categoria_gasto_maximo': categoria_gasto_maximo['id_cat_gastos__nombre'] if categoria_gasto_maximo else None,
        'categoria_gasto_minimo': categoria_gasto_minimo['id_cat_gastos__nombre'] if categoria_gasto_minimo else None
    }
    return render(request, 'balances.html', context)
