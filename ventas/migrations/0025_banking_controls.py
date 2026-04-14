# Generated migration for banking controls
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0024_cantidad_char_to_decimal'),
    ]

    operations = [
        # Add procesado field to PagoVenta
        migrations.AddField(
            model_name='pagoventa',
            name='procesado',
            field=models.BooleanField(
                default=False,
                help_text='Indica si el pago ya fue procesado y aplicado a la venta'
            ),
        ),
        
        # Add index for procesado field
        migrations.AddIndex(
            model_name='pagoventa',
            index=models.Index(fields=['procesado'], name='ventas_pago_proceso_idx'),
        ),
        
        # Add check constraint for positive payment amounts
        migrations.AddConstraint(
            model_name='pagoventa',
            constraint=models.CheckConstraint(
                condition=models.Q(monto_pago__gt=0),
                name='pago_venta_monto_positivo'
            ),
        ),
        
        # Add check constraint for positive anticipo amounts
        migrations.AddConstraint(
            model_name='anticipo',
            constraint=models.CheckConstraint(
                condition=models.Q(monto__gt=0),
                name='anticipo_monto_positivo'
            ),
        ),
        
        # Add additional indexes for performance
        migrations.AddIndex(
            model_name='anticipo',
            index=models.Index(fields=['cliente', 'estado_anticipo'], name='ventas_anti_cliente_estado_idx'),
        ),
        migrations.AddIndex(
            model_name='anticipo',
            index=models.Index(fields=['estado_anticipo'], name='ventas_anti_estado_idx'),
        ),
        migrations.AddIndex(
            model_name='pagoventa',
            index=models.Index(fields=['venta', 'fecha_pago'], name='ventas_pago_venta_fecha_idx'),
        ),
    ]
