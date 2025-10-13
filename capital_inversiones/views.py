from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, F, Case, When, Value
from .models import Inversion, CatInversion, RendimientoInversion
from .services.inversiones_service import InversionesReportService
from catalogo.models import Sucursal
from datetime import datetime, timedelta
from django.http import JsonResponse
import json


@login_required
def dashboard_inversiones(request):
    """
    Vista principal del dashboard de inversiones y capital
    
    Muestra resumen general, balances por sucursal y categoría,
    y gráficos de tendencias.
    """
    servicio = InversionesReportService()
    
    # Obtener parámetros de fecha del request
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    # Si no hay fechas, usar el mes actual
    if not fecha_inicio or not fecha_fin:
        hoy = datetime.now()
        fecha_inicio = hoy.replace(day=1).strftime('%Y-%m-%d')
        # Último día del mes
        if hoy.month == 12:
            fecha_fin = hoy.replace(day=31).strftime('%Y-%m-%d')
        else:
            fecha_fin = (hoy.replace(month=hoy.month + 1, day=1) - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Obtener datos del servicio
    resumen = servicio.get_resumen_general(fecha_inicio, fecha_fin)
    balance_sucursales = servicio.get_balance_por_sucursal(fecha_inicio, fecha_fin)
    balance_categorias = servicio.get_balance_por_categoria(fecha_inicio, fecha_fin)
    inversiones_rendimientos = servicio.get_inversiones_con_rendimientos(fecha_inicio, fecha_fin)
    
    # Calcular ROI en Python para cada inversión
    inversiones_list = []
    for inversion in inversiones_rendimientos:
        inversion_data = {
            'object': inversion,
            'total_rendimientos': inversion.total_rendimientos,
            'cantidad_rendimientos': inversion.cantidad_rendimientos,
            'roi': 0
        }
        
        # Calcular ROI si hay rendimientos
        if inversion.total_rendimientos and inversion.monto.amount > 0:
            # total_rendimientos puede ser Money o Decimal dependiendo de la agregación
            if hasattr(inversion.total_rendimientos, 'amount'):
                total_rend = float(inversion.total_rendimientos.amount)
            else:
                total_rend = float(inversion.total_rendimientos)
            
            monto_inv = float(inversion.monto.amount)
            inversion_data['roi'] = (total_rend / monto_inv) * 100
        
        inversiones_list.append(inversion_data)
    
    context = {
        'resumen': resumen,
        'balance_sucursales': balance_sucursales,
        'balance_categorias': balance_categorias,
        'inversiones_rendimientos': inversiones_list,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    }
    
    return render(request, 'capital_inversiones/dashboard.html', context)


@login_required
@login_required
def reporte_acumulado_sucursal(request):
    """
    Vista de reporte acumulado por sucursal
    
    Similar a los reportes de gastos, muestra totales acumulados
    por sucursal en el período seleccionado.
    """
    servicio = InversionesReportService()
    
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    sucursal_id = request.GET.get('sucursal')
    
    # Obtener balance por sucursal
    balance_sucursales = servicio.get_balance_por_sucursal(fecha_inicio, fecha_fin)
    
    # Obtener inversiones individuales para el detalle
    inversiones_queryset = Inversion.objects.all()
    
    # Aplicar filtros de fecha si existen
    if fecha_inicio:
        inversiones_queryset = inversiones_queryset.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        inversiones_queryset = inversiones_queryset.filter(fecha__lte=fecha_fin)
    
    # Filtrar por sucursal específica si se seleccionó una
    if sucursal_id:
        balance_sucursales = balance_sucursales.filter(id_sucursal=sucursal_id)
        inversiones_queryset = inversiones_queryset.filter(id_sucursal=sucursal_id)
    
    inversiones_queryset = inversiones_queryset.select_related(
        'id_sucursal', 'id_cat_inversion', 'id_cuenta_banco'
    ).order_by('-fecha')
    
    # Obtener lista de sucursales para el filtro
    sucursales = Sucursal.objects.all()
    
    # Calcular totales generales
    resumen = servicio.get_resumen_general(fecha_inicio, fecha_fin)
    
    context = {
        'balance_sucursales': balance_sucursales,
        'inversiones': inversiones_queryset,
        'resumen': resumen,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'sucursales': sucursales,
        'sucursal_seleccionada': sucursal_id,
    }
    
    return render(request, 'capital_inversiones/reporte_acumulado_sucursal.html', context)


@login_required
def reporte_acumulado_categoria(request):
    """
    Vista de reporte acumulado por categoría de inversión
    
    Muestra totales por categoría en el período seleccionado.
    """
    servicio = InversionesReportService()
    
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    categoria_id = request.GET.get('categoria')
    
    # Obtener balance por categoría
    balance_categorias = servicio.get_balance_por_categoria(fecha_inicio, fecha_fin)
    
    # Obtener inversiones individuales para el detalle
    inversiones_queryset = Inversion.objects.all()
    
    # Aplicar filtros de fecha si existen
    if fecha_inicio:
        inversiones_queryset = inversiones_queryset.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        inversiones_queryset = inversiones_queryset.filter(fecha__lte=fecha_fin)
    
    # Filtrar por categoría específica si se seleccionó una
    if categoria_id:
        balance_categorias = balance_categorias.filter(id_cat_inversion=categoria_id)
        inversiones_queryset = inversiones_queryset.filter(id_cat_inversion=categoria_id)
    
    inversiones_queryset = inversiones_queryset.select_related(
        'id_sucursal', 'id_cat_inversion', 'id_cuenta_banco'
    ).order_by('-fecha')
    
    # Obtener lista de categorías para el filtro
    categorias = CatInversion.objects.filter(activa=True)
    
    # Calcular totales generales
    resumen = servicio.get_resumen_general(fecha_inicio, fecha_fin)
    
    context = {
        'balance_categorias': balance_categorias,
        'inversiones': inversiones_queryset,
        'resumen': resumen,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'categorias': categorias,
        'categoria_seleccionada': categoria_id,
    }
    
    return render(request, 'capital_inversiones/reporte_acumulado_categoria.html', context)


@login_required
def reporte_rendimientos(request):
    """
    Vista de reporte de rendimientos de inversiones
    
    Muestra ROI, rendimientos totales y análisis de performance.
    """
    servicio = InversionesReportService()
    
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    # Obtener inversiones con rendimientos
    inversiones_qs = servicio.get_inversiones_con_rendimientos(fecha_inicio, fecha_fin)
    
    # Calcular ROI en Python para cada inversión
    inversiones_list = []
    total_invertido = 0
    total_rendimientos_sum = 0
    
    for inversion in inversiones_qs:
        inversion_data = {
            'object': inversion,
            'total_rendimientos': inversion.total_rendimientos,
            'cantidad_rendimientos': inversion.cantidad_rendimientos,
            'roi': 0
        }
        
        # Calcular ROI si hay rendimientos
        if inversion.total_rendimientos and inversion.monto.amount > 0:
            # total_rendimientos puede ser Money o Decimal dependiendo de la agregación
            if hasattr(inversion.total_rendimientos, 'amount'):
                total_rend = float(inversion.total_rendimientos.amount)
            else:
                total_rend = float(inversion.total_rendimientos)
            
            monto_inv = float(inversion.monto.amount)
            inversion_data['roi'] = (total_rend / monto_inv) * 100
            total_rendimientos_sum += total_rend
        
        total_invertido += float(inversion.monto.amount)
        inversiones_list.append(inversion_data)
    
    # Calcular ROI promedio
    roi_promedio = (total_rendimientos_sum / total_invertido * 100) if total_invertido > 0 else 0
    
    context = {
        'inversiones': inversiones_list,
        'total_invertido': total_invertido,
        'total_rendimientos': total_rendimientos_sum,
        'roi_promedio': round(roi_promedio, 2),
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    }
    
    return render(request, 'capital_inversiones/reporte_rendimientos.html', context)


@login_required
def api_balance_mensual(request):
    """
    API endpoint para obtener balance mensual (para gráficos)
    
    Returns:
        JSON con balance mensual de los últimos 12 meses
    """
    from django.db.models.functions import TruncMonth
    
    # Últimos 12 meses
    fecha_fin = datetime.now()
    fecha_inicio = fecha_fin - timedelta(days=365)
    
    balances = Inversion.objects.filter(
        fecha__gte=fecha_inicio,
        fecha__lte=fecha_fin
    ).annotate(
        mes=TruncMonth('fecha')
    ).values('mes').annotate(
        entradas=Sum('monto', filter=Q(tipo_movimiento='ENTRADA')),
        salidas=Sum('monto', filter=Q(tipo_movimiento='SALIDA')),
        balance=Sum(
            F('monto') * Case(
                When(tipo_movimiento='ENTRADA', then=1),
                When(tipo_movimiento='SALIDA', then=-1),
                default=0
            )
        )
    ).order_by('mes')
    
    # Formatear para Chart.js
    data = {
        'labels': [b['mes'].strftime('%b %Y') for b in balances],
        'entradas': [float(b['entradas'] or 0) for b in balances],
        'salidas': [float(b['salidas'] or 0) for b in balances],
        'balance': [float(b['balance'] or 0) for b in balances],
    }
    
    return JsonResponse(data)


@login_required
def api_distribucion_categorias(request):
    """
    API endpoint para obtener distribución por categorías (para gráficos de pie)
    
    Returns:
        JSON con distribución de inversiones por categoría
    """
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    queryset = Inversion.objects.filter(tipo_movimiento='SALIDA')
    
    if fecha_inicio:
        queryset = queryset.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        queryset = queryset.filter(fecha__lte=fecha_fin)
    
    distribucion = queryset.values('id_cat_inversion__nombre').annotate(
        total=Sum('monto')
    ).order_by('-total')
    
    data = {
        'labels': [d['id_cat_inversion__nombre'] for d in distribucion],
        'values': [float(d['total']) for d in distribucion],
    }
    
    return JsonResponse(data)
