"""
Servicio de conciliación de CFDI por cliente.

Los CFDI son los documentos fiscales reales que el cliente usa para calcular
sus ingresos y egresos. Este servicio cruza el ledger de DocumentoCFDI contra
los modelos operativos (Ventas/PagoVenta/Anticipo) y produce, por cliente:

  - Desglose por tipo de documento separado por moneda.
  - Saldo por cobrar conciliado (ventas + notas de cargo - notas de crédito
    - recibos de pago - anticipos disponibles).
  - Detección de documentos no vinculados a una venta (posible deriva).
"""
from collections import defaultdict

from ..models import DocumentoCFDI

INGRESOS_VENTA = [
    'venta_nacional', 'venta_exportacion', 'ingreso_servicio',
    'otros_ingresos',
]


def _sum_por_moneda(docs, subtipos):
    resultado = defaultdict(float)
    for doc in docs.filter(subtipo__in=subtipos):
        resultado[doc.moneda or 'MXN'] += float(doc.monto.amount)
    return dict(resultado)


def _en_rango(queryset, campo, fecha_inicio, fecha_fin):
    """Aplica filtro de rango de fechas (inclusive) sobre ``campo``."""
    if fecha_inicio:
        queryset = queryset.filter(**{f'{campo}__gte': fecha_inicio})
    if fecha_fin:
        queryset = queryset.filter(**{f'{campo}__lte': fecha_fin})
    return queryset


def _fecha_en_rango(fecha, fecha_inicio, fecha_fin):
    if fecha is None:
        return not (fecha_inicio or fecha_fin)
    if fecha_inicio and fecha < fecha_inicio:
        return False
    if fecha_fin and fecha > fecha_fin:
        return False
    return True


def cobros_no_rep(cliente, fecha_inicio=None, fecha_fin=None):
    """Cobros de ventas que no están respaldados por un recibo de pago (REP).

    Las facturas de contado (MetodoPago PUE) se pagan al emitirse y no generan
    Recibo Electrónico de Pago, por lo que su cobro vive en ``Ventas.monto_pagado``
    (en la moneda de la venta). Las ventas a crédito con pagos manuales usan sus
    ``PagoVenta``, respetando la moneda real del pago.

    Solo cuenta la parte que no está ya representada por un REP vigente, para no
    restar dos veces. Con rango de fechas, considera los pagos del periodo.
    """
    rep_por_venta = defaultdict(float)
    rep_docs = _en_rango(
        cliente.documentos_cfdi.filter(
            estado='VIGENTE', subtipo='recibo_pago', venta__isnull=False
        ),
        'fecha_emision', fecha_inicio, fecha_fin,
    )
    for doc in rep_docs:
        rep_por_venta[doc.venta_id] += float(doc.monto.amount)

    cobros = defaultdict(float)
    for venta in cliente.ventas_set.all():
        pagos = list(_en_rango(
            venta.pagos.all(), 'fecha_pago', fecha_inicio, fecha_fin
        ))
        if pagos:
            total_pagos = sum(float(p.monto_pago.amount) for p in pagos)
            sin_rep = total_pagos - rep_por_venta.get(venta.id, 0.0)
            if sin_rep <= 0:
                continue
            monedas = {str(p.monto_pago.currency) for p in pagos}
            moneda = (
                monedas.pop() if len(monedas) == 1
                else (venta.moneda_venta or 'MXN')
            )
            cobros[moneda] += sin_rep
            continue

        if venta.modalidad_pago != 'Contado':
            continue
        if not _fecha_en_rango(venta.fecha_deposito, fecha_inicio, fecha_fin):
            continue
        pagado = float(venta.monto_pagado.amount)
        if pagado <= 0:
            continue
        moneda = str(venta.monto_pagado.currency) or venta.moneda_venta or 'MXN'
        cobros[moneda] += pagado
    return dict(cobros)


def pagos_total_mxn(cliente, fecha_inicio=None, fecha_fin=None):
    """Total cobrado en pesos (equivalente MXN) usando el tipo de cambio.

    Suma los ``PagoVenta`` (con su ``monto_pago_mxn``) y, para ventas de contado
    sin pagos registrados, el ``monto_pagado`` convertido con el tipo de cambio
    de la venta.
    """
    from ..models import PagoVenta

    total = 0.0
    pagos = _en_rango(
        PagoVenta.objects.filter(venta__cliente=cliente).select_related('venta'),
        'fecha_pago', fecha_inicio, fecha_fin,
    )
    for pago in pagos:
        total += float(pago.monto_pago_mxn)

    for venta in cliente.ventas_set.filter(pagos__isnull=True, modalidad_pago='Contado'):
        if not _fecha_en_rango(venta.fecha_deposito, fecha_inicio, fecha_fin):
            continue
        if venta.monto_pagado and venta.monto_pagado.amount > 0:
            total += float(venta.monto_pagado.amount) * float(venta.tipo_cambio or 1)

    return round(total, 2)


