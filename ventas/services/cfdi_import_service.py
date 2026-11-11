"""
Servicio de importación de CFDI (3.3/4.0) → registros de negocio.

Mapea un CFDI parseado y clasificado a los modelos Ventas / Anticipo /
PagoVenta / DocumentoCFDI, conforme a la taxonomía del cliente:

  - Venta Nacional / Exportación   → Ventas + DocumentoCFDI (producto)
  - Ingreso por servicio           → Ventas sin producto + DocumentoCFDI
  - Nota de Cargo                  → DocumentoCFDI (ingreso, suma saldo)
  - Remanente de Anticipo          → Anticipo + DocumentoCFDI (saldo a favor)
  - Nota de Crédito                → DocumentoCFDI (egreso, resta saldo)
  - Recibo Electrónico de Pago     → PagoVenta + DocumentoCFDI (resta saldo)
"""
import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from djmoney.money import Money

from ..cfdi_parser import classify_naturaleza_conceptos, classify_subtipo
from ..models import Anticipo, Cliente, DocumentoCFDI, PagoVenta, Producto, Ventas


RFC_GENERICOS = {
    Cliente.RFC_GENERICO_NACIONAL,
    Cliente.RFC_GENERICO_EXTRANJERO,
    'X',
}

PAISES_ISO3_A_ISO2 = {
    'MEX': 'MX',
    'USA': 'US',
    'CAN': 'CA',
}

NOMBRES_PAIS = {
    'MEX': ('México', 'Mexico'),
    'USA': ('Estados Unidos', 'United States'),
    'CAN': ('Canadá', 'Canada'),
}


def _normalizar_identificador(valor):
    return re.sub(r'[^A-Z0-9]', '', (valor or '').strip().upper())


def parsed_to_json(parsed):
    """Serializa un CFDI parseado a JSON (Decimal/date/datetime seguros)."""

    def conv(obj):
        if isinstance(obj, Decimal):
            return {'__decimal__': str(obj)}
        if isinstance(obj, datetime):
            return {'__datetime__': obj.isoformat()}
        if isinstance(obj, date):
            return {'__date__': obj.isoformat()}
        if isinstance(obj, (list, tuple)):
            return [conv(i) for i in obj]
        if isinstance(obj, dict):
            return {k: conv(v) for k, v in obj.items()}
        return obj

    return json.dumps(conv(parsed))


