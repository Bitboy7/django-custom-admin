# Generated by Django 5.1.3 on 2025-01-16 20:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gastos', '0019_alter_gastos_fecha_alter_gastos_monto'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='catgastos',
            options={'ordering': ['id'], 'verbose_name': 'Categoria', 'verbose_name_plural': 'Categorías'},
        ),
        migrations.AddField(
            model_name='saldomensual',
            name='ultima_modificacion',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
