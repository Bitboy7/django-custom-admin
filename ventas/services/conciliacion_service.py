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
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from ..models import DocumentoCFDI

INGRESOS_VENTA = [
    'venta_nacional', 'venta_exportacion', 'ingreso_servicio',
    'otros_ingresos',
]


def _sum_por_moneda(docs, subtipos):
    resultado = defaultdict(float)
    for doc in docs:
        if doc.subtipo in subtipos:
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


def _fecha_iso_a_date(valor):
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if not valor:
        return None
    try:
        return date.fromisoformat(str(valor)[:10])
    except (TypeError, ValueError):
        return None


def _decimal(valor):
    try:
        return Decimal(str(valor if valor not in (None, '') else '0'))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal('0')


def _detalle_rep_tiene_pagos(documento):
    detalle = documento.detalle_complemento or {}
    return isinstance(detalle, dict) and isinstance(detalle.get('pagos'), list)


def _movimientos_rep(documento, fecha_inicio=None, fecha_fin=None):
    """Itera aplicaciones REP por DoctoRelacionado o el respaldo histórico."""
    detalle = documento.detalle_complemento or {}
    pagos = detalle.get('pagos') if isinstance(detalle, dict) else None
    if isinstance(pagos, list):
        for pago in pagos:
            fecha_pago = _fecha_iso_a_date(pago.get('fecha_pago'))
            if not _fecha_en_rango(fecha_pago, fecha_inicio, fecha_fin):
                continue
            for docto in (pago.get('doctos') or []):
                yield {
                    'uuid_factura': docto.get('uuid') or '',
                    'fecha_pago': fecha_pago,
                    'fecha_fuente': 'FechaPago',
                    'monto': _decimal(docto.get('imp_pagado')),
                    'saldo_insoluto': _decimal(docto.get('saldo_insoluto')),
                    'moneda': docto.get('moneda') or documento.moneda or 'MXN',
                    'legacy': False,
                }
        return

    if _fecha_en_rango(documento.fecha_emision, fecha_inicio, fecha_fin):
        yield {
            'uuid_factura': '',
            'fecha_pago': documento.fecha_emision,
            'fecha_fuente': 'fecha_emision',
            'monto': _decimal(documento.monto.amount),
            'saldo_insoluto': None,
            'moneda': documento.moneda or 'MXN',
            'legacy': True,
        }


def pagos_rep_por_moneda(documentos, fecha_inicio=None, fecha_fin=None):
    """Suma ``ImpPagado`` por ``MonedaDR``, usando ``FechaPago`` por nodo."""
    por_moneda = defaultdict(Decimal)
    for documento in documentos:
        if documento.subtipo != 'recibo_pago' or documento.estado != 'VIGENTE':
            continue
        for movimiento in _movimientos_rep(documento, fecha_inicio, fecha_fin):
            por_moneda[movimiento['moneda']] += movimiento['monto']
    return dict(por_moneda)


def _rep_documento_en_rango(documento, fecha_inicio=None, fecha_fin=None):
    detalle = documento.detalle_complemento or {}
    pagos = detalle.get('pagos') if isinstance(detalle, dict) else None
    if isinstance(pagos, list):
        return any(
            _fecha_en_rango(
                _fecha_iso_a_date(pago.get('fecha_pago')),
                fecha_inicio,
                fecha_fin,
            )
            for pago in pagos
        )
    return _fecha_en_rango(documento.fecha_emision, fecha_inicio, fecha_fin)


def _documento_factura_del_movimiento_rep(movimiento):
    uuid_factura = movimiento.get('uuid_factura')
    if uuid_factura:
        from ..models import DocumentoCFDI

        documentos = list(
            DocumentoCFDI.objects.filter(uuid__iexact=uuid_factura)
            .select_related('venta')[:2]
        )
        if len(documentos) == 1:
            return documentos[0]
    return None


