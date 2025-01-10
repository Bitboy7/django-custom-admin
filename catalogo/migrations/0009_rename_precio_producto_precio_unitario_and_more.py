# Generated by Django 5.1.3 on 2025-01-10 07:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo', '0008_producto'),
    ]

    operations = [
        migrations.RenameField(
            model_name='producto',
            old_name='precio',
            new_name='precio_unitario',
        ),
        migrations.AddField(
            model_name='producto',
            name='disponible',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='producto',
            name='stock',
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
    ]