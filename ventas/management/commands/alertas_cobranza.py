"""
Management command: alertas_cobranza
Envía un email de alerta agrupado por cliente para las ventas a crédito
que vencen dentro de los próximos N días (configurado en ConfiguracionCuentasPorCobrar).

Uso:
    python manage.py alertas_cobranza
    python manage.py alertas_cobranza --dry-run
"""
from datetime import date, timedelta
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings

from ventas.models import Ventas, ConfiguracionCuentasPorCobrar


class Command(BaseCommand):
    help = "Envía alertas de vencimiento próximo a créditos pendientes."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra las ventas que recibirían alerta sin enviar emails.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        config = ConfiguracionCuentasPorCobrar.obtener_configuracion()

        if not config.enviar_alertas_vencimiento:
            self.stdout.write("Las alertas de vencimiento están desactivadas en la configuración.")
            return

        if not config.email_responsable_cobranza:
            self.stderr.write("No hay email_responsable_cobranza configurado.")
            return

        hoy = date.today()
        limite = hoy + timedelta(days=config.dias_previos_alerta)

        qs = Ventas.objects.filter(
            modalidad_pago='Credito',
            estado_cobranza='Pendiente',
            fecha_vencimiento__gte=hoy,
            fecha_vencimiento__lte=limite,
        ).select_related('cliente')

        if not qs.exists():
            self.stdout.write(self.style.SUCCESS("No hay ventas próximas a vencer."))
            return

        # Agrupar por cliente
        por_cliente = defaultdict(list)
        for venta in qs:
            por_cliente[venta.cliente].append(venta)

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"[DRY-RUN] {qs.count()} venta(s) de {len(por_cliente)} cliente(s) "
                f"vencen en los próximos {config.dias_previos_alerta} días."
            ))
            for cliente, ventas in por_cliente.items():
                for v in ventas:
                    self.stdout.write(f"  - {cliente} | Folio {v.id} | Vence {v.fecha_vencimiento} | ${v.monto.amount}")
            return

        # Construir cuerpo del email
        lineas = [
            f"Ventas a crédito que vencen en los próximos {config.dias_previos_alerta} días:\n",
            f"Fecha de reporte: {hoy}\n",
            "-" * 60,
        ]
        for cliente, ventas in por_cliente.items():
            lineas.append(f"\nCliente: {cliente}")
            for v in ventas:
                dias_restantes = (v.fecha_vencimiento - hoy).days
                lineas.append(
                    f"  • Folio {v.id} | Vence {v.fecha_vencimiento} "
                    f"({dias_restantes} días) | ${v.monto.amount:.2f}"
                )

        cuerpo = "\n".join(lineas)

        send_mail(
            subject=(
                f"[Cobranza] {qs.count()} venta(s) próximas a vencer — {hoy}"
            ),
            message=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[config.email_responsable_cobranza],
            fail_silently=False,
        )

        self.stdout.write(self.style.SUCCESS(
            f"Alerta enviada: {qs.count()} venta(s) de {len(por_cliente)} cliente(s)."
        ))

        # Registro en auditoria
        try:
            from auditoria.models import LogActividad
            LogActividad.objects.create(
                nombre_usuario='sistema',
                tipo_accion='other',
                descripcion=(
                    f'Alerta cobranza enviada a {config.email_responsable_cobranza}: '
                    f'{qs.count()} ventas próximas a vencer.'
                ),
                modelo_afectado='Ventas',
                campos_modificados={'cantidad': qs.count(), 'dias_alerta': config.dias_previos_alerta},
            )
        except Exception:
            pass
