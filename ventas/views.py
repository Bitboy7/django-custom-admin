from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Sum, Count, Avg, Max, Min, Q
from django.db.models.functions import Extract, TruncMonth, TruncWeek, TruncDate
from django.utils import timezone
from datetime import datetime, timedelta, date
from decimal import Decimal
from collections import defaultdict, OrderedDict
import json
from .models import Anticipo, Ventas, Cliente, TerminoCredito, MercadoDestino, PagoVenta, DocumentoCFDI
from .forms import AnticipoForm
from catalogo.models import Sucursal, Pais
from gastos.models import Cuenta
from .services.reporte_cobranza_service import generar_reporte_cobranza
from .services.cache_service import VentasBalancesCache

@login_required
@permission_required('ventas.view_anticipo', raise_exception=True)
def lista_anticipos(request):
    anticipos = Anticipo.objects.all()
    return render(request, 'lista_anticipos.html', {'anticipos': anticipos})

@login_required
@permission_required('ventas.add_anticipo', raise_exception=True)
def crear_anticipo(request):
    if request.method == 'POST':
        form = AnticipoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_anticipos')
    else:
        form = AnticipoForm()
    return render(request, 'crear_anticipo.html', {'form': form})

@login_required
@permission_required('ventas.view_ventas', raise_exception=True)
def detalle_venta(request, venta_id):
    venta = get_object_or_404(Ventas, id=venta_id)
    monto_final = venta.calcular_monto_final()
    return render(request, 'detalle_venta.html', {'venta': venta, 'monto_final': monto_final})

def _parse_selected_months(query_params):
    """Normaliza months=1,2 y months=1&months=2 a una lista válida y única."""
    selected_months = []
    for raw_value in query_params.getlist('months'):
        for value in raw_value.split(','):
            value = value.strip()
            if not value.isdigit():
                continue
            month = int(value)
            normalized = str(month)
            if 1 <= month <= 12 and normalized not in selected_months:
                selected_months.append(normalized)
    return selected_months

def _agrupar_ventas(ventas_queryset, periodo):
    """Agrupa las ventas por día/semana/mes y por cliente, con sus métricas.

    Centraliza la única diferencia entre periodos (la función de truncado);
    el resto del cálculo es idéntico.
    """
    if periodo == 'diario':
        agrupado = ventas_queryset.extra(
            select={'fecha_grupo': 'DATE(fecha_deposito)'}
        )
    elif periodo == 'semanal':
        agrupado = ventas_queryset.annotate(
            fecha_grupo=TruncWeek('fecha_deposito')
        )
    else:  # mensual
        agrupado = ventas_queryset.annotate(
            fecha_grupo=TruncMonth('fecha_deposito')
        )

    return agrupado.values(
        'fecha_grupo', 'cliente__nombre', 'cuenta__numero_cuenta',
        'cuenta__id_banco__nombre', 'sucursal_id__nombre',
    ).annotate(
        total_ventas=Sum('monto'),
        total_pagado=Sum('monto_pagado'),
        fecha_vencimiento_proxima=Min('fecha_vencimiento'),
        venta_maxima=Max('monto'),
        venta_minima=Min('monto'),
        venta_promedio=Avg('monto'),
    ).order_by('fecha_grupo', 'cliente__nombre')


def _construir_balances(ventas_queryset, periodo):
    """Construye las filas de la tabla de balances con su acumulado."""
    balances = []
    acumulado = 0
    for idx, grupo in enumerate(_agrupar_ventas(ventas_queryset, periodo)):
        total = float(grupo['total_ventas'] or 0)
        acumulado += total
        pagado = float(grupo['total_pagado'] or 0)
        vencimiento = grupo.get('fecha_vencimiento_proxima')
        balances.append({
            'numero_secuencial': idx + 1,
            'cliente_nombre': grupo['cliente__nombre'],
            'cuenta_numero': grupo['cuenta__numero_cuenta'],
            'banco_nombre': grupo['cuenta__id_banco__nombre'] or 'N/A',
            'sucursal_nombre': grupo['sucursal_id__nombre'],
            'fecha': grupo['fecha_grupo'],
            'total_ventas': total,
            'total_pagado': pagado,
            'saldo_pendiente': total - pagado,
            'estado_cobranza': Ventas.derive_estado_desde_totales(total, pagado, vencimiento),
            'fecha_vencimiento': vencimiento,
            'venta_maxima': float(grupo['venta_maxima'] or 0),
            'venta_minima': float(grupo['venta_minima'] or 0),
            'venta_promedio': float(grupo['venta_promedio'] or 0),
            'acumulado': acumulado,
        })
    return balances


