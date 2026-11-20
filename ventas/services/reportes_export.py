"""Reportes descargables (Excel y PDF) de Análisis de ventas y Conciliación.

Cada reporte se arma en dos pasos:

1. ``datos_*``: calcula los indicadores a partir de los mismos filtros que la
   pantalla (sin formato, fácil de probar).
2. ``*_xlsx`` / ``*_pdf``: vuelca esos datos a un archivo.

Los importes nunca se suman entre monedas distintas: todo se agrupa por
moneda, igual que en la conciliación.
"""
from collections import defaultdict
from datetime import date
from io import BytesIO

from django.utils import timezone

from ..models import DocumentoCFDI, Ventas

MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
         'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

BUCKETS = [
    ('por_vencer', 'Por vencer'),
    ('d1_30', '1-30 días'),
    ('d31_60', '31-60 días'),
    ('d61_90', '61-90 días'),
    ('d90_mas', 'Más de 90 días'),
]

SUBTIPOS_FACTURA = {
    DocumentoCFDI.SubtipoDocumento.VENTA_NACIONAL,
    DocumentoCFDI.SubtipoDocumento.VENTA_EXPORTACION,
    DocumentoCFDI.SubtipoDocumento.INGRESO_SERVICIO,
    DocumentoCFDI.SubtipoDocumento.INGRESO_MIXTO,
}

EPS = 0.005


def _bucket(dias):
    if dias <= 0:
        return 'por_vencer'
    if dias <= 30:
        return 'd1_30'
    if dias <= 60:
        return 'd31_60'
    if dias <= 90:
        return 'd61_90'
    return 'd90_mas'


def _mes_label(clave):
    year, month = clave.split('-')
    return f'{MESES[int(month) - 1]} {year}'


def _pct(parte, total):
    return (parte / total) if total else 0.0


# =============================================================================
# Datos: Análisis de ventas
# =============================================================================

def datos_reporte_ventas(ventas_qs, cfdi_qs=None, hoy=None):
    """Indicadores del reporte de ventas para un queryset ya filtrado."""
    hoy = hoy or date.today()
    ventas = list(
        ventas_qs.select_related(
            'cliente', 'producto', 'sucursal_id', 'cuenta__id_banco', 'mercado_destino',
        ).prefetch_related('documentos_cfdi', 'pagos').order_by('fecha_deposito', 'pk')
    )

    def nuevo_kpi():
        return {
            'ventas': 0.0, 'cobrado': 0.0, 'saldo': 0.0, 'vencido': 0.0,
            'vencido_90': 0.0, 'n': 0, 'contado': 0.0, 'credito': 0.0,
            'n_credito': 0, 'sin_cfdi_monto': 0.0, 'sin_cfdi_n': 0,
            'dias_cobro_pond': 0.0, 'dias_cobro_base': 0.0,
        }

    kpis = defaultdict(nuevo_kpi)
    mensual = defaultdict(lambda: {'ventas': 0.0, 'cobrado': 0.0, 'saldo': 0.0, 'n': 0})
    clientes = defaultdict(lambda: {
        'ventas': 0.0, 'cobrado': 0.0, 'saldo': 0.0, 'vencido': 0.0, 'n': 0,
        'max_dias': 0, 'sin_cfdi': 0,
    })
    aging = defaultdict(lambda: {key: 0.0 for key, _ in BUCKETS})
    productos = defaultdict(lambda: {'cantidad': 0.0, 'ventas': 0.0, 'n': 0})
    sucursales = defaultdict(lambda: {'ventas': 0.0, 'cobrado': 0.0, 'saldo': 0.0, 'n': 0})
    detalle = []
    sin_cfdi = []

    for v in ventas:
        moneda = str(v.monto.currency)
        monto = float(v.monto.amount)
        pagado = float(v.monto_pagado.amount)
        saldo = v.saldo_por_cobrar()
        docs = [d for d in v.documentos_cfdi.all()
                if d.estado == DocumentoCFDI.EstadoDocumento.VIGENTE]
        facturas = [d for d in docs if d.subtipo in SUBTIPOS_FACTURA and d.uuid]
        es_credito = v.modalidad_pago == Ventas.ModalidadPago.CREDITO
        dias = (hoy - v.fecha_vencimiento).days if v.fecha_vencimiento else 0
        pendiente = saldo > EPS
        vencido = pendiente and dias > 0

        k = kpis[moneda]
        k['ventas'] += monto
        k['cobrado'] += pagado
        k['n'] += 1
        if es_credito:
            k['credito'] += monto
            k['n_credito'] += 1
            for pago in v.pagos.all():
                if str(pago.monto_pago.currency) != moneda:
                    continue
                importe = float(pago.monto_pago.amount)
                k['dias_cobro_pond'] += importe * max((pago.fecha_pago - v.fecha_deposito).days, 0)
                k['dias_cobro_base'] += importe
        else:
            k['contado'] += monto
        if pendiente:
            k['saldo'] += saldo
        if vencido:
            k['vencido'] += saldo
            if dias > 90:
                k['vencido_90'] += saldo
        if not facturas:
            k['sin_cfdi_monto'] += monto
            k['sin_cfdi_n'] += 1

        mes = mensual[(moneda, v.fecha_deposito.strftime('%Y-%m'))]
        mes['ventas'] += monto
        mes['cobrado'] += pagado
        mes['saldo'] += saldo if pendiente else 0.0
        mes['n'] += 1

        cliente = v.cliente.nombre
        c = clientes[(moneda, cliente)]
        c['ventas'] += monto
        c['cobrado'] += pagado
        c['n'] += 1
        if pendiente:
            c['saldo'] += saldo
            aging[(moneda, cliente)][_bucket(dias)] += saldo
        if vencido:
            c['vencido'] += saldo
            c['max_dias'] = max(c['max_dias'], dias)
        if not facturas:
            c['sin_cfdi'] += 1

        concepto = v.producto.nombre if v.producto_id else (v.descripcion or 'Servicio')
        p = productos[(moneda, concepto)]
        p['cantidad'] += float(v.cantidad or 0)
        p['ventas'] += monto
        p['n'] += 1

        s = sucursales[(moneda, v.sucursal_id.nombre if v.sucursal_id_id else 'Sin sucursal')]
        s['ventas'] += monto
        s['cobrado'] += pagado
        s['saldo'] += saldo if pendiente else 0.0
        s['n'] += 1

        fila = {
            'id': v.pk,
            'referencia': v.referencia,
            'fecha': v.fecha_deposito,
            'cliente': cliente,
            'concepto': concepto,
            'sucursal': v.sucursal_id.nombre if v.sucursal_id_id else '',
            'modalidad': v.get_modalidad_pago_display(),
            'estado': v.get_estado_cobranza_display(),
            'moneda': moneda,
            'monto': monto,
            'pagado': pagado,
            'saldo': saldo if pendiente else 0.0,
            'vencimiento': v.fecha_vencimiento,
            'dias_vencido': dias if vencido else 0,
            'facturas': ', '.join(d.folio or (d.uuid or '')[:8] for d in facturas),
        }
        detalle.append(fila)
        if not facturas:
            sin_cfdi.append(fila)

    # KPIs derivados
    for k in kpis.values():
        k['cobranza_pct'] = _pct(k['cobrado'], k['ventas'])
        k['ticket'] = k['ventas'] / k['n'] if k['n'] else 0.0
        k['vencido_pct'] = _pct(k['vencido'], k['saldo'])
        k['dias_cobro'] = (
            k['dias_cobro_pond'] / k['dias_cobro_base'] if k['dias_cobro_base'] else None
        )

    # CFDI del mismo periodo
    cfdi = defaultdict(lambda: {'facturado': 0.0, 'notas_credito': 0.0, 'rep': 0.0, 'n': 0})
    if cfdi_qs is not None:
        for doc in cfdi_qs:
            moneda = doc.moneda or str(doc.monto.currency)
            importe = float(doc.monto.amount)
            item = cfdi[moneda]
            item['n'] += 1
            if doc.tipo == DocumentoCFDI.TipoDocumento.INGRESO:
                item['facturado'] += importe
            elif doc.subtipo in (
                DocumentoCFDI.SubtipoDocumento.NOTA_CREDITO,
                DocumentoCFDI.SubtipoDocumento.DESCUENTO,
            ):
                item['notas_credito'] += importe
            elif doc.tipo == DocumentoCFDI.TipoDocumento.PAGO:
                item['rep'] += importe

    # Tendencia mensual con variación contra el mes anterior de la misma moneda
    tendencia = []
    previo = {}
    for (moneda, clave) in sorted(mensual, key=lambda x: (x[0], x[1])):
        m = mensual[(moneda, clave)]
        anterior = previo.get(moneda)
        tendencia.append({
            'moneda': moneda, 'mes': clave, 'mes_label': _mes_label(clave),
            **m,
            'cobranza_pct': _pct(m['cobrado'], m['ventas']),
            'variacion': ((m['ventas'] - anterior) / anterior) if anterior else None,
        })
        previo[moneda] = m['ventas']

    # Concentración de clientes (Pareto / ABC) por moneda
    ranking = []
    for moneda in sorted({mon for mon, _ in clientes}):
        filas = sorted(
            ((nombre, datos) for (mon, nombre), datos in clientes.items() if mon == moneda),
            key=lambda x: -x[1]['ventas'],
        )
        total = sum(d['ventas'] for _, d in filas)
        acumulado = 0.0
        for nombre, d in filas:
            participacion = _pct(d['ventas'], total)
            clase = 'A' if acumulado < 0.80 else ('B' if acumulado < 0.95 else 'C')
            acumulado += participacion
            ranking.append({
                'moneda': moneda, 'cliente': nombre, **d,
                'participacion': participacion, 'acumulado': acumulado,
                'clase': clase,
                'cobranza_pct': _pct(d['cobrado'], d['ventas']),
            })

    antiguedad = []
    for (moneda, nombre), buckets in sorted(aging.items(), key=lambda x: (x[0][0], -sum(x[1].values()))):
        total = sum(buckets.values())
        if total <= EPS:
            continue
        antiguedad.append({'moneda': moneda, 'cliente': nombre, **buckets, 'total': total})

    productos_rows = sorted(
        ({'moneda': mon, 'concepto': nombre, **d,
          'precio_promedio': d['ventas'] / d['cantidad'] if d['cantidad'] else 0.0}
         for (mon, nombre), d in productos.items()),
        key=lambda r: (r['moneda'], -r['ventas']),
    )
    sucursales_rows = sorted(
        ({'moneda': mon, 'sucursal': nombre, **d,
          'cobranza_pct': _pct(d['cobrado'], d['ventas'])}
         for (mon, nombre), d in sucursales.items()),
        key=lambda r: (r['moneda'], -r['ventas']),
    )

    datos = {
        'hoy': hoy,
        'kpis': dict(sorted(kpis.items())),
        'cfdi': dict(sorted(cfdi.items())),
        'tendencia': tendencia,
        'ranking': ranking,
        'antiguedad': antiguedad,
        'productos': productos_rows,
        'sucursales': sucursales_rows,
        'sin_cfdi': sorted(sin_cfdi, key=lambda r: (r['moneda'], -r['monto'])),
        'detalle': detalle,
    }
    datos['hallazgos'] = _hallazgos_ventas(datos)
    return datos


