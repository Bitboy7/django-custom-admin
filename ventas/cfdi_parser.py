"""
CFDI 3.3 / 4.0 XML parser for the ventas module.

Soporta tanto CFDI 3.3 (Blikon / PAC legacy) como CFDI 4.0. Extrae los campos
necesarios para clasificar el documento dentro de la taxonomía de negocio:

  - Venta Nacional / Exportación (ingreso)
  - Nota de Cargo (ingreso, TipoRelacion 02)
  - Remanente de Anticipo (ingreso, TipoRelacion 07 o concepto anticipo/remanente)
  - Nota de Crédito (egreso)
  - Recibo Electrónico de Pago (Pago / complemento RecepcionDePagos)

Security:
  - Usa defusedxml cuando está disponible (recomendado: pip install defusedxml).
  - Fallback a stdlib xml.etree.ElementTree, que NO expande entidades externas
    por defecto, mitigando ataques XXE.
  - La validación de tamaño de archivo debe aplicarse en la capa de vista antes
    de llamar a parse_cfdi().
"""
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

CFDI_33_NS = 'http://www.sat.gob.mx/cfd/3'
CFDI_40_NS = 'http://www.sat.gob.mx/cfd/4'
CCE11_NS = 'http://www.sat.gob.mx/ComercioExterior11'
CCE20_NS = 'http://www.sat.gob.mx/ComercioExterior20'
TFD_NS = 'http://www.sat.gob.mx/TimbreFiscalDigital'
PAGOS_NS = 'http://www.sat.gob.mx/Pagos'

MAX_XML_BYTES = 1 * 1024 * 1024  # 1 MB


def _get_et():
    try:
        import defusedxml.ElementTree as ET
        return ET
    except ImportError:
        import xml.etree.ElementTree as ET
        return ET


def _detect_version(root) -> str:
    """Retorna '3.3' o '4.0' según el namespace del nodo raíz."""
    tag = root.tag
    if tag.startswith(f'{{{CFDI_40_NS}}}'):
        return '4.0'
    if tag.startswith(f'{{{CFDI_33_NS}}}'):
        return '3.3'
    # Fallback: inspeccionar contenido textual
    if CFDI_33_NS in tag:
        return '3.3'
    return '4.0'


def _first_text(root, namespaces, tag_names):
    for tn in tag_names:
        for ns in namespaces:
            el = root.find(f'{{{ns}}}{tn}')
            if el is not None and el.text:
                return el.text.strip()
    return ''


def _extract_relacionados(root, cfdi_ns):
    """Extrae TipoRelacion y lista de UUIDs de CfdiRelacionados."""
    relacionados_node = root.find(f'{{{cfdi_ns}}}CfdiRelacionados')
    tipo_relacion = ''
    relacionados = []
    if relacionados_node is not None:
        tipo_relacion = relacionados_node.get('TipoRelacion', '')
        for rel in relacionados_node.findall(f'{{{cfdi_ns}}}CfdiRelacionado'):
            uuid = rel.get('UUID', '')
            if uuid:
                relacionados.append(uuid)
    return tipo_relacion, relacionados


def _extract_pagos(root):
    """
    Extrae el complemento de pagos (RecepcionDePagos / Recibo Electrónico).

    Retorna una lista de dicts con la información de cada Pago:
        [{'fecha': date, 'monto': Decimal, 'moneda': str, 'forma': str,
          'num_operacion': str, 'doctos': [{'uuid': str, 'pagado': Decimal, ...}]}]
    """
    pagos = []
    pagos_root = root.find(f'.//{{{PAGOS_NS}}}Pagos')
    if pagos_root is None:
        return pagos

    for pago in pagos_root.findall(f'{{{PAGOS_NS}}}Pago'):
        fecha_raw = pago.get('FechaPago', '')
        fecha = None
        if fecha_raw:
            try:
                fecha = date.fromisoformat(fecha_raw[:10])
            except ValueError:
                pass

        monto = Decimal('0')
        try:
            monto = Decimal(pago.get('Monto', '0') or '0')
        except InvalidOperation:
            pass

        doctos = []
        for d in pago.findall(f'{{{PAGOS_NS}}}DoctoRelacionado'):
            pagado = Decimal('0')
            try:
                pagado = Decimal(d.get('ImpPagado', '0') or '0')
            except InvalidOperation:
                pass
            doctos.append({
                'uuid': d.get('IdDocumento', ''),
                'pagado': pagado,
                'saldo_anterior': d.get('ImpSaldoAnt', ''),
                'saldo_insoluto': d.get('ImpSaldoInsoluto', ''),
                'parcialidad': d.get('NumParcialidad', ''),
                'moneda': d.get('MonedaDR', ''),
            })

        pagos.append({
            'fecha': fecha,
            'monto': monto,
            'moneda': pago.get('MonedaP', 'MXN'),
            'forma': pago.get('FormaDePagoP', ''),
            'num_operacion': pago.get('NumOperacion', ''),
            'tipo_cambio': pago.get('TipoCambioP', ''),
            'doctos': doctos,
        })

    return pagos