def _get_available_years():
    """Años disponibles para filtrar, combinando ventas y CFDI importados."""
    current_year = timezone.now().year
    years = set()
    for date_obj in Ventas.objects.dates('fecha_deposito', 'year'):
        years.add(date_obj.year)
    for date_obj in DocumentoCFDI.objects.dates('fecha_emision', 'year'):
        if date_obj.year:
            years.add(date_obj.year)
    if not years:
        years.add(current_year)
    return sorted(years, reverse=True)


def _parse_fecha(valor):
    """Convierte 'YYYY-MM-DD' en date; None si está vacío o es inválido."""
    try:
        return datetime.strptime((valor or '').strip(), '%Y-%m-%d').date()
    except ValueError:
        return None


def _parse_mes(valor):
    """Convierte 'YYYY-MM' en (primer_día, último_día); None si es inválido."""
    import calendar

    try:
        year_str, month_str = (valor or '').strip().split('-', 1)
        year, month = int(year_str), int(month_str)
        if not (1 <= month <= 12 and 1900 <= year <= 9999):
            return None
    except (ValueError, TypeError):
        return None
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def _filtro_fechas_balances(campo, filtros):
    """Q de fechas sobre ``campo`` según el período y modo elegidos.

    - Diario: día específico o rango de fechas (acepta solo inicio o solo fin).
    - Mensual con ``tipo_mes=rango``: rango de meses YYYY-MM, puede cruzar años.
      Sin mes final abarca hasta hoy; sin mes inicial, todo hasta el mes final.
    - En cualquier otro caso (o si los campos anteriores vienen vacíos): año
      seleccionado y, opcionalmente, los meses marcados.
    """
    periodo = filtros['periodo']

    if periodo == 'diario':
        if filtros['tipo_fecha'] == 'rango':
            inicio = _parse_fecha(filtros['fecha_inicio'])
            fin = _parse_fecha(filtros['fecha_fin'])
            if inicio and fin and inicio > fin:
                inicio, fin = fin, inicio
            q = Q()
            if inicio:
                q &= Q(**{f'{campo}__gte': inicio})
            if fin:
                q &= Q(**{f'{campo}__lte': fin})
            if inicio or fin:
                return q
        else:
            dia = _parse_fecha(filtros['dia'])
            if dia:
                return Q(**{campo: dia})

    if periodo == 'mensual' and filtros['tipo_mes'] == 'rango':
        inicio = _parse_mes(filtros['mes_inicio'])
        fin = _parse_mes(filtros['mes_fin'])
        if inicio and fin:
            desde, hasta = min(inicio[0], fin[0]), max(inicio[1], fin[1])
            return Q(**{f'{campo}__range': [desde, hasta]})
        if inicio:
            # Sin mes final: desde el mes inicial hasta la fecha actual.
            return Q(**{f'{campo}__range': [inicio[0], date.today()]})
        if fin:
            # Sin mes inicial: todo lo registrado hasta el cierre del mes final.
            return Q(**{f'{campo}__lte': fin[1]})

    q = Q()
    if filtros['year']:
        q &= Q(**{f'{campo}__year': int(filtros['year'])})
    months_int = [int(m) for m in filtros['months'] if m.isdigit()]
    if months_int:
        q &= Q(**{f'{campo}__month__in': months_int})
    return q