def _venta_id_del_movimiento_rep(documento, movimiento):
    uuid_factura = movimiento.get('uuid_factura')
    if uuid_factura:
        # Una fila histórica sin asociación demostrable conserva su agrupación
        # operativa previa por DocumentoCFDI.venta; el desglose REP sigue
        # mostrando por separado la factura exacta indicada en el XML.
        if documento.venta_id and not _rep_tiene_vinculo_exacto(documento):
            return documento.venta_id
        factura = _documento_factura_del_movimiento_rep(movimiento)
        return factura.venta_id if factura else documento.venta_id
    return documento.venta_id


def _estado_vinculo_rep(documento):
    detalle = documento.detalle_complemento or {}
    estado_guardado = (
        (detalle.get('vinculo_pago') or {}).get('estado')
        if isinstance(detalle, dict) else None
    )

    if not documento.pago_venta_id or not documento.uuid or not documento.venta_id:
        return estado_guardado or 'no_encontrado'

    pago = documento.pago_venta
    if pago.venta_id != documento.venta_id:
        return 'otra_venta'
    if (
        not pago.uuid_rep
        or pago.uuid_rep.strip().upper() != documento.uuid.strip().upper()
    ):
        return estado_guardado or 'no_encontrado'
    if documento.venta.cliente_id != documento.cliente_id:
        return 'cliente_documento_discordante'

    pagos = detalle.get('pagos') if isinstance(detalle, dict) else None
    if not isinstance(pagos, list):
        # Histórico sin JSON: el REP/PagoVenta UUID exacto sigue confirmado,
        # con el origen de monto y fecha marcado como legado aparte.
        return 'uuid_coincidente'
    if not pagos or any(not (pago_rep.get('doctos') or []) for pago_rep in pagos):
        return 'uuid_documento_no_encontrado'

    doctos = [
        docto
        for pago_rep in pagos
        for docto in (pago_rep.get('doctos') or [])
    ]
    for docto in doctos:
        uuid_factura = (docto.get('uuid') or '').strip()
        if not uuid_factura:
            return 'uuid_documento_no_encontrado'
        from ..models import DocumentoCFDI

        facturas = list(
            DocumentoCFDI.objects.filter(uuid__iexact=uuid_factura)
            .select_related('venta')[:2]
        )
        if not facturas:
            return 'uuid_documento_no_encontrado'
        if len(facturas) > 1:
            return 'ambiguo'

        factura = facturas[0]
        if factura.cliente_id != documento.cliente_id or (
            factura.venta_id and factura.venta.cliente_id != documento.cliente_id
        ):
            return 'cliente_documento_discordante'
        if factura.venta_id != documento.venta_id:
            return 'venta_documento_discordante'

    return 'uuid_coincidente'


def _rep_tiene_vinculo_exacto(documento):
    return _estado_vinculo_rep(documento) == 'uuid_coincidente'


def cobros_no_rep(cliente, fecha_inicio=None, fecha_fin=None):
    """Cobros de ventas que no están respaldados por un recibo de pago (REP).

    Las facturas de contado (MetodoPago PUE) se pagan al emitirse y no generan
    Recibo Electrónico de Pago, por lo que su cobro vive en ``Ventas.monto_pagado``
    (en la moneda de la venta). Las ventas a crédito con pagos manuales usan sus
    ``PagoVenta``, respetando la moneda real del pago.

    Solo cuenta la parte que no está ya representada por un REP vigente, para no
    restar dos veces. Con rango de fechas, considera los pagos del periodo.
    """
    cobros, _desglose = _cobros_no_rep_con_detalle(
        cliente, fecha_inicio, fecha_fin, incluir_detalle=False
    )
    return cobros


