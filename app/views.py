from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Sum, Avg, Max, Min
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from gastos.models import Gastos, Cuenta
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

    # Aplicar formato condicional
    red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    dxf = openpyxl.styles.differential.DifferentialStyle(fill=red_fill)
    rule = openpyxl.formatting.rule.Rule(type="expression", dxf=dxf, stopIfTrue=True)
    rule.formula = ["$D2>1000"]
    ws.conditional_formatting.add(f"D2:D{ws.max_row}", rule)

    # Ajustar ancho de columnas
    for col in ws.columns:
        max_length = 0
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[col[0].column_letter].width = max_length + 2

    # Añadir nueva hoja para resumen mensual
    ws_monthly = wb.create_sheet("Resumen Mensual")
    
    # Obtener totales mensuales
    monthly_totals = Gastos.objects.annotate(
        month=TruncMonth('fecha')
    ).values('month').annotate(
        total=Sum('monto')
    ).order_by('month')

    # Escribir encabezados
    ws_monthly.append(["Mes", "Total Gastos", "Acumulado"])

    # Escribir datos mensuales
    accumulated = 0
    monthly_data = []
    for entry in monthly_totals:
        accumulated += entry['total']
        month_str = entry['month'].strftime('%B %Y')
        ws_monthly.append([month_str, entry['total'], accumulated])
        monthly_data.append([month_str, entry['total']])

    # Aplicar formato contable
    for row in ws_monthly.iter_rows(min_row=2, min_col=2, max_col=3):
        for cell in row:
            cell.style = contable_style

    # Formato condicional para los 3 meses con más gastos
    sorted_months = sorted(monthly_data, key=lambda x: x[1], reverse=True)[:3]
    top_3_values = [item[1] for item in sorted_months]

    red_fill = PatternFill(start_color="FFE2B7", end_color="FFE2B7", fill_type="solid")
    dxf = openpyxl.styles.differential.DifferentialStyle(fill=red_fill)
    rule = openpyxl.formatting.rule.Rule(type="expression", dxf=dxf, stopIfTrue=True)
    rule.formula = [f"OR(B2>={top_3_values[0]}, B2>={top_3_values[1]}, B2>={top_3_values[2]})"]
    ws_monthly.conditional_formatting.add(f"A2:C{ws_monthly.max_row}", rule)

    # Crear gráfico de barras
    bar_chart = openpyxl.chart.BarChart()
    bar_chart.title = "Gastos Mensuales"
    bar_chart.x_axis.title = "Mes"
    bar_chart.y_axis.title = "Total Gastos"

    # Añadir datos al gráfico de barras
    data = openpyxl.chart.Reference(ws_monthly, min_col=2, min_row=1, max_row=ws_monthly.max_row, max_col=2)
    cats = openpyxl.chart.Reference(ws_monthly, min_col=1, min_row=2, max_row=ws_monthly.max_row)
    bar_chart.add_data(data, titles_from_data=True)
    bar_chart.set_categories(cats)

    # Añadir el gráfico de barras a la hoja
    ws_monthly.add_chart(bar_chart, "E2")

    # Crear gráfico de pastel
    pie_chart = openpyxl.chart.PieChart()
    pie_chart.title = "Distribución de Gastos Mensuales"

    # Añadir datos al gráfico de pastel
    pie_data = openpyxl.chart.Reference(ws_monthly, min_col=2, min_row=1, max_row=ws_monthly.max_row)
    pie_labels = openpyxl.chart.Reference(ws_monthly, min_col=1, min_row=2, max_row=ws_monthly.max_row)
    pie_chart.add_data(pie_data, titles_from_data=True)
    pie_chart.set_categories(pie_labels)

    # Añadir el gráfico de pastel a la hoja
    ws_monthly.add_chart(pie_chart, "E20")

    # Ajustar ancho de columnas
    for col in ws_monthly.columns:
        max_length = 0
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        ws_monthly.column_dimensions[col[0].column_letter].width = max_length + 2
        
    # Aplicar estilo claro a la tabla
    tab = openpyxl.worksheet.table.Table(
        displayName="GastosTableStyled", 
        ref=f"A1:E{ws.max_row-totales_cuenta.count()-3}",
        tableStyleInfo=openpyxl.worksheet.table.TableStyleInfo(
            name="TableStyleLight3",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=True
        )
    )
    ws.add_table(tab)

    current_date = datetime.now().strftime("%Y%m%d")
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="reporte_gastos_{current_date}.xlsx"'

    wb.save(response)
    return response

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