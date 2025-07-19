from django.db import models
from django.utils import timezone
from catalogo.models import Sucursal, Productor
from django.db.models import Sum
from django.utils.html import format_html

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
        if self.logotipo:
            return format_html('<img src="{}" style="width: 50px; height: 50px;" />', self.logotipo.url)
        return "No Image"
    mostrar_logotipo.short_description = 'Logotipo'

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
    monto = models.FloatField(default=0)
    fecha_registro = models.DateTimeField(default=timezone.now)
    descripcion = models.TextField(blank=True, null=True)
    fecha = models.DateField(default=timezone.now)

    def __str__(self):
        return f"Registro {self.id_sucursal.nombre} - {self.id_cat_gastos.nombre} - {self.monto}"
    
    class Meta:
        verbose_name = "Gasto"
        verbose_name_plural = "Gastos"
        ordering = ["-fecha_registro"]

class Compra(models.Model):
        from catalogo.models import Producto
        fecha_compra = models.DateField()
        productor = models.ForeignKey(Productor, on_delete=models.CASCADE)
        producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
        cantidad = models.PositiveIntegerField()
        precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
        monto_total = models.DecimalField(max_digits=10, decimal_places=2)
        fecha_registro = models.DateTimeField(default=timezone.now)
        cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE, null=True, blank=True, default=2)
        
        class TipoPago(models.TextChoices):
            Efectivo = 'Efectivo'
            Deposito = 'Deposito'
            Transferencia = 'Transferencia'
            Cheque = 'Cheque'
            
        tipo_pago = models.CharField(max_length=50, blank=True, null=True, choices=TipoPago.choices)
        
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
    saldo_inicial = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    saldo_final = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, null=True)
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
            