# Generated by Django 5.1.3 on 2025-01-13 17:20

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gastos', '0018_alter_banco_logotipo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gastos',
            name='fecha',
            field=models.DateField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='gastos',
            name='monto',
            field=models.FloatField(default=0),
        ),
    ]
