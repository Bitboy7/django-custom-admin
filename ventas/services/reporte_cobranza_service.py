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
from ventas.models import Anticipo, ObligacionFiscal, Ventas, ConfiguracionCuentasPorCobrar


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
    # 3. Tabla Ventas x Cobrar (agrupada por cliente × moneda_venta)
    # -------------------------------------------------------------------------
    ventas_por_cliente = _calcular_saldos_por_cliente(qs_ventas, sucursales)

    # Tipo de cambio para convertir ventas USD → MXN
    avg_tc_ventas = qs_ventas.filter(moneda_venta='USD').aggregate(avg=Avg('tipo_cambio'))['avg']

    filas_venta_usd = [f for f in ventas_por_cliente if f['moneda'] == 'USD']
    filas_venta_mxn = [f for f in ventas_por_cliente if f['moneda'] == 'MXN']
    totales_ventas_usd = _calcular_totales(filas_venta_usd, sucursales)
    totales_ventas_mxn_obj = _calcular_totales(filas_venta_mxn, sucursales)
    totales_ventas = _calcular_totales(ventas_por_cliente, sucursales)  # suma mixta (legacy)

    # -------------------------------------------------------------------------
    # 4. Tabla Maquila x Cobrar
    # -------------------------------------------------------------------------
    maquila_por_cliente = _calcular_saldos_por_cliente(qs_maquila, sucursales)

    # Tipo de cambio: usar override manual o valor centralizado en configuración
    if tipo_cambio_override and Decimal(str(tipo_cambio_override)) > 0:
        tipo_cambio = Decimal(str(tipo_cambio_override))
    else:
        config_tc = ConfiguracionCuentasPorCobrar.obtener_configuracion().tipo_cambio_usd
        tipo_cambio = Decimal(str(config_tc))

    totales_maquila = _calcular_totales(maquila_por_cliente, sucursales, tipo_cambio=tipo_cambio)

    # -------------------------------------------------------------------------
    # 5. Saldo a favor del cliente (anticipos + excedentes de anticipos aplicados)
    # -------------------------------------------------------------------------
    # 5a. Anticipos Pendientes (no aplicados a ninguna venta)
    anticipos_qs = Anticipo.objects.filter(estado_anticipo='Pendiente').select_related('cliente')
    if fecha_inicio:
        anticipos_qs = anticipos_qs.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        anticipos_qs = anticipos_qs.filter(fecha__lte=fecha_fin)

    anticipos_por_cliente = defaultdict(float)
    for a in anticipos_qs:
        anticipos_por_cliente[a.cliente_id] += float(a.monto.amount)

    # 5b. Anticipo aplicado cuyo monto supera el total de la venta (excedente)
    #     Ocurre cuando el cliente depositó más de lo que valía la factura y
    #     el anticipo fue marcado como Aplicado sin ajustar el importe restante.
    ventas_con_excedente = (
        Ventas.objects.filter(anticipo__isnull=False, anticipo__estado_anticipo='Aplicado')
        .select_related('cliente', 'anticipo')
    )
    if fecha_inicio:
        ventas_con_excedente = ventas_con_excedente.filter(
            fecha_salida_manifiesto__gte=fecha_inicio
        )
    if fecha_fin:
        ventas_con_excedente = ventas_con_excedente.filter(
            fecha_salida_manifiesto__lte=fecha_fin
        )
    for v in ventas_con_excedente:
        excedente = float(v.anticipo.monto.amount) - float(v.monto.amount)
        if excedente > 0:
            anticipos_por_cliente[v.cliente_id] += excedente

    # Inyectar saldo FVR en las filas de ventas (solo en la primera fila por cliente)
    seen_anticipo_ids = set()
    for fila in ventas_por_cliente:
        cliente_id = fila['cliente'].id
        if cliente_id not in seen_anticipo_ids:
            fila['anticipo'] = anticipos_por_cliente.get(cliente_id, 0.0)
            seen_anticipo_ids.add(cliente_id)

    # Total global de saldo a favor (encabezado "PANORAMA ANTICIPOS / SALDO FVR")
    total_anticipos = sum(anticipos_por_cliente.values())

    # -------------------------------------------------------------------------
    # 6. Obligación fiscal más reciente del período
    # -------------------------------------------------------------------------
    obligacion_fiscal = ObligacionFiscal.objects.order_by('-fecha_registro').first()

    # -------------------------------------------------------------------------
    # 7. Equivalencias y cartera consolidada de Ventas (como un banco)
    # -------------------------------------------------------------------------
    # Tipo de cambio ventas: promedio real del período o fallback a TC maquila
    if avg_tc_ventas:
        tipo_cambio_ventas = Decimal(str(avg_tc_ventas)).quantize(Decimal('0.0001'))
    else:
        tipo_cambio_ventas = tipo_cambio

    total_ventas_usd      = totales_ventas_usd['total']
    total_ventas_mxn_nat  = totales_ventas_mxn_obj['total']
    total_ventas_equiv_mxn = total_ventas_usd * float(tipo_cambio_ventas)
    total_cartera_ventas_mxn = total_ventas_mxn_nat + total_ventas_equiv_mxn

    return {
        'sucursales': sucursales,
        'ventas_por_cliente': ventas_por_cliente,
        'maquila_por_cliente': maquila_por_cliente,
        'totales_ventas': totales_ventas,
        'totales_ventas_usd': totales_ventas_usd,
        'totales_ventas_mxn_obj': totales_ventas_mxn_obj,
        'tipo_cambio_ventas': tipo_cambio_ventas,
        'total_ventas_usd': total_ventas_usd,
        'total_ventas_mxn_nat': total_ventas_mxn_nat,
        'total_ventas_equiv_mxn': total_ventas_equiv_mxn,
        'total_cartera_ventas_mxn': total_cartera_ventas_mxn,
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

def _calcular_saldos_por_cliente(qs, sucursales):
    """
    Agrupa por (cliente, moneda_venta) — una fila por combinación.
    El campo 'moneda' en cada fila es la moneda real del saldo ('USD' o 'MXN').
    Esto permite calcular correctamente equivalencias sin mezclar divisas.
    """
    # acum[cliente_id][moneda][sucursal_id] = saldo_float
    acum = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    clientes_map = {}

    for v in qs:
        saldo = _saldo_float(v)
        if saldo <= 0:
            continue
        cid = v.cliente_id
        sid = v.sucursal_id_id
        mon = 'USD' if (getattr(v, 'moneda_venta', 'MXN') or 'MXN').upper() == 'USD' else 'MXN'
        acum[cid][mon][sid] += saldo
        clientes_map[cid] = v.cliente

    filas = []
    for cid, por_moneda in acum.items():
        for mon, por_suc in por_moneda.items():
            total = sum(por_suc.values())
            if total > 0:
                filas.append({
                    'cliente': clientes_map[cid],
                    'por_sucursal': dict(por_suc),
                    'total': total,
                    'moneda': mon,
                    'anticipo': 0.0,
                })

    # Ordenar por nombre del cliente, luego por moneda (MXN < USD)
    filas.sort(key=lambda r: (r['cliente'].nombre, r['moneda']))
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