def _cobros_no_rep_con_detalle(
    cliente, fecha_inicio=None, fecha_fin=None, incluir_detalle=True
):
    """Calcula cobros sin REP y conserva su origen operativo por venta."""
    rep_por_venta_moneda = defaultdict(lambda: defaultdict(Decimal))
    rep_origen = defaultdict(lambda: defaultdict(list))
    pagos_rep_exactos = set()
    rep_docs = list(
        cliente.documentos_cfdi.filter(
            estado='VIGENTE', subtipo='recibo_pago'
        ).select_related('pago_venta')
    )
    for doc in rep_docs:
        if not _rep_documento_en_rango(doc, fecha_inicio, fecha_fin):
            continue
        movimientos = list(_movimientos_rep(doc, fecha_inicio, fecha_fin))
        if (
            _rep_tiene_vinculo_exacto(doc)
            and _detalle_rep_tiene_pagos(doc)
            and any(movimiento['monto'] > 0 for movimiento in movimientos)
        ):
            pagos_rep_exactos.add(doc.pago_venta_id)
            continue
        for movimiento in movimientos:
            venta_id = _venta_id_del_movimiento_rep(doc, movimiento)
            if venta_id is None:
                continue
            moneda = movimiento['moneda']
            rep_por_venta_moneda[venta_id][moneda] += movimiento['monto']
            rep_origen[venta_id][moneda].append({
                'uuid_rep': doc.uuid or '',
                'fecha_fuente': movimiento['fecha_fuente'],
            })

    cobros = defaultdict(float)
    desglose = defaultdict(list)
    ventas = cliente.ventas_set.all()
    if incluir_detalle:
        ventas = ventas.prefetch_related('documentos_cfdi')
    for venta in ventas:
        pagos = list(_en_rango(
            venta.pagos.all(), 'fecha_pago', fecha_inicio, fecha_fin
        ))
        pagos = [p for p in pagos if p.pk not in pagos_rep_exactos]
        if pagos:
            pagos_por_moneda = defaultdict(list)
            for pago in pagos:
                pagos_por_moneda[str(pago.monto_pago.currency)].append(pago)
            for moneda, pagos_moneda in pagos_por_moneda.items():
                total_pagos = sum(
                    (p.monto_pago.amount for p in pagos_moneda), Decimal('0')
                )
                rep_aplicado = rep_por_venta_moneda[venta.id].get(
                    moneda, Decimal('0')
                )
                sin_rep = total_pagos - rep_aplicado
                if sin_rep <= 0:
                    continue
                sin_rep_float = float(sin_rep)
                cobros[moneda] += sin_rep_float
                if incluir_detalle:
                    origenes = rep_origen[venta.id].get(moneda, [])
                    desglose[moneda].append({
                        'tipo': 'pago_sin_rep',
                        'venta_id': venta.pk,
                        'referencia': venta.referencia,
                        'fechas': sorted({
                            p.fecha_pago for p in pagos_moneda if p.fecha_pago
                        }),
                        'monto': round(sin_rep_float, 2),
                        'moneda': moneda,
                        'monto_operativo': round(float(total_pagos), 2),
                        'rep_aplicado': round(float(rep_aplicado), 2),
                        'diferencia_operativo_fiscal': round(
                            float(total_pagos - rep_aplicado), 2
                        ),
                        'estado_vinculo': (
                            'revision_requerida'
                            if rep_aplicado > 0 else 'sin_rep_encontrado'
                        ),
                        'requiere_revision': rep_aplicado > 0,
                        'fuente_fecha_rep': (
                            'FechaPago'
                            if any(o['fecha_fuente'] == 'FechaPago' for o in origenes)
                            else 'fecha_emision'
                        ) if origenes else '',
                        'uuids_rep': sorted({
                            o['uuid_rep'] for o in origenes if o['uuid_rep']
                        }),
                        'documentos_cfdi': _documentos_cfdi_de_venta(venta),
                    })
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
        if incluir_detalle:
            desglose[moneda].append({
                'tipo': 'venta_contado',
                'venta_id': venta.pk,
                'referencia': venta.referencia,
                'fechas': [venta.fecha_deposito] if venta.fecha_deposito else [],
                'monto': round(pagado, 2),
                'moneda': moneda,
                'monto_operativo': round(pagado, 2),
                'rep_aplicado': 0.0,
                'diferencia_operativo_fiscal': pagado,
                'estado_vinculo': 'sin_rep_encontrado',
                'requiere_revision': False,
                'fuente_fecha_rep': '',
                'uuids_rep': [],
                'documentos_cfdi': _documentos_cfdi_de_venta(venta),
            })
    return dict(cobros), dict(desglose)


