from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class LogActividad(models.Model):
    """Modelo para registrar actividad de los usuarios en el sistema"""
    
    # Tipos de acciones
    TIPOS_ACCION = (
        ('login', _('Inicio de sesión')),
        ('logout', _('Cierre de sesión')),
        ('create', _('Creación')),
        ('update', _('Actualización')),
        ('delete', _('Eliminación')),
        ('view', _('Visualización')),
        ('other', _('Otra acción')),
    )
    
    # Usuario que realizó la acción (puede ser null si no hay usuario autenticado)
    usuario = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        verbose_name=_('Usuario'),
        related_name='logs_actividad'
    )
    
    # Información del usuario en caso de que se elimine
    nombre_usuario = models.CharField(
        max_length=150, 
        verbose_name=_('Nombre de usuario')
    )
    
    # Tipo de acción realizada
    tipo_accion = models.CharField(
        max_length=10,
        choices=TIPOS_ACCION,
        verbose_name=_('Tipo de acción')
    )
    
    # Descripción de la acción
    descripcion = models.TextField(
        verbose_name=_('Descripción')
    )
    
    # Modelo sobre el que se realizó la acción
    modelo_afectado = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Modelo afectado')
    )
    
    # ID del registro afectado
    objeto_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('ID del objeto')
    )
    
    # Campos afectados (solo para updates)
    campos_modificados = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_('Campos modificados')
    )
    
    # Dirección IP
    direccion_ip = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name=_('Dirección IP')
    )
    
    # User agent
    navegador = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Navegador/Agente')
    )
    
    # Fecha y hora de la acción
    fecha_hora = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha y hora'),
        # Usando la zona horaria del servidor (no UTC)
        db_index=True
    )
    
    class Meta:
        verbose_name = _('Log de actividad')
        verbose_name_plural = _('Logs de actividad')
        ordering = ['-fecha_hora']
        indexes = [
            models.Index(fields=['usuario']),
            models.Index(fields=['tipo_accion']),
            models.Index(fields=['fecha_hora']),
            models.Index(fields=['modelo_afectado']),
        ]
    
    def __str__(self):
        return f"{self.get_tipo_accion_display()} - {self.nombre_usuario} - {self.fecha_hora}"