def conciliacion_cliente(cliente, fecha_inicio=None, fecha_fin=None):
    """Calcula la conciliación fiscal completa de un cliente.

    ``fecha_inicio``/``fecha_fin`` (date) limitan los documentos (por
    ``fecha_emision``), pagos (``fecha_pago``) y anticipos (``fecha``) al
    periodo. Sin fechas, se considera todo el histórico.
    """
    docs = _en_rango(
        cliente.documentos_cfdi.filter(estado='VIGENTE'),
        'fecha_emision', fecha_inicio, fecha_fin,
    )

    detalle = {
        'facturado': _sum_por_moneda(docs, INGRESOS_VENTA),
        'notas_cargo': _sum_por_moneda(docs, ['nota_cargo']),
        'notas_credito': _sum_por_moneda(docs, ['nota_credito']),
        'recibos_pago': _sum_por_moneda(docs, ['recibo_pago']),
        'remanentes_anticipo': _sum_por_moneda(docs, ['remanente_anticipo']),
    }

    # Cobros de contado / sin REP: descuentan el pago ya recibido que no tiene
    # un recibo electrónico de pago asociado (típicamente facturas PUE).
    detalle['cobros_contado'] = cobros_no_rep(cliente, fecha_inicio, fecha_fin)

    # Anticipos pendientes de aplicar (saldo a favor del cliente)
    anticipo_por_moneda = defaultdict(float)
    anticipos = _en_rango(
        cliente.anticipo_set.exclude(estado_anticipo='Cancelado'),
        'fecha', fecha_inicio, fecha_fin,
    )
    for a in anticipos:
        anticipo_por_moneda[str(a.monto.currency)] += a.saldo_disponible()
    detalle['anticipos_disponibles'] = dict(anticipo_por_moneda)

    # Saldo por cobrar conciliado, por moneda
    monedas = set()
    for d in detalle.values():
        monedas.update(d.keys())

    saldo = {}
    for mon in monedas:
        saldo[mon] = (
            detalle['facturado'].get(mon, 0.0)
            + detalle['notas_cargo'].get(mon, 0.0)
            - detalle['notas_credito'].get(mon, 0.0)
            - detalle['recibos_pago'].get(mon, 0.0)
            - detalle['cobros_contado'].get(mon, 0.0)
            - detalle['anticipos_disponibles'].get(mon, 0.0)
        )

    # Documentos que no pudieron vincularse a una venta (posible deriva):
    # son notas de cargo/crédito o recibos de pago cuyo CFDI padre no fue
    # encontrado por UUID (p. ej. la factura aún no se importa o no coincide).
    # Se materializan los propios documentos para poder desglosarlos y enlazar
    # cada uno a su ficha en el admin.
    sin_venta_qs = (
        docs.filter(venta__isnull=True)
        .exclude(subtipo__in=INGRESOS_VENTA + ['remanente_anticipo'])
        .select_related('cfdi_relacionado')
        .order_by('subtipo', '-fecha_emision')
    )

    por_subtipo = defaultdict(list)
    for doc in sin_venta_qs:
        por_subtipo[doc.subtipo].append({
            'id': doc.id,
            'folio': doc.folio or '',
            'uuid': doc.uuid or '',
            'fecha': doc.fecha_emision,
            'monto': doc.monto.amount,
            'moneda': doc.moneda or 'MXN',
            'relacionado_id': doc.cfdi_relacionado_id,
            'relacionado_label': str(doc.cfdi_relacionado) if doc.cfdi_relacionado_id else '',
            'tipo_relacion': doc.tipo_relacion or '',
        })

    sin_venta_detalle = [
        {
            'subtipo': subtipo,
            'total': len(documentos),
            'label': DocumentoCFDI.SubtipoDocumento(subtipo).label,
            'documentos': documentos,
        }
        for subtipo, documentos in sorted(por_subtipo.items())
    ]

    return {
        'cliente': cliente,
        'detalle': detalle,
        'saldo_por_moneda': saldo,
        'pagos_mxn': pagos_total_mxn(cliente, fecha_inicio, fecha_fin),
        'total_documentos': docs.count(),
        'documentos_sin_venta': sum(item['total'] for item in sin_venta_detalle),
        'sin_venta_detalle': sin_venta_detalle,
    }


def conciliacion_global(fecha_inicio=None, fecha_fin=None):
    """Conciliación de todos los clientes activos (opcionalmente por periodo)."""
    from ..models import Cliente
    return [
        conciliacion_cliente(c, fecha_inicio, fecha_fin)
        for c in Cliente.objects.filter(activo=True).order_by('nombre')
    ]
