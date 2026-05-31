from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class DestinatarioReporte(models.Model):
    """Correo electrónico al que se enviarán los reportes ejecutivos."""

    nombre = models.CharField(max_length=120, verbose_name="Nombre")
    correo = models.EmailField(unique=True, verbose_name="Correo electrónico")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} <{self.correo}>"

    class Meta:
        verbose_name = "Destinatario de reporte"
        verbose_name_plural = "Destinatarios de reporte"
        ordering = ["nombre"]


class ConfiguracionReporte(models.Model):
    """
    Configuración global del módulo de reportes ejecutivos.
    Solo debe existir un registro activo (patrón Singleton vía admin).
    """

    class Periodo(models.TextChoices):
        MENSUAL = "mensual", "Mensual"
        TRIMESTRAL = "trimestral", "Trimestral"
        ANUAL = "anual", "Anual"
        PERSONALIZADO = "personalizado", "Personalizado"

    nombre = models.CharField(
        max_length=120,
        default="Configuración principal",
        verbose_name="Nombre de configuración",
    )
    periodo_default = models.CharField(
        max_length=20,
        choices=Periodo.choices,
        default=Periodo.MENSUAL,
        verbose_name="Período por defecto",
    )
    asunto_email = models.CharField(
        max_length=200,
        default="Resumen Ejecutivo Financiero — {periodo}",
        verbose_name="Asunto del correo",
        help_text="Usa {periodo} para incluir el período automáticamente.",
    )
    destinatarios = models.ManyToManyField(
        DestinatarioReporte,
        blank=True,
        verbose_name="Destinatarios",
        help_text="Correos a los que se enviará el reporte.",
    )
    modelo_ia = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Modelo de IA",
        help_text=(
            "Deja en blanco para usar GOOGLE_API_MODEL del entorno. "
            "Usa el formato proveedor/modelo para OpenRouter (ej: google/gemini-3.1-flash-lite-preview)."
        ),
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Configuración de reporte"
        verbose_name_plural = "Configuración de reporte"


class ReporteEjecutivo(models.Model):
    """Historial de reportes generados y enviados."""

    class Estado(models.TextChoices):
        GENERANDO = "generando", "Generando..."
        GENERADO = "generado", "Generado"
        ENVIANDO = "enviando", "Enviando..."
        ENVIADO = "enviado", "Enviado"
        ERROR = "error", "Error"

    titulo = models.CharField(max_length=200, verbose_name="Título")
    periodo_inicio = models.DateField(verbose_name="Inicio del período")
    periodo_fin = models.DateField(verbose_name="Fin del período")

    # Datos financieros capturados al momento de la generación
    total_ventas = models.DecimalField(
        max_digits=16, decimal_places=2, default=0, verbose_name="Total ventas"
    )
    total_gastos = models.DecimalField(
        max_digits=16, decimal_places=2, default=0, verbose_name="Total gastos"
    )
    total_compras = models.DecimalField(
        max_digits=16, decimal_places=2, default=0, verbose_name="Total compras"
    )
    margen_bruto = models.DecimalField(
        max_digits=16, decimal_places=2, default=0, verbose_name="Margen bruto"
    )
    margen_porcentaje = models.DecimalField(
        max_digits=7, decimal_places=2, default=0, verbose_name="Margen (%)"
    )

    # Contenido generado por IA
    resumen_ia = models.TextField(blank=True, verbose_name="Resumen generado por IA")
    proyecciones_json = models.TextField(
        blank=True,
        verbose_name="Proyecciones de ventas (scikit-learn)",
        help_text="Proyecciones financieras generadas con scikit-learn (JSON).",
    )
    modelo_ia_usado = models.CharField(
        max_length=120, blank=True, verbose_name="Modelo de IA usado"
    )

    # Envío
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.GENERANDO,
        verbose_name="Estado",
    )
    destinatarios_enviados = models.TextField(
        blank=True,
        verbose_name="Destinatarios",
        help_text="Correos a los que se envió (JSON).",
    )
    error_detalle = models.TextField(blank=True, verbose_name="Detalle del error")

    generado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Generado por",
    )
    fecha_generacion = models.DateTimeField(default=timezone.now, verbose_name="Fecha de generación")

    def __str__(self):
        return f"{self.titulo} — {self.estado}"

    class Meta:
        verbose_name = "Reporte ejecutivo"
        verbose_name_plural = "Reportes ejecutivos"
        ordering = ["-fecha_generacion"]