def _fmt(valor, moneda=''):
    texto = f'${valor:,.2f}'
    return f'{texto} {moneda}'.strip()


def _hallazgos_ventas(datos):
    """Frases cortas con lo más relevante del periodo para la dirección."""
    hallazgos = []
    for moneda, k in datos['kpis'].items():
        if not k['ventas']:
            continue
        hallazgos.append(
            f'{moneda}: se vendieron {_fmt(k["ventas"], moneda)} en {k["n"]} operaciones '
            f'y se ha cobrado el {k["cobranza_pct"]:.1%}.'
        )
        if k['saldo'] > EPS:
            hallazgos.append(
                f'{moneda}: quedan {_fmt(k["saldo"], moneda)} por cobrar; '
                f'{_fmt(k["vencido"], moneda)} ({k["vencido_pct"]:.1%}) ya está vencido'
                + (f' y {_fmt(k["vencido_90"], moneda)} tiene más de 90 días.' if k['vencido_90'] > EPS else '.')
            )
        if k['dias_cobro'] is not None:
            hallazgos.append(
                f'{moneda}: las ventas a crédito se cobran en promedio a {k["dias_cobro"]:.0f} días '
                'desde la fecha de venta (ponderado por importe).'
            )
        if k['sin_cfdi_n']:
            hallazgos.append(
                f'{moneda}: {_n(k["sin_cfdi_n"], "venta", "ventas")} por {_fmt(k["sin_cfdi_monto"], moneda)} '
                'no tienen factura CFDI vinculada (riesgo fiscal y de cobranza).'
            )
        clase_a = [r for r in datos['ranking'] if r['moneda'] == moneda and r['clase'] == 'A']
        total_clientes = sum(1 for r in datos['ranking'] if r['moneda'] == moneda)
        if clase_a and total_clientes > 1:
            top = clase_a[0]
            hallazgos.append(
                f'{moneda}: {len(clase_a)} de {total_clientes} clientes concentran el 80% de la venta; '
                f'el principal es {top["cliente"]} con {top["participacion"]:.1%}.'
            )
        meses = [t for t in datos['tendencia'] if t['moneda'] == moneda]
        if len(meses) > 1:
            mejor = max(meses, key=lambda t: t['ventas'])
            hallazgos.append(
                f'{moneda}: el mes con mayor venta fue {mejor["mes_label"]} '
                f'({_fmt(mejor["ventas"], moneda)}).'
            )
        facturado = datos['cfdi'].get(moneda, {}).get('facturado', 0.0)
        if facturado and abs(k['ventas'] - facturado) > 1:
            hallazgos.append(
                f'{moneda}: lo vendido difiere de lo facturado en CFDI del periodo por '
                f'{_fmt(k["ventas"] - facturado, moneda)} (vendido {_fmt(k["ventas"])}, '
                f'facturado {_fmt(facturado)}).'
            )
    if not hallazgos:
        hallazgos.append('No hay ventas para los filtros seleccionados.')
    return hallazgos


