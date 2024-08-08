# Generated by Django 5.0.6 on 2024-08-02 06:02

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0006_pais"),
        ("ventas", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cliente",
            name="pais_id",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="catalogo.pais"
            ),
        ),
        migrations.RenameField(
            model_name="ventas",
            old_name="tipo_pago",
            new_name="tipo_venta",
        ),
        migrations.DeleteModel(
            name="Pais",
        ),
    ]
