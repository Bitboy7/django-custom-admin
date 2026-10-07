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
]


def _sum_por_moneda(docs, subtipos):
    resultado = defaultdict(float)
    for doc in docs.filter(subtipo__in=subtipos):
        resultado[doc.moneda or 'MXN'] += float(doc.monto.amount)
    return dict(resultado)


def cobros_no_rep(cliente):
    """Cobros de ventas que no están respaldados por un recibo de pago (REP).

    Las facturas de contado (MetodoPago PUE) se pagan al emitirse y no generan
    Recibo Electrónico de Pago, por lo que su cobro vive en ``Ventas.monto_pagado``
    y no en un ``DocumentoCFDI`` de tipo recibo_pago. Sin este ajuste, la
    conciliación mostraría la factura completa como saldo por cobrar, como si
    fuera a crédito.

    Solo se descuenta la parte del pago que no está ya representada por un REP
    vigente, para no restar dos veces en las ventas a crédito.
    """
    rep_por_venta = defaultdict(float)
    for doc in cliente.documentos_cfdi.filter(
        estado='VIGENTE', subtipo='recibo_pago', venta__isnull=False
    ):
        rep_por_venta[doc.venta_id] += float(doc.monto.amount)

    cobros = defaultdict(float)
    for venta in cliente.ventas_set.all():
        pagado = float(venta.monto_pagado.amount)
        if pagado <= 0:
            continue
        sin_rep = pagado - rep_por_venta.get(venta.id, 0.0)
        if sin_rep > 0:
            moneda = str(venta.monto_pagado.currency) or venta.moneda_venta or 'MXN'
            cobros[moneda] += sin_rep
    return dict(cobros)


def conciliacion_cliente(cliente):
    """Calcula la conciliación fiscal completa de un cliente."""
    docs = cliente.documentos_cfdi.filter(estado='VIGENTE')

    detalle = {
        'facturado': _sum_por_moneda(docs, INGRESOS_VENTA),
        'notas_cargo': _sum_por_moneda(docs, ['nota_cargo']),
        'notas_credito': _sum_por_moneda(docs, ['nota_credito']),
        'recibos_pago': _sum_por_moneda(docs, ['recibo_pago']),
        'remanentes_anticipo': _sum_por_moneda(docs, ['remanente_anticipo']),
    }

    # Cobros de contado / sin REP: descuentan el pago ya recibido que no tiene
    # un recibo electrónico de pago asociado (típicamente facturas PUE).
    detalle['cobros_contado'] = cobros_no_rep(cliente)

    # Anticipos pendientes de aplicar (saldo a favor del cliente)
    anticipo_por_moneda = defaultdict(float)
    for a in cliente.anticipo_set.exclude(estado_anticipo='Cancelado'):
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
        'total_documentos': docs.count(),
        'documentos_sin_venta': sum(item['total'] for item in sin_venta_detalle),
        'sin_venta_detalle': sin_venta_detalle,
    }


def conciliacion_global():
    """Conciliación de todos los clientes activos."""
    from ..models import Cliente
    return [
        conciliacion_cliente(c)
        for c in Cliente.objects.filter(activo=True).order_by('nombre')
    ]