# =============================================================================
# Datos: Conciliación
# =============================================================================

def _estado_saldo(valor):
    if valor > EPS:
        return 'Por cobrar'
    if valor < -EPS:
        return 'Saldo a favor'
    return 'Sin saldo'


def datos_reporte_conciliacion(filas):
    """Aplana las filas de la conciliación para exportarlas."""
    columnas = ['facturado', 'notas_cargo', 'notas_credito', 'recibos_pago',
                'cobros_contado', 'anticipos_disponibles']
    resumen = []
    totales = defaultdict(lambda: {**{c: 0.0 for c in columnas},
                                   'saldo': 0.0, 'por_cobrar': 0.0, 'a_favor': 0.0,
                                   'clientes_deuda': 0})
    incidencias = []
    reps = []
    cobros = []

    for fila in filas:
        nombre = fila['cliente'].nombre
        detalle = fila.get('detalle', {})
        saldos = fila.get('saldo_por_moneda', {})
        monedas = set(saldos)
        for c in columnas:
            monedas.update((detalle.get(c) or {}).keys())

        sin_venta_por_moneda = defaultdict(int)
        for grupo in fila.get('sin_venta_detalle', []):
            for doc in grupo['documentos']:
                sin_venta_por_moneda[doc.get('moneda') or 'MXN'] += 1
                sin_uuid = not doc.get('uuid')
                incidencias.append({
                    'tipo': f'{grupo["label"]} sin venta',
                    'cliente': nombre,
                    'documento': doc.get('folio') or doc.get('uuid') or f'#{doc["id"]}',
                    'fecha': doc.get('fecha'),
                    'monto': float(doc.get('monto') or 0),
                    'moneda': doc.get('moneda') or 'MXN',
                    'accion': (
                        'Capturado sin UUID: sustituir por el XML real y ligarlo a su venta.'
                        if sin_uuid else
                        'Importar la factura relacionada o ligar el documento a su venta.'
                    ),
                })

        cobros_sin_cfdi_por_moneda = defaultdict(int)
        for moneda, items in fila.get('cobros_contado_desglose', {}).items():
            for item in items:
                docs = item.get('documentos_cfdi') or []
                cobros.append({
                    'cliente': nombre,
                    'origen': 'Venta de contado' if item.get('tipo') == 'venta_contado' else 'Pago sin REP',
                    'referencia': item.get('referencia', ''),
                    'venta_id': item.get('venta_id'),
                    'fechas': ', '.join(f.strftime('%d/%m/%Y') for f in item.get('fechas', []) if f),
                    'monto': float(item.get('monto') or 0),
                    'moneda': item.get('moneda') or moneda,
                    'cfdi': ', '.join(d.get('folio') or (d.get('uuid') or '')[:8] for d in docs),
                })
                if not docs:
                    cobros_sin_cfdi_por_moneda[moneda] += 1
                    incidencias.append({
                        'tipo': 'Cobro sin CFDI',
                        'cliente': nombre,
                        'documento': f'{item.get("referencia", "")} (venta #{item.get("venta_id")})',
                        'fecha': (item.get('fechas') or [None])[0],
                        'monto': float(item.get('monto') or 0),
                        'moneda': item.get('moneda') or moneda,
                        'accion': 'Emitir o importar la factura de la venta.',
                    })

        for rep in fila.get('rep_desglose', []):
            reps.append({'cliente': nombre, **rep})
            if rep.get('estado_vinculo') != 'uuid_coincidente':
                incidencias.append({
                    'tipo': 'REP por revisar',
                    'cliente': nombre,
                    'documento': rep.get('folio_rep') or rep.get('uuid_rep') or '',
                    'fecha': rep.get('fecha_pago'),
                    'monto': float(rep.get('monto_rep_aplicado') or 0),
                    'moneda': rep.get('moneda') or 'MXN',
                    'accion': 'Revisar el UUID de la factura que paga el REP.',
                })

        for moneda in sorted(monedas):
            saldo = float(saldos.get(moneda, 0.0))
            row = {
                'cliente': nombre,
                'moneda': moneda,
                **{c: float((detalle.get(c) or {}).get(moneda, 0.0)) for c in columnas},
                'saldo': saldo,
                'estado': _estado_saldo(saldo),
                'sin_vincular': sin_venta_por_moneda.get(moneda, 0),
                'cobros_sin_cfdi': cobros_sin_cfdi_por_moneda.get(moneda, 0),
            }
            resumen.append(row)
            t = totales[moneda]
            for c in columnas:
                t[c] += row[c]
            t['saldo'] += saldo
            if saldo > EPS:
                t['por_cobrar'] += saldo
                t['clientes_deuda'] += 1
            elif saldo < -EPS:
                t['a_favor'] += saldo
                incidencias.append({
                    'tipo': 'Saldo a favor del cliente',
                    'cliente': nombre,
                    'documento': '',
                    'fecha': None,
                    'monto': saldo,
                    'moneda': moneda,
                    'accion': 'Aplicar a ventas pendientes, documentar anticipo o reembolsar.',
                })

    # Concentración de la cartera por cobrar
    concentracion = []
    for moneda, t in sorted(totales.items()):
        deudores = sorted(
            (r for r in resumen if r['moneda'] == moneda and r['saldo'] > EPS),
            key=lambda r: -r['saldo'],
        )
        acumulado = 0.0
        for r in deudores:
            participacion = _pct(r['saldo'], t['por_cobrar'])
            acumulado += participacion
            concentracion.append({
                'moneda': moneda, 'cliente': r['cliente'], 'saldo': r['saldo'],
                'participacion': participacion, 'acumulado': acumulado,
            })

    orden_tipo = {'Saldo a favor del cliente': 3, 'REP por revisar': 2, 'Cobro sin CFDI': 1}
    incidencias.sort(key=lambda i: (orden_tipo.get(i['tipo'], 0), i['cliente'], -abs(i['monto'])))

    datos = {
        'resumen': resumen,
        'totales': dict(sorted(totales.items())),
        'concentracion': concentracion,
        'incidencias': incidencias,
        'reps': reps,
        'cobros': cobros,
    }
    datos['hallazgos'] = _hallazgos_conciliacion(datos)
    return datos


def _n(cantidad, singular, plural):
    return f'{cantidad} {singular if cantidad == 1 else plural}'


