"""Completa detalle REP histórico y vínculos demostrables por UUID exacto."""
from collections import Counter

from django.core.management.base import BaseCommand

from ventas.cfdi_parser import parse_cfdi
from ventas.models import DocumentoCFDI
from ventas.services.cfdi_import_service import (
    _documentos_docto_pertenecen_al_cliente,
    _resolver_cfdi_relacionado,
    _resolver_documentos_doctos,
    _resolver_pago_venta_exacto,
    _serializar_detalle_complemento,
)


class Command(BaseCommand):
    help = (
        'Completa el detalle de REP desde el XML almacenado y vincula pagos '
        'solo por UUID exacto.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--cliente-id', type=int)
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        documentos = DocumentoCFDI.objects.filter(
            subtipo=DocumentoCFDI.SubtipoDocumento.RECIBO_PAGO,
        ).select_related('cliente', 'venta').order_by('pk')
        if options.get('cliente_id'):
            documentos = documentos.filter(cliente_id=options['cliente_id'])

        dry_run = options.get('dry_run', False)
        conteo = Counter()
        for documento in documentos.iterator():
            conteo['procesados'] += 1
            cambios = {}
            parsed = None
            archivo = documento.archivo_xml
            existe_xml = bool(archivo and archivo.name)

            if existe_xml:
                try:
                    existe_xml = archivo.storage.exists(archivo.name)
                except (OSError, ValueError):
                    existe_xml = False

            if existe_xml:
                try:
                    with archivo.open('rb') as xml_file:
                        parsed = parse_cfdi(xml_file.read())
                except Exception as exc:
                    conteo['xml_con_error'] += 1
                    self.stderr.write(
                        f'XML inválido para DocumentoCFDI {documento.pk}: {exc}'
                    )
            else:
                conteo['xml_faltante'] += 1

            detalle = None
            uuid_rep = documento.uuid

            if existe_xml and parsed is None:
                pago, estado_pago = None, 'xml_con_error'
            elif parsed is not None:
                uuid_xml = (parsed.get('uuid') or '').strip()
                uuid_documento = (documento.uuid or '').strip()
                if not uuid_xml:
                    conteo['uuid_xml_ausente'] += 1
                    pago, estado_pago = None, 'uuid_xml_ausente'
                elif not uuid_documento or \
                        uuid_documento.upper() != uuid_xml.upper():
                    conteo['uuid_xml_discordante'] += 1
                    pago, estado_pago = None, 'uuid_xml_discordante'
                else:
                    uuid_rep = uuid_xml
                    detalle = _serializar_detalle_complemento(parsed)
                    _referencias, documentos_docto, pendientes_docto, ventas_docto = (
                        _resolver_documentos_doctos(parsed)
                    )
                    venta_resuelta = None
                    if not _documentos_docto_pertenecen_al_cliente(
                        documentos_docto, documento.cliente
                    ) or (
                        documento.venta_id
                        and documento.venta.cliente_id != documento.cliente_id
                    ):
                        estado = 'cliente_documento_discordante'
                    elif len(ventas_docto) > 1:
                        estado = 'multiples_ventas_revision'
                    elif pendientes_docto:
                        estado = 'uuid_documento_no_encontrado'
                        conteo['uuid_sin_coincidencia'] += sum(
                            pendiente['estado'] == 'no_encontrado'
                            for pendiente in pendientes_docto
                        )
                        conteo['uuid_duplicado'] += sum(
                            pendiente['estado'] == 'ambiguo'
                            for pendiente in pendientes_docto
                        )
                    elif len(ventas_docto) == 1:
                        venta_resuelta = ventas_docto[0]
                        if documento.venta_id and \
                                documento.venta_id != venta_resuelta.pk:
                            conteo['venta_discordante'] += 1
                            estado = 'venta_documento_discordante'
                        else:
                            if not documento.venta_id:
                                cambios['venta'] = venta_resuelta
                            estado = None
                    else:
                        estado = 'venta_no_resuelta'

                    relacionado = _resolver_cfdi_relacionado(
                        parsed, cliente=documento.cliente,
                    )
                    if relacionado and not documento.cfdi_relacionado_id:
                        cambios['cfdi_relacionado'] = relacionado

                    if estado is not None:
                        pago, estado_pago = None, estado
                    else:
                        pago, estado_pago = _resolver_pago_venta_exacto(
                            uuid_rep,
                            venta_resuelta or documento.venta,
                        )
            elif documento.venta_id and \
                    documento.venta.cliente_id != documento.cliente_id:
                pago, estado_pago = None, 'cliente_documento_discordante'
            else:
                pago, estado_pago = _resolver_pago_venta_exacto(
                    uuid_rep, documento.venta,
                )

            if documento.pago_venta_id:
                estado_pago = 'ya_vinculado'
            elif pago is not None:
                cambios['pago_venta'] = pago
                conteo['vinculos_exactos'] += 1
            elif estado_pago == 'no_encontrado':
                conteo['uuid_sin_coincidencia'] += 1
            elif estado_pago == 'ambiguo':
                conteo['uuid_duplicado'] += 1
            elif estado_pago == 'otra_venta':
                conteo['coincidencia_otra_venta'] += 1
            elif estado_pago == 'cliente_documento_discordante':
                conteo['cliente_discordante'] += 1

            if detalle is not None:
                detalle['vinculo_pago'] = {
                    'estado': estado_pago,
                    'uuid_rep': uuid_rep or '',
                }
                cambios['detalle_complemento'] = detalle

            if cambios:
                conteo['con_cambios'] += 1
                if not dry_run:
                    for campo, valor in cambios.items():
                        setattr(documento, campo, valor)
                    documento.save(update_fields=list(cambios))
                    conteo['actualizados'] += 1

        modo = 'DRY-RUN' if dry_run else 'Aplicado'
        self.stdout.write(
            f'{modo}: {conteo["procesados"]} REP procesados; '
            f'{conteo["con_cambios"]} con cambios; '
            f'{conteo["actualizados"]} actualizados; '
            f'{conteo["xml_faltante"]} XML faltantes; '
            f'{conteo["xml_con_error"]} XML con error; '
            f'{conteo["uuid_sin_coincidencia"]} UUID sin coincidencia; '
            f'{conteo["uuid_duplicado"]} UUID duplicados; '
            f'{conteo["uuid_xml_discordante"]} UUID XML discordantes; '
            f'{conteo["uuid_xml_ausente"]} UUID XML ausentes; '
            f'{conteo["cliente_discordante"]} documentos de otro cliente; '
            f'{conteo["coincidencia_otra_venta"]} coincidencias de otra venta.'
        )
