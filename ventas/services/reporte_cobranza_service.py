"""
Servicio para generar el Reporte Global de Cobranza.

Produce tres secciones:
  1. Ventas x Cobrar — por cliente, desglosado por sucursal.
  2. Maquila x Cobrar — por cliente, desglosado por sucursal (moneda USD + conversión MXN).
  3. Impuestos a Pagar — desde el modelo ObligacionFiscal.
"""
from decimal import Decimal
from collections import defaultdict

from django.db.models import Sum, Avg, Q

from catalogo.models import Sucursal
from ventas.models import Anticipo, ObligacionFiscal, Ventas


# Estados que representan deuda pendiente de cobro
ESTADOS_CON_DEUDA = ['Pendiente', 'Parcial', 'Vencido']


def _saldo_float(venta):
    """Retorna el saldo pendiente de una venta como float, nunca negativo."""
    saldo = float(venta.monto.amount) - float(venta.monto_pagado.amount)
    return max(saldo, 0.0)


def generar_reporte_cobranza(fecha_inicio=None, fecha_fin=None, tipo_cambio_override=None):
    """
    Genera los datos para el reporte global de cobranza.

    Parámetros:
        fecha_inicio (date | None):  Inicio del período. None = sin límite inferior.
        fecha_fin    (date | None):  Fin del período.   None = sin límite superior.
        tipo_cambio_override (Decimal | None): Override manual del tipo de cambio USD→MXN.

    Retorna dict con claves:
        sucursales          — lista ordenada de Sucursal usadas en el período
        ventas_por_cliente  — lista de filas para la tabla Ventas x Cobrar
        maquila_por_cliente — lista de filas para la tabla Maquila x Cobrar
        totales_ventas      — dict de totales de la sección ventas
        totales_maquila     — dict de totales de la sección maquila (USD + MXN)
        tipo_cambio         — tipo de cambio efectivo usado para maquila
        anticipos_por_cliente — dict {cliente_id: monto_float} saldos FVR
        obligacion_fiscal   — instancia ObligacionFiscal más reciente o None
        fecha_inicio        — fecha inicio del período
        fecha_fin           — fecha fin del período
    """
    # -------------------------------------------------------------------------
    # 1. Base querysets filtradas por período
    # -------------------------------------------------------------------------
    qs_base = Ventas.objects.select_related('cliente', 'sucursal_id').filter(
        estado_cobranza__in=ESTADOS_CON_DEUDA
    )
    if fecha_inicio:
        qs_base = qs_base.filter(fecha_salida_manifiesto__gte=fecha_inicio)
    if fecha_fin:
        qs_base = qs_base.filter(fecha_salida_manifiesto__lte=fecha_fin)

    qs_ventas = qs_base.filter(tipo_registro='VENTA')
    qs_maquila = qs_base.filter(tipo_registro='MAQUILA')

    # -------------------------------------------------------------------------
    # 2. Sucursales con movimientos en el período
    # -------------------------------------------------------------------------
    sucursal_ids_ventas = set(qs_ventas.values_list('sucursal_id_id', flat=True))
    sucursal_ids_maquila = set(qs_maquila.values_list('sucursal_id_id', flat=True))
    all_sucursal_ids = sucursal_ids_ventas | sucursal_ids_maquila

    sucursales = list(
        Sucursal.objects.filter(id__in=all_sucursal_ids).order_by('nombre')
    )

    # -------------------------------------------------------------------------
    # 3. Tabla Ventas x Cobrar
    # -------------------------------------------------------------------------
    ventas_por_cliente = _calcular_saldos_por_cliente(qs_ventas, sucursales, moneda='MXN')

    totales_ventas = _calcular_totales(ventas_por_cliente, sucursales)

    # -------------------------------------------------------------------------
    # 4. Tabla Maquila x Cobrar
    # -------------------------------------------------------------------------
    maquila_por_cliente = _calcular_saldos_por_cliente(qs_maquila, sucursales, moneda='USD')

    # Tipo de cambio: usar override manual o promedio de los registros
    if tipo_cambio_override and Decimal(str(tipo_cambio_override)) > 0:
        tipo_cambio = Decimal(str(tipo_cambio_override))
    else:
        avg = qs_maquila.aggregate(avg=Avg('tipo_cambio'))['avg']
        tipo_cambio = Decimal(str(avg)) if avg else Decimal('1.0000')

    totales_maquila = _calcular_totales(maquila_por_cliente, sucursales, tipo_cambio=tipo_cambio)

    # -------------------------------------------------------------------------
    # 5. Anticipos pendientes (SALDO FVR CLIENTE)
    # -------------------------------------------------------------------------
    anticipos_qs = Anticipo.objects.filter(estado_anticipo='Pendiente').select_related('cliente')
    if fecha_inicio:
        anticipos_qs = anticipos_qs.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        anticipos_qs = anticipos_qs.filter(fecha__lte=fecha_fin)

    anticipos_por_cliente = defaultdict(float)
    for a in anticipos_qs:
        anticipos_por_cliente[a.cliente_id] += float(a.monto.amount)

    # Inyectar saldo FVR en las filas de ventas
    for fila in ventas_por_cliente:
        cliente_id = fila['cliente'].id
        fila['anticipo'] = anticipos_por_cliente.get(cliente_id, 0.0)

    # Total global de anticipos (encabezado "PANORAMA ANTICIPOS")
    total_anticipos = sum(anticipos_por_cliente.values())

    # -------------------------------------------------------------------------
    # 6. Obligación fiscal más reciente del período
    # -------------------------------------------------------------------------
    obligacion_fiscal = ObligacionFiscal.objects.order_by('-fecha_registro').first()

    return {
        'sucursales': sucursales,
        'ventas_por_cliente': ventas_por_cliente,
        'maquila_por_cliente': maquila_por_cliente,
        'totales_ventas': totales_ventas,
        'totales_maquila': totales_maquila,
        'tipo_cambio': tipo_cambio,
        'anticipos_por_cliente': dict(anticipos_por_cliente),
        'total_anticipos': total_anticipos,
        'obligacion_fiscal': obligacion_fiscal,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    }