def _hallazgos_conciliacion(datos):
    hallazgos = []
    for moneda, t in datos['totales'].items():
        hallazgos.append(
            f'{moneda}: cartera por cobrar {_fmt(t["por_cobrar"], moneda)} en '
            f'{_n(t["clientes_deuda"], "cliente", "clientes")}; '
            f'saldo a favor de clientes {_fmt(abs(t["a_favor"]), moneda)}.'
        )
        top = [c for c in datos['concentracion'] if c['moneda'] == moneda][:3]
        if len(top) > 1:
            hallazgos.append(
                f'{moneda}: los {len(top)} mayores deudores concentran el {top[-1]["acumulado"]:.1%} '
                'de la cartera (' + ', '.join(c['cliente'] for c in top) + ').'
            )
    conteo = defaultdict(int)
    for inc in datos['incidencias']:
        conteo[inc['tipo']] += 1
    if conteo:
        hallazgos.append(
            'Incidencias por resolver: '
            + '; '.join(f'{tipo}: {n}' for tipo, n in sorted(conteo.items())) + '.'
        )
    else:
        hallazgos.append('Sin incidencias de vinculación para los filtros seleccionados.')
    return hallazgos


# =============================================================================
# Excel
# =============================================================================

COLOR_PRIMARIO = '2F4550'
COLOR_ACENTO = 'C9A227'
FMT_MONEDA = '#,##0.00'
FMT_PCT = '0.0%'


class _Libro:
    """Ayudante mínimo sobre openpyxl con el estilo de la empresa."""

    def __init__(self):
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill

        self._openpyxl = openpyxl
        self.wb = openpyxl.Workbook()
        self.wb.remove(self.wb.active)
        self.font_header = Font(color='FFFFFF', bold=True)
        self.fill_header = PatternFill('solid', start_color=COLOR_PRIMARIO, end_color=COLOR_PRIMARIO)
        self.fill_total = PatternFill('solid', start_color='EEF2F4', end_color='EEF2F4')
        self.font_bold = Font(bold=True)
        self.font_titulo = Font(bold=True, size=14, color=COLOR_PRIMARIO)
        self.font_sub = Font(italic=True, color='666666')
        self.wrap = Alignment(wrap_text=True, vertical='top')
        self.center = Alignment(horizontal='center', vertical='center', wrap_text=True)

    def hoja(self, titulo, encabezados, filas, formatos=None, titulo_largo=None,
             subtitulo=None, totales=None):
        """Crea una hoja con tabla, filtros, encabezado fijo y anchos legibles.

        ``formatos``: {indice_columna: 'moneda'|'pct'|'fecha'|'entero'}.
        ``totales``: lista con valores para una fila de totales (None = vacío).
        """
        from openpyxl.utils import get_column_letter

        ws = self.wb.create_sheet(titulo[:31])
        formatos = formatos or {}
        fila_inicio = 1
        if titulo_largo:
            ws.cell(row=1, column=1, value=titulo_largo).font = self.font_titulo
            fila_inicio = 2
            if subtitulo:
                ws.cell(row=2, column=1, value=subtitulo).font = self.font_sub
                fila_inicio = 3
            fila_inicio += 1

        for col, texto in enumerate(encabezados, start=1):
            cell = ws.cell(row=fila_inicio, column=col, value=texto)
            cell.font = self.font_header
            cell.fill = self.fill_header
            cell.alignment = self.center
        ws.row_dimensions[fila_inicio].height = 30

        for r, fila in enumerate(filas, start=fila_inicio + 1):
            for col, valor in enumerate(fila, start=1):
                cell = ws.cell(row=r, column=col, value=valor)
                self._formato(cell, formatos.get(col - 1))

        ultima = fila_inicio + len(filas)
        if filas:
            ws.auto_filter.ref = (
                f'A{fila_inicio}:{get_column_letter(len(encabezados))}{ultima}'
            )
        if totales:
            r = ultima + 1
            for col, valor in enumerate(totales, start=1):
                cell = ws.cell(row=r, column=col, value=valor)
                cell.font = self.font_bold
                cell.fill = self.fill_total
                self._formato(cell, formatos.get(col - 1))
        ws.freeze_panes = ws.cell(row=fila_inicio + 1, column=1)

        for col in range(1, len(encabezados) + 1):
            letra = get_column_letter(col)
            largo = max(
                [len(str(encabezados[col - 1]))]
                + [len(self._texto(f[col - 1], formatos.get(col - 1))) for f in filas[:500]]
            )
            ws.column_dimensions[letra].width = min(max(largo + 2, 10), 60)
        return ws

    def _formato(self, cell, tipo):
        if tipo == 'moneda':
            cell.number_format = FMT_MONEDA
        elif tipo == 'pct':
            cell.number_format = FMT_PCT
        elif tipo == 'fecha':
            cell.number_format = 'DD/MM/YYYY'
        elif tipo == 'entero':
            cell.number_format = '#,##0'

    @staticmethod
    def _texto(valor, tipo):
        if valor is None:
            return ''
        if tipo == 'moneda' and isinstance(valor, (int, float)):
            return f'{valor:,.2f}'
        if tipo == 'fecha':
            return '00/00/0000'
        if tipo == 'pct':
            return '100.0%'
        return str(valor)

    def hoja_texto(self, titulo, titulo_largo, bloques):
        """Hoja de portada: título y bloques (subtítulo, [(clave, valor)] | [str])."""
        ws = self.wb.create_sheet(titulo[:31], 0)
        ws.cell(row=1, column=1, value=titulo_largo).font = self.font_titulo
        ws.cell(
            row=2, column=1,
            value=f'Generado: {timezone.localtime().strftime("%d/%m/%Y %H:%M")}',
        ).font = self.font_sub
        r = 4
        for subtitulo, contenido in bloques:
            cell = ws.cell(row=r, column=1, value=subtitulo)
            cell.font = self.font_header
            cell.fill = self.fill_header
            ws.cell(row=r, column=2).fill = self.fill_header
            r += 1
            for item in contenido:
                if isinstance(item, tuple):
                    clave, valor, *fmt = item
                    ws.cell(row=r, column=1, value=clave).font = self.font_bold
                    cell = ws.cell(row=r, column=2, value=valor)
                    self._formato(cell, fmt[0] if fmt else None)
                else:
                    cell = ws.cell(row=r, column=1, value=f'• {item}')
                    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
                    cell.alignment = self.wrap
                    ws.row_dimensions[r].height = 30
                r += 1
            r += 1
        ws.column_dimensions['A'].width = 42
        ws.column_dimensions['B'].width = 26
        for letra in 'CDEF':
            ws.column_dimensions[letra].width = 18
        return ws

    def bytes(self):
        buffer = BytesIO()
        self.wb.save(buffer)
        return buffer.getvalue()


