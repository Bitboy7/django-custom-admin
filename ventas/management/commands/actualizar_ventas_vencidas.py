"""
Management command: actualizar_ventas_vencidas
Marca como 'Vencido' todas las ventas a crédito cuya fecha_vencimiento ya pasó
y cuyo estado_cobranza sigue en 'Pendiente' o 'Parcial'.

Uso:
    python manage.py actualizar_ventas_vencidas
    python manage.py actualizar_ventas_vencidas --dry-run
"""
from datetime import date

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings

from ventas.models import Ventas, ConfiguracionCuentasPorCobrar


class Command(BaseCommand):
    help = "Marca como Vencidas las ventas a crédito con fecha_vencimiento pasada."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra cuántas ventas se afectarían sin aplicar cambios.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        hoy = date.today()

        qs = Ventas.objects.filter(
            modalidad_pago='Credito',
            estado_cobranza__in=['Pendiente', 'Parcial'],
            fecha_vencimiento__lt=hoy,
        )

        count = qs.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No hay ventas para marcar como Vencidas."))
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"[DRY-RUN] {count} venta(s) serían marcadas como Vencidas.")
            )
            return

        # Guardar IDs antes del update para sincronizar SaldoCliente después
        ids_a_actualizar = list(qs.values_list('id', flat=True))

        updated = qs.update(estado_cobranza='Vencido')

        # Sincronizar SaldoCliente para que refleje el nuevo estado
        try:
            from ventas.models import SaldoCliente
            SaldoCliente.objects.filter(venta_id__in=ids_a_actualizar).update(estado='VENCIDO')
        except Exception:
            pass  # No detener el proceso si falla la sincronización

        self.stdout.write(self.style.SUCCESS(f"{updated} venta(s) marcadas como Vencidas."))

        # Registro en auditoria
        try:
            from auditoria.models import LogActividad
            LogActividad.objects.create(
                nombre_usuario='sistema',
                tipo_accion='update',
                descripcion=f'Comando actualizar_ventas_vencidas: {updated} ventas marcadas como Vencidas.',
                modelo_afectado='Ventas',
                campos_modificados={'estado_cobranza': 'Vencido', 'cantidad': updated},
            )
        except Exception:
            pass  # No interrumpir el flujo si falla la auditoría

        # Notificación por email si está configurada
        try:
            config = ConfiguracionCuentasPorCobrar.obtener_configuracion()
            if config.enviar_alertas_vencimiento and config.email_responsable_cobranza:
                send_mail(
                    subject=f'[Cobranza] {updated} ventas marcadas como Vencidas — {hoy}',
                    message=(
                        f'El comando actualizar_ventas_vencidas marcó {updated} venta(s) '
                        f'como Vencidas el {hoy}.\n\n'
                        'Revisa el módulo de Cobranza para más detalles.'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[config.email_responsable_cobranza],
                    fail_silently=True,
                )
        except Exception:
            pass
