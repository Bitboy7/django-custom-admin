from django.db import models
from catalogo.models import Sucursal, Pais, Producto
from django.utils.html import format_html
from djmoney.models.fields import MoneyField
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime, timedelta
from decimal import Decimal
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
    """
    Anticipo de cliente - Pago adelantado que se aplicará a futuras ventas.
    
    Estándares Bancarios Implementados:
    - RF07: No se puede asignar un anticipo a una venta ya completada
    - RF08: Un anticipo solo puede estar en un estado a la vez
    - RF09: Control de disponibilidad del anticipo antes de asignación
    - RF10: Auditoría de cambios de estado
    """
    from gastos.models import Cuenta
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE)
    monto = MoneyField(
        max_digits=10, 
        decimal_places=2, 
        default_currency='MXN'
    )
    fecha = models.DateField()
    descripcion = models.TextField(blank=True, null=True, default='Sin descripción')
    folio_factura_anticipo = models.CharField(
        max_length=50, null=True, blank=True,
        verbose_name='Folio factura anticipo',
        help_text="Folio del CFDI de anticipo (ej: B 1980)"
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    class Estado_anticipo(models.TextChoices):
        Pendiente = 'Pendiente', 'Pendiente de Aplicar'
        Aplicado = 'Aplicado', 'Aplicado a Venta'
        Cancelado = 'Cancelado', 'Cancelado'
    
    estado_anticipo = models.CharField(
        max_length=20, 
        choices=Estado_anticipo.choices, 
        default=Estado_anticipo.Pendiente
    )
    
    def __str__(self):
        return f"Anticipo de {self.cliente.nombre} - {self.monto} ({self.estado_anticipo})"
    
    def clean(self):
        """
        Validaciones de nivel bancario para anticipos.
        """
        from django.core.exceptions import ValidationError
        
        # Validar monto positivo
        if self.monto.amount <= 0:
            raise ValidationError({
                'monto': 'El monto del anticipo debe ser mayor a cero.'
            })
        
        # Validar fecha no futura
        if self.fecha > timezone.now().date():
            raise ValidationError({
                'fecha': 'La fecha del anticipo no puede ser futura.'
            })
        
        # RF09: Validar disponibilidad si está siendo aplicado
        if self.estado_anticipo == self.Estado_anticipo.Aplicado:
            # Verificar que hay una venta asociada
            if not hasattr(self, 'ventas') or not self.ventas.exists():
                raise ValidationError({
                    'estado_anticipo': 'No se puede marcar como Aplicado sin una venta asociada.'
                })
    
    def puede_ser_aplicado(self):
        """Verifica si el anticipo está disponible para ser aplicado"""
        return self.estado_anticipo == self.Estado_anticipo.Pendiente
    
    def aplicar_a_venta(self, venta):
        """
        Aplica el anticipo a una venta específica.
        Implementa validaciones bancarias.
        """
        from django.core.exceptions import ValidationError
        from django.db import transaction
        
        with transaction.atomic():
            # Validar que el anticipo esté disponible
            if not self.puede_ser_aplicado():
                raise ValidationError(
                    f'Este anticipo ya fue {self.estado_anticipo.lower()}. '
                    'Solo se pueden aplicar anticipos pendientes.'
                )
            
            # RF07: Validar que la venta NO esté completada
            if venta.estado_cobranza == Ventas.EstadoCobranza.PAGADO:
                raise ValidationError(
                    'No se puede aplicar un anticipo a una venta que ya está completamente pagada.'
                )
            
            # Validar que el anticipo sea del mismo cliente
            if self.cliente_id != venta.cliente_id:
                raise ValidationError(
                    f'El anticipo es del cliente {self.cliente.nombre} pero la venta es de {venta.cliente.nombre}. '
                    'El cliente debe coincidir.'
                )
            
            # Marcar anticipo como aplicado
            self.estado_anticipo = self.Estado_anticipo.Aplicado
            self.save(update_fields=['estado_anticipo'])
            
            # Asignar anticipo a la venta
            venta.anticipo = self
            venta.save(update_fields=['anticipo'])
            
            # Auditoría
            self._registrar_aplicacion(venta)
    
    def _registrar_aplicacion(self, venta):
        """Registra la aplicación del anticipo en auditoría"""
        try:
            from auditoria.models import LogActividad
            LogActividad.objects.create(
                usuario=None,
                nombre_usuario='Sistema',
                tipo_accion='update',
                descripcion=f'Anticipo de ${self.monto.amount:,.2f} aplicado a venta {venta.carga}',
                modelo_afectado='Anticipo',
                objeto_id=str(self.pk),
                campos_modificados={
                    'estado_anticipo': {'de': 'Pendiente', 'a': 'Aplicado'},
                    'venta_aplicada': venta.id,
                },
            )
        except Exception:
            pass

    class Meta:
        verbose_name = 'Anticipo'
        verbose_name_plural = 'Anticipos'
        ordering = ['-fecha_registro']
        indexes = [
            models.Index(fields=['cliente', 'estado_anticipo']),
            models.Index(fields=['estado_anticipo']),
            models.Index(fields=['fecha']),
        ]
        # Constraint de BD: monto positivo
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monto__gt=0),
                name='anticipo_monto_positivo'
            ),
        ]
        
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
    cantidad = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text="Cantidad vendida (ej: 1500.000 kg)"
    )
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

    class TipoRegistro(models.TextChoices):
        VENTA = 'VENTA', 'Venta'
        MAQUILA = 'MAQUILA', 'Maquila'

    tipo_registro = models.CharField(
        max_length=10,
        choices=TipoRegistro.choices,
        default=TipoRegistro.VENTA,
        help_text="Tipo de registro: Venta normal o Maquila"
    )

    # ── Documentación Fiscal ──────────────────────────────────────────────
    fecha_emision_cfdi = models.DateField(
        null=True, blank=True,
        verbose_name='Fecha emisión CFDI',
        help_text="Fecha de emisión del CFDI de exportación"
    )
    folio_factura = models.CharField(
        max_length=50, null=True, blank=True,
        verbose_name='Folio factura',
        help_text="Folio del CFDI (ej: B 1996)"
    )
    cfdi_cancelado = models.CharField(
        max_length=100, null=True, blank=True,
        verbose_name='CFDIs cancelados',
    )
    nota_credito = models.CharField(
        max_length=50, null=True, blank=True,
        verbose_name='Nota de crédito',
    )
    nota_cargo = models.CharField(
        max_length=50, null=True, blank=True,
        verbose_name='Nota de cargo',
    )
    # ── Referencia comprador / ajustes ────────────────────────────────────
    numero_carga_comprador = models.CharField(
        max_length=50, null=True, blank=True,
        verbose_name='Carga comprador (PANORAMA LOAD)',
    )
    ajuste = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Ajuste',
        help_text="Ajuste positivo (cargo) o negativo (descuento)"
    )

    def __str__(self):
        return f"-{self.carga} - {self.fecha_salida_manifiesto} - {self.monto} - {self.cliente.nombre}- {self.producto.nombre}"
    
    def clean(self):
        """
        Validaciones de integridad financiera nivel bancario.
        RF07: Previene asignación de anticipos a ventas completadas.
        """
        from django.core.exceptions import ValidationError
        
        # RF07: Validar asignación de anticipo
        if self.anticipo_id:
            # Verificar que el anticipo esté disponible
            if not self.anticipo.puede_ser_aplicado() and not self.pk:
                raise ValidationError({
                    'anticipo': f'Este anticipo ya fue {self.anticipo.estado_anticipo.lower()}. '
                               'Solo se pueden asignar anticipos pendientes.'
                })
            
            # Verificar que el anticipo sea del mismo cliente
            if self.anticipo.cliente_id != self.cliente_id:
                raise ValidationError({
                    'anticipo': f'El anticipo seleccionado es del cliente {self.anticipo.cliente.nombre} '
                               f'pero esta venta es de {self.cliente.nombre}. Deben coincidir.'
                })
            
            # RF07: NO permitir asignar anticipo si la venta ya está pagada
            if self.pk and self.estado_cobranza == self.EstadoCobranza.PAGADO:
                # Verificar si cambió el anticipo
                venta_original = Ventas.objects.get(pk=self.pk)
                if venta_original.anticipo_id != self.anticipo_id:
                    raise ValidationError({
                        'anticipo': 'No se puede asignar o cambiar el anticipo de una venta que ya está completamente pagada.'
                    })
        
        # Validar que montos sean positivos
        if self.monto.amount <= 0:
            raise ValidationError({
                'monto': 'El monto de la venta debe ser mayor a cero.'
            })
        
        if self.cantidad <= 0:
            raise ValidationError({
                'cantidad': 'La cantidad debe ser mayor a cero.'
            })
    
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
        
        # Invalidar cache del dashboard tras guardar venta
        try:
            from ventas.services.cache_service import CuentasPorCobrarCache
            from django.core.cache import cache
            cache.delete('cxc_dashboard_ventas_principal')
        except Exception:
            pass  # No fallar si el cache no está disponible
    
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
    
    @staticmethod
    def derive_estado_desde_totales(total_ventas, total_pagado, fecha_vencimiento):
        """
        Deriva el estado de cobranza a partir de totales agregados.
        Fuente de verdad única usada por views y management commands.
        """
        from django.utils import timezone as tz
        saldo = total_ventas - total_pagado
        if saldo <= 0:
            return 'Pagado'
        hoy = tz.now().date()
        vencida = bool(fecha_vencimiento and fecha_vencimiento < hoy)
        if total_pagado > 0:
            return 'Vencido' if vencida else 'Parcial'
        return 'Vencido' if vencida else 'Pendiente'

    def _sync_saldo_cxc(self):
        """Mantiene SaldoCliente sincronizado con el estado real de Ventas."""
        try:
            saldo = self.saldo_cxc  # reverse OneToOne accessor
            saldo.saldo_pendiente = self.monto - self.monto_pagado
            saldo.estado = self.estado_cobranza.upper()
            ultimo_pago = self.pagos.order_by('-fecha_pago').first()
            if ultimo_pago:
                saldo.fecha_ultimo_pago = ultimo_pago.fecha_registro
            saldo.save(update_fields=[
                'saldo_pendiente_amount', 'saldo_pendiente_currency',
                'estado', 'fecha_ultimo_pago',
            ])
        except Exception:
            pass  # SaldoCliente no existe en ventas de contado

    def actualizar_estado_cobranza(self):
        """Actualiza el estado de cobranza basado en los pagos registrados"""
        if self.modalidad_pago == self.ModalidadPago.CONTADO:
            return

        estado_anterior = self.estado_cobranza

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

        if self.estado_cobranza != estado_anterior:
            try:
                from auditoria.models import LogActividad
                LogActividad.objects.create(
                    usuario=None,
                    nombre_usuario='Sistema',
                    tipo_accion='update',
                    descripcion=f'Estado de cobranza cambió de {estado_anterior} a {self.estado_cobranza}',
                    modelo_afectado='Ventas',
                    objeto_id=str(self.pk),
                    campos_modificados={
                        'estado_cobranza': {'de': estado_anterior, 'a': self.estado_cobranza}
                    },
                )
            except Exception:
                pass

        self._sync_saldo_cxc()
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
    """
    Modelo para rastrear pagos individuales de ventas a crédito.
    
    Estándares Bancarios Implementados:
    - RF01: Un pago solo puede pertenecer a UNA venta (garantizado por ForeignKey)
    - RF02: No se permiten pagos a ventas completadas (validación clean)
    - RF03: No se permiten sobrepagos (validación clean)
    - RF04: Transacciones atómicas con control de concurrencia
    - RF05: Auditoría completa de cada pago
    - RF06: Validación en múltiples niveles (BD + Modelo + Formulario)
    """
    from gastos.models import Cuenta
    
    venta = models.ForeignKey(
        Ventas, 
        on_delete=models.CASCADE, 
        related_name='pagos',
        help_text="Venta a la que pertenece este pago (relación 1:N)"
    )
    fecha_pago = models.DateField()
    monto_pago = MoneyField(
        max_digits=12, 
        decimal_places=2, 
        default_currency='MXN'
    )
    cuenta_destino = models.ForeignKey(Cuenta, on_delete=models.CASCADE)
    
    class MetodoPago(models.TextChoices):
        EFECTIVO = 'Efectivo', 'Efectivo'
        TRANSFERENCIA = 'Transferencia', 'Transferencia Bancaria'
        CHEQUE = 'Cheque', 'Cheque'
        TARJETA = 'Tarjeta', 'Tarjeta de Crédito/Débito'
        
    metodo_pago = models.CharField(max_length=15, choices=MetodoPago.choices)
    referencia = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="Número de referencia, cheque o ID de transacción"
    )
    notas = models.TextField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    # Comprobante de pago (imagen o PDF)
    comprobante_pago = models.FileField(
        upload_to='comprobantes_pagos/%Y/%m/',
        blank=True,
        null=True,
        help_text="Comprobante de pago (imagen o PDF)",
        verbose_name="Comprobante de Pago"
    )
    
    def __str__(self):
        return f"Pago {self.monto_pago} - {self.venta.carga} - {self.fecha_pago}"
    
    def clean(self):
        """
        Validaciones de nivel bancario ANTES de guardar.
        Garantiza integridad financiera absoluta.
        """
        from django.core.exceptions import ValidationError
        
        if not self.venta_id:
            return  # Skip si aún no hay venta asignada (formulario vacío)
        
        # RF02: PROHIBIDO pagar ventas ya completadas
        if self.venta.estado_cobranza == Ventas.EstadoCobranza.PAGADO:
            raise ValidationError({
                'venta': 'Esta venta ya está completamente pagada. No se permiten más pagos.'
            })
        
        # RF03: PROHIBIDO sobrepagar una venta
        saldo_actual = self.venta.saldo_pendiente()
        
        # Si estamos editando, restar el monto original del pago
        if self.pk:
            pago_anterior = PagoVenta.objects.get(pk=self.pk)
            saldo_actual += float(pago_anterior.monto_pago.amount)
        
        if float(self.monto_pago.amount) > saldo_actual:
            raise ValidationError({
                'monto_pago': f'El monto del pago (${self.monto_pago.amount:,.2f}) excede el saldo pendiente (${saldo_actual:,.2f}). '
                              f'No se permiten sobrepagos.'
            })
        
        # Validar que no sea un monto negativo o cero
        if self.monto_pago.amount <= 0:
            raise ValidationError({
                'monto_pago': 'El monto del pago debe ser mayor a cero.'
            })
        
        # Validar fecha de pago no sea futura
        if self.fecha_pago > timezone.now().date():
            raise ValidationError({
                'fecha_pago': 'La fecha del pago no puede ser futura.'
            })
        
        # Validar que la venta sea a crédito
        if self.venta.modalidad_pago != Ventas.ModalidadPago.CREDITO:
            raise ValidationError({
                'venta': 'Solo se pueden registrar pagos para ventas a crédito.'
            })
    
    def save(self, *args, **kwargs):
        """
        Guarda el pago con transacción atómica y control de concurrencia.
        Implementa estándares bancarios de integridad transaccional.
        """
        from django.db import transaction
        from django.core.exceptions import ValidationError
        
        # RF04: Ejecutar TODA la operación en transacción atómica
        with transaction.atomic():
            # Control de concurrencia: bloquear la venta para evitar race conditions
            venta_bloqueada = Ventas.objects.select_for_update().get(pk=self.venta_id)
            
            # Validar nuevamente dentro de la transacción
            if venta_bloqueada.estado_cobranza == Ventas.EstadoCobranza.PAGADO and not self.pk:
                raise ValidationError('La venta ya está completamente pagada.')
            
            # Guardar el pago
            es_nuevo = self.pk is None
            super().save(*args, **kwargs)
            
            # Actualizar el estado de la venta
            venta_bloqueada.actualizar_estado_cobranza()
            
            # RF05: Auditoría completa
            self._registrar_auditoria(es_nuevo, venta_bloqueada)
        
        # Invalidar cache del dashboard tras registrar pago
        try:
            from django.core.cache import cache
            cache.delete('cxc_dashboard_ventas_principal')
        except Exception:
            pass  # No fallar si el cache no está disponible
    
    def _registrar_auditoria(self, es_nuevo, venta):
        """Registra el pago en auditoría para trazabilidad completa"""
        try:
            from auditoria.models import LogActividad
            LogActividad.objects.create(
                usuario=None,
                nombre_usuario='Sistema',
                tipo_accion='create' if es_nuevo else 'update',
                descripcion=f'Pago de ${self.monto_pago.amount:,.2f} registrado para venta {venta.carga}. '
                           f'Saldo restante: ${venta.saldo_pendiente():,.2f}',
                modelo_afectado='PagoVenta',
                objeto_id=str(self.pk),
                campos_modificados={
                    'monto_pago': float(self.monto_pago.amount),
                    'metodo_pago': self.metodo_pago,
                    'venta_id': venta.id,
                    'saldo_pendiente_venta': venta.saldo_pendiente(),
                },
            )
        except Exception:
            pass  # No fallar la transacción por errores de auditoría
        
    class Meta:
        verbose_name = 'Pago de Venta'
        verbose_name_plural = 'Pagos de Ventas'
        ordering = ['-fecha_pago', '-fecha_registro']
        indexes = [
            models.Index(fields=['venta', 'fecha_pago']),
            models.Index(fields=['fecha_pago']),
        ]
        # Constraint de BD: asegurar que monto_pago sea siempre positivo
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monto_pago__gt=0),
                name='pago_venta_monto_positivo'
            ),
        ]


