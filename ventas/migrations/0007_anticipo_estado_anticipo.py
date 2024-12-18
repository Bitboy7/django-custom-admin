# Generated by Django 5.1.3 on 2024-12-09 00:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0006_anticipo_ventas_anticipo'),
    ]

    operations = [
        migrations.AddField(
            model_name='anticipo',
            name='estado_anticipo',
            field=models.CharField(choices=[('Pendiente', 'Pendiente'), ('Aplicado', 'Aplicado'), ('Cancelado', 'Cancelado')], default='Pendiente', max_length=20),
        ),
    ]
