"""
CFDI 4.0 XML parser for the ventas module.

Security:
  - Uses defusedxml when available (recommended: pip install defusedxml).
  - Falls back to stdlib xml.etree.ElementTree, which does NOT expand
    external entities by default, mitigating XXE attacks.
  - File-size validation must be applied at the view layer before calling
    parse_cfdi().
"""
import re
from datetime import date
from decimal import Decimal, InvalidOperation

CFDI_NS = 'http://www.sat.gob.mx/cfd/4'
CCE20_NS = 'http://www.sat.gob.mx/ComercioExterior20'
TFD_NS = 'http://www.sat.gob.mx/TimbreFiscalDigital'

MAX_XML_BYTES = 1 * 1024 * 1024  # 1 MB


def _get_et():
    try:
        import defusedxml.ElementTree as ET
        return ET
    except ImportError:
        import xml.etree.ElementTree as ET
        return ET


def parse_cfdi(xml_bytes: bytes) -> dict:
    """
    Parse a CFDI 4.0 XML document and return a dict of extracted fields.

    Returns a dict with:
      - Direct model-field keys matching Ventas (where mappable)
      - Private keys prefixed with '_' for lookup hints (client name, etc.)

    Raises ValueError with a user-friendly message on parse failure.
    """
    if len(xml_bytes) > MAX_XML_BYTES:
        raise ValueError("El archivo XML excede el tamaño máximo permitido (1 MB).")

    ET = _get_et()
    try:
        root = ET.fromstring(xml_bytes)
    except Exception as exc:
        raise ValueError(f"El archivo no es un XML válido: {exc}") from exc

    ns = {
        'cfdi': CFDI_NS,
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

    moneda_venta = attr(root, 'Moneda', 'MXN')

    try:
        monto = Decimal(attr(root, 'Total', '0'))
    except InvalidOperation:
        monto = Decimal('0')

    metodo_pago = attr(root, 'MetodoPago')  # PUE = Contado, PPD = Crédito
    modalidad_pago = 'Credito' if metodo_pago == 'PPD' else 'Contado'

    exportacion = attr(root, 'Exportacion')
    tipo_venta = 'Exportación' if exportacion in ('02', '03') else 'Nacional'

    # ── Receptor (cliente) ────────────────────────────────────────────────
    receptor = root.find('cfdi:Receptor', ns)
    receptor_nombre = attr(receptor, 'Nombre')
    receptor_rfc = attr(receptor, 'Rfc')

    # ── Primer concepto ───────────────────────────────────────────────────
    concepto = root.find('.//cfdi:Concepto', ns)
    cantidad = None
    descripcion = ''
    no_identificacion = ''
    if concepto is not None:
        try:
            cantidad = Decimal(attr(concepto, 'Cantidad', '0'))
        except InvalidOperation:
            cantidad = None
        raw_desc = attr(concepto, 'Descripcion')
        # Collapse whitespace and newlines; truncate to field max_length
        descripcion = re.sub(r'\s+', ' ', raw_desc).strip()[:100]
        no_identificacion = attr(concepto, 'NoIdentificacion')

    # Extract PO from description, e.g. "P.O: 16210" or "PO 16210"
    po = ''
    if descripcion:
        m = re.search(r'P\.?O[:\s#]+(\S+)', descripcion, re.IGNORECASE)
        if m:
            po = m.group(1)

    # ── Complemento ComercioExterior 2.0 ──────────────────────────────────
    cce = root.find('.//cce20:ComercioExterior', ns)
    tipo_cambio = Decimal('1.0000')
    incoterm = ''
    fraccion_arancelaria = ''
    cantidad_aduana = None
    if cce is not None:
        try:
            tipo_cambio = Decimal(attr(cce, 'TipoCambioUSD', '1'))
        except InvalidOperation:
            pass
        incoterm = attr(cce, 'Incoterm')
        mercancia = cce.find(f'{{{CCE20_NS}}}Mercancias/{{{CCE20_NS}}}Mercancia')
        if mercancia is not None:
            fraccion_arancelaria = attr(mercancia, 'FraccionArancelaria')
            try:
                cantidad_aduana = Decimal(attr(mercancia, 'CantidadAduana', '0'))
            except InvalidOperation:
                pass

    # ── TimbreFiscalDigital (UUID / folio fiscal) ─────────────────────────
    tfd = root.find(f'.//{{{TFD_NS}}}TimbreFiscalDigital')
    uuid = attr(tfd, 'UUID') if tfd is not None else ''

    # Append UUID to folio for traceability
    if uuid:
        folio_factura = f"{folio_factura} | {uuid}".strip(' |') if folio_factura else uuid

    return {
        # ── Direct Ventas model fields ────────────────────────────────────
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
        # ── Lookup hints (not model fields) ───────────────────────────────
        '_receptor_nombre': receptor_nombre,
        '_receptor_rfc': receptor_rfc,
        '_no_identificacion': no_identificacion,
        '_fraccion_arancelaria': fraccion_arancelaria,
        '_cantidad_aduana_kg': cantidad_aduana,
        '_uuid': uuid,
        '_metodo_pago_raw': metodo_pago,
    }