def reporte_ventas_xlsx(datos, filtros):
    libro = _Libro()

    resumen = [('Filtros aplicados', [(k, v) for k, v in filtros] or [('Filtros', 'Ninguno')]),
               ('Hallazgos clave', datos['hallazgos'])]
    for moneda, k in datos['kpis'].items():
        cfdi = datos['cfdi'].get(moneda, {})
        resumen.append((f'Indicadores {moneda}', [
            ('Ventas', k['ventas'], 'moneda'),
            ('Operaciones', k['n'], 'entero'),
            ('Ticket promedio', k['ticket'], 'moneda'),
            ('Cobrado', k['cobrado'], 'moneda'),
            ('Cobranza efectiva', k['cobranza_pct'], 'pct'),
            ('Saldo por cobrar (neto de notas de crédito)', k['saldo'], 'moneda'),
            ('Saldo vencido', k['vencido'], 'moneda'),
            ('% del saldo vencido', k['vencido_pct'], 'pct'),
            ('Vencido más de 90 días', k['vencido_90'], 'moneda'),
            ('Ventas de contado', k['contado'], 'moneda'),
            ('Ventas a crédito', k['credito'], 'moneda'),
            ('Días promedio de cobro (crédito)',
             round(k['dias_cobro'], 1) if k['dias_cobro'] is not None else 'Sin pagos'),
            ('Ventas sin factura CFDI', k['sin_cfdi_n'], 'entero'),
            ('Importe sin factura CFDI', k['sin_cfdi_monto'], 'moneda'),
            ('Facturado CFDI del periodo', cfdi.get('facturado', 0.0), 'moneda'),
            ('Notas de crédito CFDI del periodo', cfdi.get('notas_credito', 0.0), 'moneda'),
            ('REP emitidos en el periodo', cfdi.get('rep', 0.0), 'moneda'),
        ]))
    libro.hoja_texto('Resumen', 'Reporte de análisis de ventas', resumen)

    libro.hoja(
        'Tendencia mensual',
        ['Moneda', 'Mes', 'Operaciones', 'Ventas', 'Cobrado', 'Saldo pendiente',
         '% cobrado', 'Variación vs mes anterior'],
        [[t['moneda'], t['mes_label'], t['n'], t['ventas'], t['cobrado'], t['saldo'],
          t['cobranza_pct'], t['variacion']] for t in datos['tendencia']],
        {2: 'entero', 3: 'moneda', 4: 'moneda', 5: 'moneda', 6: 'pct', 7: 'pct'},
        titulo_largo='Tendencia mensual de ventas y cobranza',
    )
    libro.hoja(
        'Clientes ABC',
        ['Moneda', 'Cliente', 'Clase', 'Operaciones', 'Ventas', '% participación',
         '% acumulado', 'Cobrado', '% cobrado', 'Saldo', 'Vencido',
         'Máx. días vencido', 'Ventas sin CFDI'],
        [[r['moneda'], r['cliente'], r['clase'], r['n'], r['ventas'], r['participacion'],
          r['acumulado'], r['cobrado'], r['cobranza_pct'], r['saldo'], r['vencido'],
          r['max_dias'], r['sin_cfdi']] for r in datos['ranking']],
        {3: 'entero', 4: 'moneda', 5: 'pct', 6: 'pct', 7: 'moneda', 8: 'pct',
         9: 'moneda', 10: 'moneda', 11: 'entero', 12: 'entero'},
        titulo_largo='Concentración de clientes (Pareto ABC)',
        subtitulo='A: clientes que suman el 80% de la venta · B: siguiente 15% · C: resto',
    )
    libro.hoja(
        'Antigüedad de cartera',
        ['Moneda', 'Cliente'] + [label for _, label in BUCKETS] + ['Total'],
        [[a['moneda'], a['cliente']] + [a[key] for key, _ in BUCKETS] + [a['total']]
         for a in datos['antiguedad']],
        {i: 'moneda' for i in range(2, 3 + len(BUCKETS))},
        titulo_largo='Antigüedad de saldos por cobrar',
        subtitulo='Saldo neto de notas de crédito; días contados desde la fecha de vencimiento.',
    )
    libro.hoja(
        'Productos',
        ['Moneda', 'Producto / concepto', 'Operaciones', 'Cantidad', 'Ventas', 'Precio promedio'],
        [[p['moneda'], p['concepto'], p['n'], p['cantidad'], p['ventas'], p['precio_promedio']]
         for p in datos['productos']],
        {2: 'entero', 3: 'moneda', 4: 'moneda', 5: 'moneda'},
        titulo_largo='Ventas por producto',
    )
    libro.hoja(
        'Sucursales',
        ['Moneda', 'Sucursal', 'Operaciones', 'Ventas', 'Cobrado', '% cobrado', 'Saldo'],
        [[s['moneda'], s['sucursal'], s['n'], s['ventas'], s['cobrado'], s['cobranza_pct'], s['saldo']]
         for s in datos['sucursales']],
        {2: 'entero', 3: 'moneda', 4: 'moneda', 5: 'pct', 6: 'moneda'},
        titulo_largo='Ventas por sucursal',
    )
    columnas_venta = ['Venta', 'Referencia', 'Fecha', 'Cliente', 'Concepto', 'Sucursal',
                      'Modalidad', 'Estado', 'Moneda', 'Monto', 'Pagado', 'Saldo',
                      'Vencimiento', 'Días vencido', 'Facturas CFDI']
    formatos_venta = {2: 'fecha', 9: 'moneda', 10: 'moneda', 11: 'moneda', 12: 'fecha', 13: 'entero'}

    def fila_venta(d):
        return [d['id'], d['referencia'], d['fecha'], d['cliente'], d['concepto'], d['sucursal'],
                d['modalidad'], d['estado'], d['moneda'], d['monto'], d['pagado'], d['saldo'],
                d['vencimiento'], d['dias_vencido'], d['facturas']]

    libro.hoja('Ventas sin CFDI', columnas_venta, [fila_venta(d) for d in datos['sin_cfdi']],
               formatos_venta, titulo_largo='Ventas sin factura CFDI vinculada',
               subtitulo='Revisar si falta emitir o importar la factura.')
    libro.hoja('Detalle de ventas', columnas_venta, [fila_venta(d) for d in datos['detalle']],
               formatos_venta, titulo_largo='Detalle de ventas filtradas')
    return libro.bytes()


