# Generated by Django 5.1.3 on 2025-01-11 22:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0009_alter_ventas_producto_delete_producto'),
    ]

    operations = [
        migrations.AddField(
            model_name='cliente',
            name='direccion',
            field=models.CharField(blank=True, default='Desconocida', max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='anticipo',
            name='descripcion',
            field=models.TextField(blank=True, default='Sin descripción', null=True),
        ),
        migrations.AlterField(
            model_name='cliente',
            name='correo',
            field=models.EmailField(blank=True, default='-', max_length=254, null=True),
        ),
        migrations.AlterField(
            model_name='cliente',
            name='telefono',
            field=models.CharField(blank=True, default='-', max_length=15, null=True),
        ),
        migrations.AlterField(
            model_name='ventas',
            name='carga',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]