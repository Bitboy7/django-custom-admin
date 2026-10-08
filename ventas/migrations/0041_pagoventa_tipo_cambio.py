from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0040_alter_ventas_cuenta'),
    ]

    operations = [
        migrations.AddField(
            model_name='pagoventa',
            name='tipo_cambio',
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal('1.0000'),
                help_text=(
                    'MXN por 1 unidad de la moneda del pago. '
                    'En pagos en pesos debe ser 1.0000.'
                ),
                max_digits=10,
                verbose_name='Tipo de cambio',
            ),
        ),
    ]
