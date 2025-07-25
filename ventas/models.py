from django.db import models
from catalogo.models import Sucursal, Pais, Producto
from django.utils.html import format_html
from djmoney.models.fields import MoneyField

class Cliente(models.Model):
    nombre = models.CharField(max_length=50)
    telefono = models.CharField(max_length=15, blank=True, null=True, default='-')
    correo = models.EmailField(blank=True, null=True, default='-')
    direccion = models.CharField(max_length=250, blank=True, null=True, default='Desconocida')
    pais = models.ForeignKey(Pais, on_delete=models.CASCADE, default=3)
    fecha_registro = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    imagen = models.ImageField(upload_to='clientes', blank=True, null=True, default='clientes/default.png', editable=True)

    def __str__(self):
        return f"{self.nombre} - {self.pais}"

    def mostrar_logotipo(self):
        if self.imagen:
            return format_html('<img src="{}" style="width: 70px; height: 70px;" />', self.imagen.url)
        return "No Image"
    mostrar_logotipo.short_description = "Logotipo"
    
    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

class Agente(models.Model):
    nombre = models.CharField(max_length=50)
    telefono = models.CharField(max_length=15, blank=True, null=True, default='Sin teléfono')
    correo = models.EmailField(blank=True, null=True)
    pais = models.ForeignKey(Pais, on_delete=models.CASCADE, default=1)
    fecha_registro = models.DateField(auto_now_add=True)
   
    def __str__(self):
        return self.nombre
    
    class Meta:
        verbose_name = 'Agente aduanal'
        verbose_name_plural = 'Agentes aduanales'
        
class Anticipo(models.Model):
    from gastos.models import Cuenta
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE)
    monto = MoneyField(max_digits=10, decimal_places=2, default_currency='MXN')
    fecha = models.DateField()
    descripcion = models.TextField(blank=True, null=True, default='Sin descripción')
    fecha_registro = models.DateTimeField(auto_now_add=True)
    class Estado_anticipo(models.TextChoices):
        Pendiente = 'Pendiente'
        Aplicado = 'Aplicado'
        Cancelado = 'Cancelado'
    estado_anticipo = models.CharField(max_length=20, choices=Estado_anticipo.choices, default=Estado_anticipo.Pendiente)
    
    def __str__(self):
        return f"Anticipo de {self.cliente.nombre} - {self.monto}"

    class Meta:
        verbose_name = 'Anticipo'
        verbose_name_plural = 'Anticipos'
        ordering = ['-fecha_registro']
        
class Ventas(models.Model):
    from gastos.models import Cuenta
    from django.utils import timezone
    
    fecha_salida_manifiesto = models.DateField()
    agente_id = models.ForeignKey(Agente, on_delete=models.CASCADE, verbose_name='Agente aduanal')
    fecha_deposito = models.DateField(default=timezone.now)
    pedimento = models.CharField(max_length=50, blank=True, null=True)
    carga = models.CharField(max_length=50, blank=True, null=True)
    PO = models.CharField(max_length=50, blank=True, null=True)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.CharField(max_length=50)
    monto = MoneyField(max_digits=10, decimal_places=2, default_currency='MXN')
    descripcion = models.CharField(max_length=100, blank=True, null=True)  
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    sucursal_id = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE, null=True, blank=True, default=2)
    anticipo = models.ForeignKey(Anticipo, on_delete=models.SET_NULL, null=True, blank=True)
    
    class TipoVenta(models.TextChoices):
        NACIONAL = 'Nacional'
        EXPORTACION = 'Exportación'
        
    tipo_venta = models.CharField(max_length=50, choices=TipoVenta.choices)

    def __str__(self):
        return f"-{self.carga} - {self.fecha_salida_manifiesto} - {self.monto} - {self.cliente.nombre}- {self.producto.nombre}"
        
    class Meta:
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'        