# =============================================================================
# Helpers
# =============================================================================

def _calcular_saldos_por_cliente(qs, sucursales, moneda='MXN'):
    """
    Agrupa el queryset de Ventas por (cliente, sucursal) y
    retorna una lista de dicts, uno por cliente.

    Cada dict:
        cliente         — instancia Cliente
        por_sucursal    — {sucursal.id: saldo_float}
        total           — saldo total del cliente
    """
    # Agrupar en Python para poder llamar saldo_pendiente() sin duplicar lógica SQL
    # (el saldo = monto - monto_pagado, ya calculado en el modelo)
    acum = defaultdict(lambda: defaultdict(float))   # {cliente_id: {sucursal_id: saldo}}
    clientes_map = {}

    for v in qs:
        saldo = _saldo_float(v)
        if saldo <= 0:
            continue
        cid = v.cliente_id
        sid = v.sucursal_id_id
        acum[cid][sid] += saldo
        clientes_map[cid] = v.cliente

    filas = []
    for cid, por_suc in acum.items():
        total = sum(por_suc.values())
        filas.append({
            'cliente': clientes_map[cid],
            'por_sucursal': dict(por_suc),
            'total': total,
            'anticipo': 0.0,   # se rellena más abajo para ventas
            'moneda': moneda,
        })

    # Ordenar por nombre del cliente
    filas.sort(key=lambda r: r['cliente'].nombre)
    return filas


def _calcular_totales(filas, sucursales, tipo_cambio=None):
    """
    Calcula totales de columna a partir de las filas.

    Si se proporciona tipo_cambio, también añade total_mxn (USD→MXN).
    """
    total_general = 0.0
    por_sucursal = {s.id: 0.0 for s in sucursales}

    for fila in filas:
        total_general += fila['total']
        for sid, monto in fila['por_sucursal'].items():
            if sid in por_sucursal:
                por_sucursal[sid] += monto

    result = {
        'total': total_general,
        'por_sucursal': por_sucursal,
    }
    if tipo_cambio is not None:
        result['total_mxn'] = total_general * float(tipo_cambio)
        result['tipo_cambio'] = tipo_cambio

    return result