def _build_cfdi_filters(selected_cliente_id, filtros_fecha):
    """Construye filtros de DocumentoCFDI por cliente y rango de fechas.

    Se mantienen solo los filtros que se aplican de forma directa sobre el
    documento fiscal (cliente y fecha de emisión). Los filtros operativos de
    sucursal/mercado/modalidad no siempre están disponibles en el CFDI y su
    join generaba errores de lookup con el campo ``sucursal_id`` de ``Ventas``.
    """
    cfdi_filters = Q(estado=DocumentoCFDI.EstadoDocumento.VIGENTE)

    if selected_cliente_id:
        cfdi_filters &= Q(cliente_id=selected_cliente_id)

    return cfdi_filters & _filtro_fechas_balances('fecha_emision', filtros_fecha)


def leer_filtros_balances(request):
    """Lee y normaliza los filtros de la pantalla de balances desde ``GET``.

    Fuente única para la pantalla y para los reportes Excel/PDF: así el
    reporte descargado siempre corresponde a lo que el usuario ve.
    """
    tipo_mes = request.GET.get('tipo_mes', 'anio')
    if tipo_mes != 'rango':
        tipo_mes = 'anio'
    f = {
        'cliente_id': request.GET.get('cliente_id', ''),
        'cuenta_id': request.GET.get('cuenta_id', ''),
        'sucursal_id': request.GET.get('sucursal_id', ''),
        'mercado_id': request.GET.get('mercado_id', ''),
        'modalidad': request.GET.get('modalidad_pago', ''),
        'estado': request.GET.get('estado_cobranza', ''),
        'year': ''.join(
            ch for ch in request.GET.get('year', '') if ch.isdigit()
        ) or str(timezone.now().year),
        'months': _parse_selected_months(request.GET),
        'periodo': request.GET.get('periodo', 'mensual'),
        'dia': request.GET.get('dia', ''),
        'fecha_inicio': request.GET.get('fecha_inicio', ''),
        'fecha_fin': request.GET.get('fecha_fin', ''),
        'tipo_fecha': request.GET.get('tipo_fecha', 'dia'),
        'tipo_mes': tipo_mes,
        'mes_inicio': request.GET.get('mes_inicio', ''),
        'mes_fin': request.GET.get('mes_fin', ''),
    }
    f['filtros_fecha'] = {
        key: f[key] for key in (
            'periodo', 'year', 'months', 'dia', 'fecha_inicio', 'fecha_fin',
            'tipo_fecha', 'tipo_mes', 'mes_inicio', 'mes_fin',
        )
    }
    return f


def q_ventas_balances(f):
    """Q de ``Ventas`` para los filtros leídos con ``leer_filtros_balances``."""
    filters = Q()
    if f['cliente_id']:
        filters &= Q(cliente_id=f['cliente_id'])
    if f['cuenta_id']:
        filters &= Q(cuenta_id=f['cuenta_id'])
    if f['sucursal_id']:
        filters &= Q(sucursal_id=f['sucursal_id'])
    if f['mercado_id']:
        filters &= Q(mercado_destino_id=f['mercado_id'])
    if f['modalidad']:
        filters &= Q(modalidad_pago=f['modalidad'])
    if f['estado']:
        filters &= Q(estado_cobranza=f['estado'])
    return filters & _filtro_fechas_balances('fecha_deposito', f['filtros_fecha'])


