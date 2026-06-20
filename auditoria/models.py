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


class UserProfile(models.Model):
    """Perfil extendido de usuario — almacena la foto de perfil."""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_('Usuario'),
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        verbose_name=_('Foto de perfil'),
        help_text=_('Imagen cuadrada recomendada, mín. 80×80 px.'),
    )

    class Meta:
        verbose_name = _('Perfil de usuario')
        verbose_name_plural = _('Perfiles de usuario')

    def __str__(self):
        return f'Perfil de {self.user.username}'

    @property
    def avatar_url(self):
        """Devuelve la URL del avatar o vacío si no tiene."""
        if self.avatar and getattr(self.avatar, 'name', '') and hasattr(self.avatar, 'url'):
            try:
                if not self.avatar.storage.exists(self.avatar.name):
                    return ''
            except Exception:
                return ''
            return self.avatar.url
        return ''


class SiteConfiguration(models.Model):
    """Configuración global del sitio — singleton (solo un registro con pk=1)."""

    site_title = models.CharField(
        max_length=200,
        default='Sistema administrativo - Agricola de la Costa San Luis',
        verbose_name=_('Título de la pestaña'),
        help_text=_('Texto que aparece en la pestaña del navegador.'),
    )
    site_header = models.CharField(
        max_length=100,
        default='Agricola de la Costa San Luis',
        verbose_name=_('Encabezado del login'),
        help_text=_('Título principal en la pantalla de inicio de sesión.'),
    )
    site_brand = models.CharField(
        max_length=60,
        default='Agricola de la Costa',
        verbose_name=_('Nombre en barra lateral'),
        help_text=_('Nombre corto que aparece junto al logo en la barra lateral.'),
    )
    company_logo = models.ImageField(
        upload_to='site/',
        null=True,
        blank=True,
        verbose_name=_('Logo de la empresa'),
        help_text=_('PNG o SVG con fondo transparente. Recomendado ≥ 200 × 60 px.'),
    )
    navigation_expanded = models.BooleanField(
        default=False,
        verbose_name=_('Sidebar expandido al entrar'),
        help_text=_('Muestra todas las secciones del menú lateral abiertas al cargar la página.'),
    )
    show_ui_builder = models.BooleanField(
        default=False,
        verbose_name=_('Habilitar selector de temas'),
        help_text=_(
            'Muestra el panel de personalización de tema (UI Builder) en la barra lateral del admin. '
            'Recomendado solo para administradores durante configuración inicial.'
        ),
    )
    custom_topbar_css = models.TextField(
        blank=True,
        verbose_name=_('CSS personalizado para la barra superior'),
        help_text=_('CSS personalizado que se aplicará a la barra de navegación superior del admin.'),
    )

    class Meta:
        verbose_name = _('Configuración del Sitio')
        verbose_name_plural = _('Configuración del Sitio')

    def __str__(self):
        return 'Configuración del Sitio'

    def save(self, *args, **kwargs):
        self.pk = 1  # Singleton: nunca crea un segundo registro
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # No se permite eliminar la configuración del sitio

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def company_logo_url(self):
        if self.company_logo and hasattr(self.company_logo, 'url'):
            return self.company_logo.url
        return ''
