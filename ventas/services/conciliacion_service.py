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

from django.db.models import Count

from ..models import DocumentoCFDI

INGRESOS_VENTA = ['venta_nacional', 'venta_exportacion']


def _sum_por_moneda(docs, subtipos):
    resultado = defaultdict(float)
    for doc in docs.filter(subtipo__in=subtipos):
        resultado[doc.moneda or 'MXN'] += float(doc.monto.amount)
    return dict(resultado)


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

    # Anticipos pendientes de aplicar (saldo a favor del cliente)
    anticipo_por_moneda = defaultdict(float)
    for a in cliente.anticipo_set.exclude(estado_anticipo='Cancelado'):
        anticipo_por_moneda[a.monto.currency] += a.saldo_disponible()
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
            - detalle['anticipos_disponibles'].get(mon, 0.0)
        )

    # Documentos que no pudieron vincularse a una venta (posible deriva):
    # son notas de cargo/crédito o recibos de pago cuyo CFDI padre no fue
    # encontrado por UUID (p. ej. la factura aún no se importa o no coincide).
    sin_venta_qs = docs.filter(
        venta__isnull=True
    ).exclude(subtipo__in=INGRESOS_VENTA + ['remanente_anticipo'])

    sin_venta_detalle = [
        {
            'subtipo': item['subtipo'],
            'total': item['total'],
            'label': DocumentoCFDI.SubtipoDocumento(item['subtipo']).label,
        }
        for item in sin_venta_qs.values('subtipo').annotate(total=Count('id')).order_by('subtipo')
    ]

    return {
        'cliente': cliente,
        'detalle': detalle,
        'saldo_por_moneda': saldo,
        'total_documentos': docs.count(),
        'documentos_sin_venta': sin_venta_qs.count(),
        'sin_venta_detalle': sin_venta_detalle,
    }


def conciliacion_global():
    """Conciliación de todos los clientes activos."""
    from ..models import Cliente
    return [
        conciliacion_cliente(c)
        for c in Cliente.objects.filter(activo=True).order_by('nombre')
    ]