def build_ventas_balances_context(request):
    """Construye y retorna el contexto para la vista de balances de ventas."""    # Obtener parámetros de filtro
    selected_cliente_id = request.GET.get('cliente_id', '')
    selected_cuenta_id = request.GET.get('cuenta_id', '')
    selected_sucursal_id = request.GET.get('sucursal_id', '')
    selected_mercado_id = request.GET.get('mercado_id', '')
    selected_modalidad = request.GET.get('modalidad_pago', '')
    selected_estado = request.GET.get('estado_cobranza', '')
    selected_year = ''.join(
        ch for ch in request.GET.get('year', '') if ch.isdigit()
    ) or str(timezone.now().year)
    selected_months = _parse_selected_months(request.GET)
    selected_periodo = request.GET.get('periodo', 'mensual')
    
    # Filtros de fecha específicos para período diario
    selected_dia = request.GET.get('dia', '')
    selected_fecha_inicio = request.GET.get('fecha_inicio', '')
    selected_fecha_fin = request.GET.get('fecha_fin', '')
    tipo_fecha = request.GET.get('tipo_fecha', 'dia')

    # Rango de meses (YYYY-MM) para período mensual
    tipo_mes = request.GET.get('tipo_mes', 'anio')
    if tipo_mes != 'rango':
        tipo_mes = 'anio'
    selected_mes_inicio = request.GET.get('mes_inicio', '')
    selected_mes_fin = request.GET.get('mes_fin', '')

    filtros_fecha = {
        'periodo': selected_periodo,
        'year': selected_year,
        'months': selected_months,
        'dia': selected_dia,
        'fecha_inicio': selected_fecha_inicio,
        'fecha_fin': selected_fecha_fin,
        'tipo_fecha': tipo_fecha,
        'tipo_mes': tipo_mes,
        'mes_inicio': selected_mes_inicio,
        'mes_fin': selected_mes_fin,
    }

    # Obtener listas para los filtros
    clientes = Cliente.objects.filter(activo=True).order_by('nombre')
    cuentas = Cuenta.objects.select_related('id_banco').order_by('numero_cuenta')
    sucursales = Sucursal.objects.all().order_by('nombre')
    mercados = MercadoDestino.objects.filter(activo=True).order_by('nombre')
    
    # Años disponibles combinando ventas y CFDI importados
    available_years = _get_available_years()
    current_year = timezone.now().year

    # ── Cache check ────────────────────────────────────────────────────────────
    _filter_params = {
        'cliente_id':    selected_cliente_id,
        'cuenta_id':     selected_cuenta_id,
        'sucursal_id':   selected_sucursal_id,
        'mercado_id':    selected_mercado_id,
        'modalidad':     selected_modalidad,
        'estado':        selected_estado,
        'year':          selected_year,
        'months':        '|'.join(sorted(selected_months)) if selected_months else '',
        'periodo':       selected_periodo,
        'dia':           selected_dia,
        'fecha_inicio':  selected_fecha_inicio,
        'fecha_fin':     selected_fecha_fin,
        'tipo_fecha':    tipo_fecha,
        'tipo_mes':      tipo_mes,
        'mes_inicio':    selected_mes_inicio,
        'mes_fin':       selected_mes_fin,
    }
    _cached = VentasBalancesCache.get(_filter_params)
    if _cached is not None:
        _cached.update({
            'clientes': clientes,
            'cuentas': cuentas,
            'sucursales': sucursales,
            'mercados': mercados,
            'available_years': available_years,
            'current_year': current_year,
            'selected_cliente_id':   selected_cliente_id,
            'selected_cuenta_id':    selected_cuenta_id,
            'selected_sucursal_id':  selected_sucursal_id,
            'selected_mercado_id':   selected_mercado_id,
            'selected_modalidad':    selected_modalidad,
            'selected_estado':       selected_estado,
            'selected_year':         selected_year,
            'selected_months':       selected_months,
            'selected_periodo':      selected_periodo,
            'selected_dia':          selected_dia,
            'selected_fecha_inicio': selected_fecha_inicio,
            'selected_fecha_fin':    selected_fecha_fin,
            'tipo_fecha':            tipo_fecha,
            'tipo_mes':              tipo_mes,
            'selected_mes_inicio':   selected_mes_inicio,
            'selected_mes_fin':      selected_mes_fin,
            'modalidad_choices': Ventas.ModalidadPago.choices,
            'estado_choices':    Ventas.EstadoCobranza.choices,
            # Defaults para entradas cacheadas antes de la incorporación de métricas CFDI
            'total_facturado_cfdi': _cached.get('total_facturado_cfdi', 0),
            'total_notas_credito_cfdi': _cached.get('total_notas_credito_cfdi', 0),
            'total_recibos_pago_cfdi': _cached.get('total_recibos_pago_cfdi', 0),
            'numero_cfdis': _cached.get('numero_cfdis', 0),
        })
        return _cached
    # ── /Cache check ────────────────────────────────────────────────────────────

    # Filtros base (misma fuente que los reportes Excel/PDF)
    filters = q_ventas_balances(leer_filtros_balances(request))

    # Obtener ventas filtradas
    ventas_queryset = Ventas.objects.filter(filters).select_related(
        'cliente', 'cuenta', 'sucursal_id', 'mercado_destino', 'producto', 'agente_id'
    ).prefetch_related('pagos')
    
    # Preparar datos para la tabla según el período
    balances = _construir_balances(ventas_queryset, selected_periodo)

    # Calcular métricas generales
    totales = ventas_queryset.aggregate(
        total_ventas=Sum('monto'),
        total_pagado=Sum('monto_pagado'),
        numero_transacciones=Count('id'),
        venta_maxima=Max('monto'),
        venta_minima=Min('monto'),
        venta_promedio=Avg('monto')
    )
    
    total_ventas = float(totales['total_ventas'] or 0)
    total_pagado = float(totales['total_pagado'] or 0)
    saldo_pendiente_total = total_ventas - total_pagado
    numero_transacciones = totales['numero_transacciones'] or 0
    venta_maxima = float(totales['venta_maxima'] or 0)
    venta_minima = float(totales['venta_minima'] or 0)
    promedio_ventas = float(totales['venta_promedio'] or 0)
    
    # Calcular ventas por modalidad de pago para gráficos
    ventas_por_modalidad = ventas_queryset.values('modalidad_pago').annotate(
        total=Sum('monto')
    ).order_by('-total')
    
    # Convertir Decimal a float para JavaScript
    ventas_por_modalidad = [
        {'modalidad_pago': item['modalidad_pago'], 'total': float(item['total'] or 0)}
        for item in ventas_por_modalidad
    ]
    
    # Calcular ventas por estado de cobranza para gráficos
    ventas_por_estado = ventas_queryset.values('estado_cobranza').annotate(
        total=Sum('monto')
    ).order_by('-total')
    
    # Convertir Decimal a float para JavaScript
    ventas_por_estado = [
        {'estado_cobranza': item['estado_cobranza'], 'total': float(item['total'] or 0)}
        for item in ventas_por_estado
    ]
    
    # Calcular ventas por cliente para gráficos
    ventas_por_cliente = ventas_queryset.values('cliente__nombre').annotate(
        total=Sum('monto')
    ).order_by('-total')[:10]  # Top 10 clientes
    
    # Convertir Decimal a float para JavaScript
    ventas_por_cliente = [
        {'cliente__nombre': item['cliente__nombre'], 'total': float(item['total'] or 0)}
        for item in ventas_por_cliente
    ]
    
    # Calcular métricas adicionales
    ventas_contado = ventas_queryset.filter(modalidad_pago='Contado').aggregate(
        total=Sum('monto'), count=Count('id')
    )
    ventas_credito = ventas_queryset.filter(modalidad_pago='Credito').aggregate(
        total=Sum('monto'), count=Count('id')
    )
    
    ventas_vencidas = ventas_queryset.filter(
        estado_cobranza='Vencido'
    ).aggregate(total=Sum('monto'), count=Count('id'))

    # Métricas de CFDI importados (vigentes) en el mismo rango de filtros
    cfdi_filters = _build_cfdi_filters(selected_cliente_id, filtros_fecha)
    cfdi_qs = DocumentoCFDI.objects.filter(cfdi_filters)
    cfdi_totals = cfdi_qs.aggregate(
        total_facturado=Sum('monto', filter=Q(tipo=DocumentoCFDI.TipoDocumento.INGRESO)),
        total_notas_credito=Sum('monto', filter=Q(subtipo__in=[
            DocumentoCFDI.SubtipoDocumento.NOTA_CREDITO,
            DocumentoCFDI.SubtipoDocumento.DESCUENTO,
        ])),
        total_recibos_pago=Sum('monto', filter=Q(tipo=DocumentoCFDI.TipoDocumento.PAGO)),
        numero_cfdis=Count('id'),
    )
    total_facturado_cfdi = float(cfdi_totals['total_facturado'] or 0)
    total_notas_credito_cfdi = float(cfdi_totals['total_notas_credito'] or 0)
    total_recibos_pago_cfdi = float(cfdi_totals['total_recibos_pago'] or 0)
    numero_cfdis = cfdi_totals['numero_cfdis'] or 0

    context = {
        # Datos para filtros
        'clientes': clientes,
        'cuentas': cuentas,
        'sucursales': sucursales,
        'mercados': mercados,
        'available_years': available_years,
        'current_year': current_year,
        
        # Valores seleccionados en filtros
        'selected_cliente_id': selected_cliente_id,
        'selected_cuenta_id': selected_cuenta_id,
        'selected_sucursal_id': selected_sucursal_id,
        'selected_mercado_id': selected_mercado_id,
        'selected_modalidad': selected_modalidad,
        'selected_estado': selected_estado,
        'selected_year': selected_year,
        'selected_months': selected_months,
        'selected_periodo': selected_periodo,
        'selected_dia': selected_dia,
        'selected_fecha_inicio': selected_fecha_inicio,
        'selected_fecha_fin': selected_fecha_fin,
        'tipo_fecha': tipo_fecha,
        'tipo_mes': tipo_mes,
        'selected_mes_inicio': selected_mes_inicio,
        'selected_mes_fin': selected_mes_fin,

        # Datos para la tabla
        'balances': balances,
        
        # Métricas generales
        'total_ventas': total_ventas,
        'total_pagado': total_pagado,
        'saldo_pendiente_total': saldo_pendiente_total,
        'numero_transacciones': numero_transacciones,
        'venta_maxima': venta_maxima,
        'venta_minima': venta_minima,
        'promedio_ventas': promedio_ventas,
        
        # Métricas por modalidad
        'ventas_contado_total': float(ventas_contado['total'] or 0),
        'ventas_contado_count': ventas_contado['count'] or 0,
        'ventas_credito_total': float(ventas_credito['total'] or 0),
        'ventas_credito_count': ventas_credito['count'] or 0,
        
        # Métricas de cobranza
        'ventas_vencidas_total': float(ventas_vencidas['total'] or 0),
        'ventas_vencidas_count': ventas_vencidas['count'] or 0,

        # Métricas de CFDI
        'total_facturado_cfdi': total_facturado_cfdi,
        'total_notas_credito_cfdi': total_notas_credito_cfdi,
        'total_recibos_pago_cfdi': total_recibos_pago_cfdi,
        'numero_cfdis': numero_cfdis,

        # Datos para gráficos (serializados como JSON)
        'ventas_por_modalidad': json.dumps(ventas_por_modalidad),
        'ventas_por_estado': json.dumps(ventas_por_estado),
        'ventas_por_cliente': json.dumps(ventas_por_cliente),
        
        # Opciones para filtros
        'modalidad_choices': Ventas.ModalidadPago.choices,
        'estado_choices': Ventas.EstadoCobranza.choices,
    }

    # Cachear solo los datos computados (no las queryset de opciones de filtro)
    VentasBalancesCache.set(_filter_params, {
        'balances':               context['balances'],
        'total_ventas':           context['total_ventas'],
        'total_pagado':           context['total_pagado'],
        'saldo_pendiente_total':  context['saldo_pendiente_total'],
        'numero_transacciones':   context['numero_transacciones'],
        'venta_maxima':           context['venta_maxima'],
        'venta_minima':           context['venta_minima'],
        'promedio_ventas':        context['promedio_ventas'],
        'ventas_contado_total':   context['ventas_contado_total'],
        'ventas_contado_count':   context['ventas_contado_count'],
        'ventas_credito_total':   context['ventas_credito_total'],
        'ventas_credito_count':   context['ventas_credito_count'],
        'ventas_vencidas_total':  context['ventas_vencidas_total'],
        'ventas_vencidas_count':  context['ventas_vencidas_count'],
        'total_facturado_cfdi':   context['total_facturado_cfdi'],
        'total_notas_credito_cfdi': context['total_notas_credito_cfdi'],
        'total_recibos_pago_cfdi': context['total_recibos_pago_cfdi'],
        'numero_cfdis':           context['numero_cfdis'],
        'ventas_por_modalidad':   context['ventas_por_modalidad'],
        'ventas_por_estado':      context['ventas_por_estado'],
        'ventas_por_cliente':     context['ventas_por_cliente'],
    })

    return context