def _documentos_cfdi_de_venta(venta):
    """Metadatos mínimos para enlazar cada cobro con sus CFDI relacionados."""
    return [
        {
            'id': doc.pk,
            'folio': doc.folio or '',
            'uuid': doc.uuid or '',
            'subtipo': doc.get_subtipo_display(),
            'estado': doc.estado,
            'fecha_emision': doc.fecha_emision,
        }
        for doc in venta.documentos_cfdi.all()
    ]


def _documentos_en_periodo(cliente, fecha_inicio=None, fecha_fin=None):
    documentos = list(_en_rango(
        cliente.documentos_cfdi.filter(estado='VIGENTE')
        .exclude(subtipo='recibo_pago'),
        'fecha_emision', fecha_inicio, fecha_fin,
    ))
    recibos = cliente.documentos_cfdi.filter(
        estado='VIGENTE', subtipo='recibo_pago',
    ).select_related('pago_venta')
    documentos.extend(
        doc for doc in recibos
        if _rep_documento_en_rango(doc, fecha_inicio, fecha_fin)
    )
    return documentos


def _rep_aplicado_detalle(documentos, fecha_inicio=None, fecha_fin=None):
    """Crea filas de auditoría REP con aplicación fiscal y origen de fecha."""
    filas = []
    for documento in documentos:
        motivo_vinculo = _estado_vinculo_rep(documento)
        vinculo_exacto = motivo_vinculo == 'uuid_coincidente'
        usados_operativo = set()

        for movimiento in _movimientos_rep(documento, fecha_inicio, fecha_fin):
            factura = _documento_factura_del_movimiento_rep(movimiento)
            venta_id = (
                factura.venta_id if factura
                else (
                    documento.venta_id
                    if not movimiento.get('uuid_factura') else None
                )
            )
            monto_operativo = None
            moneda_operativa = ''
            if vinculo_exacto:
                pago = documento.pago_venta
                clave = (venta_id, movimiento['moneda'])
                if clave not in usados_operativo:
                    moneda_operativa = str(pago.monto_pago.currency)
                    monto_operativo = float(pago.monto_pago.amount)
                    usados_operativo.add(clave)
            elif venta_id:
                from ..models import Ventas

                pagos = _en_rango(
                    Ventas.objects.get(pk=venta_id).pagos.all(),
                    'fecha_pago', fecha_inicio, fecha_fin,
                )
                clave = (venta_id, movimiento['moneda'])
                if clave not in usados_operativo:
                    total_operativo = sum(
                        (p.monto_pago.amount for p in pagos
                         if str(p.monto_pago.currency) == movimiento['moneda']),
                        Decimal('0'),
                    )
                    if total_operativo:
                        monto_operativo = float(total_operativo)
                        moneda_operativa = movimiento['moneda']
                    usados_operativo.add(clave)

            diferencia = None
            if monto_operativo is not None and moneda_operativa == movimiento['moneda']:
                diferencia = round(monto_operativo - float(movimiento['monto']), 2)

            filas.append({
                'documento_id': documento.pk,
                'uuid_rep': documento.uuid or '',
                'folio_rep': (
                    documento.folio
                    or (
                        documento.pago_venta.folio_rep
                        if documento.pago_venta_id else ''
                    )
                    or ''
                ),
                'uuid_factura': movimiento['uuid_factura'],
                'documento_factura_id': factura.pk if factura else None,
                'venta_id': venta_id,
                'fecha_pago': movimiento['fecha_pago'],
                'fecha_fuente': movimiento['fecha_fuente'],
                'es_legacy': movimiento['legacy'],
                'monto_rep_aplicado': round(float(movimiento['monto']), 2),
                'moneda': movimiento['moneda'],
                'imp_saldo_insoluto': (
                    round(float(movimiento['saldo_insoluto']), 2)
                    if movimiento['saldo_insoluto'] is not None else None
                ),
                'monto_operativo': (
                    round(monto_operativo, 2)
                    if monto_operativo is not None else None
                ),
                'moneda_operativa': moneda_operativa,
                'diferencia_operativo_fiscal': diferencia,
                'estado_vinculo': (
                    'uuid_coincidente' if vinculo_exacto
                    else 'revision_requerida'
                ),
                'motivo_vinculo': motivo_vinculo,
                'requiere_revision': not vinculo_exacto,
            })
    return filas


