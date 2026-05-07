"""
ventas/signals.py

Señales Django para automatizar el ciclo de vida de cuentas por cobrar.

- post_save Ventas  → crea SaldoCliente al registrar venta a crédito nueva;
                      sincroniza saldo en actualizaciones.
- post_save PagoVenta → ya manejado en PagoVenta.save() mediante
                        actualizar_estado_cobranza() → _sync_saldo_cxc().
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='ventas.Ventas')
def auto_sincronizar_saldo_cliente(sender, instance, created, **kwargs):
    """
    RF1: Crea SaldoCliente automáticamente al registrar una venta a crédito nueva.
    En actualizaciones sincroniza el registro existente (saldo, estado, fechas).

    No llama a instance.save() para evitar recursión.
    """
    from .models import Ventas, SaldoCliente

    if instance.modalidad_pago != Ventas.ModalidadPago.CREDITO:
        return

    try:
        if created:
            # Solo crear si la venta tiene fecha de vencimiento calculada
            if not instance.fecha_vencimiento:
                logger.warning(
                    "Venta a crédito %s creada sin fecha_vencimiento; "
                    "SaldoCliente no creado automáticamente.",
                    instance.pk,
                )
                return

            saldo, fue_creado = SaldoCliente.objects.get_or_create(
                venta=instance,
                defaults={
                    'cliente': instance.cliente,
                    'monto_original': instance.monto,
                    'saldo_pendiente': instance.monto,
                    'fecha_vencimiento': instance.fecha_vencimiento,
                    'moneda': instance.moneda_venta or 'MXN',
                    'estado': SaldoCliente.EstadosSaldo.PENDIENTE,
                },
            )
            if fue_creado:
                logger.info(
                    "SaldoCliente %s creado automáticamente para venta %s (cliente: %s).",
                    saldo.pk, instance.pk, instance.cliente_id,
                )
        else:
            # Sincronizar SaldoCliente si existe (no lanza excepción si no existe)
            instance._sync_saldo_cxc()

    except Exception:
        logger.exception(
            "auto_sincronizar_saldo_cliente: error inesperado para venta %s.", instance.pk
        )
