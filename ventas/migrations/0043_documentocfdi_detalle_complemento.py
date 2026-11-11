from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0042_alter_documentocfdi_subtipo'),
    ]

    operations = [
        migrations.AddField(
            model_name='documentocfdi',
            name='detalle_complemento',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    'Detalle de pagos REP y documentos relacionados extraído '
                    'del XML, con montos decimales serializados como texto.'
                ),
                verbose_name='Detalle del complemento',
            ),
        ),
    ]