def parsed_from_json(data):
    """Reconstruye un CFDI parseado desde el JSON de parsed_to_json."""

    def conv(obj):
        if isinstance(obj, dict):
            if '__decimal__' in obj:
                return Decimal(obj['__decimal__'])
            if '__datetime__' in obj:
                return datetime.fromisoformat(obj['__datetime__'])
            if '__date__' in obj:
                return date.fromisoformat(obj['__date__'])
            return {k: conv(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [conv(i) for i in obj]
        return obj

    return conv(json.loads(data))


def match_cliente(parsed):
    """Busca al receptor por su identidad fiscal y después por razón social."""
    nombre = (parsed.get('_receptor_nombre') or '').strip()
    rfc = _normalizar_identificador(parsed.get('_receptor_rfc'))
    residencia = _normalizar_identificador(
        parsed.get('_receptor_residencia_fiscal')
    )
    registro_extranjero = _normalizar_identificador(
        parsed.get('_receptor_num_reg_id_trib')
    )

    if rfc and rfc not in RFC_GENERICOS:
        cliente = Cliente.objects.filter(rfc__iexact=rfc, activo=True).first()
        if cliente:
            return cliente

    if residencia and registro_extranjero:
        cliente = Cliente.objects.filter(
            residencia_fiscal__iexact=residencia,
            numero_registro_fiscal__iexact=registro_extranjero,
            activo=True,
        ).first()
        if cliente:
            return cliente

    if not nombre:
        return None

    qs = Cliente.objects.filter(nombre__iexact=nombre, activo=True)
    if qs.exists():
        return qs.first()

    words = [w for w in nombre.split() if len(w) > 3]
    for word in words:
        qs = Cliente.objects.filter(nombre__icontains=word, activo=True)
        if qs.count() == 1:
            return qs.first()
    return None


def sugerir_pais(parsed):
    """Sugiere un Pais del catálogo usando residencia fiscal o tipo de RFC."""
    from catalogo.models import Pais

    residencia = _normalizar_identificador(
        parsed.get('_receptor_residencia_fiscal')
    )
    rfc = _normalizar_identificador(parsed.get('_receptor_rfc'))

    codigo = residencia
    if not codigo and rfc != Cliente.RFC_GENERICO_EXTRANJERO:
        codigo = 'MEX'
    if not codigo:
        return None

    codigos = [codigo]
    if PAISES_ISO3_A_ISO2.get(codigo):
        codigos.append(PAISES_ISO3_A_ISO2[codigo])
    pais = Pais.objects.filter(siglas__in=codigos).first()
    if pais:
        return pais

    for nombre in NOMBRES_PAIS.get(codigo, ()):
        pais = Pais.objects.filter(nombre__iexact=nombre).first()
        if pais:
            return pais
    return None


@transaction.atomic
def crear_cliente_desde_cfdi(parsed, *, pais):
    """Crea de forma explícita un cliente contado con los datos del receptor."""
    nombre = (parsed.get('_receptor_nombre') or '').strip()
    if not nombre:
        raise ValueError('El CFDI no contiene la razón social del receptor.')
    if pais is None:
        raise ValueError('Selecciona el país del cliente antes de crearlo.')

    existente = match_cliente(parsed)
    if existente:
        return existente, False

    rfc = _normalizar_identificador(parsed.get('_receptor_rfc')) or None
    residencia = _normalizar_identificador(
        parsed.get('_receptor_residencia_fiscal')
    ) or None
    registro_extranjero = _normalizar_identificador(
        parsed.get('_receptor_num_reg_id_trib')
    ) or None

    # No dupliques identidades fiscales inactivas de forma silenciosa.
    if rfc and rfc not in RFC_GENERICOS:
        inactivo = Cliente.objects.filter(rfc__iexact=rfc, activo=False).first()
        if inactivo:
            raise ValueError(
                f'El cliente {inactivo.nombre} ya existe con ese RFC, pero está inactivo.'
            )
    if residencia and registro_extranjero:
        inactivo = Cliente.objects.filter(
            residencia_fiscal__iexact=residencia,
            numero_registro_fiscal__iexact=registro_extranjero,
            activo=False,
        ).first()
        if inactivo:
            raise ValueError(
                f'El cliente {inactivo.nombre} ya existe con ese registro fiscal, pero está inactivo.'
            )

    cliente = Cliente(
        nombre=nombre[:200],
        pais=pais,
        rfc=rfc,
        residencia_fiscal=residencia,
        numero_registro_fiscal=registro_extranjero,
        codigo_postal_fiscal=(
            parsed.get('_receptor_domicilio_fiscal') or ''
        ).strip()[:12] or None,
        regimen_fiscal=(
            parsed.get('_receptor_regimen_fiscal') or ''
        ).strip()[:3] or None,
        tipo_cliente=Cliente.TipoCliente.CONTADO,
        correo=None,
        activo=True,
    )
    cliente.full_clean()
    cliente.save()
    return cliente, True


def actualizar_datos_fiscales_cliente(cliente, parsed):
    """Completa únicamente datos fiscales vacíos de un cliente confirmado."""
    valores = {
        'rfc': _normalizar_identificador(parsed.get('_receptor_rfc')) or None,
        'residencia_fiscal': _normalizar_identificador(
            parsed.get('_receptor_residencia_fiscal')
        ) or None,
        'numero_registro_fiscal': _normalizar_identificador(
            parsed.get('_receptor_num_reg_id_trib')
        ) or None,
        'codigo_postal_fiscal': (
            parsed.get('_receptor_domicilio_fiscal') or ''
        ).strip()[:12] or None,
        'regimen_fiscal': (
            parsed.get('_receptor_regimen_fiscal') or ''
        ).strip()[:3] or None,
    }
    modificados = []
    for campo, valor in valores.items():
        if valor and not getattr(cliente, campo):
            setattr(cliente, campo, valor)
            modificados.append(campo)
    if modificados:
        cliente.save(update_fields=modificados)
    return modificados


def match_producto(parsed):
    """Busca el producto más probable según descripción / NoIdentificacion."""
    if classify_naturaleza_conceptos(parsed) != 'producto':
        return None
    conceptos = parsed.get('conceptos') or []
    descripciones = [parsed.get('descripcion') or '']
    descripciones.extend(c.get('descripcion') or '' for c in conceptos)
    identificadores = [parsed.get('_no_identificacion') or '']
    identificadores.extend(c.get('no_identificacion') or '' for c in conceptos)
    fraccion = parsed.get('_fraccion_arancelaria') or ''
    productos = list(
        Producto.objects.filter(disponible=True).order_by('variedad')
    )

    for identificador in identificadores:
        identificador = identificador.strip().lower()
        if not identificador:
            continue
        for p in productos:
            valores = (p.variedad or '', p.nombre or '', p.descripcion or '')
            if any(identificador in valor.lower() for valor in valores):
                return p

    for descripcion in descripciones:
        descripcion_normalizada = descripcion.strip().lower()
        if not descripcion_normalizada:
            continue
        palabras_descripcion = set(re.findall(r'[a-záéíóúñ0-9]+', descripcion_normalizada))
        for p in productos:
            variedad = (p.variedad or '').strip().lower()
            nombre = (p.nombre or '').strip().lower()
            if (variedad and variedad in descripcion_normalizada) or (
                nombre and nombre in descripcion_normalizada
            ):
                return p
            palabras_variedad = {
                palabra for palabra in re.findall(r'[a-záéíóúñ0-9]+', variedad)
                if len(palabra) >= 4
            }
            if palabras_variedad & palabras_descripcion:
                return p

    if fraccion:
        return Producto.objects.filter(nombre__icontains='Mango').first()
    return None


def sugerir_producto_desde_cfdi(parsed):
    """Obtiene una propuesta de catálogo cuando el CFDI contiene un solo producto.

    Una venta puede incluir varios renglones del mismo producto (por ejemplo,
    distintas cantidades de Soya). En ese caso se conserva una sola propuesta.
    Si hay descripciones diferentes, no se adivina cuál debería representar a
    toda la venta porque el modelo ``Ventas`` admite un único producto.
    """
    if classify_naturaleza_conceptos(parsed) != 'producto':
        return None

    conceptos = parsed.get('conceptos') or []
    if not conceptos:
        conceptos = [{
            'descripcion': parsed.get('descripcion') or '',
            'clave_prod_serv': parsed.get('_clave_prod_serv') or '',
            'no_identificacion': parsed.get('_no_identificacion') or '',
            'clave_unidad': '',
        }]

    conceptos_validos = []
    descripciones = set()
    for concepto in conceptos:
        descripcion = re.sub(
            r'\s+', ' ', (concepto.get('descripcion') or '').strip()
        )
        if not descripcion:
            continue
        conceptos_validos.append((concepto, descripcion))
        descripciones.add(descripcion.casefold())

    if not conceptos_validos or len(descripciones) != 1:
        return None

    concepto, descripcion = conceptos_validos[0]
    return {
        'nombre': descripcion[:100],
        'variedad': descripcion[:50],
        'clave_sat': (concepto.get('clave_prod_serv') or '').strip(),
        'no_identificacion': (
            concepto.get('no_identificacion') or ''
        ).strip(),
        'clave_unidad': (concepto.get('clave_unidad') or '').strip(),
    }


@transaction.atomic
def crear_producto_desde_cfdi(parsed):
    """Crea explícitamente un producto disponible a partir del concepto CFDI."""
    existente = match_producto(parsed)
    if existente:
        return existente, False

    sugerencia = sugerir_producto_desde_cfdi(parsed)
    if sugerencia is None:
        raise ValueError(
            'El CFDI contiene varios productos o no incluye una descripción '
            'suficiente. Selecciona un producto del catálogo.'
        )

    existente = Producto.objects.filter(
        disponible=True,
        variedad__iexact=sugerencia['variedad'],
    ).first()
    if existente:
        return existente, False

    inactivo = Producto.objects.filter(
        variedad__iexact=sugerencia['variedad'],
        disponible=False,
    ).first()
    if inactivo:
        raise ValueError(
            f'El producto {inactivo.variedad} ya existe, pero no está disponible.'
        )

    metadatos = ['Creado desde CFDI.']
    if sugerencia['clave_sat']:
        metadatos.append(f"Clave SAT: {sugerencia['clave_sat']}.")
    if sugerencia['no_identificacion']:
        metadatos.append(
            f"No. identificación: {sugerencia['no_identificacion']}."
        )
    if sugerencia['clave_unidad']:
        metadatos.append(f"Unidad SAT: {sugerencia['clave_unidad']}.")

    producto = Producto(
        nombre=sugerencia['nombre'],
        variedad=sugerencia['variedad'],
        precio_unitario=0,
        disponible=True,
        descripcion=' '.join(metadatos),
    )
    producto.full_clean()
    producto.save()
    return producto, True


def resolver_venta(parsed):
    """Resuelve la venta padre a partir de los UUIDs relacionados."""
    relacionados = parsed.get('relacionados') or []
    if not relacionados:
        return None
    doc = DocumentoCFDI.objects.filter(
        uuid__in=relacionados, venta__isnull=False
    ).select_related('venta').first()
    return doc.venta if doc else None


def resolver_documentos_relacionados(uuids):
    """Resuelve documentos solo por UUID completo y separa los pendientes."""
    resueltos = {}
    pendientes = []
    vistos = set()

    for valor in (uuids or []):
        uuid = str(valor or '').strip()
        clave = uuid.upper()
        if not uuid or clave in vistos:
            continue
        vistos.add(clave)

        documentos = list(
            DocumentoCFDI.objects.filter(uuid__iexact=uuid).order_by('pk')
        )
        if len(documentos) == 1:
            resueltos[clave] = documentos[0]
        else:
            pendientes.append({
                'uuid': uuid,
                'estado': 'ambiguo' if documentos else 'no_encontrado',
            })

    return resueltos, pendientes


def _uuids_cfdi_relacionados(parsed):
    """Devuelve solo UUIDs provenientes del bloque CfdiRelacionados."""
    if 'relacionados_cfdi' in parsed:
        return parsed.get('relacionados_cfdi') or []
    # Compatibilidad con datos parseados antes de separar los UUID fiscales de
    # los IdDocumento usados por Pagos 2.0.
    if parsed.get('tipo_relacion'):
        return parsed.get('relacionados') or []
    return []


def _resolver_documentos_doctos(parsed):
    """Resuelve por UUID las facturas indicadas en los DoctoRelacionado."""
    uuids = [
        docto.get('uuid')
        for pago in (parsed.get('pagos') or [])
        for docto in (pago.get('doctos') or [])
        if docto.get('uuid')
    ]
    resueltos, pendientes = resolver_documentos_relacionados(uuids)
    documentos = list({doc.pk: doc for doc in resueltos.values()}.values())
    ventas = list({
        doc.venta_id: doc.venta
        for doc in documentos
        if doc.venta_id and doc.venta
    }.values())
    return uuids, documentos, pendientes, ventas


def _documentos_docto_pertenecen_al_cliente(documentos, cliente):
    return all(
        documento.cliente_id == cliente.pk
        and (
            not documento.venta_id
            or documento.venta.cliente_id == cliente.pk
        )
        for documento in documentos
    )


def _resolver_cfdi_relacionado(parsed, cliente=None):
    """Resuelve la FK fiscal solo desde UUIDs explícitos del comprobante."""
    uuids = _uuids_cfdi_relacionados(parsed)
    if not uuids:
        return None
    resueltos, pendientes = resolver_documentos_relacionados(uuids)
    if pendientes or len(resueltos) != 1:
        return None
    relacionado = next(iter(resueltos.values()))
    if cliente and not _documentos_docto_pertenecen_al_cliente(
        [relacionado], cliente
    ):
        return None
    return relacionado


def _resolver_pago_venta_exacto(uuid_rep, venta):
    """Busca un PagoVenta único por UUID REP y valida que sea de la misma Venta."""
    if not uuid_rep:
        return None, 'uuid_ausente'

    pagos = list(
        PagoVenta.objects.filter(uuid_rep__iexact=str(uuid_rep).strip())
        .select_related('venta')
        .order_by('pk')
    )
    if len(pagos) > 1:
        return None, 'ambiguo'
    if not pagos:
        return None, 'no_encontrado'
    if venta is None:
        return None, 'venta_no_resuelta'

    pago = pagos[0]
    if pago.venta_id != venta.pk:
        return None, 'otra_venta'
    if DocumentoCFDI.objects.filter(pago_venta_id=pago.pk).exists():
        return None, 'ya_vinculado'
    return pago, 'uuid_coincidente'


def _monto_recibo(parsed):
    """Monto total pagado en un recibo electrónico de pago."""
    pagos = parsed.get('pagos') or []
    if pagos and pagos[0].get('monto'):
        return Decimal(str(pagos[0]['monto']))
    return Decimal(str(parsed.get('monto') or 0))


def _moneda_recibo(parsed):
    """Moneda real de un recibo electrónico de pago (MonedaP)."""
    pagos = parsed.get('pagos') or []
    if pagos and pagos[0].get('moneda'):
        return pagos[0]['moneda']
    return parsed.get('moneda_venta') or 'MXN'


def _tipo_cambio_recibo(parsed, venta, moneda):
    """Tipo de cambio (MXN por unidad) de un recibo electrónico de pago.

    Prioridad: ``TipoCambioP`` del complemento, luego el tipo de cambio del
    CFDI/venta y, por último, 1.0 (pagos en pesos). Así el equivalente MXN de
    un REP en moneda extranjera no queda subvaluado con el default 1.0.
    """
    if moneda == 'MXN':
        return Decimal('1.0000')

    raw = None
    if parsed.get('pagos'):
        raw = parsed['pagos'][0].get('tipo_cambio')
    raw = raw or parsed.get('tipo_cambio') or (venta.tipo_cambio if venta else None)

    try:
        tipo_cambio = Decimal(str(raw)) if raw not in (None, '') else Decimal('1.0000')
    except (InvalidOperation, ValueError):
        tipo_cambio = Decimal('1.0000')

    if tipo_cambio <= 0:
        tipo_cambio = Decimal('1.0000')
    return tipo_cambio


def _serializar_detalle_complemento(parsed, *, vinculo_pago=None):
    """Normaliza pagos REP a datos JSON sin perder pagos parciales."""
    relacionados = [
        str(uuid) for uuid in _uuids_cfdi_relacionados(parsed) if uuid
    ]
    pagos = []

    for pago in (parsed.get('pagos') or []):
        fecha = pago.get('fecha')
        if isinstance(fecha, (date, datetime)):
            fecha = fecha.isoformat()
        elif fecha is not None:
            fecha = str(fecha)

        doctos = []
        for docto in (pago.get('doctos') or []):
            pagado = docto.get('pagado')
            doctos.append({
                'uuid': docto.get('uuid') or '',
                'saldo_anterior': str(docto.get('saldo_anterior') or ''),
                'imp_pagado': str(pagado if pagado is not None else '0'),
                'saldo_insoluto': str(docto.get('saldo_insoluto') or ''),
                'parcialidad': str(docto.get('parcialidad') or ''),
                'moneda': docto.get('moneda') or '',
                'equivalencia': str(docto.get('equivalencia') or ''),
            })

        monto = pago.get('monto')
        pagos.append({
            'fecha_pago': fecha,
            'monto': str(monto if monto is not None else '0'),
            'moneda': pago.get('moneda') or '',
            'tipo_cambio': str(pago.get('tipo_cambio') or ''),
            'forma': pago.get('forma') or '',
            'num_operacion': pago.get('num_operacion') or '',
            'doctos': doctos,
        })

    detalle = {
        'relacionados': relacionados,
        'tipo_relacion': parsed.get('tipo_relacion') or '',
        'pagos': pagos,
    }
    if vinculo_pago:
        detalle['vinculo_pago'] = vinculo_pago
    return detalle


def crear_documento(parsed, *, cliente, subtipo=None, venta=None,
                    anticipo=None, pago_venta=None, estado='VIGENTE',
                    conceptos=None, archivo_pdf=None, archivo_xml=None,
                    cfdi_relacionado=None, detalle_complemento=None):
    """Crea un DocumentoCFDI a partir de un CFDI parseado."""
    subtipo = subtipo or classify_subtipo(parsed)

    if subtipo == 'recibo_pago':
        tipo = DocumentoCFDI.TipoDocumento.PAGO
    elif subtipo == 'nota_credito':
        tipo = DocumentoCFDI.TipoDocumento.EGRESO
    else:
        tipo = DocumentoCFDI.TipoDocumento.INGRESO

    if subtipo == 'recibo_pago':
        moneda = _moneda_recibo(parsed)
        monto = _monto_recibo(parsed)
    else:
        moneda = parsed.get('moneda_venta') or 'MXN'
        monto = parsed.get('monto') or Decimal('0')
    fecha_timbrado = parsed.get('fecha_timbrado')
    if fecha_timbrado and timezone.is_naive(fecha_timbrado):
        fecha_timbrado = timezone.make_aware(fecha_timbrado)

    if conceptos is None:
        conceptos = parsed.get('conceptos') or []

    folio = parsed.get('folio_num') or parsed.get('folio_factura') or None
    return DocumentoCFDI.objects.create(
        cliente=cliente,
        tipo=tipo,
        subtipo=subtipo,
        serie=parsed.get('serie') or None,
        folio=folio,
        uuid=parsed.get('uuid') or None,
        fecha_emision=parsed.get('fecha_emision_cfdi'),
        fecha_timbrado=fecha_timbrado,
        monto=Money(Decimal(str(monto)), moneda),
        moneda=moneda,
        tipo_cambio=parsed.get('tipo_cambio') or Decimal('1.0000'),
        estado=estado,
        cfdi_relacionado=cfdi_relacionado,
        tipo_relacion=parsed.get('tipo_relacion') or None,
        venta=venta,
        anticipo=anticipo,
        pago_venta=pago_venta,
        conceptos=conceptos,
        detalle_complemento=(
            detalle_complemento
            if detalle_complemento is not None
            else _serializar_detalle_complemento(parsed)
        ),
        archivo_pdf=archivo_pdf,
        archivo_xml=archivo_xml,
    )


def _crear_venta(parsed, cliente, producto, sucursal, cuenta, *,
                 es_servicio=False, termino_credito=None):
    if es_servicio:
        producto = None
    else:
        producto = producto or match_producto(parsed)
    if not es_servicio and producto is None:
        raise ValueError(
            'Selecciona un producto para importar este CFDI como venta.'
        )

    modalidad = parsed.get('modalidad_pago') or 'Contado'

    if sucursal is None:
        raise ValueError('Selecciona la sucursal para importar esta venta.')
    if modalidad == 'Contado' and cuenta is None:
        raise ValueError(
            'Selecciona la cuenta bancaria para esta venta de contado.'
        )

    # El término de crédito solo aplica a ventas a crédito.
    if modalidad != 'Credito':
        termino_credito = None

    fecha = parsed.get('fecha_emision_cfdi') or timezone.now().date()
    moneda = parsed.get('moneda_venta') or 'MXN'
    monto = parsed.get('monto') or Decimal('0')
    cantidad = parsed.get('cantidad') or Decimal('0')

    venta = Ventas.objects.create(
        cliente=cliente,
        sucursal_id=sucursal,
        producto=producto,
        cuenta=cuenta,
        tipo_venta=parsed.get('tipo_venta') or 'Nacional',
        tipo_registro=(
            Ventas.TipoRegistro.SERVICIO
            if es_servicio else Ventas.TipoRegistro.VENTA
        ),
        modalidad_pago=modalidad,
        termino_credito=termino_credito,
        monto=Money(Decimal(str(monto)), moneda),
        moneda_venta=moneda,
        tipo_cambio=parsed.get('tipo_cambio') or Decimal('1.0000'),
        cantidad=cantidad,
        descripcion=parsed.get('descripcion') or '',
        incoterm=parsed.get('incoterm') or None,
        PO=parsed.get('PO') or None,
        fecha_salida_manifiesto=fecha,
        fecha_deposito=fecha,
    )
    return venta


def _crear_anticipo(parsed, cliente, cuenta):
    if cuenta is None:
        raise ValueError('Selecciona la cuenta bancaria para este anticipo.')
    moneda = parsed.get('moneda_venta') or 'MXN'
    monto = parsed.get('monto') or Decimal('0')

    if Decimal(str(monto)) <= 0:
        raise ValueError(
            'No se puede crear un anticipo con monto menor o igual a cero.'
        )

    anticipo = Anticipo.objects.create(
        cliente=cliente,
        cuenta=cuenta,
        monto=Money(Decimal(str(monto)), moneda),
        fecha=parsed.get('fecha_emision_cfdi') or timezone.now().date(),
        descripcion=parsed.get('descripcion') or 'Anticipo / Remanente',
        uuid_cfdi=parsed.get('uuid') or None,
        es_remanente=True,
        estado_anticipo=Anticipo.Estado_anticipo.Pendiente,
    )
    return anticipo


def _crear_recibo_pago(parsed, cliente, cuenta, archivo_pdf=None, archivo_xml=None):
    pagos = parsed.get('pagos') or []
    referencias, documentos_docto, pendientes, ventas = (
        _resolver_documentos_doctos(parsed)
    )
    cliente_discordante = not _documentos_docto_pertenecen_al_cliente(
        documentos_docto, cliente
    )
    venta = (
        ventas[0]
        if len(ventas) == 1 and not pendientes and not cliente_discordante
        else None
    )
    relacionado = _resolver_cfdi_relacionado(parsed, cliente=cliente)

    pago_existente, estado_vinculo = _resolver_pago_venta_exacto(
        parsed.get('uuid'), venta,
    )
    if cliente_discordante:
        estado_vinculo = 'cliente_documento_discordante'
        pago_existente = None
    elif len(ventas) > 1:
        estado_vinculo = 'multiples_ventas_revision'
        pago_existente = None
    elif pendientes:
        estado_vinculo = 'uuid_documento_no_encontrado'
        pago_existente = None
    elif estado_vinculo != 'uuid_coincidente' and len(pagos) > 1:
        estado_vinculo = 'multipago_revision'
    elif estado_vinculo != 'uuid_coincidente' and referencias and venta is None:
        estado_vinculo = 'venta_no_resuelta'

    puede_crear_pago = (
        pago_existente is None
        and len(pagos) == 1
        and len(ventas) == 1
        and not pendientes
        and estado_vinculo == 'no_encontrado'
        and bool(parsed.get('uuid'))
    )
    detalle = _serializar_detalle_complemento(
        parsed,
        vinculo_pago={
            'estado': estado_vinculo,
            'uuid_rep': parsed.get('uuid') or '',
        },
    )

    doc = crear_documento(
        parsed,
        cliente=cliente,
        venta=venta,
        cfdi_relacionado=relacionado,
        detalle_complemento=detalle,
        subtipo='recibo_pago',
        archivo_pdf=archivo_pdf, archivo_xml=archivo_xml,
    )

    if pago_existente:
        doc.pago_venta = pago_existente
        doc.save(update_fields=['pago_venta'])
        return pago_existente, doc

    if puede_crear_pago and venta.modalidad_pago == Ventas.ModalidadPago.CREDITO and \
            venta.estado_cobranza in ('Pendiente', 'Parcial', 'Vencido'):
        saldo = venta.saldo_por_cobrar()
        if saldo > 0:
            monto_pago = min(_monto_recibo(parsed), Decimal(str(saldo)))
            if monto_pago > 0:
                moneda = _moneda_recibo(parsed)
                num_operacion = ''
                fecha_pago = parsed.get('fecha_emision_cfdi') or timezone.now().date()
                if parsed.get('pagos'):
                    primer_pago = parsed['pagos'][0]
                    num_operacion = primer_pago.get('num_operacion') or ''
                    fecha_pago = primer_pago.get('fecha') or fecha_pago
                cuenta_destino = cuenta or venta.cuenta
                if cuenta_destino is None:
                    raise ValueError(
                        'Selecciona la cuenta bancaria para registrar este pago.'
                    )
                pago = PagoVenta.objects.create(
                    venta=venta,
                    fecha_pago=fecha_pago,
                    monto_pago=Money(monto_pago, moneda),
                    tipo_cambio=_tipo_cambio_recibo(parsed, venta, moneda),
                    cuenta_destino=cuenta_destino,
                    metodo_pago=PagoVenta.MetodoPago.TRANSFERENCIA,
                    referencia=num_operacion,
                    folio_rep=parsed.get('folio_num') or None,
                    uuid_rep=parsed.get('uuid') or None,
                )
                doc.pago_venta = pago
                doc.detalle_complemento['vinculo_pago']['estado'] = (
                    'uuid_coincidente'
                )
                doc.save(update_fields=['pago_venta', 'detalle_complemento'])
                return pago, doc

    return None, doc


@transaction.atomic
def importar_cfdi(parsed, *, cliente=None, producto=None, sucursal=None, cuenta=None,
                  archivo_pdf=None, archivo_xml=None, termino_credito=None):
    """
    Importa un CFDI ya parseado y clasificado.

    Retorna (objeto_principal, documento, subtipo).
    """
    subtipo = classify_subtipo(parsed)
    uuid = (parsed.get('uuid') or '').strip()
    existente = (
        DocumentoCFDI.objects.filter(uuid__iexact=uuid).first()
        if uuid else None
    )
    if existente:
        complemento_incompleto = (
            subtipo == 'recibo_pago'
            and existente.subtipo == DocumentoCFDI.SubtipoDocumento.RECIBO_PAGO
            and existente.venta_id is None
            and existente.pago_venta_id is None
            and existente.monto.amount == 0
        )
        if complemento_incompleto:
            # Permite reparar importaciones antiguas que guardaron Pagos 2.0
            # como documentos de monto cero. Si la reparación falla, atomic
            # revierte también esta eliminación.
            existente.delete()
        else:
            raise ValueError(f'El CFDI con UUID {uuid} ya fue importado.')

    cliente = cliente or match_cliente(parsed)

    if cliente is None:
        raise ValueError(
            f"No se pudo identificar el cliente para el CFDI {parsed.get('folio_factura') or parsed.get('uuid')}."
        )

    actualizar_datos_fiscales_cliente(cliente, parsed)

    kwargs_doc = {'archivo_pdf': archivo_pdf, 'archivo_xml': archivo_xml}

    if subtipo in ('venta_nacional', 'venta_exportacion', 'ingreso_servicio'):
        venta = _crear_venta(
            parsed, cliente, producto, sucursal, cuenta,
            es_servicio=subtipo == 'ingreso_servicio',
            termino_credito=termino_credito,
        )
        doc = crear_documento(parsed, cliente=cliente, venta=venta, subtipo=subtipo, **kwargs_doc)
        return venta, doc, subtipo

    if subtipo == 'ingreso_mixto':
        raise ValueError(
            'El CFDI mezcla productos y servicios. Revisa los conceptos y '
            'registra cada operación manualmente antes de vincular el documento.'
        )

    if subtipo in ('nota_cargo', 'nota_credito'):
        venta = resolver_venta(parsed)
        doc = crear_documento(parsed, cliente=cliente, venta=venta, subtipo=subtipo, **kwargs_doc)
        return doc, doc, subtipo

    if subtipo == 'remanente_anticipo':
        monto = Decimal(str(parsed.get('monto') or 0))
        if monto == 0:
            # Un CFDI de aplicacion de anticipo puede quedar en cero cuando el
            # descuento cancela por completo el subtotal. Se conserva como
            # documento fiscal, pero no genera un nuevo saldo a favor.
            doc = crear_documento(
                parsed, cliente=cliente, subtipo=subtipo, **kwargs_doc
            )
            return doc, doc, subtipo
        anticipo = _crear_anticipo(parsed, cliente, cuenta)
        doc = crear_documento(parsed, cliente=cliente, anticipo=anticipo, subtipo=subtipo, **kwargs_doc)
        return anticipo, doc, subtipo

    if subtipo == 'recibo_pago':
        pago, doc = _crear_recibo_pago(parsed, cliente, cuenta, archivo_pdf=archivo_pdf, archivo_xml=archivo_xml)
        return pago, doc, subtipo

    raise ValueError(f'Subtipo no soportado: {subtipo}')