def _agrupar_rep_por_moneda(rep_desglose):
    por_moneda = defaultdict(list)
    for movimiento in rep_desglose:
        por_moneda[movimiento['moneda']].append(movimiento)
    return dict(por_moneda)


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


def _calcular(
    cliente, fecha_inicio=None, fecha_fin=None, incluir_cobros_detalle=False
):
    """Calcula el desglose y el saldo conciliado de un cliente.

    Fuente única de la fórmula de saldo. Retorna documentos, desglose por
    concepto/moneda, saldo, cobros operativos y desglose REP. La usan
    ``conciliacion_cliente`` y ``saldo_por_moneda`` para no duplicar la regla.

    ``fecha_inicio``/``fecha_fin`` (date) limitan documentos/anticipos por su
    fecha propia y movimientos REP por ``FechaPago``.
    """
    docs = _documentos_en_periodo(cliente, fecha_inicio, fecha_fin)
    documentos_rep = [doc for doc in docs if doc.subtipo == 'recibo_pago']
    rep_por_moneda = pagos_rep_por_moneda(
        documentos_rep, fecha_inicio, fecha_fin
    )
    rep_desglose = _rep_aplicado_detalle(
        documentos_rep, fecha_inicio, fecha_fin
    )

    detalle = {
        'facturado': _sum_por_moneda(docs, INGRESOS_VENTA),
        'notas_cargo': _sum_por_moneda(docs, ['nota_cargo']),
        'notas_credito': _sum_por_moneda(docs, ['nota_credito']),
        'recibos_pago': {
            moneda: float(monto) for moneda, monto in rep_por_moneda.items()
        },
        'remanentes_anticipo': _sum_por_moneda(docs, ['remanente_anticipo']),
    }

    # Cobros de contado / sin REP: descuentan el pago ya recibido que no tiene
    # un recibo electrónico de pago asociado (típicamente facturas PUE).
    if incluir_cobros_detalle:
        detalle['cobros_contado'], cobros_contado_desglose = (
            _cobros_no_rep_con_detalle(cliente, fecha_inicio, fecha_fin)
        )
    else:
        detalle['cobros_contado'] = cobros_no_rep(
            cliente, fecha_inicio, fecha_fin
        )
        cobros_contado_desglose = {}

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

    return docs, detalle, saldo, cobros_contado_desglose, rep_desglose


def saldo_por_moneda(cliente, fecha_inicio=None, fecha_fin=None):
    """Saldo conciliado del cliente desglosado por moneda.

    Fuente única de la fórmula de saldo: la consumen
    ``Cliente.saldo_conciliado()`` y la vista de conciliación, de modo que no
    existan dos implementaciones que puedan desincronizarse.
    """
    _docs, _detalle, saldo, _cobros_contado_desglose, _rep_desglose = _calcular(
        cliente, fecha_inicio, fecha_fin
    )
    return saldo