# =============================================================================
# MODELOS DE CUENTAS POR COBRAR - EXTENSION DEL SISTEMA
# =============================================================================

class SaldoCliente(models.Model):
    """
    RF1: Tabla central para el control de saldos por cliente.
    Se crea automáticamente cuando hay una venta a crédito.
    RF2: Actualiza saldo instantáneamente con cada abono registrado.
    """
    from django.contrib.auth.models import User
    
    # Relaciones principales
    cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.PROTECT,
        related_name='saldos_cxc',
        help_text="Cliente asociado al saldo"
    )
    venta = models.OneToOneField(
        Ventas,
        on_delete=models.PROTECT,
        related_name='saldo_cxc',
        unique=True,
        help_text="Venta que origina este saldo"
    )
    
    # Montos y fechas
    monto_original = MoneyField(
        max_digits=12, 
        decimal_places=2,
        default_currency='MXN',
        help_text="Monto original de la venta a crédito"
    )
    saldo_pendiente = MoneyField(
        max_digits=12, 
        decimal_places=2,
        default_currency='MXN',
        help_text="Saldo actual después de abonos"
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        help_text="Momento en que se registró la deuda"
    )
    fecha_vencimiento = models.DateField(
        help_text="Fecha límite para pago sin intereses"
    )
    fecha_ultimo_pago = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Fecha del último pago registrado"
    )
    
    # Control de estado
    class EstadosSaldo(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        PARCIAL = 'PARCIAL', 'Parcial'
        PAGADO = 'PAGADO', 'Pagado'
        VENCIDO = 'VENCIDO', 'Vencido'
        INCOBRABLE = 'INCOBRABLE', 'Incobrable'
    
    estado = models.CharField(
        max_length=20, 
        choices=EstadosSaldo.choices, 
        default=EstadosSaldo.PENDIENTE,
        help_text="Estado actual del saldo"
    )
    
    # Metadatos
    moneda = models.CharField(
        max_length=3, 
        default='MXN',
        help_text="Moneda del saldo (MXN, USD, etc.)"
    )
    notas = models.TextField(
        blank=True,
        help_text="Notas adicionales sobre el saldo o gestiones de cobranza"
    )
    
    def __str__(self):
        return f"{self.cliente.nombre} - {self.monto_original} ({self.estado})"
    
    class Meta:
        db_table = 'ventas_saldo_cliente'
        verbose_name = 'Saldo por Cobrar'
        verbose_name_plural = 'Saldos por Cobrar'
        indexes = [
            models.Index(fields=['cliente', 'estado']),
            models.Index(fields=['fecha_vencimiento']),
            models.Index(fields=['estado', 'fecha_vencimiento']),
            models.Index(fields=['cliente', 'fecha_creacion']),
        ]
        ordering = ['-fecha_creacion']
    
    def dias_vencido(self):
        """RF3: Calcula días transcurridos desde vencimiento"""
        if self.fecha_vencimiento <= timezone.now().date():
            return (timezone.now().date() - self.fecha_vencimiento).days
        return 0
    
    def categoria_antiguedad(self):
        """RF3: Determina categoría de antigüedad del saldo según días vencidos"""
        dias = self.dias_vencido()
        if dias <= 0:
            return 'CORRIENTE'
        elif dias <= 30:
            return 'CORRIENTE'
        elif dias <= 60:
            return 'VENCIDO_1'  # 31-60 días
        elif dias <= 90:
            return 'VENCIDO_2'  # 61-90 días
        else:
            return 'VENCIDO_3'  # +90 días
    
    def porcentaje_pagado(self):
        """Calcula porcentaje pagado del total"""
        if self.monto_original.amount > 0:
            pagado = self.monto_original.amount - self.saldo_pendiente.amount
            return round((pagado / self.monto_original.amount) * 100, 2)
        return 0
    
    def interes_moratorio_acumulado(self):
        """Calcula interés moratorio acumulado si aplica"""
        if (self.dias_vencido() > 0 and 
            self.venta.termino_credito and 
            self.saldo_pendiente.amount > 0):
            
            dias_mora = self.dias_vencido()
            meses_mora = dias_mora / 30.0
            tasa_mensual = float(self.venta.termino_credito.tasa_interes_mensual)
            interes = float(self.saldo_pendiente.amount) * tasa_mensual * meses_mora
            return round(interes, 2)
        return 0
    
    def monto_total_con_intereses(self):
        """Calcula monto total incluyendo intereses moratorios"""
        return float(self.saldo_pendiente.amount) + self.interes_moratorio_acumulado()


class AntigüedadSaldo(models.Model):
    """
    RF3: Snapshot de antigüedad de saldos por cliente en una fecha específica.
    Se calcula periódicamente (diario/semanal) para análisis histórico y trending.
    """
    
    # Identificación y fecha de cálculo
    cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.CASCADE,
        related_name='historico_aging',
        help_text="Cliente analizado"
    )
    fecha_calculo = models.DateField(
        default=timezone.now,
        help_text="Fecha en que se calculó este aging"
    )
    
    # Distribución por buckets de aging (RF3)
    corriente = MoneyField(
        max_digits=12, 
        decimal_places=2, 
        default_currency='MXN',
        default=0,
        help_text="Saldos 0-30 días desde vencimiento"
    )
    vencido_1 = MoneyField(
        max_digits=12, 
        decimal_places=2, 
        default_currency='MXN',
        default=0,
        help_text="Saldos 31-60 días vencidos"
    )
    vencido_2 = MoneyField(
        max_digits=12, 
        decimal_places=2, 
        default_currency='MXN',
        default=0,
        help_text="Saldos 61-90 días vencidos"
    )
    vencido_3 = MoneyField(
        max_digits=12, 
        decimal_places=2, 
        default_currency='MXN',
        default=0,
        help_text="Saldos +90 días vencidos (morosos críticos)"
    )
    
    # Totales y métricas derivadas
    total_saldo = MoneyField(
        max_digits=12, 
        decimal_places=2, 
        default_currency='MXN',
        default=0,
        help_text="Total de saldos pendientes"
    )
    numero_facturas = models.PositiveIntegerField(
        default=0,
        help_text="Cantidad de facturas pendientes"
    )
    promedio_dias_pago = models.FloatField(
        null=True, 
        blank=True,
        help_text="Promedio histórico de días para pago completo"
    )
    
    # Metadatos
    moneda = models.CharField(
        max_length=3, 
        default='MXN',
        help_text="Moneda base para los cálculos"
    )
    calculado_por = models.CharField(
        max_length=100,
        default='Sistema',
        help_text="Sistema o usuario que ejecutó el cálculo"
    )
    
    def __str__(self):
        return f"{self.cliente.nombre} - Aging {self.fecha_calculo} - Total: {self.total_saldo}"
    
    class Meta:
        db_table = 'ventas_antiguedad_saldo'
        verbose_name = 'Análisis de Antigüedad'
        verbose_name_plural = 'Análisis de Antigüedad de Saldos'
        unique_together = [('cliente', 'fecha_calculo')]
        indexes = [
            models.Index(fields=['fecha_calculo']),
            models.Index(fields=['cliente', 'fecha_calculo']),
            models.Index(fields=['fecha_calculo', 'total_saldo']),
        ]
        ordering = ['-fecha_calculo', '-total_saldo']
    
    @property
    def porcentaje_corriente(self):
        """% del total que está corriente (no vencido)"""
        if self.total_saldo.amount > 0:
            return round((self.corriente.amount / self.total_saldo.amount) * 100, 2)
        return 0
    
    @property
    def porcentaje_vencido_critico(self):
        """% del total en categorías críticas (61+ días)"""
        if self.total_saldo.amount > 0:
            critico = self.vencido_2.amount + self.vencido_3.amount
            return round((critico / self.total_saldo.amount) * 100, 2)
        return 0
    
    @property 
    def clasificacion_riesgo(self):
        """Califica el riesgo del cliente basado en distribución de aging"""
        if self.total_saldo.amount == 0:
            return 'SIN_SALDO'
        
        pct_vencido_critico = self.porcentaje_vencido_critico
        
        if pct_vencido_critico >= 50:
            return 'ALTO'
        elif pct_vencido_critico >= 25:
            return 'MEDIO'
        elif pct_vencido_critico > 0:
            return 'BAJO'
        else:
            return 'EXCELENTE'
    
    def distribucion_porcentual(self):
        """Retorna dict con distribución porcentual por categoría"""
        if self.total_saldo.amount > 0:
            total = float(self.total_saldo.amount)
            return {
                'corriente': round((float(self.corriente.amount) / total) * 100, 2),
                'vencido_1': round((float(self.vencido_1.amount) / total) * 100, 2),
                'vencido_2': round((float(self.vencido_2.amount) / total) * 100, 2),
                'vencido_3': round((float(self.vencido_3.amount) / total) * 100, 2),
            }
        return {'corriente': 0, 'vencido_1': 0, 'vencido_2': 0, 'vencido_3': 0}


