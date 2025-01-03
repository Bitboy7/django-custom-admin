# Generated by Django 5.1.3 on 2024-12-30 06:51

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gastos', '0011_alter_compra_options_saldomensual'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='catgastos',
            options={'ordering': ['id'], 'verbose_name': 'Categoría de Gasto', 'verbose_name_plural': 'Categorías de Gastos'},
        ),
        migrations.AlterModelOptions(
            name='saldomensual',
            options={'verbose_name': 'Saldo inicial', 'verbose_name_plural': 'Saldos iniciales'},
        ),
        migrations.AddField(
            model_name='saldomensual',
            name='fecha_registro',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='saldomensual',
            name='saldo_final',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='saldomensual',
            name='año',
            field=models.PositiveIntegerField(choices=[(1999, 1999), (2000, 2000), (2001, 2001), (2002, 2002), (2003, 2003), (2004, 2004), (2005, 2005), (2006, 2006), (2007, 2007), (2008, 2008), (2009, 2009), (2010, 2010), (2011, 2011), (2012, 2012), (2013, 2013), (2014, 2014), (2015, 2015), (2016, 2016), (2017, 2017), (2018, 2018), (2019, 2019), (2020, 2020), (2021, 2021), (2022, 2022), (2023, 2023), (2024, 2024)]),
        ),
        migrations.AlterField(
            model_name='saldomensual',
            name='mes',
            field=models.PositiveIntegerField(choices=[(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9), (10, 10), (11, 11), (12, 12)]),
        ),
        migrations.AlterField(
            model_name='saldomensual',
            name='saldo_inicial',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
