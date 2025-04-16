from django.shortcuts import render, redirect, get_object_or_404
from .forms import GastoForm
from .models import Cuenta, Compra, Banco, SaldoMensual
from catalogo.models import Productor, Producto
from django.utils import timezone
import decimal
import numpy as np
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.db.models import Sum, Avg, Count, Max, Min
from django.contrib.auth.decorators import user_passes_test
from datetime import date, datetime, timedelta
import json
from app.views import is_admin
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .forms import CompraForm

@login_required
def compras_balances_view(request):
    """
    Vista para análisis de compras que permite filtrar y visualizar datos
    de compras por diferentes periodos, productores, productos, y métodos de pago.
    """
    # Obtener parámetros de filtrado de la solicitud
    cuenta_id = request.GET.get('cuenta_id', '')
    productor_id = request.GET.get('productor_id', '')
    producto_id = request.GET.get('producto_id', '')
    tipo_pago = request.GET.get('tipo_pago', '')
    year = request.GET.get('year', datetime.now().year)
    month = request.GET.get('month', datetime.now().month)
    periodo = request.GET.get('periodo', 'diario')  # 'diario', 'semanal' o 'mensual'
    dia = request.GET.get('dia', datetime.now().strftime('%Y-%m-%d'))
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')

    # Obtener los años disponibles
    available_years = Compra.objects.dates('fecha_compra', 'year')

    # Lista de meses
    months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", 
              "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

    # Tipos de pago disponibles
    tipos_pago = Compra.objects.values_list('tipo_pago', flat=True).distinct()
    
    # Verificar si hay filtros aplicados
    has_filters = any([
        cuenta_id, 
        productor_id,
        producto_id,
        tipo_pago,
        str(year) != str(datetime.now().year),
        month and str(month) != str(datetime.now().month),
        periodo != 'diario',
        dia and str(dia) != datetime.now().strftime('%Y-%m-%d'),
        fecha_inicio,
        fecha_fin
    ])
    
    # Obtener nombres para mostrar en filtros
    selected_cuenta_nombre = ""
    if cuenta_id:
        try:
            cuenta_obj = Cuenta.objects.get(id=cuenta_id)
            selected_cuenta_nombre = f"{cuenta_obj.numero_cuenta} - {cuenta_obj.id_banco.nombre}"
        except Cuenta.DoesNotExist:
            pass
    
    selected_productor_nombre = ""
    if productor_id:
        try:
            productor_obj = Productor.objects.get(id=productor_id)
            selected_productor_nombre = productor_obj.nombre_completo
        except Productor.DoesNotExist:
            pass
    
    selected_producto_nombre = ""
    if producto_id:
        try:
            producto_obj = Producto.objects.get(id=producto_id)
            selected_producto_nombre = f"{producto_obj.nombre} - {producto_obj.variedad}"
        except Producto.DoesNotExist:
            pass
    
    # Filtrar y agrupar los datos de compras según el periodo seleccionado
    filters = {'fecha_compra__year': year}
    if cuenta_id:
        filters['cuenta_id'] = cuenta_id
    if month:
        filters['fecha_compra__month'] = month
    if productor_id:
        filters['productor_id'] = productor_id
    if producto_id:
        filters['producto_id'] = producto_id
    if tipo_pago:
        filters['tipo_pago'] = tipo_pago

    # Aplicar filtros de fecha según el periodo seleccionado
    if periodo == 'diario':
        if dia:
            filters['fecha_compra'] = dia
        elif fecha_inicio and fecha_fin:
            filters['fecha_compra__range'] = [fecha_inicio, fecha_fin]
        
        compras_data = Compra.objects.filter(**filters).values(
            'cuenta__id',
            'cuenta__numero_cuenta',
            'cuenta__id_banco__nombre',
            'productor__nombre_completo',
            'producto__nombre',
            'producto__variedad',
            'tipo_pago',
            'fecha_compra'
        ).annotate(
            total_compras=Sum('monto_total'),
            cantidad_total=Sum('cantidad'),
            precio_promedio=Avg('precio_unitario')
        ).order_by('cuenta__id', 'fecha_compra')
        
    elif periodo == 'semanal':
        compras_data = Compra.objects.filter(**filters).annotate(
            semana=TruncWeek('fecha_compra')
        ).values(
            'cuenta__id',
            'cuenta__numero_cuenta',
            'cuenta__id_banco__nombre',
            'productor__nombre_completo',
            'producto__nombre',
            'producto__variedad',
            'tipo_pago',
            'semana'
        ).annotate(
            total_compras=Sum('monto_total'),
            cantidad_total=Sum('cantidad'),
            precio_promedio=Avg('precio_unitario')
        ).order_by('cuenta__id', 'semana')
        
    elif periodo == 'mensual':
        compras_data = Compra.objects.filter(**filters).annotate(
            mes=TruncMonth('fecha_compra')
        ).values(
            'cuenta__id',
            'cuenta__numero_cuenta',
            'cuenta__id_banco__nombre',
            'productor__nombre_completo',
            'producto__nombre',
            'producto__variedad',
            'tipo_pago',
            'mes'
        ).annotate(
            total_compras=Sum('monto_total'),
            cantidad_total=Sum('cantidad'),
            precio_promedio=Avg('precio_unitario')
        ).order_by('cuenta__id', 'mes')
        
    else:
        compras_data = []

    # Calcular el acumulado de la suma de montos
    acumulado = 0
    for compra in compras_data:
        acumulado += compra['total_compras']
        compra['acumulado'] = acumulado

    # Métricas clave para el análisis de compras
    total_compras = Compra.objects.filter(**filters).aggregate(total=Sum('monto_total'))['total'] or 0
    cantidad_total = Compra.objects.filter(**filters).aggregate(total=Sum('cantidad'))['total'] or 0
    promedio_compra = Compra.objects.filter(**filters).aggregate(promedio=Avg('monto_total'))['promedio'] or 0
    numero_transacciones = Compra.objects.filter(**filters).count()
    
    # Compras máximas y mínimas
    compra_maxima = Compra.objects.filter(**filters).aggregate(maximo=Max('monto_total'))['maximo'] or 0
    compra_minima = Compra.objects.filter(**filters).filter(monto_total__gt=0).aggregate(minimo=Min('monto_total'))['minimo'] or 0
    
    # Para cálculo de mediana necesitamos valores en una lista
    montos_compras = list(Compra.objects.filter(**filters).values_list('monto_total', flat=True))
    compra_mediana = np.median(montos_compras) if montos_compras else 0
    
    # Análisis por método de pago
    compras_por_tipo_pago = Compra.objects.filter(**filters).values('tipo_pago').annotate(
        total=Sum('monto_total'),
        cantidad=Count('id')
    ).order_by('-total')
    
    # Análisis por productor
    top_productores = Compra.objects.filter(**filters).values(
        'productor__nombre_completo', 'productor__id'
    ).annotate(
        total_compras=Sum('monto_total'),
        cantidad_compras=Count('id')
    ).order_by('-total_compras')[:5]
    
    # Análisis por producto
    top_productos = Compra.objects.filter(**filters).values(
        'producto__nombre', 'producto__variedad', 'producto__id'
    ).annotate(
        total=Sum('monto_total'),
        cantidad=Sum('cantidad'),
        precio_promedio=Avg('precio_unitario')
    ).order_by('-total')[:5]
    
    # Datos para gráficos de evolución mensual
    meses_labels = []
    datos_compras_mensuales = []
    
    # Obtener datos de los últimos 6 meses para el gráfico
    for i in range(5, -1, -1):
        # Calcular mes en retroceso
        date = datetime.now() - timezone.timedelta(days=30 * i)
        month_num = date.month
        year_num = date.year
        
        # Filtro para este mes
        month_filter = Compra.objects.filter(
            fecha_compra__month=month_num,
            fecha_compra__year=year_num
        ).aggregate(total=Sum('monto_total'))['total'] or 0
        
        # Añadir datos al gráfico
        meses_labels.append(months[month_num - 1])
        datos_compras_mensuales.append(float(month_filter))

    # Obtener todas las cuentas para el filtro
    cuentas = Cuenta.objects.all()
    
    # Obtener todos los productores y productos para los filtros
    from catalogo.models import Productor, Producto
    productores = Productor.objects.all()
    productos = Producto.objects.all()
    
    context = {
        'compras_data': compras_data,
        'cuentas': cuentas,
        'productores': productores,
        'productos': productos,
        'tipos_pago': tipos_pago,
        'selected_cuenta_id': cuenta_id,
        'selected_productor_id': productor_id,
        'selected_producto_id': producto_id,
        'selected_tipo_pago': tipo_pago,
        'selected_year': year,
        'selected_month': month,
        'selected_periodo': periodo,
        'selected_dia': dia,
        'selected_fecha_inicio': fecha_inicio,
        'selected_fecha_fin': fecha_fin,
        'available_years': available_years,
        'months': months,
        'total_compras': total_compras,
        'cantidad_total': cantidad_total,
        'promedio_compra': promedio_compra,
        'numero_transacciones': numero_transacciones,
        'compra_maxima': compra_maxima,
        'compra_minima': compra_minima,
        'compra_mediana': compra_mediana,
        'compras_por_tipo_pago': compras_por_tipo_pago,
        'top_productores': top_productores,
        'top_productos': top_productos,
        'meses_labels': meses_labels,
        'datos_compras_mensuales': datos_compras_mensuales,
        # Variables añadidas para mejora de usabilidad
        'has_filters': has_filters,
        'selected_cuenta_nombre': selected_cuenta_nombre,
        'selected_productor_nombre': selected_productor_nombre,
        'selected_producto_nombre': selected_producto_nombre,
    }
    
    return render(request, 'compras/compras_balances.html', context)