class EstadoCuentaCliente(models.Model):
    """
    RF4: Registra la generación de estados de cuenta para auditoría
    y facilita regeneración o consulta de reportes históricos.
    """
    from django.contrib.auth.models import User
    
    # Identificación del estado de cuenta
    cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.CASCADE,
        related_name='estados_cuenta',
        help_text="Cliente del estado de cuenta"
    )
    fecha_generacion = models.DateTimeField(
        auto_now_add=True,
        help_text="Momento en que se generó el reporte"
    )
    
    # Período del reporte
    periodo_inicio = models.DateField(
        help_text="Fecha de inicio del período analizado"
    )
    periodo_fin = models.DateField(
        help_text="Fecha de fin del período analizado"
    )
    
    # Resumen financiero del estado de cuenta (RF4: Venta Original - Suma de Abonos = Saldo Pendiente)
    total_ventas = MoneyField(
        max_digits=12, 
        decimal_places=2, 
        default_currency='MXN',
        default=0,
        help_text="Total de ventas a crédito en el período"
    )
    total_abonos = MoneyField(
        max_digits=12, 
        decimal_places=2, 
        default_currency='MXN',
        default=0,
        help_text="Total de abonos/pagos recibidos en el período"
    )
    saldo_final = MoneyField(
        max_digits=12, 
        decimal_places=2, 
        default_currency='MXN',
        default=0,
        help_text="Saldo pendiente al final del período (Ventas - Abonos)"
    )
    numero_facturas = models.PositiveIntegerField(
        default=0,
        help_text="Cantidad de facturas incluidas en el período"
    )
    
    # Control de generación y formato
    class FormatoEstado(models.TextChoices):
        WEB = 'WEB', 'Vista Web'
        PDF = 'PDF', 'Documento PDF'
        EXCEL = 'EXCEL', 'Hoja de Excel'
    
    formato_generado = models.CharField(
        max_length=10,
        choices=FormatoEstado.choices,
        default=FormatoEstado.WEB,
        help_text="Formato en que se generó el estado de cuenta"
    )
    
    archivo_generado = models.FileField(
        upload_to='estados_cuenta/%Y/%m/', 
        null=True, 
        blank=True,
        help_text="Archivo generado (PDF o Excel) si aplica"
    )
    
    # Metadatos de auditoría
    generado_por = models.CharField(
        max_length=150,
        help_text="Usuario que generó el estado de cuenta"
    )
    notas = models.TextField(
        blank=True,
        help_text="Notas adicionales sobre el estado de cuenta"
    )
    
    def __str__(self):
        return f"Estado {self.cliente.nombre} - {self.periodo_inicio} a {self.periodo_fin}"
    
    class Meta:
        db_table = 'ventas_estado_cuenta_cliente'
        verbose_name = 'Estado de Cuenta'
        verbose_name_plural = 'Estados de Cuenta de Clientes'
        indexes = [
            models.Index(fields=['cliente', 'fecha_generacion']),
            models.Index(fields=['periodo_inicio', 'periodo_fin']),
            models.Index(fields=['fecha_generacion']),
        ]
        ordering = ['-fecha_generacion']
    
    @property
    def duracion_periodo(self):
        """Calcula la duración del período en días"""
        return (self.periodo_fin - self.periodo_inicio).days
    
    @property
    def porcentaje_recuperacion(self):
        """Calcula el % de recuperación (abonos vs ventas)"""
        if self.total_ventas.amount > 0:
            return round((self.total_abonos.amount / self.total_ventas.amount) * 100, 2)
        return 0
    
    @property
    def promedio_por_factura(self):
        """Calcula el monto promedio por factura"""
        if self.numero_facturas > 0:
            return round(self.total_ventas.amount / self.numero_facturas, 2)
        return 0
    
    def nombre_archivo_sugerido(self):
        """Genera nombre sugerido para archivo de descarga"""
        fecha_inicio = self.periodo_inicio.strftime('%Y%m%d')
        fecha_fin = self.periodo_fin.strftime('%Y%m%d')
        cliente_limpio = ''.join(c for c in self.cliente.nombre if c.isalnum() or c in ' -_')[:20]
        return f"EstadoCuenta_{cliente_limpio}_{fecha_inicio}_{fecha_fin}"


