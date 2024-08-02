from django.conf import settings
from django.db import models
from django.utils import timezone

class Pais(models.Model):
    siglas = models.CharField(max_length=10)
    nombre = models.CharField(max_length=50)
    
    def __str__(self):
        return self.siglas
    
    class Meta:
        verbose_name_plural = 'Paises'
        ordering = ['siglas']

class Estado(models.Model):
    id = models.CharField(max_length=25, primary_key=True)
    nombre = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre
    
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
        return self.nombre + " - " + self.direccion + " - " + self.id_estado.nombre
    
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
    
    def __str__(self):
        return self.nombre_completo + " - " + self.num_cuenta + " - " + self.clabe_interbancaria + " - " + self.id_sucursal.nombre + "-" + self.telefono + "- " + str(self.fecha_creacion)
    
    class Meta:
        verbose_name = "Productor"
        verbose_name_plural = "Productores"
        ordering = ["nombre_completo"]