@login_required
@permission_required('ventas.view_ventas', raise_exception=True)
def ventas_balances(request):
    """Vista para mostrar balances y análisis de ventas con filtros avanzados"""
    from django.http import HttpResponse
    context = build_ventas_balances_context(request)
    context['export_xlsx_url'] = reverse('ventas:exportar_balances_xlsx')
    context['export_pdf_url'] = reverse('ventas:exportar_balances_pdf')

    results_html = render_to_string(
        'admin/ventas/partials/ventas_balances_results.html',
        context,
        request=request,
    )

    if request.headers.get('HX-Request') == 'true':
        response = HttpResponse(results_html)
        response['HX-Trigger'] = json.dumps({
            'showToast': {
                'type': 'info',
                'title': 'Filtros aplicados',
                'message': 'La información ha sido filtrada según los criterios seleccionados.'
            }
        })
        return response

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'kpis': {
                'total_ventas': float(context['total_ventas']),
                'total_pagado': float(context['total_pagado']),
                'saldo_pendiente_total': float(context['saldo_pendiente_total']),
                'numero_transacciones': context['numero_transacciones'],
                'venta_maxima': float(context['venta_maxima']),
                'promedio_ventas': float(context['promedio_ventas']),
                'ventas_contado_total': float(context['ventas_contado_total']),
                'ventas_contado_count': context['ventas_contado_count'],
                'ventas_credito_total': float(context['ventas_credito_total']),
                'ventas_credito_count': context['ventas_credito_count'],
                'ventas_vencidas_total': float(context['ventas_vencidas_total']),
                'ventas_vencidas_count': context['ventas_vencidas_count'],
                'total_facturado_cfdi': float(context['total_facturado_cfdi']),
                'total_notas_credito_cfdi': float(context['total_notas_credito_cfdi']),
                'total_recibos_pago_cfdi': float(context['total_recibos_pago_cfdi']),
                'numero_cfdis': context['numero_cfdis'],
            },
            'chart_data': {
                'modalidad': json.loads(context['ventas_por_modalidad']),
                'estados': json.loads(context['ventas_por_estado']),
                'clientes': json.loads(context['ventas_por_cliente']),
            },
            'results_html': results_html,
        })

    context['results_html'] = results_html
    return render(request, 'ventas/ventas_balances.html', context)