class ConfiguracionCuentasPorCobrar(models.Model):
    """
    Configuraciones globales del módulo de cuentas por cobrar.
    Permite ajustar comportamiento sin cambios de código.
    Solo debe existir UN registro de configuración en el sistema.
    """
    
    # Parámetros de aging (RF3)
    dias_corriente = models.PositiveIntegerField(
        default=30,
        help_text="Días máximos para considerar saldo como 'Corriente'"
    )
    dias_vencido_1 = models.PositiveIntegerField(
        default=60,
        help_text="Días máximos para 'Vencido 1' (31-60 días)"
    )
    dias_vencido_2 = models.PositiveIntegerField(
        default=90,
        help_text="Días máximos para 'Vencido 2' (61-90 días)"
    )
    # Nota: Todo lo que exceda dias_vencido_2 se considera 'Vencido 3' (+90 días)
    
    # Automatización de procesos
    calculo_automatico_aging = models.BooleanField(
        default=True,
        help_text="Activar cálculo automático diario de aging"
    )
    hora_calculo_aging = models.TimeField(
        default='02:00:00',
        help_text="Hora del día para ejecutar cálculo automático"
    )
    
    class FrecuenciaCalculo(models.TextChoices):
        DIARIO = 'DIARIO', 'Diario'
        SEMANAL = 'SEMANAL', 'Semanal'
    
    frecuencia_calculo = models.CharField(
        max_length=10,
        choices=FrecuenciaCalculo.choices,
        default=FrecuenciaCalculo.DIARIO,
        help_text="Frecuencia para cálculo automático de aging"
    )
    
    # Alertas y notificaciones
    enviar_alertas_vencimiento = models.BooleanField(
        default=True,
        help_text="Enviar alertas automáticas por vencimientos próximos"
    )
    dias_previos_alerta = models.PositiveIntegerField(
        default=5,
        help_text="Días antes del vencimiento para enviar alerta"
    )
    email_responsable_cobranza = models.EmailField(
        blank=True,
        help_text="Email del responsable de cobranza para recibir alertas"
    )
    
    # Límites y validaciones
    permitir_sobregiro_credito = models.BooleanField(
        default=False,
        help_text="Permitir ventas que excedan límite de crédito (con autorización)"
    )
    porcentaje_sobregiro_permitido = models.FloatField(
        default=10.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Porcentaje máximo de sobregiro permitido sobre límite de crédito"
    )

    # Tipo de cambio de referencia
    tipo_cambio_usd = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=17.0000,
        validators=[MinValueValidator(0.0001)],
        help_text="Tipo de cambio USD→MXN vigente (actualizar manualmente cada día)"
    )
    
    # Metadatos
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Configuración CxC - Aging cada {self.frecuencia_calculo.lower()}"
    
    class Meta:
        db_table = 'ventas_configuracion_cxc'
        verbose_name = 'Configuración de Cuentas por Cobrar'
        verbose_name_plural = 'Configuraciones de Cuentas por Cobrar'
    
    def save(self, *args, **kwargs):
        """Asegurar que solo existe una configuración"""
        if not self.pk and ConfiguracionCuentasPorCobrar.objects.exists():
            raise ValueError("Solo se permite una configuración de Cuentas por Cobrar")
        super().save(*args, **kwargs)
    
    @classmethod
    def obtener_configuracion(cls):
        """Obtiene o crea la configuración única del sistema"""
        config, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'dias_corriente': 30,
                'dias_vencido_1': 60,
                'dias_vencido_2': 90,
                'calculo_automatico_aging': True,
                'enviar_alertas_vencimiento': True,
                'dias_previos_alerta': 5,
                'permitir_sobregiro_credito': False,
                'porcentaje_sobregiro_permitido': 10.0,
                'tipo_cambio_usd': 17.0000,
            }
        )
        return config


