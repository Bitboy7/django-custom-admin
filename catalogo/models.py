from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib import admin
from django.utils.html import format_html

class Pais(models.Model):
    siglas = models.CharField(max_length=10)
    nombre = models.CharField(max_length=50)
    moneda = models.CharField(max_length=20, default='MXN')
    bandera = models.ImageField(
        upload_to='paises/banderas/',
        null=True,
        blank=True,
        verbose_name='Bandera del País', 
        editable=True
    )
    
    def mostrar_bandera(self):
        if self.bandera:
            return format_html('<img src="{}" style="width: 40px; height: 40px;" />', self.bandera.url)
        return "No Image"
    mostrar_bandera.short_description = 'Bandera'
    
    def __str__(self):
        return f'{self.id} - {self.siglas} - {self.nombre}'

    class Meta:
        verbose_name = 'Pais'
        verbose_name_plural = 'Paises'
        ordering = ['siglas']

class Estado(models.Model):
    id = models.CharField(max_length=25, primary_key=True)
    nombre = models.CharField(max_length=50)
    pais = models.ForeignKey(Pais, on_delete=models.CASCADE, blank=True, null=True, default=3)

    def __str__(self):
        return f'{self.id} - {self.nombre}'
    
    class Meta:
        verbose_name = "Estado"
        verbose_name_plural = "Estados"
        ordering = ["nombre"]

class Sucursal(models.Model):
    nombre = models.CharField(max_length=50)
    direccion = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    id_estado = models.ForeignKey(Estado, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.nombre} - {self.id_estado}'
    
    class Meta:
        verbose_name = "Sucursal"
        verbose_name_plural = "Sucursales"
        ordering = ["nombre"]

class Productor(models.Model):
    nombre_completo = models.CharField(max_length=200)
    num_cuenta = models.CharField(max_length=20, default="0000000000")
    clabe_interbancaria = models.CharField(max_length=20, editable=True, default="000000000000000000")
    telefono = models.CharField(max_length=10, blank=True, null=True)
    correo = models.EmailField(max_length=254, blank=True, null=True)
    id_sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, default=1)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    nacimiento = models.DateField(blank=True, null=True)
    nacionalidad = models.ForeignKey(Pais, on_delete=models.CASCADE, default=3)
    imagen = models.ImageField(
        upload_to='productores/imagenes/',
        null=True,
        blank=True,
        verbose_name='Imagen del Productor', 
        editable=True, 
        default='productores/imagenes/default.svg',
        help_text='Subir imagen con formato .jpg, .jpeg o .png'
    )

    def __str__(self):
        return f'{self.nombre_completo}- {self.telefono}'
    
    class Meta:
        verbose_name = "Productor"
        verbose_name_plural = "Productores"
        ordering = ["nombre_completo"]
        
class Producto(models.Model):
    nombre = models.CharField(max_length=100, default='Mango')
    variedad = models.CharField(max_length=50)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, blank=True, null=True)
    disponible = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    imagen = models.ImageField(
                upload_to='catalogo/productos/',
                null=True,
                blank=True,
                verbose_name='Imagen del Producto',
                editable=True,
                help_text='Subir imagen con formato .jpg, .jpeg o .png'
            )
    
    def __str__(self):
            return f"{self.variedad} - {self.disponible}"    
                
    class Meta:
            verbose_name = 'Producto'
            verbose_name_plural = 'Productos'

        