def reporte_conciliacion_xlsx(datos, filtros):
    libro = _Libro()
    bloques = [('Filtros aplicados', [(k, v) for k, v in filtros] or [('Filtros', 'Ninguno')]),
               ('Hallazgos clave', datos['hallazgos'])]
    for moneda, t in datos['totales'].items():
        bloques.append((f'Totales {moneda}', [
            ('Facturado', t['facturado'], 'moneda'),
            ('+ Notas de cargo', t['notas_cargo'], 'moneda'),
            ('− Notas de crédito', t['notas_credito'], 'moneda'),
            ('− Pagos (REP)', t['recibos_pago'], 'moneda'),
            ('− Cobros contado / sin REP', t['cobros_contado'], 'moneda'),
            ('− Anticipos disponibles', t['anticipos_disponibles'], 'moneda'),
            ('= Saldo conciliado neto', t['saldo'], 'moneda'),
            ('Cartera por cobrar', t['por_cobrar'], 'moneda'),
            ('Saldo a favor de clientes', t['a_favor'], 'moneda'),
            ('Clientes con deuda', t['clientes_deuda'], 'entero'),
        ]))
    libro.hoja_texto('Resumen', 'Reporte de conciliación de CFDI', bloques)

    m = 'moneda'
    libro.hoja(
        'Conciliación',
        ['Cliente', 'Moneda', 'Facturado', '+ Notas cargo', '− Notas crédito', '− Pagos (REP)',
         '− Cobros contado / sin REP', '− Anticipos', 'Saldo conciliado', 'Estado',
         'Docs. sin vincular', 'Cobros sin CFDI'],
        [[r['cliente'], r['moneda'], r['facturado'], r['notas_cargo'], r['notas_credito'],
          r['recibos_pago'], r['cobros_contado'], r['anticipos_disponibles'], r['saldo'],
          r['estado'], r['sin_vincular'], r['cobros_sin_cfdi']] for r in datos['resumen']],
        {2: m, 3: m, 4: m, 5: m, 6: m, 7: m, 8: m, 10: 'entero', 11: 'entero'},
        titulo_largo='Conciliación por cliente y moneda',
        subtitulo='Saldo = Facturado + Notas cargo − Notas crédito − REP − Cobros contado/sin REP − Anticipos',
    )
    libro.hoja(
        'Concentración cartera',
        ['Moneda', 'Cliente', 'Saldo por cobrar', '% de la cartera', '% acumulado'],
        [[c['moneda'], c['cliente'], c['saldo'], c['participacion'], c['acumulado']]
         for c in datos['concentracion']],
        {2: m, 3: 'pct', 4: 'pct'},
        titulo_largo='Concentración de la cartera por cobrar',
    )
    libro.hoja(
        'Incidencias',
        ['Tipo', 'Cliente', 'Documento', 'Fecha', 'Monto', 'Moneda', 'Acción sugerida'],
        [[i['tipo'], i['cliente'], i['documento'], i['fecha'], i['monto'], i['moneda'], i['accion']]
         for i in datos['incidencias']],
        {3: 'fecha', 4: m},
        titulo_largo='Incidencias por resolver',
        subtitulo='Pendientes que impiden que el saldo fiscal y el operativo cuadren.',
    )
    libro.hoja(
        'Cobros contado-sin REP',
        ['Cliente', 'Origen', 'Referencia', 'Venta', 'Fecha(s)', 'Monto', 'Moneda', 'CFDI relacionado'],
        [[c['cliente'], c['origen'], c['referencia'], c['venta_id'], c['fechas'], c['monto'],
          c['moneda'], c['cfdi'] or 'Sin CFDI'] for c in datos['cobros']],
        {5: m},
        titulo_largo='Origen de cobros de contado y pagos sin REP',
    )
    estados_rep = {'uuid_coincidente': 'UUID coincidente'}
    libro.hoja(
        'Aplicaciones REP',
        ['Cliente', 'Folio REP', 'UUID REP', 'UUID factura', 'Fecha de pago', 'REP aplicado',
         'Moneda', 'Pago operativo', 'Diferencia operativo-fiscal', 'Saldo insoluto', 'Vínculo'],
        [[r['cliente'], r.get('folio_rep') or '', r.get('uuid_rep') or '', r.get('uuid_factura') or '',
          r.get('fecha_pago'), _num(r.get('monto_rep_aplicado')), r.get('moneda') or '',
          _num(r.get('monto_operativo')), _num(r.get('diferencia_operativo_fiscal')),
          _num(r.get('imp_saldo_insoluto')),
          estados_rep.get(r.get('estado_vinculo'), 'Revisión requerida')]
         for r in datos['reps']],
        {4: 'fecha', 5: m, 7: m, 8: m, 9: m},
        titulo_largo='Aplicaciones de recibos de pago (REP)',
    )
    return libro.bytes()


def _num(valor):
    return float(valor) if valor is not None else None


# =============================================================================
# PDF
# =============================================================================

