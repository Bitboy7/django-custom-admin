from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Sum
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
    tab = openpyxl.worksheet.table.Table(displayName="GastosTable", ref=f"A1:E{ws.max_row-totales_cuenta.count()-3}")
    ws.add_table(tab)

    # Aplicar formato condicional
    red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    dxf = openpyxl.styles.differential.DifferentialStyle(fill=red_fill)
    rule = openpyxl.formatting.rule.Rule(type="expression", dxf=dxf, stopIfTrue=True)
    rule.formula = ["$D2>1000"]
    ws.conditional_formatting.add(f"D2:D{ws.max_row}", rule)

    # Crear respuesta HTTP
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="reporte_gastos.xlsx"'

    wb.save(response)
    return response

def balances_view(request):
    cuenta_id = request.GET.get('cuenta_id')
    year = request.GET.get('year')
    month = request.GET.get('month')
    periodo = request.GET.get('periodo', 'diario')  # 'diario', 'semanal' o 'mensual'

    # Obtener los años disponibles
    available_years = Gastos.objects.dates('fecha', 'year')

    # Lista de meses
    months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

    # Filtrar y agrupar los datos de los gastos según el periodo seleccionado
    filters = {'id_cuenta_banco_id': cuenta_id, 'fecha__year': year}
    if month:
        filters['fecha__month'] = month

    if periodo == 'diario':
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

    cuentas = Cuenta.objects.all()
    context = {
        'balances': balances,
        'cuentas': cuentas,
        'selected_cuenta_id': cuenta_id,
        'selected_year': year,
        'selected_month': month,
        'selected_periodo': periodo,
        'available_years': available_years,
        'months': months,
        'total_gastos': total_gastos
    }
    return render(request, 'balances.html', context)