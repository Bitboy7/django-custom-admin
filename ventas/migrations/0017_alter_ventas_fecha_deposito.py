# Generated by Django 5.1.3 on 2025-01-16 20:33

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0016_alter_cliente_imagen'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ventas',
            name='fecha_deposito',
            field=models.DateField(default=django.utils.timezone.now),
        ),
    ]
