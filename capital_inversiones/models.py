from django.db import models
from django.utils import timezone
from catalogo.models import Sucursal
from gastos.models import Cuenta
from djmoney.models.fields import MoneyField
from djmoney.models.validators import MinMoneyValidator
from djmoney.money import Money
from decimal import Decimal


class CatInversion(models.Model):
    """
    Categorías de inversiones y capital
    
    Ejemplos:
    - Capital de trabajo
    - Inversión en activos fijos
    - Inversión financiera
    - Reinversión de utilidades
    - Aportación de socios
    - Compra de acciones
    - Inversión inmobiliaria
    """
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre de la Categoría")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    activa = models.BooleanField(default=True, verbose_name="Categoría Activa")
    fecha_registro = models.DateTimeField(default=timezone.now, verbose_name="Fecha de Registro")

    def __str__(self):
        return self.nombre
    
    class Meta:
        verbose_name = "Categoría de Inversión"
        verbose_name_plural = "Categorías de Inversión"
        ordering = ["nombre"]


class Inversion(models.Model):
    """
    Modelo principal para registrar movimientos de capital e inversiones
    
    Permite registrar tanto entradas como salidas de capital con su respectiva
    categorización, sucursal, cuenta bancaria y documentación de soporte.
    """
    
    class TipoMovimiento(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada de Capital'
        SALIDA = 'SALIDA', 'Salida de Capital (Inversión)'
    
    # Relaciones
    id_sucursal = models.ForeignKey(
        Sucursal, 
        on_delete=models.CASCADE,
        verbose_name="Sucursal"
    )
    id_cat_inversion = models.ForeignKey(
        CatInversion, 
        on_delete=models.PROTECT,
        verbose_name="Categoría de Inversión"
    )
    id_cuenta_banco = models.ForeignKey(
        Cuenta, 
        on_delete=models.CASCADE,
        verbose_name="Cuenta Bancaria"
    )
    
    # Datos principales
    tipo_movimiento = models.CharField(
        max_length=10,
        choices=TipoMovimiento.choices,
        default=TipoMovimiento.SALIDA,
        verbose_name="Tipo de Movimiento"
    )
    monto = MoneyField(
        max_digits=14, 
        decimal_places=2, 
        default_currency='MXN',
        validators=[MinMoneyValidator(Money('0.01', 'MXN'))],
        verbose_name="Monto"
    )
    fecha = models.DateField(
        default=timezone.now,
        verbose_name="Fecha del Movimiento"
    )
    descripcion = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Descripción"
    )
    
    # Documentación
    documento_soporte = models.FileField(
        upload_to='capital_inversiones/documentos/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Documento de Soporte',
        help_text='Subir contrato, comprobante o documento relacionado (PDF, Word, Excel, imágenes)'
    )
    
    # Metadatos
    fecha_registro = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha de Registro en Sistema"
    )
    ultima_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name="Última Modificación"
    )
    
    # Campos adicionales para análisis
    notas = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Notas Adicionales"
    )

    def __str__(self):
        return f"{self.tipo_movimiento} - {self.id_sucursal.nombre} - {self.id_cat_inversion.nombre} - {self.monto}"
    
    class Meta:
        verbose_name = "Inversión"
        verbose_name_plural = "Inversiones y Capital"
        ordering = ["-fecha", "-fecha_registro"]
        indexes = [
            models.Index(fields=['-fecha', 'id_sucursal']),
            models.Index(fields=['tipo_movimiento', 'fecha']),
            models.Index(fields=['id_cat_inversion', 'fecha']),
        ]


class RendimientoInversion(models.Model):
    """
    Modelo opcional para registrar rendimientos de inversiones
    
    Permite hacer seguimiento de retornos, dividendos, intereses o ganancias
    generadas por las inversiones realizadas.
    """
    
    inversion = models.ForeignKey(
        Inversion,
        on_delete=models.CASCADE,
        related_name='rendimientos',
        verbose_name="Inversión Relacionada",
        limit_choices_to={'tipo_movimiento': 'SALIDA'}
    )
    
    fecha_rendimiento = models.DateField(
        default=timezone.now,
        verbose_name="Fecha del Rendimiento"
    )
    
    monto_rendimiento = MoneyField(
        max_digits=14, 
        decimal_places=2, 
        default_currency='MXN',
        validators=[MinMoneyValidator(Money('0.00', 'MXN'))],
        verbose_name="Monto del Rendimiento"
    )
    
    porcentaje_rendimiento = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="% Rendimiento",
        help_text="Porcentaje de rendimiento calculado"
    )
    
    tipo_rendimiento = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Tipo de Rendimiento",
        help_text="Ej: Dividendo, Interés, Ganancia de Capital, etc."
    )
    
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción"
    )
    
    fecha_registro = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha de Registro"
    )
    
    def save(self, *args, **kwargs):
        """Calcular porcentaje de rendimiento automáticamente si es posible"""
        if self.monto_rendimiento and self.inversion.monto:
            monto_inversion = float(self.inversion.monto.amount)
            monto_rend = float(self.monto_rendimiento.amount)
            if monto_inversion > 0:
                self.porcentaje_rendimiento = Decimal((monto_rend / monto_inversion) * 100)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Rendimiento - {self.inversion.id_cat_inversion.nombre} - {self.monto_rendimiento} ({self.fecha_rendimiento})"
    
    class Meta:
        verbose_name = "Rendimiento de Inversión"
        verbose_name_plural = "Rendimientos de Inversiones"
        ordering = ["-fecha_rendimiento"]
