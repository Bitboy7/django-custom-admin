# Generated by Django 5.1.3 on 2024-12-03 18:27

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gastos', '0008_alter_compra_options_alter_compra_fecha_registro'),
        ('ventas', '0004_rename_caja_ventas_cantidad'),
    ]

    operations = [
        migrations.AddField(
            model_name='ventas',
            name='cuenta',
            field=models.ForeignKey(blank=True, default=2, null=True, on_delete=django.db.models.deletion.CASCADE, to='gastos.cuenta'),
        ),
    ]