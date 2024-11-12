from django.db import models
from catalogo.models import Sucursal, Pais

class Cliente(models.Model):
    nombre = models.CharField(max_length=50)
    telefono = models.CharField(max_length=15)
    correo = models.EmailField(blank=True)
    pais_id = models.ForeignKey(Pais, on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre

class Agente(models.Model):
    nombre = models.CharField(max_length=50)
    fecha = models.DateField(auto_now_add=True)
    
    def __str__(self):
        return self.nombre
    
    class Meta:
        verbose_name_plural = 'Agentes aduanales'

class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    variedad = models.CharField(max_length=50)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return self.variedad
    
    class Meta:
        verbose_name_plural = 'Productos'

class Ventas(models.Model):
    fecha_salida_manifiesto = models.DateField()
    agente_id = models.ForeignKey(Agente, on_delete=models.CASCADE, verbose_name='Agente aduanal')
    fecha_deposito = models.DateField()
    pedimento = models.CharField(max_length=50, blank=True, null=True)
    carga = models.CharField(max_length=50)
    PO = models.CharField(max_length=50, blank=True, null=True)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    caja = models.CharField(max_length=50)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.CharField(max_length=100, blank=True, null=True)  
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    sucursal_id = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    
    class TipoVenta(models.TextChoices):
        NACIONAL = 'Nacional'
        EXPORTACION = 'Exportacion'
        
    tipo_venta = models.CharField(max_length=50, choices=TipoVenta.choices)



    def __str__(self):
        return self.carga
    
    class Meta:
        verbose_name_plural = 'Ventas'
    
