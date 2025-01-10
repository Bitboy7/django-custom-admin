# Generated by Django 5.1.3 on 2025-01-10 07:47

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo', '0010_remove_producto_stock_producto_descripcion_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='productor',
            name='nacimiento',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='productor',
            name='nacionalidad',
            field=models.ForeignKey(default=3, on_delete=django.db.models.deletion.CASCADE, to='catalogo.pais'),
        ),
    ]
