"""Diagnóstico de conciliación para un cliente específico.

Uso:
    python manage.py diagnosticar_conciliacion_cliente "PRODUCTOS BGA"
    python manage.py diagnosticar_conciliacion_cliente --cliente-id 123
"""
import json
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from catalogo.models import Sucursal
from ventas.models import Cliente, DocumentoCFDI, PagoVenta, Ventas
from ventas.services.conciliacion_service import conciliacion_cliente


class Command(BaseCommand):
    help = 'Imprime diagnóstico de conciliación de un cliente.'

    def add_arguments(self, parser):
        parser.add_argument('nombre', nargs='?', type=str, help='Nombre (o parte) del cliente')
        parser.add_argument('--cliente-id', type=int, help='ID exacto del cliente')
        parser.add_argument('--sucursal-id', type=int, help='Filtrar por sucursal')

    def handle(self, *args, **options):
        if options['cliente_id']:
            cliente = Cliente.objects.filter(pk=options['cliente_id']).first()
        elif options['nombre']:
            clientes = list(Cliente.objects.filter(nombre__icontains=options['nombre']))
            if len(clientes) > 1:
                self.stdout.write(self.style.WARNING(
                    f'Se encontraron {len(clientes)} clientes:'
                ))
                for c in clientes:
                    self.stdout.write(f'  {c.id}: {c.nombre}')
                return
            if not clientes:
                raise CommandError('No se encontró ningún cliente con ese nombre.')
            cliente = clientes[0]
        else:
            raise CommandError('Proporciona un nombre o --cliente-id.')

        self.stdout.write(self.style.NOTICE(f'Cliente: {cliente.id} - {cliente.nombre}'))

        fila = conciliacion_cliente(cliente, sucursal_id=options.get('sucursal_id'))
        self.stdout.write('\nResumen de conciliación:')
        self.stdout.write(json.dumps(fila['detalle'], indent=2, default=str))
        self.stdout.write(f"Saldo por moneda: {fila['saldo_por_moneda']}")
        self.stdout.write(f"Documentos sin venta: {fila['documentos_sin_venta']}")

        self.stdout.write('\n--- Ventas ---')
        ventas_qs = Ventas.objects.filter(cliente=cliente)
        if options.get('sucursal_id'):
            ventas_qs = ventas_qs.filter(sucursal_id=options['sucursal_id'])
        for v in ventas_qs.order_by('pk'):
            pagos = list(v.pagos.all())
            pagos_str = ', '.join(
                f'PV#{p.pk} {p.monto_pago} ({p.fecha_pago}, uuid_rep={p.uuid_rep or "-"})'
                for p in pagos
            ) or 'sin pagos'
            self.stdout.write(
                f'  Venta #{v.pk} {v.referencia or "-"} | '
                f'sucursal={v.sucursal_id.nombre if v.sucursal_id else "-"} | '
                f'modalidad={v.modalidad_pago} | monto={v.monto} | '
                f'pagado={v.monto_pagado} | pagos=[{pagos_str}]'
            )

        self.stdout.write('\n--- Documentos CFDI ---')
        docs_qs = DocumentoCFDI.objects.filter(cliente=cliente, estado='VIGENTE')
        if options.get('sucursal_id'):
            docs_qs = docs_qs.filter(venta__sucursal_id=options['sucursal_id'])
        for d in docs_qs.order_by('subtipo', 'pk'):
            self.stdout.write(
                f'  Doc #{d.pk} {d.subtipo} | folio={d.folio or "-"} | '
                f'uuid={d.uuid or "-"} | monto={d.monto} | '
                f'venta_id={d.venta_id or "-"} | pago_venta_id={d.pago_venta_id or "-"}'
            )
            if d.subtipo == 'recibo_pago' and d.detalle_complemento:
                detalle = d.detalle_complemento
                pagos = detalle.get('pagos') if isinstance(detalle, dict) else None
                if isinstance(pagos, list):
                    for pago in pagos:
                        for docto in (pago.get('doctos') or []):
                            self.stdout.write(
                                f'      DoctoRelacionado: '
                                f'uuid={docto.get("uuid") or "-"} | '
                                f'imp_pagado={docto.get("imp_pagado") or "-"} | '
                                f'saldo_anterior={docto.get("saldo_anterior") or "-"} | '
                                f'saldo_insoluto={docto.get("saldo_insoluto") or "-"}'
                            )

        self.stdout.write('\n--- Desglose Cobros contado / sin REP ---')
        for moneda, items in fila['cobros_contado_desglose'].items():
            for item in items:
                self.stdout.write(
                    f'  {moneda} | venta=#{item["venta_id"]} | '
                    f'tipo={item["tipo"]} | monto={item["monto"]} | '
                    f'monto_operativo={item.get("monto_operativo")} | '
                    f'rep_aplicado={item.get("rep_aplicado")} | '
                    f'saldo_insoluto_rep={item.get("saldo_insoluto_rep")}'
                )
