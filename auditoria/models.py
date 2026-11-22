import uuid

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from app.media_utils import safe_file_url


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
        return safe_file_url(self.avatar)


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
        return safe_file_url(self.company_logo)


class ConversacionAsistente(models.Model):
    """Conversación del asistente MCP, propiedad de un usuario."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversaciones_asistente",
        verbose_name=_("Usuario"),
    )
    titulo = models.CharField(max_length=160, blank=True, default="", verbose_name=_("Título"))
    creada_en = models.DateTimeField(auto_now_add=True, verbose_name=_("Creada en"))
    actualizada_en = models.DateTimeField(auto_now=True, db_index=True, verbose_name=_("Actualizada en"))
    archivada = models.BooleanField(default=False, verbose_name=_("Archivada"))

    class Meta:
        verbose_name = _("Conversación del asistente")
        verbose_name_plural = _("Conversaciones del asistente")
        ordering = ["-actualizada_en"]
        indexes = [
            models.Index(fields=["usuario", "-actualizada_en"], name="asist_conv_user_fecha_idx"),
        ]

    def __str__(self):
        return self.titulo or f"Conversación {self.pk}"


class MensajeAsistente(models.Model):
    """Turno de la conversación: pregunta del usuario o respuesta del asistente."""

    class Rol(models.TextChoices):
        USUARIO = "user", _("Usuario")
        ASISTENTE = "assistant", _("Asistente")

    conversacion = models.ForeignKey(
        ConversacionAsistente,
        on_delete=models.CASCADE,
        related_name="mensajes",
        verbose_name=_("Conversación"),
    )
    rol = models.CharField(max_length=12, choices=Rol.choices, verbose_name=_("Rol"))
    contenido = models.TextField(blank=True, default="", verbose_name=_("Contenido"))
    orden = models.PositiveIntegerField(verbose_name=_("Orden"))
    modelo = models.CharField(max_length=80, blank=True, default="", verbose_name=_("Modelo"))
    tokens_entrada = models.PositiveIntegerField(default=0, verbose_name=_("Tokens de entrada"))
    tokens_salida = models.PositiveIntegerField(default=0, verbose_name=_("Tokens de salida"))
    tokens_razonamiento = models.PositiveIntegerField(default=0, verbose_name=_("Tokens de razonamiento"))
    tokens_total = models.PositiveIntegerField(default=0, verbose_name=_("Tokens totales"))
    costo_estimado_usd = models.DecimalField(
        max_digits=14,
        decimal_places=8,
        default=0,
        verbose_name=_("Costo estimado (USD)"),
    )
    duracion_ms = models.PositiveIntegerField(default=0, verbose_name=_("Duración (ms)"))
    error = models.TextField(blank=True, default="", verbose_name=_("Error"))
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name=_("Creado en"))

    class Meta:
        verbose_name = _("Mensaje del asistente")
        verbose_name_plural = _("Mensajes del asistente")
        ordering = ["orden"]
        constraints = [
            models.UniqueConstraint(
                fields=["conversacion", "orden"],
                name="asist_mensaje_conv_orden_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["conversacion", "orden"], name="asist_msg_conv_orden_idx"),
        ]

    def __str__(self):
        return f"{self.get_rol_display()} #{self.orden}"


class TrazaHerramientaAsistente(models.Model):
    """Herramienta MCP ejecutada durante una respuesta, para auditoría y reapertura."""

    mensaje = models.ForeignKey(
        MensajeAsistente,
        on_delete=models.CASCADE,
        related_name="trazas",
        verbose_name=_("Mensaje"),
    )
    herramienta = models.CharField(max_length=80, verbose_name=_("Herramienta"))
    argumentos = models.JSONField(default=dict, blank=True, verbose_name=_("Argumentos"))
    num_filas = models.PositiveIntegerField(default=0, verbose_name=_("Filas"))
    columnas = models.JSONField(default=list, blank=True, verbose_name=_("Columnas"))
    duracion_ms = models.PositiveIntegerField(default=0, verbose_name=_("Duración (ms)"))
    error = models.TextField(blank=True, default="", verbose_name=_("Error"))
    resultado = models.JSONField(default=dict, blank=True, verbose_name=_("Resultado (recortado)"))
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name=_("Creado en"))

    class Meta:
        verbose_name = _("Traza de herramienta")
        verbose_name_plural = _("Trazas de herramientas")
        ordering = ["id"]

    def __str__(self):
        return self.herramienta