def conciliacion_cliente(cliente, fecha_inicio=None, fecha_fin=None):
    """Calcula la conciliación fiscal completa de un cliente.

    ``fecha_inicio``/``fecha_fin`` (date) limitan los documentos (por
    ``fecha_emision``), pagos (``fecha_pago``) y anticipos (``fecha``) al
    periodo. Sin fechas, se considera todo el histórico.
    """
    docs, detalle, saldo, cobros_contado_desglose, rep_desglose = _calcular(
        cliente, fecha_inicio, fecha_fin, incluir_cobros_detalle=True
    )

    # Documentos que no pudieron vincularse a una venta (posible deriva):
    # son notas de cargo/crédito o recibos de pago cuyo CFDI padre no fue
    # encontrado por UUID (p. ej. la factura aún no se importa o no coincide).
    # Se materializan los propios documentos para poder desglosarlos y enlazar
    # cada uno a su ficha en el admin.
    sin_venta_docs = [
        doc for doc in docs
        if doc.venta_id is None
        and doc.subtipo not in INGRESOS_VENTA + ['remanente_anticipo']
    ]
    sin_venta_docs.sort(key=lambda doc: (
        doc.subtipo,
        -(doc.fecha_emision.toordinal() if doc.fecha_emision else 0),
    ))

    por_subtipo = defaultdict(list)
    for doc in sin_venta_docs:
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
        'cobros_contado_desglose': cobros_contado_desglose,
        'rep_desglose': rep_desglose,
        'rep_desglose_por_moneda': _agrupar_rep_por_moneda(rep_desglose),
        'saldo_por_moneda': saldo,
        'pagos_mxn': pagos_total_mxn(cliente, fecha_inicio, fecha_fin),
        'total_documentos': len(docs),
        'documentos_sin_venta': sum(item['total'] for item in sin_venta_detalle),
        'sin_venta_detalle': sin_venta_detalle,
    }


def _serializar_fila(fila):
    """Convierte una fila de conciliación a tipos JSON-serializables.

    El backend de cache de producción usa serializador JSON, que no admite
    instancias de modelo ni ``Decimal`` anidados: se reemplaza el cliente por
    su id (no se usa al rehidratar) y se normalizan fechas y montos.
    """
    fila = dict(fila)
    fila['cliente'] = fila['cliente'].pk
    fila['sin_venta_detalle'] = [
        {
            **grupo,
            'documentos': [
                {
                    **doc,
                    'monto': float(doc['monto']),
                    'fecha': doc['fecha'].isoformat() if doc['fecha'] else None,
                }
                for doc in grupo['documentos']
            ],
        }
        for grupo in fila['sin_venta_detalle']
    ]
    fila['cobros_contado_desglose'] = {
        moneda: [
            {
                **item,
                'fechas': [fecha.isoformat() for fecha in item['fechas']],
                'documentos_cfdi': [
                    {
                        **doc,
                        'fecha_emision': (
                            doc['fecha_emision'].isoformat()
                            if doc['fecha_emision'] else None
                        ),
                    }
                    for doc in item['documentos_cfdi']
                ],
            }
            for item in items
        ]
        for moneda, items in fila['cobros_contado_desglose'].items()
    }
    fila['rep_desglose'] = [
        {
            **item,
            'fecha_pago': (
                item['fecha_pago'].isoformat() if item['fecha_pago'] else None
            ),
        }
        for item in fila.get('rep_desglose', [])
    ]
    fila['rep_desglose_por_moneda'] = _agrupar_rep_por_moneda(
        fila['rep_desglose']
    )
    return fila


def _rehidratar_fila(fila, cliente):
    """Reconstruye una fila cacheada con su cliente y los tipos originales."""
    fila = dict(fila)
    fila['cliente'] = cliente
    fila['sin_venta_detalle'] = [
        {
            **grupo,
            'documentos': [
                {
                    **doc,
                    'monto': float(doc['monto']) if doc.get('monto') is not None else 0.0,
                    'fecha': date.fromisoformat(doc['fecha']) if doc.get('fecha') else None,
                }
                for doc in grupo['documentos']
            ],
        }
        for grupo in fila['sin_venta_detalle']
    ]
    fila['cobros_contado_desglose'] = {
        moneda: [
            {
                **item,
                'fechas': [date.fromisoformat(fecha) for fecha in item['fechas']],
                'documentos_cfdi': [
                    {
                        **doc,
                        'fecha_emision': (
                            date.fromisoformat(doc['fecha_emision'])
                            if doc.get('fecha_emision') else None
                        ),
                    }
                    for doc in item['documentos_cfdi']
                ],
            }
            for item in items
        ]
        for moneda, items in fila.get('cobros_contado_desglose', {}).items()
    }
    fila['rep_desglose'] = [
        {
            **item,
            'fecha_pago': (
                date.fromisoformat(item['fecha_pago'])
                if item.get('fecha_pago') else None
            ),
        }
        for item in fila.get('rep_desglose', [])
    ]
    fila['rep_desglose_por_moneda'] = _agrupar_rep_por_moneda(
        fila['rep_desglose']
    )
    return fila


