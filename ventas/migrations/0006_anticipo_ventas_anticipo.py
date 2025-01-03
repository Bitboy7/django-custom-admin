# Generated by Django 5.1.3 on 2024-12-09 00:00

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo', '0007_pais_moneda'),
        ('gastos', '0010_alter_compra_options'),
        ('ventas', '0005_ventas_cuenta'),
    ]

    operations = [
        migrations.CreateModel(
            name='Anticipo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('monto', models.DecimalField(decimal_places=2, max_digits=10)),
                ('fecha', models.DateField()),
                ('descripcion', models.TextField(blank=True, null=True)),
                ('fecha_registro', models.DateTimeField(auto_now_add=True)),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ventas.cliente')),
                ('cuenta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gastos.cuenta')),
                ('sucursal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='catalogo.sucursal')),
            ],
            options={
                'verbose_name_plural': 'Anticipos',
                'ordering': ['-fecha_registro'],
            },
        ),
        migrations.AddField(
            model_name='ventas',
            name='anticipo',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='ventas.anticipo'),
        ),
    ]
