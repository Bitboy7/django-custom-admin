from django.core.management.base import BaseCommand
from django.utils import timezone
from catalogo.models import Sucursal
from gastos.models import Cuenta
from capital_inversiones.models import Inversion, CatInversion, RendimientoInversion
from djmoney.money import Money
import random

class Command(BaseCommand):
    help = 'Carga ejemplos de inversiones y rendimientos para pruebas.'

    def handle(self, *args, **options):
        # Buscar sucursal, cuenta y categoría (usar las primeras disponibles)
        sucursal = Sucursal.objects.first()
        cuenta = Cuenta.objects.first()
        categorias = list(CatInversion.objects.all())
        if not sucursal or not cuenta or not categorias:
            self.stdout.write(self.style.ERROR('Debes tener al menos una sucursal, cuenta y categoría de inversión.'))
            return

        # Crear 5 inversiones tipo SALIDA y 3 tipo ENTRADA
        for i in range(1, 6):
            inv = Inversion.objects.create(
                id_sucursal=sucursal,
                id_cat_inversion=random.choice(categorias),
                id_cuenta_banco=cuenta,
                tipo_movimiento='SALIDA',
                monto=Money(random.randint(5000, 20000), 'MXN'),
                fecha=timezone.now().date() - timezone.timedelta(days=30*i),
                descripcion=f'Inversión de ejemplo #{i} (SALIDA)'
            )
            # Agregar entre 1 y 3 rendimientos
            for r in range(random.randint(1, 3)):
                monto_rend = Money(random.randint(500, 3000), 'MXN')
                RendimientoInversion.objects.create(
                    inversion=inv,
                    fecha_rendimiento=inv.fecha + timezone.timedelta(days=15*(r+1)),
                    monto_rendimiento=monto_rend,
                    tipo_rendimiento=random.choice(['Intereses', 'Dividendos', 'Ganancia de capital']),
                )

        for i in range(1, 4):
            Inversion.objects.create(
                id_sucursal=sucursal,
                id_cat_inversion=random.choice(categorias),
                id_cuenta_banco=cuenta,
                tipo_movimiento='ENTRADA',
                monto=Money(random.randint(10000, 30000), 'MXN'),
                fecha=timezone.now().date() - timezone.timedelta(days=10*i),
                descripcion=f'Inversión de ejemplo #{i} (ENTRADA)'
            )

        self.stdout.write(self.style.SUCCESS('Ejemplos de inversiones y rendimientos cargados correctamente.'))