def parse_cfdi(xml_bytes: bytes) -> dict:
    """
    Parse a CFDI 3.3 o 4.0 XML document and return a dict of extracted fields.

    Returns a dict with:
      - Direct model-field keys matching Ventas (donde sea mapeable)
      - Claves de clasificación: tipo_comprobante, tipo_relacion, relacionados,
        uuid, pagos (REP).
      - Claves privadas prefijadas con '_' para hints de lookup (cliente, etc.)

    Raises ValueError con un mensaje amigable ante error de parseo.
    """
    if len(xml_bytes) > MAX_XML_BYTES:
        raise ValueError("El archivo XML excede el tamaño máximo permitido (1 MB).")

    ET = _get_et()
    try:
        root = ET.fromstring(xml_bytes)
    except Exception as exc:
        raise ValueError(f"El archivo no es un XML válido: {exc}") from exc

    version = _detect_version(root)
    cfdi_ns = CFDI_40_NS if version == '4.0' else CFDI_33_NS

    ns = {
        'cfdi': cfdi_ns,
        'cce11': CCE11_NS,
        'cce20': CCE20_NS,
        'tfd': TFD_NS,
    }

    def attr(el, name, default=''):
        return el.get(name, default) if el is not None else default

    # ── Comprobante root ──────────────────────────────────────────────────
    serie = attr(root, 'Serie')
    folio = attr(root, 'Folio')
    folio_factura = f"{serie} {folio}".strip() if (serie or folio) else ''

    fecha_raw = attr(root, 'Fecha')
    fecha_emision_cfdi = None
    if fecha_raw:
        try:
            fecha_emision_cfdi = date.fromisoformat(fecha_raw[:10])
        except ValueError:
            pass

    tipo_comprobante = attr(root, 'TipoDeComprobante', 'I').upper()

    moneda_venta = attr(root, 'Moneda', 'MXN')

    try:
        monto = Decimal(attr(root, 'Total', '0'))
    except InvalidOperation:
        monto = Decimal('0')

    metodo_pago = attr(root, 'MetodoPago')  # PUE = Contado, PPD = Crédito
    modalidad_pago = 'Credito' if metodo_pago == 'PPD' else 'Contado'

    tipo_cambio = Decimal('1.0000')
    try:
        raw_tc = attr(root, 'TipoCambio', '1')
        tipo_cambio = round(Decimal(raw_tc or '1'), 4)
    except InvalidOperation:
        pass

    # Detección de exportación: 4.0 usa atributo Exportacion; 3.3 usa complemento
    exportacion = attr(root, 'Exportacion')
    if exportacion in ('02', '03'):
        tipo_venta = 'Exportación'
    else:
        tipo_venta = 'Nacional'

    # ── TipoRelacion / CfdiRelacionados ───────────────────────────────────
    tipo_relacion, relacionados = _extract_relacionados(root, cfdi_ns)

    # ── Receptor (cliente) ────────────────────────────────────────────────
    receptor = root.find('cfdi:Receptor', ns)
    receptor_nombre = attr(receptor, 'Nombre')
    receptor_rfc = attr(receptor, 'Rfc')
    receptor_residencia_fiscal = attr(receptor, 'ResidenciaFiscal')
    receptor_num_reg_id_trib = attr(receptor, 'NumRegIdTrib')
    receptor_domicilio_fiscal = attr(receptor, 'DomicilioFiscalReceptor')
    receptor_regimen_fiscal = attr(receptor, 'RegimenFiscalReceptor')
    receptor_uso_cfdi = attr(receptor, 'UsoCFDI')

    # ── Primer concepto ───────────────────────────────────────────────────
    concepto = root.find('.//cfdi:Concepto', ns)
    cantidad = None
    descripcion = ''
    no_identificacion = ''
    clave_prod_serv = ''
    if concepto is not None:
        try:
            cantidad = Decimal(attr(concepto, 'Cantidad', '0'))
        except InvalidOperation:
            cantidad = None
        raw_desc = attr(concepto, 'Descripcion')
        descripcion = re.sub(r'\s+', ' ', raw_desc).strip()[:100]
        no_identificacion = attr(concepto, 'NoIdentificacion')
        clave_prod_serv = attr(concepto, 'ClaveProdServ')

    # ── Complemento ComercioExterior (1.1 o 2.0) ──────────────────────────
    cce = root.find('.//cce20:ComercioExterior', ns)
    if cce is None:
        cce = root.find('.//cce11:ComercioExterior', ns)

    incoterm = ''
    fraccion_arancelaria = ''
    cantidad_aduana = None
    if cce is not None:
        try:
            tipo_cambio = round(Decimal(attr(cce, 'TipoCambioUSD', '1') or '1'), 4)
        except InvalidOperation:
            pass
        incoterm = attr(cce, 'Incoterm')
        # Si hay complemento de comercio exterior, es exportación
        tipo_venta = 'Exportación'

        for merc_ns in (CCE20_NS, CCE11_NS):
            mercancia = cce.find(f'{{{merc_ns}}}Mercancias/{{{merc_ns}}}Mercancia')
            if mercancia is not None:
                fraccion_arancelaria = attr(mercancia, 'FraccionArancelaria')
                try:
                    cantidad_aduana = Decimal(attr(mercancia, 'CantidadAduana', '0'))
                except InvalidOperation:
                    pass
                break

    # ── TimbreFiscalDigital (UUID / folio fiscal) ─────────────────────────
    tfd = root.find(f'.//{{{TFD_NS}}}TimbreFiscalDigital')
    uuid = attr(tfd, 'UUID') if tfd is not None else ''
    fecha_timbrado = None
    if tfd is not None:
        tfd_fecha = attr(tfd, 'FechaTimbrado')
        if tfd_fecha:
            try:
                fecha_timbrado = datetime.fromisoformat(tfd_fecha)
            except ValueError:
                pass

    # Append UUID to folio for traceability
    if uuid:
        folio_factura = f"{folio_factura} | {uuid}".strip(' |') if folio_factura else uuid

    # ── Complemento de pagos (REP) ────────────────────────────────────────
    pagos = _extract_pagos(root)

    # ── P.O. detection ────────────────────────────────────────────────────
    po = _detect_po(root, cfdi_ns, descripcion)

    return {
        # ── Claves compatibles con Ventas / forms ─────────────────────────
        'folio_factura': folio_factura,
        'fecha_emision_cfdi': fecha_emision_cfdi,
        'monto': monto,
        'moneda_venta': moneda_venta,
        'tipo_cambio': tipo_cambio,
        'incoterm': incoterm,
        'tipo_venta': tipo_venta,
        'modalidad_pago': modalidad_pago,
        'cantidad': cantidad,
        'descripcion': descripcion,
        'PO': po,
        # ── Claves de clasificación ───────────────────────────────────────
        'tipo_comprobante': tipo_comprobante,
        'tipo_relacion': tipo_relacion,
        'relacionados': relacionados,
        'serie': serie,
        'folio_num': folio,
        'uuid': uuid,
        'fecha_timbrado': fecha_timbrado,
        'pagos': pagos,
        'version': version,
        # ── Lookup hints (no son campos de modelo) ────────────────────────
        '_receptor_nombre': receptor_nombre,
        '_receptor_rfc': receptor_rfc,
        '_receptor_residencia_fiscal': receptor_residencia_fiscal,
        '_receptor_num_reg_id_trib': receptor_num_reg_id_trib,
        '_receptor_domicilio_fiscal': receptor_domicilio_fiscal,
        '_receptor_regimen_fiscal': receptor_regimen_fiscal,
        '_receptor_uso_cfdi': receptor_uso_cfdi,
        '_no_identificacion': no_identificacion,
        '_clave_prod_serv': clave_prod_serv,
        '_fraccion_arancelaria': fraccion_arancelaria,
        '_cantidad_aduana_kg': cantidad_aduana,
        '_uuid': uuid,
        '_metodo_pago_raw': metodo_pago,
    }


