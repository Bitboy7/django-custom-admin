from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0036_remove_anticipo_folio_factura_anticipo_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cliente',
            name='nombre',
            field=models.CharField(max_length=200),
        ),
        migrations.AddField(
            model_name='cliente',
            name='rfc',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='RFC del cliente. Para extranjeros puede ser XEXX010101000.',
                max_length=13,
                null=True,
                verbose_name='RFC',
            ),
        ),
        migrations.AddField(
            model_name='cliente',
            name='residencia_fiscal',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='Código de país SAT/ISO 3166-1 alfa-3, por ejemplo MEX, USA o CAN.',
                max_length=3,
                null=True,
                verbose_name='Residencia fiscal',
            ),
        ),
        migrations.AddField(
            model_name='cliente',
            name='numero_registro_fiscal',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='NumRegIdTrib del CFDI; identifica al cliente cuando el RFC es XEXX010101000.',
                max_length=40,
                null=True,
                verbose_name='Registro fiscal extranjero',
            ),
        ),
        migrations.AddField(
            model_name='cliente',
            name='codigo_postal_fiscal',
            field=models.CharField(
                blank=True,
                max_length=12,
                null=True,
                verbose_name='Código postal fiscal',
            ),
        ),
        migrations.AddField(
            model_name='cliente',
            name='regimen_fiscal',
            field=models.CharField(
                blank=True,
                max_length=3,
                null=True,
                verbose_name='Régimen fiscal SAT',
            ),
        ),
    ]