def describir_filtros_balances(f):
    """Filtros activos en texto legible para la portada de los reportes."""
    def nombre(modelo, pk, campo='nombre'):
        obj = modelo.objects.filter(pk=pk).first() if str(pk).isdigit() else None
        return getattr(obj, campo, pk) if obj else pk

    meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio',
             'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    filtros = []
    if f['cliente_id']:
        filtros.append(('Cliente', nombre(Cliente, f['cliente_id'])))
    if f['cuenta_id']:
        filtros.append(('Cuenta', nombre(Cuenta, f['cuenta_id'], 'numero_cuenta')))
    if f['sucursal_id']:
        filtros.append(('Sucursal', nombre(Sucursal, f['sucursal_id'])))
    if f['mercado_id']:
        filtros.append(('Mercado', nombre(MercadoDestino, f['mercado_id'])))
    if f['modalidad']:
        filtros.append(('Modalidad', dict(Ventas.ModalidadPago.choices).get(f['modalidad'], f['modalidad'])))
    if f['estado']:
        filtros.append(('Estado', dict(Ventas.EstadoCobranza.choices).get(f['estado'], f['estado'])))

    if f['periodo'] == 'diario':
        if f['tipo_fecha'] == 'rango' and (f['fecha_inicio'] or f['fecha_fin']):
            filtros.append(('Periodo', f"{f['fecha_inicio'] or 'inicio'} a {f['fecha_fin'] or 'hoy'}"))
        elif f['dia']:
            filtros.append(('Día', f['dia']))
    elif f['periodo'] == 'mensual' and f['tipo_mes'] == 'rango' and (f['mes_inicio'] or f['mes_fin']):
        filtros.append(('Periodo', f"{f['mes_inicio'] or 'inicio'} a {f['mes_fin'] or 'hoy'}"))
    else:
        texto = f['year']
        if f['months']:
            texto += ' · ' + ', '.join(meses[int(m) - 1] for m in f['months'])
        filtros.append(('Año', texto))
    filtros.append(('Agrupación', f['periodo'].capitalize()))
    return filtros