def _detect_po(root, cfdi_ns, descripcion):
    """
    Busca el P.O. (Purchase Order) en la Addenda y, como fallback, en la
    descripción del concepto.
    """
    po = ''
    _PO_RE = re.compile(r'P\.?\s*O\.?[:\s#]*(\w+)', re.IGNORECASE)
    _PO_TAG_RE = re.compile(r'^P[_\.]?O$|orden.?compra|purchase.?order', re.IGNORECASE)

    addenda = root.find(f'{{{cfdi_ns}}}Addenda')
    if addenda is not None:
        for el in addenda.iter():
            tag_local = el.tag.split('}')[-1] if '}' in el.tag else el.tag

            if _PO_TAG_RE.search(tag_local):
                po = (el.text or '').strip()
                if po:
                    break

            attrs = el.attrib
            for name_key in ('nombre', 'name', 'label', 'descripcion', 'campo'):
                label_val = attrs.get(name_key, '')
                if _PO_RE.match(label_val + ':x'):
                    for val_key in ('valor', 'value', 'dato', 'data', 'contenido'):
                        if val_key in attrs:
                            po = attrs[val_key].strip()
                            break
                    if po:
                        break
            if po:
                break

            for aname, aval in attrs.items():
                alocal = aname.split('}')[-1] if '}' in aname else aname
                if _PO_TAG_RE.search(alocal):
                    po = aval.strip()
                    break
            if po:
                break

            if el.text:
                m = _PO_RE.search(el.text)
                if m:
                    po = m.group(1)
                    break

    if not po and descripcion:
        m = _PO_RE.search(descripcion)
        if m:
            po = m.group(1)

    return po


