# Generated by Django 5.1.3 on 2025-01-08 22:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gastos', '0014_alter_saldomensual_año'),
    ]

    operations = [
        migrations.AddField(
            model_name='banco',
            name='logotipo',
            field=models.ImageField(blank=True, null=True, upload_to='bancos/logos/', verbose_name='Logotipo del Banco'),
        ),
    ]