import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from catalogo.models import Sucursal, Productor, Producto
from django.db.models import Sum
from django.utils.html import format_html
from djmoney.models.fields import MoneyField
from app.media_utils import safe_file_url

class CatGastos(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    fecha_registro = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.nombre
    
    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorías"
        ordering = ["id"]

class Banco(models.Model):
    nombre = models.CharField(max_length=50)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    direccion = models.CharField(max_length=100, blank=True, null=True)
    fecha_registro = models.DateTimeField(default=timezone.now)
    logotipo = models.ImageField(
        upload_to='bancos/logos/',
        null=True,
        blank=True,
        verbose_name='Logotipo del Banco',
        help_text='Subir imagen con formato .jpg, .jpeg o .png',
        editable=True
    )

    def mostrar_logotipo(self):
        url = safe_file_url(self.logotipo)
        if url:
            return format_html('<img src="{}" style="width: 50px; height: 50px;" />', url)
        return "Sin imagen"
    mostrar_logotipo.short_description = 'Logotipo'

    @property
    def logotipo_url(self):
        return safe_file_url(self.logotipo)

    def __str__(self):
        return f"{self.nombre}"
    
    class Meta:
        verbose_name = "Banco"
        verbose_name_plural = "Bancos"
        ordering = ["nombre"]

class Cuenta(models.Model):
    id_banco = models.ForeignKey(Banco, on_delete=models.CASCADE)
    id_sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    numero_cuenta = models.CharField(max_length=25)
    numero_cliente = models.CharField(max_length=25, blank=True, null=True)
    rfc = models.CharField(max_length=15, blank=True, null=True)
    clabe = models.CharField(max_length=25, blank=True, null=True)
    fecha_registro = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.id} - {self.id_banco.nombre} - {self.id_sucursal.nombre} - {self.numero_cuenta}"
    
    class Meta:
        verbose_name = "Cuenta"
        verbose_name_plural = "Cuentas"
        ordering = ["-fecha_registro"]

class Gastos(models.Model):
    id_sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    id_cat_gastos = models.ForeignKey(CatGastos, on_delete=models.CASCADE)
    id_cuenta_banco = models.ForeignKey(Cuenta, on_delete=models.CASCADE)
    monto = MoneyField(max_digits=14, decimal_places=2, default_currency='MXN')
    fecha_registro = models.DateTimeField(default=timezone.now)
    descripcion = models.TextField(blank=True, null=True)
    fecha = models.DateField(default=timezone.now)

    def __str__(self):
        return f"Registro {self.id_sucursal.nombre} - {self.id_cat_gastos.nombre} - {self.monto}"
    
    class Meta:
        verbose_name = "Gasto"
        verbose_name_plural = "Gastos"
        ordering = ["-fecha_registro"]


def comprobante_upload_path(instance, filename):
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'bin'
    return f"comprobantes_gastos/{timezone.now():%Y/%m}/{instance.storage_key}.{extension}"


class ComprobanteGasto(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'pending', 'Pendiente de procesar'
        PROCESANDO = 'processing', 'Procesando'
        REVISION = 'review', 'Listo para revisi?n'
        ERROR = 'error', 'Error de procesamiento'
        REGISTRADO = 'recorded', 'Gasto registrado'

    storage_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    archivo = models.FileField(upload_to=comprobante_upload_path)
    nombre_original = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    tamano_bytes = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64, db_index=True)
    estado = models.CharField(max_length=16, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True)
    datos_extraidos = models.JSONField(default=dict, blank=True)
    texto_ocr = models.TextField(blank=True)
    confianza = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    error_procesamiento = models.TextField(blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    gasto = models.OneToOneField(Gastos, null=True, blank=True, on_delete=models.SET_NULL, related_name='comprobante')
    creado_en = models.DateTimeField(auto_now_add=True)
    procesado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['estado', 'creado_en'], name='gastos_comp_estado_fecha_idx'),
            models.Index(fields=['sha256', 'creado_en'], name='gastos_comp_hash_fecha_idx'),
        ]

    def __str__(self):
        return f"Comprobante {self.pk} - {self.get_estado_display()}"

class Compra(models.Model):
        fecha_compra = models.DateField()
        productor = models.ForeignKey(Productor, on_delete=models.CASCADE)
        producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
        cantidad = models.PositiveIntegerField()
        precio_unitario = MoneyField(max_digits=10, decimal_places=2, default_currency='MXN')
        monto_total = MoneyField(max_digits=10, decimal_places=2, default_currency='MXN')
        fecha_registro = models.DateTimeField(default=timezone.now)
        cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE, null=True, blank=True, default=2)
        
        class TipoPago(models.TextChoices):
            Efectivo = 'Efectivo'
            Deposito = 'Deposito'
            Transferencia = 'Transferencia'
            Cheque = 'Cheque'
            
        tipo_pago = models.CharField(max_length=50, blank=True, null=True, choices=TipoPago.choices)
        
        def save(self, *args, **kwargs):
            # Calcular automáticamente el monto total antes de guardar
            if self.cantidad and self.precio_unitario:
                self.monto_total = self.cantidad * self.precio_unitario
            super().save(*args, **kwargs)
        
        def __str__(self):
            return f'{self.productor} - {self.producto.nombre}'

        class Meta:
            verbose_name = "Compra"
            verbose_name_plural = "Compras de fruta"
            ordering = ['-fecha_compra']
            permissions = [("can_view_compras", "Can view compras")]
           
class SaldoMensual(models.Model):
    cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE)
    año = models.PositiveIntegerField(choices=[(r, r) for r in range(1999, timezone.now().year + 1)], default=2025)
    mes = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 13)], default=timezone.now().month)
    saldo_inicial = MoneyField(max_digits=10, decimal_places=2, default_currency='MXN', default=0)
    saldo_final = MoneyField(max_digits=10, decimal_places=2, default_currency='MXN', default=0, blank=True, null=True)
    fecha_registro = models.DateTimeField(default=timezone.now)
    ultima_modificacion = models.DateTimeField(auto_now=True, editable=True)

    class Meta:
        unique_together = ('cuenta', 'año', 'mes')
        verbose_name = "Saldo inicial"
        verbose_name_plural = "Saldos iniciales"

    def __str__(self):
        return f"{self.cuenta} - {self.año}/{self.mes} - {self.saldo_inicial}"

    def calcular_saldo_final(self):
        gastos = Gastos.objects.filter(id_cuenta_banco=self.cuenta, fecha__year=self.año, fecha__month=self.mes).aggregate(total_gastos=Sum('monto'))['total_gastos'] or 0
        compras = Compra.objects.filter(cuenta=self.cuenta, fecha_compra__year=self.año, fecha_compra__month=self.mes).aggregate(total_compras=Sum('monto_total'))['total_compras'] or 0
        self.saldo_final = self.saldo_inicial - gastos + compras
        self.save()
            