# Mapa subtipo → tipo de comprobante SAT
SUBIPO_TO_TIPO = {
    'venta_nacional': 'I',
    'venta_exportacion': 'I',
    'nota_cargo': 'I',
    'remanente_anticipo': 'I',
    'nota_credito': 'E',
    'recibo_pago': 'P',
}


def classify_subtipo(parsed: dict) -> str:
    """
    Clasifica un CFDI parseado en uno de los 6 subtipos de negocio.

    Reglas:
      - Pago (P)                          → recibo_pago
      - Egreso (E)                        → nota_credito
      - Ingreso (I) + TipoRelacion 02     → nota_cargo
      - Ingreso (I) + TipoRelacion 07 o
        concepto anticipo/remanente       → remanente_anticipo
      - Ingreso (I) resto                 → venta (nacional/exportación)
    """
    tipo_comprobante = (parsed.get('tipo_comprobante') or 'I').upper()
    tipo_relacion = parsed.get('tipo_relacion') or ''
    descripcion = (parsed.get('descripcion') or '').lower()

    if tipo_comprobante == 'P':
        return 'recibo_pago'
    if tipo_comprobante == 'E':
        return 'nota_credito'

    # Ingreso
    if tipo_relacion == '02':
        return 'nota_cargo'
    if tipo_relacion == '07' or 'anticipo' in descripcion or 'remanente' in descripcion:
        return 'remanente_anticipo'
    if tipo_relacion in ('01', '03'):
        return 'nota_credito'

    return 'venta_exportacion' if parsed.get('tipo_venta') == 'Exportación' else 'venta_nacional'
