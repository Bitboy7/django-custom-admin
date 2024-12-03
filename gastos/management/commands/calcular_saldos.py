from django.core.management.base import BaseCommand
from gastos.models import Cuenta
from gastos.utils import calcular_saldo_anterior
from datetime import datetime

class Command(BaseCommand):
    help = 'Calcula el saldo anterior de cada cuenta al final del mes'

    def handle(self, *args, **kwargs):
        fecha_final_mes = datetime(2023, 1, 31)
        cuentas = Cuenta.objects.all()

        for cuenta in cuentas:
            saldo_anterior = calcular_saldo_anterior(cuenta, fecha_final_mes)
            self.stdout.write(self.style.SUCCESS(f"Cuenta: {cuenta.numero_cuenta}, Saldo Anterior: {saldo_anterior}"))