def _datos_reporte_balances(request):
    from .services.reportes_export import datos_reporte_ventas

    f = leer_filtros_balances(request)
    ventas_qs = Ventas.objects.filter(q_ventas_balances(f))
    cfdi_qs = DocumentoCFDI.objects.filter(
        _build_cfdi_filters(f['cliente_id'], f['filtros_fecha'])
    )
    return datos_reporte_ventas(ventas_qs, cfdi_qs), describir_filtros_balances(f)


def _archivo(contenido, content_type, nombre):
    response = HttpResponse(contenido, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{nombre}"'
    return response


@login_required
@permission_required('ventas.view_ventas', raise_exception=True)
def exportar_balances_xlsx(request):
    """Reporte Excel del análisis de ventas con los filtros actuales.

    Hojas: resumen e indicadores, tendencia mensual, clientes ABC, antigüedad
    de cartera, productos, sucursales, ventas sin CFDI y detalle.
    """
    from .services.reportes_export import reporte_ventas_xlsx

    datos, filtros = _datos_reporte_balances(request)
    return _archivo(
        reporte_ventas_xlsx(datos, filtros),
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        f'analisis_ventas_{date.today():%Y%m%d}.xlsx',
    )


@login_required
@permission_required('ventas.view_ventas', raise_exception=True)
def exportar_balances_pdf(request):
    """Reporte PDF ejecutivo del análisis de ventas con los filtros actuales."""
    from .services.reportes_export import reporte_ventas_pdf

    datos, filtros = _datos_reporte_balances(request)
    return _archivo(
        reporte_ventas_pdf(datos, filtros),
        'application/pdf',
        f'analisis_ventas_{date.today():%Y%m%d}.pdf',
    )


@login_required
@permission_required('ventas.view_ventas', raise_exception=True)
def reporte_cobranza_global(request):
    """
    Vista principal del Reporte Global de Cobranza.

    GET params:
        fecha_inicio  (YYYY-MM-DD)  — inicio del período
        fecha_fin     (YYYY-MM-DD)  — fin del período
        tipo_cambio   (decimal)     — override manual del tipo de cambio USD→MXN
    """
    hoy = date.today()
    # Default: temporada / año fiscal actual (1-ene al 31-dic)
    default_inicio = date(hoy.year, 1, 1)
    default_fin = date(hoy.year, 12, 31)

    fecha_inicio_str = request.GET.get('fecha_inicio', default_inicio.isoformat())
    fecha_fin_str = request.GET.get('fecha_fin', default_fin.isoformat())
    tipo_cambio_str = request.GET.get('tipo_cambio', '')

    # Parsear fechas
    try:
        fecha_inicio = date.fromisoformat(fecha_inicio_str)
    except (ValueError, TypeError):
        fecha_inicio = default_inicio

    try:
        fecha_fin = date.fromisoformat(fecha_fin_str)
    except (ValueError, TypeError):
        fecha_fin = default_fin

    # Parsear tipo de cambio
    tipo_cambio_override = None
    if tipo_cambio_str:
        try:
            tipo_cambio_override = Decimal(tipo_cambio_str)
        except Exception:
            pass

    datos = generar_reporte_cobranza(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        tipo_cambio_override=tipo_cambio_override,
    )

    context = {
        **datos,
        'fecha_inicio_str': fecha_inicio.isoformat(),
        'fecha_fin_str': fecha_fin.isoformat(),
        'tipo_cambio_input': tipo_cambio_str,
        'hoy': hoy,
    }
    return render(request, 'ventas/reporte_cobranza.html', context)
