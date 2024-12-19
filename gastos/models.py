from django.db import models
from django.utils import timezone
from catalogo.models import Sucursal, Productor
from django.db.models import Sum

class CatGastos(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    fecha_registro = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.nombre
    
    class Meta:
        verbose_name_plural = "Categorías de Gastos"
        ordering = ["nombre"]

class Banco(models.Model):
    nombre = models.CharField(max_length=50)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    direccion = models.CharField(max_length=100, blank=True, null=True)
    fecha_registro = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.nombre} - {self.telefono}"
    
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
    monto = models.FloatField()
    fecha_registro = models.DateTimeField(default=timezone.now)
    descripcion = models.TextField(blank=True, null=True)
    fecha = models.DateField()

    def __str__(self):
        return f"Registro {self.id_sucursal.nombre} - {self.id_cat_gastos.nombre} - {self.monto}"
    
    class Meta:
        verbose_name = "Gasto"
        verbose_name_plural = "Gastos"
        ordering = ["-fecha_registro"]

class Compra(models.Model):
        from ventas.models import Producto
        fecha_compra = models.DateField()
        productor = models.ForeignKey(Productor, on_delete=models.CASCADE)
        producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
        cantidad = models.PositiveIntegerField()
        precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
        monto_total = models.DecimalField(max_digits=10, decimal_places=2)
        fecha_registro = models.DateTimeField(default=timezone.now)
        cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE, null=True, blank=True, default=2)
        
        def __str__(self):
            return f'{self.productor} - {self.producto.nombre}'

        class Meta:
            verbose_name = "Compra de fruta"
            verbose_name_plural = "Compras de fruta"
            ordering = ['-fecha_compra']
            permissions = [("can_view_compras", "Can view compras")]
            
            