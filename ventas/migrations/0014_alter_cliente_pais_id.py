# Generated by Django 5.1.3 on 2025-01-12 00:32

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo', '0016_estado_pais'),
        ('ventas', '0013_alter_cliente_pais_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cliente',
            name='pais_id',
            field=models.ForeignKey(default=3, on_delete=django.db.models.deletion.CASCADE, to='catalogo.pais'),
        ),
    ]
