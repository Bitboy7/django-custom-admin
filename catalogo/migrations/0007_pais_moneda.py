# Generated by Django 5.0.6 on 2024-08-03 00:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0006_pais"),
    ]

    operations = [
        migrations.AddField(
            model_name="pais",
            name="moneda",
            field=models.CharField(default="MXN", max_length=20),
        ),
    ]