# =============================================================================
# OBLIGACIONES FISCALES
# =============================================================================

class ObligacionFiscal(models.Model):
    """
    Registro manual de obligaciones fiscales por período semestral.
    Se captura desde el admin para incluirlo en el reporte global de cobranza.
    """
    periodo = models.CharField(
        max_length=100,
        help_text="Ej: Semestre Julio-Diciembre 2025"
    )
    isr_ingresos_propios = MoneyField(
        max_digits=14, decimal_places=2, default_currency='MXN', default=0,
        help_text="ISR Ingresos Propios"
    )
    isr_resico = MoneyField(
        max_digits=14, decimal_places=2, default_currency='MXN', default=0,
        help_text="ISR RESICO Servicios Profesionales"
    )
    isr_retenciones_salarios = MoneyField(
        max_digits=14, decimal_places=2, default_currency='MXN', default=0,
        help_text="ISR Retenciones por Salarios"
    )
    iva_retenciones_profesionales = MoneyField(
        max_digits=14, decimal_places=2, default_currency='MXN', default=0,
        help_text="IVA Retenciones Servicios Profesionales"
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def total_impuestos(self):
        return (
            self.isr_ingresos_propios.amount
            + self.isr_resico.amount
            + self.isr_retenciones_salarios.amount
            + self.iva_retenciones_profesionales.amount
        )

    def __str__(self):
        return f"Impuestos {self.periodo}"

    class Meta:
        verbose_name = 'Obligación Fiscal'
        verbose_name_plural = 'Obligaciones Fiscales'
        ordering = ['-fecha_registro']

    def rangos_aging_configurados(self):
        """Retorna dict con los rangos de aging configurados"""
        return {
            'corriente': f"0-{self.dias_corriente} días",
            'vencido_1': f"{self.dias_corriente + 1}-{self.dias_vencido_1} días",
            'vencido_2': f"{self.dias_vencido_1 + 1}-{self.dias_vencido_2} días",
            'vencido_3': f"{self.dias_vencido_2 + 1}+ días (moroso crítico)"
        }