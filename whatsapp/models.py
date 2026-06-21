from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class EvolutionInstance(models.Model):
    """Configuracion de conexion a una instancia de Evolution API."""

    class Estado(models.TextChoices):
        CONECTADO = "conectado", "Conectado"
        DESCONECTADO = "desconectado", "Desconectado"
        ERROR = "error", "Error"

    instance_id = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="ID de instancia",
        help_text="Nombre o ID de la instancia en Evolution API (ej: ddcdaf19-e686-47d2-b7f3-1a3d12a31611).",
    )
    nombre = models.CharField(
        max_length=255,
        verbose_name="Nombre",
        help_text="Nombre descriptivo para identificar esta instancia en el sistema.",
    )
    api_url = models.URLField(
        max_length=500,
        verbose_name="URL de Evolution API",
        help_text="URL base del servidor Evolution API (ej: https://agricola-evolutionapi-...sslip.io).",
    )
    apikey = models.CharField(
        max_length=255,
        verbose_name="API Key",
        help_text="Clave de API para autenticar con Evolution (se envia en header 'apikey').",
    )
    webhook_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name="URL del webhook",
        help_text="URL donde Evolution enviara los eventos entrantes. Se configura automaticamente si se deja en blanco.",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.DESCONECTADO,
        verbose_name="Estado",
    )
    ultima_verificacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Ultima verificacion",
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creacion",
    )

    def __str__(self):
        return f"{self.nombre} ({self.instance_id})"

    class Meta:
        verbose_name = "Instancia Evolution"
        verbose_name_plural = "Instancias Evolution"
        ordering = ["nombre"]


class DestinatarioWhatsApp(models.Model):
    """Contacto de WhatsApp al que se enviaran reportes y alertas."""

    nombre = models.CharField(
        max_length=255,
        verbose_name="Nombre",
    )
    telefono = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Telefono",
        help_text="Numero con codigo de pais, sin '+', ej: 5216671234567.",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )
    notas = models.TextField(
        blank=True,
        verbose_name="Notas",
        help_text="Informacion adicional sobre este contacto.",
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de registro",
    )

    def __str__(self):
        return f"{self.nombre} ({self.telefono})"

    class Meta:
        verbose_name = "Destinatario WhatsApp"
        verbose_name_plural = "Destinatarios WhatsApp"
        ordering = ["nombre"]


class ConfiguracionWhatsApp(models.Model):
    """
    Configuracion de notificaciones por WhatsApp.
    Si usuario es nulo, es la configuracion global por defecto.
    """

    class FrecuenciaReporte(models.TextChoices):
        DIARIO = "diario", "Diario"
        SEMANAL = "semanal", "Semanal"
        MENSUAL = "mensual", "Mensual"
        MANUAL = "manual", "Solo manual"

    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="config_whatsapp",
        verbose_name="Usuario",
        help_text="Dejar en blanco para configuracion global.",
    )
    instancia = models.ForeignKey(
        EvolutionInstance,
        on_delete=models.PROTECT,
        verbose_name="Instancia Evolution",
        help_text="Instancia de WhatsApp a usar para el envio.",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )
    enviar_reportes = models.BooleanField(
        default=True,
        verbose_name="Enviar reportes ejecutivos",
    )
    enviar_alertas = models.BooleanField(
        default=True,
        verbose_name="Enviar alertas",
        help_text="Alertas de cobranza, vencimientos, etc.",
    )
    frecuencia_envio = models.CharField(
        max_length=20,
        choices=FrecuenciaReporte.choices,
        default=FrecuenciaReporte.MENSUAL,
        verbose_name="Frecuencia de envio",
    )
    hora_envio = models.TimeField(
        default="08:00",
        verbose_name="Hora de envio",
        help_text="Hora del dia en que se enviaran los reportes (formato 24h).",
    )
    dia_semana = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Dia de la semana",
        help_text="1=Lunes, 7=Domingo. Solo aplica para frecuencia semanal.",
        choices=[(i, d) for i, d in enumerate(["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"], 1)],
    )
    dia_mes = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Dia del mes",
        help_text="1-28. Solo aplica para frecuencia mensual.",
    )
    destinatarios = models.ManyToManyField(
        DestinatarioWhatsApp,
        blank=True,
        verbose_name="Destinatarios",
        help_text="Contactos a los que se enviaran los reportes y alertas.",
    )
    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name="Fecha de actualizacion",
    )

    def __str__(self):
        if self.usuario:
            return f"Config. {self.usuario.username}"
        return "Configuracion global"

    class Meta:
        verbose_name = "Configuracion WhatsApp"
        verbose_name_plural = "Configuraciones WhatsApp"
        ordering = ["-fecha_actualizacion"]


