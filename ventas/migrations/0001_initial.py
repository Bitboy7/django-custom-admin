# Generated by Django 5.0.6 on 2024-08-02 05:56

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("catalogo", "0005_alter_estado_options_alter_productor_options_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Agente",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("nombre", models.CharField(max_length=50)),
                ("fecha", models.DateField(auto_now_add=True)),
            ],
            options={
                "verbose_name_plural": "Agentes aduanales",
            },
        ),
        migrations.CreateModel(
            name="Pais",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("siglas", models.CharField(max_length=10)),
                ("nombre", models.CharField(max_length=50)),
            ],
            options={
                "verbose_name_plural": "Paises",
            },
        ),
        migrations.CreateModel(
            name="Producto",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("nombre", models.CharField(max_length=100)),
                ("variedad", models.CharField(max_length=50)),
                ("precio", models.DecimalField(decimal_places=2, max_digits=10)),
            ],
            options={
                "verbose_name_plural": "Productos",
            },
        ),
        migrations.CreateModel(
            name="Cliente",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("nombre", models.CharField(max_length=50)),
                ("telefono", models.CharField(max_length=15)),
                ("correo", models.EmailField(blank=True, max_length=254)),
                (
                    "pais_id",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="ventas.pais"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Ventas",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("fecha_salida_manifiesto", models.DateField()),
                ("fecha_deposito", models.DateField()),
                ("carga", models.CharField(max_length=50)),
                ("PO", models.CharField(max_length=50)),
                ("caja", models.CharField(max_length=50)),
                ("monto", models.DecimalField(decimal_places=2, max_digits=10)),
                ("descripcion", models.CharField(max_length=100)),
                ("fecha_registro", models.DateTimeField(auto_now_add=True)),
                (
                    "tipo_pago",
                    models.CharField(
                        choices=[
                            ("Nacional", "Nacional"),
                            ("Exportacion", "Exportacion"),
                        ],
                        max_length=50,
                    ),
                ),
                (
                    "agente_id",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="ventas.agente"
                    ),
                ),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="ventas.cliente"
                    ),
                ),
                (
                    "producto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="ventas.producto",
                    ),
                ),
                (
                    "sucursal_id",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="catalogo.sucursal",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Ventas",
            },
        ),
    ]