class _Pdf:
    """Documento horizontal con encabezado, pie con página y tablas paginables."""

    def __init__(self, titulo, filtros):
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_RIGHT
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm

        self.colors = colors
        self.cm = cm
        self.pagesize = landscape(letter)
        self.titulo = titulo
        self.filtros = filtros
        self.elements = []
        base = getSampleStyleSheet()
        self.primario = colors.HexColor('#' + COLOR_PRIMARIO)
        self.acento = colors.HexColor('#' + COLOR_ACENTO)
        self.st_h1 = ParagraphStyle('h1', parent=base['Title'], fontSize=17,
                                    textColor=self.primario, alignment=0, spaceAfter=2)
        self.st_h2 = ParagraphStyle('h2', parent=base['Heading2'], fontSize=12,
                                    textColor=self.primario, spaceBefore=10, spaceAfter=4)
        self.st_txt = ParagraphStyle('txt', parent=base['BodyText'], fontSize=8.5, leading=11)
        self.st_sub = ParagraphStyle('sub', parent=self.st_txt, textColor=colors.HexColor('#666666'))
        self.st_cell = ParagraphStyle('cell', parent=base['BodyText'], fontSize=7.5, leading=9)
        self.st_cell_r = ParagraphStyle('cellr', parent=self.st_cell, alignment=TA_RIGHT)
        self.st_head = ParagraphStyle('head', parent=self.st_cell, textColor=colors.white,
                                      fontName='Helvetica-Bold')
        self.st_kpi_v = ParagraphStyle('kv', parent=base['BodyText'], fontSize=12,
                                       fontName='Helvetica-Bold', textColor=self.primario, leading=14)
        self.st_kpi_l = ParagraphStyle('kl', parent=self.st_cell, textColor=colors.HexColor('#555555'))

        self._p(titulo, self.st_h1)
        filtros_txt = ' · '.join(f'<b>{_esc(k)}:</b> {_esc(v)}' for k, v in filtros) or 'Sin filtros'
        self._p(filtros_txt, self.st_sub)
        self._p(f'Generado el {timezone.localtime().strftime("%d/%m/%Y %H:%M")}', self.st_sub)

    def _p(self, texto, estilo):
        from reportlab.platypus import Paragraph
        self.elements.append(Paragraph(texto, estilo))

    def seccion(self, texto, nota=None):
        self._p(_esc(texto), self.st_h2)
        if nota:
            self._p(_esc(nota), self.st_sub)

    def vinetas(self, items):
        for item in items:
            self._p('• ' + _esc(item), self.st_txt)

    def kpis(self, tarjetas):
        """Fila de tarjetas (etiqueta, valor) en bloques de 4 por renglón."""
        from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
        celdas = [[Paragraph(_esc(v), self.st_kpi_v), Paragraph(_esc(lbl), self.st_kpi_l)]
                  for lbl, v in tarjetas]
        por_fila = 4
        ancho = (self.pagesize[0] - 2.4 * self.cm) / por_fila
        for i in range(0, len(celdas), por_fila):
            grupo = celdas[i:i + por_fila]
            grupo += [['', '']] * (por_fila - len(grupo))
            t = Table([grupo], colWidths=[ancho] * por_fila)
            t.setStyle(TableStyle([
                ('BOX', (0, 0), (-1, -1), 0.25, self.colors.HexColor('#D5DCE0')),
                ('INNERGRID', (0, 0), (-1, -1), 0.25, self.colors.HexColor('#D5DCE0')),
                ('LINEABOVE', (0, 0), (-1, 0), 2, self.acento),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            self.elements.append(t)
            self.elements.append(Spacer(1, 4))

    def tabla(self, encabezados, filas, anchos, numericas=(), total=None, vacio='Sin datos.'):
        """Tabla con encabezado repetido en cada página.

        ``anchos`` son proporciones; ``numericas`` índices alineados a la derecha.
        """
        from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
        if not filas:
            self._p(_esc(vacio), self.st_sub)
            return
        disponible = self.pagesize[0] - 2.4 * self.cm
        suma = float(sum(anchos))
        col_widths = [disponible * a / suma for a in anchos]

        def celda(valor, idx, estilo=None):
            st = estilo or (self.st_cell_r if idx in numericas else self.st_cell)
            return Paragraph(_esc(valor), st)

        data = [[Paragraph(_esc(h), self.st_head) for h in encabezados]]
        data += [[celda(v, i) for i, v in enumerate(f)] for f in filas]
        if total:
            data.append([celda(v, i) for i, v in enumerate(total)])
        t = Table(data, colWidths=col_widths, repeatRows=1)
        estilo = [
            ('BACKGROUND', (0, 0), (-1, 0), self.primario),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.25, self.colors.HexColor('#D5DCE0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.colors.white, self.colors.HexColor('#F6F8F9')]),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]
        if total:
            estilo += [('BACKGROUND', (0, -1), (-1, -1), self.colors.HexColor('#EEF2F4')),
                       ('LINEABOVE', (0, -1), (-1, -1), 1, self.primario)]
        t.setStyle(TableStyle(estilo))
        self.elements.append(t)
        self.elements.append(Spacer(1, 6))

    def salto(self):
        from reportlab.platypus import PageBreak
        self.elements.append(PageBreak())

    def bytes(self):
        from reportlab.platypus import SimpleDocTemplate
        buffer = BytesIO()
        titulo = self.titulo

        def pie(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 7)
            canvas.setFillColor(self.colors.HexColor('#777777'))
            canvas.drawString(1.2 * self.cm, 0.7 * self.cm,
                              f'Agrícola de la Costa San Luis · {titulo}')
            canvas.drawRightString(self.pagesize[0] - 1.2 * self.cm, 0.7 * self.cm,
                                   f'Página {doc.page}')
            canvas.restoreState()

        doc = SimpleDocTemplate(
            buffer, pagesize=self.pagesize, title=titulo,
            leftMargin=1.2 * self.cm, rightMargin=1.2 * self.cm,
            topMargin=1.1 * self.cm, bottomMargin=1.3 * self.cm,
        )
        doc.build(self.elements, onFirstPage=pie, onLaterPages=pie)
        return buffer.getvalue()


def _esc(valor):
    from xml.sax.saxutils import escape
    if valor is None:
        return ''
    if isinstance(valor, date):
        return valor.strftime('%d/%m/%Y')
    # Helvetica (fuente base de reportlab) no trae el signo menos U+2212.
    return escape(str(valor).replace('−', '-'))


def _m(valor):
    return '' if valor is None else f'{valor:,.2f}'


def _p100(valor):
    return '' if valor is None else f'{valor:.1%}'


def reporte_ventas_pdf(datos, filtros, limite_detalle=300):
    pdf = _Pdf('Reporte de análisis de ventas', filtros)

    pdf.seccion('Hallazgos clave')
    pdf.vinetas(datos['hallazgos'])

    for moneda, k in datos['kpis'].items():
        pdf.seccion(f'Indicadores {moneda}')
        cfdi = datos['cfdi'].get(moneda, {})
        pdf.kpis([
            ('Ventas', _fmt(k['ventas'])),
            ('Cobrado', f'{_fmt(k["cobrado"])} ({k["cobranza_pct"]:.1%})'),
            ('Saldo por cobrar', _fmt(k['saldo'])),
            ('Vencido', f'{_fmt(k["vencido"])} ({k["vencido_pct"]:.1%})'),
            ('Operaciones', f'{k["n"]:,}'),
            ('Ticket promedio', _fmt(k['ticket'])),
            ('Días promedio de cobro (crédito)',
             f'{k["dias_cobro"]:.0f} días' if k['dias_cobro'] is not None else 'Sin pagos'),
            ('Ventas sin factura CFDI', f'{k["sin_cfdi_n"]} · {_fmt(k["sin_cfdi_monto"])}'),
            ('Contado / Crédito', f'{_fmt(k["contado"])} / {_fmt(k["credito"])}'),
            ('Facturado CFDI', _fmt(cfdi.get('facturado', 0.0))),
            ('Notas de crédito CFDI', _fmt(cfdi.get('notas_credito', 0.0))),
            ('REP emitidos', _fmt(cfdi.get('rep', 0.0))),
        ])

    pdf.seccion('Tendencia mensual')
    pdf.tabla(
        ['Moneda', 'Mes', 'Operaciones', 'Ventas', 'Cobrado', 'Saldo', '% cobrado', 'Var. vs mes ant.'],
        [[t['moneda'], t['mes_label'], t['n'], _m(t['ventas']), _m(t['cobrado']), _m(t['saldo']),
          _p100(t['cobranza_pct']), _p100(t['variacion'])] for t in datos['tendencia']],
        [1, 1.4, 1, 2, 2, 2, 1.2, 1.4], numericas={2, 3, 4, 5, 6, 7},
    )

    pdf.seccion('Concentración de clientes (Pareto ABC)',
                'A: clientes que suman el 80% de la venta · B: siguiente 15% · C: resto')
    pdf.tabla(
        ['Moneda', 'Cliente', 'Clase', 'Ventas', '% part.', '% acum.', 'Cobrado', 'Saldo', 'Vencido', 'Máx. días'],
        [[r['moneda'], r['cliente'], r['clase'], _m(r['ventas']), _p100(r['participacion']),
          _p100(r['acumulado']), _m(r['cobrado']), _m(r['saldo']), _m(r['vencido']), r['max_dias'] or '']
         for r in datos['ranking']],
        [0.9, 3.6, 0.7, 1.8, 1, 1, 1.8, 1.8, 1.8, 1], numericas={3, 4, 5, 6, 7, 8, 9},
    )

    pdf.seccion('Antigüedad de saldos por cobrar',
                'Saldo neto de notas de crédito; días desde la fecha de vencimiento.')
    totales = defaultdict(lambda: defaultdict(float))
    for a in datos['antiguedad']:
        for key, _ in BUCKETS:
            totales[a['moneda']][key] += a[key]
        totales[a['moneda']]['total'] += a['total']
    filas = [[a['moneda'], a['cliente']] + [_m(a[key]) for key, _ in BUCKETS] + [_m(a['total'])]
             for a in datos['antiguedad']]
    filas += [[mon, 'TOTAL'] + [_m(t[key]) for key, _ in BUCKETS] + [_m(t['total'])]
              for mon, t in sorted(totales.items())]
    pdf.tabla(['Moneda', 'Cliente'] + [lbl for _, lbl in BUCKETS] + ['Total'], filas,
              [0.9, 3.4, 1.6, 1.6, 1.6, 1.6, 1.6, 1.8], numericas=set(range(2, 8)),
              vacio='No hay saldos pendientes.')

    pdf.seccion('Ventas por producto')
    pdf.tabla(
        ['Moneda', 'Producto / concepto', 'Operaciones', 'Cantidad', 'Ventas', 'Precio promedio'],
        [[p['moneda'], p['concepto'], p['n'], f'{p["cantidad"]:,.2f}', _m(p['ventas']),
          _m(p['precio_promedio'])] for p in datos['productos']],
        [0.9, 4, 1.2, 1.8, 2, 1.8], numericas={2, 3, 4, 5},
    )
    pdf.seccion('Ventas por sucursal')
    pdf.tabla(
        ['Moneda', 'Sucursal', 'Operaciones', 'Ventas', 'Cobrado', '% cobrado', 'Saldo'],
        [[s['moneda'], s['sucursal'], s['n'], _m(s['ventas']), _m(s['cobrado']),
          _p100(s['cobranza_pct']), _m(s['saldo'])] for s in datos['sucursales']],
        [0.9, 3.5, 1.2, 2, 2, 1.2, 2], numericas={2, 3, 4, 5, 6},
    )

    def filas_venta(lista):
        return [[d['referencia'], d['fecha'], d['cliente'], d['modalidad'], d['estado'], d['moneda'],
                 _m(d['monto']), _m(d['pagado']), _m(d['saldo']), d['vencimiento'],
                 d['dias_vencido'] or '', d['facturas'] or '—'] for d in lista]

    cols = ['Referencia', 'Fecha', 'Cliente', 'Modalidad', 'Estado', 'Moneda', 'Monto',
            'Pagado', 'Saldo', 'Vence', 'Días venc.', 'Facturas']
    anchos = [1.5, 1.1, 3, 1, 1.2, 0.8, 1.6, 1.6, 1.6, 1.1, 0.8, 1.6]
    pdf.salto()
    pdf.seccion('Ventas sin factura CFDI vinculada', 'Revisar si falta emitir o importar la factura.')
    pdf.tabla(cols, filas_venta(datos['sin_cfdi']), anchos, numericas={6, 7, 8, 10},
              vacio='Todas las ventas tienen factura vinculada.')

    detalle = datos['detalle']
    nota = None
    if len(detalle) > limite_detalle:
        nota = (f'Se muestran las {limite_detalle} ventas con mayor saldo de {len(detalle)}. '
                'El detalle completo está en el reporte Excel.')
        detalle = sorted(detalle, key=lambda d: -d['saldo'])[:limite_detalle]
    pdf.seccion('Detalle de ventas', nota)
    pdf.tabla(cols, filas_venta(detalle), anchos, numericas={6, 7, 8, 10})
    return pdf.bytes()


def reporte_conciliacion_pdf(datos, filtros):
    pdf = _Pdf('Reporte de conciliación de CFDI', filtros)
    pdf.seccion('Hallazgos clave')
    pdf.vinetas(datos['hallazgos'])

    for moneda, t in datos['totales'].items():
        pdf.seccion(f'Totales {moneda}')
        pdf.kpis([
            ('Facturado', _fmt(t['facturado'])),
            ('Notas de crédito', _fmt(t['notas_credito'])),
            ('Pagos (REP)', _fmt(t['recibos_pago'])),
            ('Cobros contado / sin REP', _fmt(t['cobros_contado'])),
            ('Cartera por cobrar', _fmt(t['por_cobrar'])),
            ('Saldo a favor de clientes', _fmt(abs(t['a_favor']))),
            ('Saldo conciliado neto', _fmt(t['saldo'])),
            ('Clientes con deuda', str(t['clientes_deuda'])),
        ])

    pdf.seccion('Conciliación por cliente',
                'Saldo = Facturado + Notas cargo − Notas crédito − REP − Cobros contado/sin REP − Anticipos')
    columnas = ['facturado', 'notas_cargo', 'notas_credito', 'recibos_pago',
                'cobros_contado', 'anticipos_disponibles', 'saldo']
    filas = [[r['cliente'], r['moneda']] + [_m(r[c]) for c in columnas]
             + [r['sin_vincular'] or '', r['cobros_sin_cfdi'] or '']
             for r in datos['resumen']]
    filas += [['TOTAL', mon] + [_m(t[c]) for c in columnas] + ['', '']
              for mon, t in datos['totales'].items()]
    pdf.tabla(
        ['Cliente', 'Moneda', 'Facturado', '+ N. cargo', '− N. crédito', '− REP',
         '− Contado / sin REP', '− Anticipos', 'Saldo', 'Sin vinc.', 'Cobros sin CFDI'],
        filas, [3.2, 0.8, 1.7, 1.3, 1.5, 1.7, 1.7, 1.5, 1.7, 0.8, 1], numericas=set(range(2, 11)),
    )

    pdf.seccion('Concentración de la cartera por cobrar')
    pdf.tabla(
        ['Moneda', 'Cliente', 'Saldo por cobrar', '% de la cartera', '% acumulado'],
        [[c['moneda'], c['cliente'], _m(c['saldo']), _p100(c['participacion']), _p100(c['acumulado'])]
         for c in datos['concentracion']],
        [1, 5, 2, 1.5, 1.5], numericas={2, 3, 4}, vacio='No hay cartera por cobrar.',
    )

    pdf.salto()
    pdf.seccion('Incidencias por resolver',
                'Pendientes que impiden que el saldo fiscal y el operativo cuadren.')
    pdf.tabla(
        ['Tipo', 'Cliente', 'Documento', 'Fecha', 'Monto', 'Moneda', 'Acción sugerida'],
        [[i['tipo'], i['cliente'], i['documento'], i['fecha'], _m(i['monto']), i['moneda'], i['accion']]
         for i in datos['incidencias']],
        [1.8, 2.6, 2, 1, 1.5, 0.8, 4], numericas={4}, vacio='Sin incidencias.',
    )
    return pdf.bytes()