class ProgramacionEnvio(models.Model):
    """
    Registro de programacion de envios automaticos.
    Controla cuando fue la ultima ejecucion y cual es la proxima.
    """

    class EstadoEjecucion(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_EJECUCION = "en_ejecucion", "En ejecucion"
        COMPLETADO = "completado", "Completado"
        ERROR = "error", "Error"

    configuracion = models.ForeignKey(
        ConfiguracionWhatsApp,
        on_delete=models.CASCADE,
        related_name="programaciones",
        verbose_name="Configuracion",
    )
    reporte = models.ForeignKey(
        "reportes.ReporteEjecutivo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="envios_whatsapp",
        verbose_name="Reporte ejecutivo",
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoEjecucion.choices,
        default=EstadoEjecucion.PENDIENTE,
        verbose_name="Estado",
    )
    programado_para = models.DateTimeField(
        verbose_name="Programado para",
    )
    ejecutado_en = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Ejecutado en",
    )
    error_detalle = models.TextField(
        blank=True,
        verbose_name="Detalle del error",
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creacion",
    )

    def __str__(self):
        return f"Envio {self.id} - {self.configuracion} - {self.estado}"

    class Meta:
        verbose_name = "Programacion de envio"
        verbose_name_plural = "Programaciones de envio"
        ordering = ["-programado_para"]


class MensajeWhatsApp(models.Model):
    """Historial de mensajes enviados por WhatsApp."""

    class Tipo(models.TextChoices):
        REPORTE = "reporte", "Reporte ejecutivo"
        ALERTA = "alerta", "Alerta"
        MANUAL = "manual", "Manual"
        PRUEBA = "prueba", "Prueba"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        ENVIADO = "enviado", "Enviado"
        ERROR = "error", "Error"

    instancia = models.ForeignKey(
        EvolutionInstance,
        on_delete=models.PROTECT,
        verbose_name="Instancia",
    )
    destinatario = models.ForeignKey(
        DestinatarioWhatsApp,
        on_delete=models.PROTECT,
        verbose_name="Destinatario",
    )
    tipo = models.CharField(
        max_length=20,
        choices=Tipo.choices,
        default=Tipo.MANUAL,
        verbose_name="Tipo de mensaje",
    )
    contenido = models.TextField(
        verbose_name="Contenido",
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
        verbose_name="Estado de envio",
    )
    reporte = models.ForeignKey(
        "reportes.ReporteEjecutivo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mensajes_whatsapp",
        verbose_name="Reporte asociado",
    )
    evolution_message_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="ID del mensaje en Evolution",
        help_text="Identificador retornado por Evolution API.",
    )
    error_detalle = models.TextField(
        blank=True,
        verbose_name="Detalle del error",
    )
    fecha_envio = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de envio",
    )

    def __str__(self):
        return f"Mensaje a {self.destinatario} - {self.tipo} ({self.estado})"

    class Meta:
        verbose_name = "Mensaje WhatsApp"
        verbose_name_plural = "Mensajes WhatsApp"
        ordering = ["-fecha_envio"]


class WebhookLog(models.Model):
    """Registro de eventos recibidos via webhook desde Evolution API."""

    instancia = models.ForeignKey(
        EvolutionInstance,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="webhooks",
        verbose_name="Instancia",
    )
    tipo_evento = models.CharField(
        max_length=50,
        verbose_name="Tipo de evento",
        help_text="Ej: messages-upsert, qrcode.updated, connection.update.",
    )
    payload = models.JSONField(
        verbose_name="Payload completo",
        help_text="Datos completos recibidos del webhook.",
    )
    telefono_remitente = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Telefono remitente",
    )
    mensaje = models.TextField(
        blank=True,
        verbose_name="Mensaje recibido",
    )
    procesado = models.BooleanField(
        default=False,
        verbose_name="Procesado",
        help_text="Indica si el evento ya fue procesado por el sistema.",
    )
    fecha_recepcion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de recepcion",
    )

    def __str__(self):
        return f"Webhook {self.tipo_evento} - {self.instancia.nombre} ({self.fecha_recepcion})"

    class Meta:
        verbose_name = "Log de webhook"
        verbose_name_plural = "Logs de webhooks"
        ordering = ["-fecha_recepcion"]

    @classmethod
    def registrar(cls, instance_id: str, payload: dict) -> "WebhookLog":
        """Registra un evento de webhook de forma rapida."""
        instancia = EvolutionInstance.objects.filter(instance_id=instance_id, activo=True).first()

        data = payload.get("data", {})
        tipo_evento = payload.get("event", "desconocido")

        telefono = ""
        mensaje_texto = ""

        if tipo_evento == "messages.upsert":
            msg_data = data.get("message", {}) or data
            key = data.get("key", {})
            telefono = key.get("remoteJid", "").split("@")[0] if key.get("remoteJid") else ""
            if msg_data:
                if "conversation" in msg_data:
                    mensaje_texto = msg_data.get("conversation", "")
                elif "extendedTextMessage" in msg_data:
                    mensaje_texto = msg_data.get("extendedTextMessage", {}).get("text", "")
                elif "imageMessage" in msg_data:
                    mensaje_texto = f"[Imagen] {msg_data.get('imageMessage', {}).get('caption', '')}"
                elif "documentMessage" in msg_data:
                    mensaje_texto = f"[Documento] {msg_data.get('documentMessage', {}).get('fileName', '')}"

        return cls.objects.create(
            instancia=instancia,
            tipo_evento=tipo_evento,
            payload=payload,
            telefono_remitente=telefono,
            mensaje=mensaje_texto,
        )
