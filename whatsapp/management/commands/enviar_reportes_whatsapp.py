"""
Comando de gestion para procesar envios automaticos de reportes por WhatsApp.
Debe ejecutarse via cron o scheduler del sistema operativo.

Uso:
    python manage.py enviar_reportes_whatsapp

Ejemplo cron (cada hora):
    0 * * * * cd /ruta/proyecto && python manage.py enviar_reportes_whatsapp >> logs/whatsapp_cron.log 2>&1
"""

import logging
import sys

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Procesa los envios automaticos de reportes por WhatsApp segun la configuracion."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo evalua que se enviaria sin enviar realmente.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Fuerza el envio ignorando si debe ejecutarse hoy.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]

        self.stdout.write(self.style.NOTICE("=== Procesando envios automaticos WhatsApp ==="))

        from whatsapp.services.report_scheduler import procesar_envios_pendientes, debe_ejecutarse_hoy

        if dry_run:
            self.stdout.write(self.style.WARNING("MODO DRY-RUN: no se realizaran envios reales."))
            from whatsapp.models import ConfiguracionWhatsApp

            configs = ConfiguracionWhatsApp.objects.filter(
                activo=True,
                instancia__activo=True,
                enviar_reportes=True,
            ).exclude(frecuencia_envio="manual")

            for config in configs:
                debe = debe_ejecutarse_hoy(config) or force
                self.stdout.write(
                    f"  {config}: debe_ejecutarse={debe}, "
                    f"frecuencia={config.frecuencia_envio}, "
                    f"hora={config.hora_envio}, "
                    f"destinatarios={config.destinatarios.count()}"
                )
            return

        resultado = procesar_envios_pendientes()

        self.stdout.write(self.style.SUCCESS(
            f"Evaluadas: {resultado['configuraciones_evaluadas']} configuraciones"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Reportes generados: {resultado['reportes_generados']}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Reportes enviados: {resultado['reportes_enviados']}"
        ))

        if resultado["errores"]:
            self.stdout.write(self.style.ERROR(f"Errores: {resultado['errores']}"))

        for detalle in resultado["detalles"]:
            if detalle["estado"] == "completado":
                self.stdout.write(f"  OK: {detalle['configuracion']} -> {detalle['destinatarios']} destinatarios")
            else:
                self.stdout.write(self.style.ERROR(f"  ERROR: {detalle['configuracion']} -> {detalle.get('error', '?')}"))

        if resultado["errores"]:
            sys.exit(1)