def conciliacion_global(fecha_inicio=None, fecha_fin=None, cliente_id=None):
    """Conciliación de los clientes activos (opcionalmente por periodo).

    ``cliente_id`` limita el resultado a un cliente. El resultado se cachea por
    rango de fechas y cliente (``ConciliacionCache``) para evitar recalcular la
    conciliación de cada cliente en cada carga. Al leer del cache se rehidrata
    cada fila con su cliente actual.
    """
    from ..models import Cliente
    from .cache_service import ConciliacionCache

    qs = Cliente.objects.filter(activo=True)
    if cliente_id:
        qs = qs.filter(pk=cliente_id)
    clientes = list(qs.order_by('nombre'))

    cacheadas = ConciliacionCache.get(fecha_inicio, fecha_fin, cliente_id)
    if cacheadas is not None and len(cacheadas) == len(clientes):
        return [
            _rehidratar_fila(fila, cliente)
            for fila, cliente in zip(cacheadas, clientes)
        ]

    filas = [
        conciliacion_cliente(c, fecha_inicio, fecha_fin)
        for c in clientes
    ]
    ConciliacionCache.set(
        fecha_inicio, fecha_fin, cliente_id,
        [_serializar_fila(f) for f in filas],
    )
    return filas


def monedas_disponibles_conciliacion(filas):
    """Monedas que aparecen en los importes de las filas mostradas."""
    monedas = set()
    for fila in filas:
        monedas.update(fila.get('saldo_por_moneda', {}).keys())
        for importes in fila.get('detalle', {}).values():
            if isinstance(importes, dict):
                monedas.update(importes.keys())
    return sorted(monedas)


def _estado_saldo_conciliacion(saldo_por_moneda, moneda=None):
    """Clasifica saldos por moneda sin sumar divisas distintas entre sí."""
    if moneda:
        valores = [saldo_por_moneda.get(moneda, 0.0)]
    else:
        valores = list(saldo_por_moneda.values())

    tiene_deuda = any(valor > 0 for valor in valores)
    tiene_favor = any(valor < 0 for valor in valores)
    if tiene_deuda and tiene_favor:
        return 'mixto'
    if tiene_deuda:
        return 'deuda'
    if tiene_favor:
        return 'favor'
    return 'cero'


def _tiene_cobros_sin_cfdi(fila):
    return any(
        not item.get('documentos_cfdi')
        for items in fila.get('cobros_contado_desglose', {}).values()
        for item in items
    )


def filtrar_filas_conciliacion(
    filas, *, moneda=None, estado_saldo=None, incidencia=None
):
    """Filtra clientes sin modificar importes ni saldos conciliados.

    ``moneda`` selecciona clientes con actividad en esa moneda. El estado se
    calcula en esa moneda si está seleccionada; de otro modo identifica deuda,
    saldo a favor, saldo mixto o cero entre las monedas del cliente.
    """
    resultado = []
    for fila in filas:
        monedas_fila = set(fila.get('saldo_por_moneda', {}).keys())
        for importes in fila.get('detalle', {}).values():
            if isinstance(importes, dict):
                monedas_fila.update(importes.keys())
        if moneda and moneda not in monedas_fila:
            continue

        if estado_saldo and _estado_saldo_conciliacion(
            fila.get('saldo_por_moneda', {}), moneda
        ) != estado_saldo:
            continue

        tiene_cfdi_sin_venta = fila.get('documentos_sin_venta', 0) > 0
        tiene_cobro_sin_cfdi = _tiene_cobros_sin_cfdi(fila)
        if incidencia == 'cfdi_sin_venta' and not tiene_cfdi_sin_venta:
            continue
        if incidencia == 'cobro_sin_cfdi' and not tiene_cobro_sin_cfdi:
            continue
        if incidencia == 'any' and not (tiene_cfdi_sin_venta or tiene_cobro_sin_cfdi):
            continue

        resultado.append(fila)
    return resultado
