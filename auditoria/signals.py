"""Registro central de eliminaciones, incluidas las hechas en bloque."""
from django.contrib.admin.models import LogEntry
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .models import LogActividad
from .request_context import registrar_evento_modelo


@receiver(pre_delete)
def registrar_eliminacion_modelo(sender, instance, **kwargs):
    if sender in (LogActividad, LogEntry):
        return

    try:
        representacion = str(instance)
    except Exception:
        representacion = f'{sender._meta.label} #{instance.pk}'

    registrar_evento_modelo(
        tipo_accion='delete',
        descripcion=f'Se eliminó {sender._meta.verbose_name}: {representacion}',
        modelo_afectado=sender._meta.label,
        objeto_id=instance.pk,
        campos_modificados={'representacion': representacion},
    )
