# Generated by Django 5.1.3 on 2024-12-09 00:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gastos', '0009_alter_compra_options_compra_cuenta'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='compra',
            options={'ordering': ['-fecha_compra'], 'permissions': [('can_view_compras', 'Can view compras')], 'verbose_name': 'Compra de fruta', 'verbose_name_plural': 'Compras de fruta'},
        ),
    ]
