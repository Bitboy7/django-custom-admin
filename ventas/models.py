from django.db import models
from catalogo.models import Sucursal, Pais, Producto
from django.utils.html import format_html
from djmoney.models.fields import MoneyField
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime, timedelta
from django.utils import timezone

class TerminoCredito(models.Model):
    """Modelo para manejar diferentes términos de crédito"""
    nombre = models.CharField(max_length=100, help_text="Ej: Net 30, Net 60, etc.")
    dias_credito = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(365)],
        help_text="Número de días para el crédito (1-365)"
    )
    tasa_interes_mensual = models.DecimalField(
        max_digits=5, decimal_places=4, default=0.0000,
        help_text="Tasa de interés mensual (decimal, ej: 0.0200 = 2%)"
    )
    activo = models.BooleanField(default=True)
    descripcion = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nombre} ({self.dias_credito} días)"
    
    class Meta:
        verbose_name = 'Término de Crédito'
        verbose_name_plural = 'Términos de Crédito'
        ordering = ['dias_credito']

class MercadoDestino(models.Model):
    """Modelo para categorizar mercados de destino"""
    nombre = models.CharField(max_length=100, help_text="Ej: Nacional, USA, Canadá, Europa")
    paises = models.ManyToManyField(Pais, help_text="Países que pertenecen a este mercado")
    requiere_documentacion_especial = models.BooleanField(default=False)
    moneda_preferida = models.CharField(max_length=3, default='USD', help_text="Código de moneda ISO")
    factor_riesgo = models.DecimalField(
        max_digits=3, decimal_places=2, default=1.00,
        validators=[MinValueValidator(0.1), MaxValueValidator(5.0)],
        help_text="Factor de riesgo (1.0 = normal, >1.0 = mayor riesgo)"
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.nombre
    
    class Meta:
        verbose_name = 'Mercado de Destino'
        verbose_name_plural = 'Mercados de Destino'
        ordering = ['nombre']

class Cliente(models.Model):
    nombre = models.CharField(max_length=50)
    telefono = models.CharField(max_length=15, blank=True, null=True, default='-')
    correo = models.EmailField(blank=True, null=True, default='-')
    direccion = models.CharField(max_length=250, blank=True, null=True, default='Desconocida')
    pais = models.ForeignKey(Pais, on_delete=models.CASCADE, default=3)
    mercado_destino = models.ForeignKey(MercadoDestino, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Configuración de crédito
    limite_credito = MoneyField(max_digits=12, decimal_places=2, default_currency='MXN', default=0)
    termino_credito_predeterminado = models.ForeignKey(TerminoCredito, on_delete=models.SET_NULL, null=True, blank=True)
    
    class TipoCliente(models.TextChoices):
        CONTADO = 'Contado', 'Solo Contado'
        CREDITO = 'Credito', 'Solo Crédito'
        MIXTO = 'Mixto', 'Contado y Crédito'
    
    tipo_cliente = models.CharField(max_length=10, choices=TipoCliente.choices, default=TipoCliente.CONTADO)
    
    # Campos de riesgo crediticio
    calificacion_credito = models.CharField(
        max_length=2, 
        choices=[('A+', 'Excelente'), ('A', 'Bueno'), ('B', 'Regular'), ('C', 'Riesgoso')],
        default='A',
        help_text="Calificación crediticia del cliente"
    )
    
    fecha_registro = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    imagen = models.ImageField(upload_to='clientes', blank=True, null=True, default='clientes/default.png', editable=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} - {self.pais}"

    def mostrar_logotipo(self):
        if self.imagen:
            return format_html('<img src="{}" style="width: 70px; height: 70px;" />', self.imagen.url)
        return "No Image"
    mostrar_logotipo.short_description = "Logotipo"
    
    def credito_disponible(self):
        """Calcula el crédito disponible del cliente"""
        if self.tipo_cliente == self.TipoCliente.CONTADO:
            return 0
        
        credito_usado = sum(
            venta.saldo_pendiente() for venta in self.ventas_set.filter(
                modalidad_pago='Credito', 
                estado_cobranza__in=['Pendiente', 'Parcial']
            )
        )
        return max(0, float(self.limite_credito.amount) - credito_usado)
    
    def puede_otorgar_credito(self, monto):
        """Verifica si se puede otorgar un crédito por el monto especificado"""
        return self.credito_disponible() >= float(monto)
    
    @property
    def es_internacional(self):
        """Determina si el cliente es internacional basado en su mercado"""
        if self.mercado_destino:
            return self.mercado_destino.nombre != 'Nacional'
        return self.pais.nombre != 'México'  # Asumiendo que México es el país base
    
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
    
    # Campos existentes
    fecha_salida_manifiesto = models.DateField()
    agente_id = models.ForeignKey(Agente, on_delete=models.CASCADE, verbose_name='Agente aduanal')
    fecha_deposito = models.DateField(default=timezone.now)
    pedimento = models.CharField(max_length=50, blank=True, null=True)
    carga = models.CharField(max_length=50, blank=True, null=True)
    PO = models.CharField(max_length=50, blank=True, null=True)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.CharField(max_length=50)
    monto = MoneyField(max_digits=12, decimal_places=2, default_currency='MXN')
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
    
    # Nuevos campos para manejo de crédito
    class ModalidadPago(models.TextChoices):
        CONTADO = 'Contado', 'Contado'
        CREDITO = 'Credito', 'Crédito'
        
    modalidad_pago = models.CharField(
        max_length=10, 
        choices=ModalidadPago.choices, 
        default=ModalidadPago.CONTADO
    )
    
    termino_credito = models.ForeignKey(
        TerminoCredito, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Solo requerido para ventas a crédito"
    )
    
    fecha_vencimiento = models.DateField(
        null=True, 
        blank=True,
        help_text="Fecha de vencimiento para ventas a crédito"
    )
    
    class EstadoCobranza(models.TextChoices):
        PAGADO = 'Pagado', 'Pagado'
        PENDIENTE = 'Pendiente', 'Pendiente'
        PARCIAL = 'Parcial', 'Parcialmente Pagado'
        VENCIDO = 'Vencido', 'Vencido'
        INCOBRABLE = 'Incobrable', 'Incobrable'
        
    estado_cobranza = models.CharField(
        max_length=15, 
        choices=EstadoCobranza.choices, 
        default=EstadoCobranza.PAGADO
    )
    
    monto_pagado = MoneyField(
        max_digits=12, 
        decimal_places=2, 
        default_currency='MXN', 
        default=0,
        help_text="Monto total pagado hasta la fecha"
    )
    
    # Campos para análisis de mercado internacional
    mercado_destino = models.ForeignKey(
        MercadoDestino, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    incoterm = models.CharField(
        max_length=10, 
        blank=True, 
        null=True,
        help_text="Términos internacionales de comercio (FOB, CIF, etc.)"
    )
    
    moneda_venta = models.CharField(
        max_length=3, 
        default='MXN',
        help_text="Moneda en la que se realizó la venta"
    )
    
    tipo_cambio = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        default=1.0000,
        help_text="Tipo de cambio aplicado al momento de la venta"
    )

    def __str__(self):
        return f"-{self.carga} - {self.fecha_salida_manifiesto} - {self.monto} - {self.cliente.nombre}- {self.producto.nombre}"
    
    def save(self, *args, **kwargs):
        """Override save para calcular automáticamente campos derivados"""
        # Establecer mercado de destino basado en el cliente
        if not self.mercado_destino and self.cliente.mercado_destino:
            self.mercado_destino = self.cliente.mercado_destino
        
        # Calcular fecha de vencimiento para créditos
        if self.modalidad_pago == self.ModalidadPago.CREDITO and self.termino_credito:
            if not self.fecha_vencimiento:
                self.fecha_vencimiento = self.fecha_deposito + timedelta(days=self.termino_credito.dias_credito)
        
        # Establecer estado de cobranza inicial
        if self.modalidad_pago == self.ModalidadPago.CONTADO:
            self.estado_cobranza = self.EstadoCobranza.PAGADO
            self.monto_pagado = self.monto
        elif self.modalidad_pago == self.ModalidadPago.CREDITO and not self.pk:
            self.estado_cobranza = self.EstadoCobranza.PENDIENTE
            
        super().save(*args, **kwargs)
    
    def saldo_pendiente(self):
        """Calcula el saldo pendiente de pago"""
        return float(self.monto.amount) - float(self.monto_pagado.amount)
    
    def dias_vencido(self):
        """Calcula los días de vencimiento (negativo si no ha vencido)"""
        if not self.fecha_vencimiento:
            return 0
        delta = timezone.now().date() - self.fecha_vencimiento
        return delta.days
    
    def esta_vencida(self):
        """Determina si la venta está vencida"""
        return self.dias_vencido() > 0 and self.estado_cobranza in [self.EstadoCobranza.PENDIENTE, self.EstadoCobranza.PARCIAL]
    
    def calcular_interes_mora(self):
        """Calcula el interés moratorio acumulado"""
        if not self.esta_vencida() or not self.termino_credito:
            return 0
        
        dias_mora = self.dias_vencido()
        meses_mora = dias_mora / 30.0
        saldo = self.saldo_pendiente()
        interes_total = saldo * float(self.termino_credito.tasa_interes_mensual) * meses_mora
        
        return round(interes_total, 2)
    
    def monto_total_con_interes(self):
        """Calcula el monto total incluyendo intereses moratorios"""
        return self.saldo_pendiente() + self.calcular_interes_mora()
    
    @property
    def es_exportacion(self):
        """Determina si es una venta de exportación"""
        return self.tipo_venta == self.TipoVenta.EXPORTACION
    
    @property
    def requiere_documentacion_especial(self):
        """Determina si requiere documentación especial basado en el mercado"""
        if self.mercado_destino:
            return self.mercado_destino.requiere_documentacion_especial
        return self.es_exportacion
    
    def actualizar_estado_cobranza(self):
        """Actualiza el estado de cobranza basado en los pagos registrados"""
        if self.modalidad_pago == self.ModalidadPago.CONTADO:
            return
            
        total_pagos = sum(pago.monto_pago.amount for pago in self.pagos.all())
        self.monto_pagado.amount = total_pagos
        
        saldo = self.saldo_pendiente()
        
        if saldo <= 0:
            self.estado_cobranza = self.EstadoCobranza.PAGADO
        elif total_pagos > 0:
            if self.esta_vencida():
                self.estado_cobranza = self.EstadoCobranza.VENCIDO
            else:
                self.estado_cobranza = self.EstadoCobranza.PARCIAL
        else:
            if self.esta_vencida():
                self.estado_cobranza = self.EstadoCobranza.VENCIDO
            else:
                self.estado_cobranza = self.EstadoCobranza.PENDIENTE
                
        self.save()
        
    class Meta:
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering = ['-fecha_registro']
        indexes = [
            models.Index(fields=['modalidad_pago', 'estado_cobranza']),
            models.Index(fields=['fecha_vencimiento']),
            models.Index(fields=['cliente', 'estado_cobranza']),
        ]

class PagoVenta(models.Model):
    """Modelo para rastrear pagos individuales de ventas a crédito"""
    from gastos.models import Cuenta
    
    venta = models.ForeignKey(Ventas, on_delete=models.CASCADE, related_name='pagos')
    fecha_pago = models.DateField()
    monto_pago = MoneyField(max_digits=12, decimal_places=2, default_currency='MXN')
    cuenta_destino = models.ForeignKey(Cuenta, on_delete=models.CASCADE)
    
    class MetodoPago(models.TextChoices):
        EFECTIVO = 'Efectivo', 'Efectivo'
        TRANSFERENCIA = 'Transferencia', 'Transferencia Bancaria'
        CHEQUE = 'Cheque', 'Cheque'
        TARJETA = 'Tarjeta', 'Tarjeta de Crédito/Débito'
        
    metodo_pago = models.CharField(max_length=15, choices=MetodoPago.choices)
    referencia = models.CharField(max_length=100, blank=True, null=True, help_text="Número de referencia o cheque")
    notas = models.TextField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Pago {self.monto_pago} - {self.venta.carga} - {self.fecha_pago}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Actualizar el estado de la venta después de registrar el pago
        self.venta.actualizar_estado_cobranza()
        
    class Meta:
        verbose_name = 'Pago de Venta'
        verbose_name_plural = 'Pagos de Ventas'
        ordering = ['-fecha_pago']        