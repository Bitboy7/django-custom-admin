from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Sum
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from gastos.models import Gastos
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics import renderPDF
from reportlab.graphics.charts.barcharts import VerticalBarChart
import openpyxl
from openpyxl.styles import PatternFill, Font
from openpyxl import Workbook

def reportes(request):
    # Obtener los parámetros de filtro de la solicitud
    cuenta_id = request.GET.get('cuenta_id')
    periodo = request.GET.get('periodo')  # 'diario', 'semanal' o 'mensual'

    # Crear una respuesta HTTP con el tipo de contenido PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_gastos.pdf"'

    # Crear un objeto canvas
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    # Título del reporte
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, height - 50, "Reporte de Gastos por Cuenta")

    # Filtrar y agrupar los datos de los gastos según el periodo seleccionado
    if periodo == 'diario':
        gastos = Gastos.objects.filter(id_cuenta_banco_id=cuenta_id).values('id_cuenta_banco__numero_cuenta').annotate(
            periodo=TruncDay('fecha'),
            total_gastos=Sum('monto')
        ).order_by('id_cuenta_banco__numero_cuenta', 'periodo')
    elif periodo == 'semanal':
        gastos = Gastos.objects.filter(id_cuenta_banco_id=cuenta_id).values('id_cuenta_banco__numero_cuenta').annotate(
            periodo=TruncWeek('fecha'),
            total_gastos=Sum('monto')
        ).order_by('id_cuenta_banco__numero_cuenta', 'periodo')
    else:  # mensual
        gastos = Gastos.objects.filter(id_cuenta_banco_id=cuenta_id).values('id_cuenta_banco__numero_cuenta').annotate(
            periodo=TruncMonth('fecha'),
            total_gastos=Sum('monto')
        ).order_by('id_cuenta_banco__numero_cuenta', 'periodo')

    # Configurar la posición inicial
    y = height - 100
    p.setFont("Helvetica", 12)

    # Escribir los datos en el PDF con estilo mejorado
    for gasto in gastos:
        p.setFont("Helvetica-Bold", 12)
        p.setFillColor(colors.blue)
        p.drawString(100, y, f"Cuenta: {gasto['id_cuenta_banco__numero_cuenta']}")
        p.setFont("Helvetica", 12)
        p.setFillColor(colors.black)
        p.drawString(300, y, f"Periodo: {gasto['periodo'].strftime('%Y-%m-%d')}")
        p.setFont("Helvetica-Bold", 12)
        p.setFillColor(colors.red)
        p.drawString(500, y, f"Total Gastos: ${gasto['total_gastos']:.2f}")
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 50

    # Crear un gráfico de barras
    drawing = Drawing(400, 200)
    data = []
    labels = []
    for gasto in gastos:
        labels.append(gasto['periodo'].strftime('%Y-%m-%d'))
        data.append(gasto['total_gastos'])

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = [data]
    bc.strokeColor = colors.black
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = max(data) + 100
    bc.valueAxis.valueStep = 100
    bc.categoryAxis.labels.boxAnchor = 'ne'
    bc.categoryAxis.labels.dx = -10
    bc.categoryAxis.labels.dy = -2
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.categoryNames = labels
    bc.bars[0].fillColor = colors.green

    drawing.add(bc)
    renderPDF.draw(drawing, p, 100, y - 200)

    # Finalizar el PDF
    p.showPage()
    p.save()

    return response

def export_to_excel(request):
        # Crear un libro de trabajo y una hoja
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Reporte de Gastos"

        # Escribir encabezados
        headers = ["Cuenta", "Mes", "Total Gastos"]
        ws.append(headers)

        # Obtener los datos de los gastos
        balances = Gastos.objects.values('id_cuenta_banco__id', 'id_cuenta_banco__numero_cuenta').annotate(
            month=TruncMonth('fecha'),
            total_gastos=Sum('monto')
        ).order_by('id_cuenta_banco__id', 'month')

        # Escribir los datos en la hoja
        for balance in balances:
            ws.append([
                balance['id_cuenta_banco__numero_cuenta'],
                balance['month'].strftime('%B %Y'),
                balance['total_gastos']
            ])

        # Aplicar colores según el monto de gastos
        for row in ws.iter_rows(min_row=2, min_col=3, max_col=3):
            for cell in row:
                if cell.value > 1000:  # Umbral para gastos altos
                    cell.fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
                else:
                    cell.fill = PatternFill(start_color="00FF00", end_color="00FF00", fill_type="solid")

        # Crear una respuesta HTTP con el tipo de contenido Excel
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="reporte_gastos.xlsx"'

        # Guardar el libro de trabajo en la respuesta
        wb.save(response)

        return response
    
from gastos.models import Cuenta

from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Sum
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from gastos.models import Gastos, Cuenta

def balances_view(request):
    cuenta_id = request.GET.get('cuenta_id')
    periodo = request.GET.get('periodo', 'mensual')  # 'diario', 'semanal' o 'mensual'

    # Filtrar y agrupar los datos de los gastos según el periodo seleccionado
    if periodo == 'diario':
        balances = Gastos.objects.filter(id_cuenta_banco_id=cuenta_id).values('id_cuenta_banco__id', 'id_cuenta_banco__numero_cuenta').annotate(
            periodo=TruncDay('fecha'),
            total_gastos=Sum('monto')
        ).order_by('id_cuenta_banco__id', 'periodo')
    elif periodo == 'semanal':
        balances = Gastos.objects.filter(id_cuenta_banco_id=cuenta_id).values('id_cuenta_banco__id', 'id_cuenta_banco__numero_cuenta').annotate(
            periodo=TruncWeek('fecha'),
            total_gastos=Sum('monto')
        ).order_by('id_cuenta_banco__id', 'periodo')
    else:  # mensual
        balances = Gastos.objects.filter(id_cuenta_banco_id=cuenta_id).values('id_cuenta_banco__id', 'id_cuenta_banco__numero_cuenta').annotate(
            periodo=TruncMonth('fecha'),
            total_gastos=Sum('monto')
        ).order_by('id_cuenta_banco__id', 'periodo')

    cuentas = Cuenta.objects.all()
    context = {'balances': balances, 'cuentas': cuentas, 'selected_cuenta_id': cuenta_id, 'selected_periodo': periodo}
    return render(request, 'balances.html', context)

def exportar_gastos_excel(request):
    # Crear un libro de trabajo y una hoja
    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte de Gastos"

    # Agregar encabezados
    headers = ["Cuenta", "Total Gastos"]
    ws.append(headers)

    # Aplicar estilo a los encabezados
    for cell in ws["1:1"]:
        cell.font = Font(bold=True)

    # Obtener los datos de los gastos
    gastos = Gastos.objects.values('id_cuenta_banco__numero_cuenta').annotate(
        total_gastos=Sum('monto')
    ).order_by('id_cuenta_banco__numero_cuenta')

    # Agregar datos a la hoja
    for gasto in gastos:
        ws.append([gasto['id_cuenta_banco__numero_cuenta'], gasto['total_gastos']])

    # Crear una respuesta HTTP con el tipo de contenido Excel
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="reporte_gastos.xlsx"'

    # Guardar el libro de trabajo en la respuesta
    wb.save(response)

    return response
