# Documentación Técnica - Sistema de Cuentas por Cobrar

## 📋 Información General

**Proyecto**: Django Custom Admin - Extensión Cuentas por Cobrar  
**Versión**: 1.0.0  
**Fecha**: 11 de marzo, 2026  
**Autor**: Sistema de Desarrollo  
**Módulo Base**: ventas/

## 🎯 Objetivos Técnicos

### Objetivo Principal

Extender el módulo `ventas/` existente para implementar un sistema integral de gestión de cuentas por cobrar que automatice la sincronización de deuda, el registro de abonos multiforma, el cálculo de antigüedad de saldos y la generación de reportes históricos.

### Objetivos Específicos

1. **Automatización**: Eliminar procesos manuales en el registro de deuda por ventas a crédito
2. **Trazabilidad**: Mantener historial completo de pagos y estados de cuenta
3. **Análisis**: Proveer herramientas para análisis de riesgo y performance de cobranza
4. **Integración**: Aprovechar la infraestructura existente (cache, logs, reportes)

---

## 🏗️ Arquitectura del Sistema

### Stack Tecnológico Actual

```
Frontend: Django Admin + Django Unfold (UI personalizada)
Backend: Django 5.0 + Python 3.11
Base de Datos: MySQL 8.0
Cache: Redis 6.2 (con fallback local)
Logs: LogActividad middleware
Reportes: openpyxl + Excel export
Monedas: django-money (validación + formateo)
```

### Principios de Diseño

- **Extensión**: No modificar modelos existentes, solo extender
- **Compatibilidad**: Mantener funcionalidad actual intacta
- **Performance**: Usar cache Redis para cálculos frecuentes
- **Auditoría**: Registrar todos los cambios en LogActividad
- **Transaccionalidad**: Operaciones críticas en transacciones atómicas

---

## 📊 Diseño de Base de Datos

### Modelos Existentes (No Modificar)

```python
# ventas/models.py - BASE EXISTENTE
class Ventas(models.Model):
    cliente = models.ForeignKey(Cliente)
    modalidad_pago = models.CharField()  # Crédito, Contado, Mixto
    estado_cobranza = models.CharField()  # Pagado, Pendiente, Parcial, Vencido, Incobrable
    total_venta = MoneyField()
    fecha_vencimiento = models.DateField()
    # ... otros campos existentes

class PagoVenta(models.Model):
    venta = models.ForeignKey(Ventas)
    monto = MoneyField()
    metodo_pago = models.CharField()  # efectivo, transferencia, tarjeta, cheque
    fecha_pago = models.DateTimeField()
    # ... otros campos existentes

class Cliente(models.Model):
    limite_credito = MoneyField()
    termino_credito = models.ForeignKey(TerminoCredito)
    # ... otros campos existentes
```

### Nuevos Modelos a Implementar

#### 1. SaldoCliente - Registro Principal de Cuentas por Cobrar

```python
class SaldoCliente(models.Model):
    """
    Tabla central para el control de saldos por cliente.
    Se crea automáticamente cuando hay una venta a crédito.
    """

    # Relaciones
    cliente = models.ForeignKey(
        'Cliente',
        on_delete=models.PROTECT,
        related_name='saldos_cxc'
    )
    venta = models.OneToOneField(
        'Ventas',
        on_delete=models.PROTECT,
        related_name='saldo_cxc',
        unique=True
    )

    # Montos y fechas
    monto_original = MoneyField(
        max_digits=12,
        decimal_places=2,
        help_text="Monto original de la venta a crédito"
    )
    saldo_pendiente = MoneyField(
        max_digits=12,
        decimal_places=2,
        help_text="Saldo actual después de abonos"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateField()
    fecha_ultimo_pago = models.DateTimeField(null=True, blank=True)

    # Control de estado
    ESTADOS_SALDO = [
        ('PENDIENTE', 'Pendiente'),
        ('PARCIAL', 'Parcial'),
        ('PAGADO', 'Pagado'),
        ('VENCIDO', 'Vencido'),
        ('INCOBRABLE', 'Incobrable'),
    ]
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS_SALDO,
        default='PENDIENTE'
    )

    # Metadatos
    moneda = models.CharField(max_length=3, default='MXN')
    notas = models.TextField(blank=True)
    creado_por = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        db_table = 'ventas_saldo_cliente'
        indexes = [
            models.Index(fields=['cliente', 'estado']),
            models.Index(fields=['fecha_vencimiento']),
            models.Index(fields=['estado', 'fecha_vencimiento']),
        ]

    def dias_vencido(self):
        """Calcula días transcurridos desde vencimiento"""
        if self.fecha_vencimiento <= timezone.now().date():
            return (timezone.now().date() - self.fecha_vencimiento).days
        return 0

    def categoria_antiguedad(self):
        """Determina categoría de antigüedad del saldo"""
        dias = self.dias_vencido()
        if dias <= 30:
            return 'CORRIENTE'
        elif dias <= 60:
            return 'VENCIDO_1'
        elif dias <= 90:
            return 'VENCIDO_2'
        else:
            return 'VENCIDO_3'

    def porcentaje_pagado(self):
        """Calcula porcentaje pagado del total"""
        if self.monto_original > 0:
            pagado = self.monto_original - self.saldo_pendiente
            return (pagado / self.monto_original) * 100
        return 0
```

#### 2. AntigüedadSaldo - Análisis de Aging

```python
class AntigüedadSaldo(models.Model):
    """
    Snapshot de antigüedad de saldos por cliente en una fecha específica.
    Se calcula periódicamente (diario/semanal) para análisis histórico.
    """

    # Identificación
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    fecha_calculo = models.DateField(default=timezone.now)

    # Distribución por aging buckets (en la moneda del cliente)
    corriente = MoneyField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Saldos 0-30 días"
    )
    vencido_1 = MoneyField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Saldos 31-60 días"
    )
    vencido_2 = MoneyField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Saldos 61-90 días"
    )
    vencido_3 = MoneyField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Saldos +90 días"
    )

    # Totales y métricas
    total_saldo = MoneyField(max_digits=12, decimal_places=2, default=0)
    numero_facturas = models.PositiveIntegerField(default=0)
    promedio_dias_pago = models.FloatField(null=True, blank=True)

    # Metadatos
    moneda = models.CharField(max_length=3, default='MXN')
    calculado_por = models.CharField(max_length=100)  # Sistema/Usuario

    class Meta:
        db_table = 'ventas_antiguedad_saldo'
        unique_together = [('cliente', 'fecha_calculo')]
        indexes = [
            models.Index(fields=['fecha_calculo']),
            models.Index(fields=['cliente', 'fecha_calculo']),
        ]

    @property
    def porcentaje_corriente(self):
        """% del total que está corriente"""
        if self.total_saldo > 0:
            return (self.corriente / self.total_saldo) * 100
        return 0

    @property
    def riesgo_cobranza(self):
        """Califica el riesgo basado en distribución de aging"""
        if self.total_saldo == 0:
            return 'SIN_SALDO'

        pct_vencido = ((self.vencido_2 + self.vencido_3) / self.total_saldo) * 100

        if pct_vencido >= 50:
            return 'ALTO'
        elif pct_vencido >= 25:
            return 'MEDIO'
        else:
            return 'BAJO'
```

#### 3. EstadoCuentaCliente - Estados de Cuenta Históricos

```python
class EstadoCuentaCliente(models.Model):
    """
    Registra la generación de estados de cuenta para auditoría
    y facilita regeneración de reportes históricos.
    """

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()

    # Resumen del estado de cuenta
    total_ventas = MoneyField(max_digits=12, decimal_places=2, default=0)
    total_abonos = MoneyField(max_digits=12, decimal_places=2, default=0)
    saldo_final = MoneyField(max_digits=12, decimal_places=2, default=0)
    numero_facturas = models.PositiveIntegerField(default=0)

    # Control de generación
    generado_por = models.ForeignKey(User, on_delete=models.PROTECT)
    formato_generado = models.CharField(
        max_length=10,
        choices=[('PDF', 'PDF'), ('EXCEL', 'Excel'), ('WEB', 'Web')],
        default='WEB'
    )
    archivo_generado = models.FileField(
        upload_to='estados_cuenta/',
        null=True, blank=True
    )

    class Meta:
        db_table = 'ventas_estado_cuenta_cliente'
        indexes = [
            models.Index(fields=['cliente', 'fecha_generacion']),
            models.Index(fields=['periodo_inicio', 'periodo_fin']),
        ]
```

#### 4. ConfiguracionCuentasPorCobrar - Parámetros del Sistema

```python
class ConfiguracionCuentasPorCobrar(models.Model):
    """
    Configuraciones globales del módulo de cuentas por cobrar.
    Permite ajustar comportamiento sin cambios de código.
    """

    # Parámetros de aging
    dias_corriente = models.PositiveIntegerField(default=30)
    dias_vencido_1 = models.PositiveIntegerField(default=60)
    dias_vencido_2 = models.PositiveIntegerField(default=90)

    # Automatización
    calculo_automatico_aging = models.BooleanField(default=True)
    hora_calculo_aging = models.TimeField(default='02:00:00')
    frecuencia_calculo = models.CharField(
        max_length=10,
        choices=[('DIARIO', 'Diario'), ('SEMANAL', 'Semanal')],
        default='DIARIO'
    )

    # Alertas y notificaciones
    enviar_alertas_vencimiento = models.BooleanField(default=True)
    dias_previos_alerta = models.PositiveIntegerField(default=5)
    email_responsable_cobranza = models.EmailField(blank=True)

    # Límites y validaciones
    permitir_sobregiro_credito = models.BooleanField(default=False)
    porcentaje_sobregiro_permitido = models.FloatField(default=10.0)

    class Meta:
        db_table = 'ventas_configuracion_cxc'
        verbose_name = 'Configuración Cuentas por Cobrar'
        verbose_name_plural = 'Configuraciones Cuentas por Cobrar'
```

---

## 🔧 Servicios y Lógica de Negocio

### 1. Servicio de Sincronización de Deuda

```python
# ventas/services/cuentas_por_cobrar_service.py

class CuentasPorCobrarService:
    """
    Servicio principal para operaciones de cuentas por cobrar.
    Centraliza la lógica de negocio y mantiene consistencia.
    """

    @staticmethod
    @transaction.atomic
    def sincronizar_deuda_venta(venta_id):
        """
        RF1: Crea automáticamente registro en SaldoCliente
        cuando se registra venta a crédito.
        """
        try:
            venta = Ventas.objects.get(id=venta_id)

            # Solo procesar ventas a crédito
            if venta.modalidad_pago not in ['Crédito', 'Mixto']:
                return None

            # Verificar que no existe saldo previo
            if hasattr(venta, 'saldo_cxc'):
                raise ValueError(f"Ya existe saldo para venta {venta.id}")

            # Calcular monto a crédito
            if venta.modalidad_pago == 'Crédito':
                monto_credito = venta.total_venta
            elif venta.modalidad_pago == 'Mixto':
                # Asumir que existe campo monto_credito en Ventas
                monto_credito = getattr(venta, 'monto_credito', venta.total_venta)

            # Crear registro de saldo
            saldo = SaldoCliente.objects.create(
                cliente=venta.cliente,
                venta=venta,
                monto_original=monto_credito,
                saldo_pendiente=monto_credito,
                fecha_vencimiento=venta.fecha_vencimiento,
                moneda=venta.moneda_venta or 'MXN',
                creado_por=venta.creado_por if hasattr(venta, 'creado_por') else None
            )

            # Log de auditoría
            LogActividad.objects.create(
                tabla='SaldoCliente',
                accion='CREATE',
                objeto_id=saldo.id,
                descripcion=f'Saldo creado automáticamente para venta {venta.id}',
                usuario=venta.creado_por if hasattr(venta, 'creado_por') else None
            )

            return saldo

        except Exception as e:
            logger.error(f"Error sincronizando deuda venta {venta_id}: {e}")
            raise

    @staticmethod
    @transaction.atomic
    def registrar_abono(saldo_id, monto_abono, metodo_pago, fecha_pago=None, referencia='', usuario=None):
        """
        RF2: Registra abono parcial y actualiza saldo instantáneamente.
        """
        try:
            saldo = SaldoCliente.objects.select_for_update().get(id=saldo_id)

            # Validaciones
            if monto_abono <= 0:
                raise ValueError("El monto del abono debe ser positivo")

            if monto_abono > saldo.saldo_pendiente:
                if not ConfiguracionCuentasPorCobrar.load().permitir_sobregiro_credito:
                    raise ValueError("El abono excede el saldo pendiente")

            # Crear registro de pago
            pago = PagoVenta.objects.create(
                venta=saldo.venta,
                monto=monto_abono,
                metodo_pago=metodo_pago,
                fecha_pago=fecha_pago or timezone.now(),
                referencia=referencia,
                registrado_por=usuario
            )

            # Actualizar saldo
            saldo.saldo_pendiente -= monto_abono
            saldo.fecha_ultimo_pago = pago.fecha_pago

            # Actualizar estado según saldo restante
            if saldo.saldo_pendiente <= 0:
                saldo.estado = 'PAGADO'
                saldo.venta.estado_cobranza = 'Pagado'
            elif saldo.saldo_pendiente < saldo.monto_original:
                saldo.estado = 'PARCIAL'
                saldo.venta.estado_cobranza = 'Parcial'

            saldo.save()
            saldo.venta.save()

            # Invalidar cache de métricas del cliente
            cache.delete(f'cliente_metricas_{saldo.cliente.id}')

            # Log de auditoría
            LogActividad.objects.create(
                tabla='SaldoCliente',
                accion='UPDATE',
                objeto_id=saldo.id,
                descripcion=f'Abono registrado: {monto_abono} - Nuevo saldo: {saldo.saldo_pendiente}',
                usuario=usuario
            )

            return pago, saldo

        except Exception as e:
            logger.error(f"Error registrando abono para saldo {saldo_id}: {e}")
            raise

    @staticmethod
    def calcular_antiguedad_cliente(cliente_id, fecha_corte=None):
        """
        RF3: Calcula y clasifica antigüedad de saldos por cliente.
        """
        if fecha_corte is None:
            fecha_corte = timezone.now().date()

        try:
            cliente = Cliente.objects.get(id=cliente_id)

            # Obtener saldos pendientes
            saldos = SaldoCliente.objects.filter(
                cliente=cliente,
                estado__in=['PENDIENTE', 'PARCIAL', 'VENCIDO']
            ).exclude(saldo_pendiente=0)

            # Inicializar buckets
            aging_data = {
                'corriente': Money(0, 'MXN'),
                'vencido_1': Money(0, 'MXN'),
                'vencido_2': Money(0, 'MXN'),
                'vencido_3': Money(0, 'MXN'),
                'numero_facturas': saldos.count()
            }

            # Clasificar por antigüedad
            for saldo in saldos:
                dias_desde_vencimiento = (fecha_corte - saldo.fecha_vencimiento).days

                if dias_desde_vencimiento <= 30:
                    aging_data['corriente'] += saldo.saldo_pendiente
                elif dias_desde_vencimiento <= 60:
                    aging_data['vencido_1'] += saldo.saldo_pendiente
                elif dias_desde_vencimiento <= 90:
                    aging_data['vencido_2'] += saldo.saldo_pendiente
                else:
                    aging_data['vencido_3'] += saldo.saldo_pendiente

            aging_data['total_saldo'] = (
                aging_data['corriente'] + aging_data['vencido_1'] +
                aging_data['vencido_2'] + aging_data['vencido_3']
            )

            # Crear/actualizar registro de antigüedad
            antiguedad, created = AntigüedadSaldo.objects.update_or_create(
                cliente=cliente,
                fecha_calculo=fecha_corte,
                defaults=aging_data
            )

            return antiguedad

        except Exception as e:
            logger.error(f"Error calculando antigüedad cliente {cliente_id}: {e}")
            raise

    @staticmethod
    def generar_estado_cuenta(cliente_id, fecha_inicio, fecha_fin, formato='WEB', usuario=None):
        """
        RF4: Genera estado de cuenta histórico por cliente.
        """
        try:
            cliente = Cliente.objects.get(id=cliente_id)

            # Obtener movimientos del período
            ventas = Ventas.objects.filter(
                cliente=cliente,
                fecha_venta__range=[fecha_inicio, fecha_fin]
            ).order_by('fecha_venta')

            pagos = PagoVenta.objects.filter(
                venta__cliente=cliente,
                fecha_pago__range=[fecha_inicio, fecha_fin]
            ).order_by('fecha_pago')

            # Construir datos del estado de cuenta
            movimientos = []
            saldo_acumulado = Money(0, 'MXN')

            # Agregar ventas
            for venta in ventas:
                if venta.modalidad_pago in ['Crédito', 'Mixto']:
                    monto_credito = venta.monto_credito if hasattr(venta, 'monto_credito') else venta.total_venta
                    saldo_acumulado += monto_credito

                    movimientos.append({
                        'fecha': venta.fecha_venta,
                        'tipo': 'VENTA',
                        'referencia': venta.numero_factura,
                        'concepto': f'Venta a crédito',
                        'cargo': monto_credito,
                        'abono': Money(0, 'MXN'),
                        'saldo': saldo_acumulado
                    })

            # Agregar pagos
            for pago in pagos:
                saldo_acumulado -= pago.monto

                movimientos.append({
                    'fecha': pago.fecha_pago.date(),
                    'tipo': 'PAGO',
                    'referencia': pago.referencia,
                    'concepto': f'Pago - {pago.metodo_pago}',
                    'cargo': Money(0, 'MXN'),
                    'abono': pago.monto,
                    'saldo': saldo_acumulado
                })

            # Ordenar cronológicamente
            movimientos.sort(key=lambda x: x['fecha'])

            # Crear registro del estado de cuenta
            estado_cuenta = EstadoCuentaCliente.objects.create(
                cliente=cliente,
                periodo_inicio=fecha_inicio,
                periodo_fin=fecha_fin,
                total_ventas=sum(v.total_venta for v in ventas if v.modalidad_pago in ['Crédito', 'Mixto']),
                total_abonos=sum(p.monto for p in pagos),
                saldo_final=saldo_acumulado,
                numero_facturas=ventas.count(),
                generado_por=usuario,
                formato_generado=formato
            )

            return {
                'estado_cuenta': estado_cuenta,
                'movimientos': movimientos,
                'resumen': {
                    'cliente': cliente,
                    'periodo_inicio': fecha_inicio,
                    'periodo_fin': fecha_fin,
                    'total_ventas': estado_cuenta.total_ventas,
                    'total_abonos': estado_cuenta.total_abonos,
                    'saldo_final': estado_cuenta.saldo_final
                }
            }

        except Exception as e:
            logger.error(f"Error generando estado de cuenta cliente {cliente_id}: {e}")
            raise
```

---

## 🔗 Integración con Sistema Existente

### Hooks y Señales Django

```python
# ventas/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .services.cuentas_por_cobrar_service import CuentasPorCobrarService

@receiver(post_save, sender=Ventas)
def sincronizar_deuda_post_venta(sender, instance, created, **kwargs):
    """
    Hook automático: Crea SaldoCliente cuando se registra venta a crédito
    """
    if created and instance.modalidad_pago in ['Crédito', 'Mixto']:
        try:
            CuentasPorCobrarService.sincronizar_deuda_venta(instance.id)
        except Exception as e:
            logger.error(f"Error auto-sincronizando deuda venta {instance.id}: {e}")

@receiver(post_save, sender=PagoVenta)
def actualizar_saldo_post_pago(sender, instance, created, **kwargs):
    """
    Hook automático: Actualiza saldo cuando se registra pago
    """
    if created:
        try:
            # Buscar saldo correspondiente
            saldo = SaldoCliente.objects.get(venta=instance.venta)

            # Recalcular saldo actual
            total_pagos = PagoVenta.objects.filter(venta=instance.venta).aggregate(
                total=Sum('monto')
            )['total'] or 0

            nuevo_saldo = saldo.monto_original - total_pagos

            # Actualizar estado
            if nuevo_saldo <= 0:
                saldo.estado = 'PAGADO'
                saldo.venta.estado_cobranza = 'Pagado'
            elif nuevo_saldo < saldo.monto_original:
                saldo.estado = 'PARCIAL'
                saldo.venta.estado_cobranza = 'Parcial'

            saldo.saldo_pendiente = max(nuevo_saldo, 0)
            saldo.fecha_ultimo_pago = instance.fecha_pago
            saldo.save()
            saldo.venta.save()

        except SaldoCliente.DoesNotExist:
            # Venta no tiene saldo (probablemente es contado)
            pass
        except Exception as e:
            logger.error(f"Error actualizando saldo post-pago {instance.id}: {e}")
```

### Cache Strategy

```python
# ventas/cache_utils.py

class CuentasPorCobrarCache:
    """
    Gestión de cache para métricas de cuentas por cobrar.
    Usa Redis existente con fallback a cache local.
    """

    CACHE_TIMEOUT = 900  # 15 minutos

    @classmethod
    def get_metricas_cliente(cls, cliente_id):
        """Cache de métricas por cliente"""
        cache_key = f'cxc_metricas_{cliente_id}'

        metricas = cache.get(cache_key)
        if metricas is None:
            metricas = cls._calcular_metricas_cliente(cliente_id)
            cache.set(cache_key, metricas, cls.CACHE_TIMEOUT)

        return metricas

    @classmethod
    def get_dashboard_global(cls):
        """Cache de dashboard global"""
        cache_key = 'cxc_dashboard_global'

        dashboard = cache.get(cache_key)
        if dashboard is None:
            dashboard = cls._calcular_dashboard_global()
            cache.set(cache_key, dashboard, cls.CACHE_TIMEOUT)

        return dashboard

    @classmethod
    def invalidar_cliente(cls, cliente_id):
        """Invalida cache específico de cliente"""
        cache.delete(f'cxc_metricas_{cliente_id}')
        cache.delete('cxc_dashboard_global')  # También global

    @staticmethod
    def _calcular_metricas_cliente(cliente_id):
        """Calcula métricas frescas por cliente"""
        saldos = SaldoCliente.objects.filter(cliente_id=cliente_id)

        return {
            'total_saldo': saldos.aggregate(Sum('saldo_pendiente'))['saldo_pendiente__sum'] or 0,
            'numero_facturas': saldos.count(),
            'saldo_vencido': saldos.filter(estado='VENCIDO').aggregate(Sum('saldo_pendiente'))['saldo_pendiente__sum'] or 0,
            'ultimo_pago': saldos.aggregate(Max('fecha_ultimo_pago'))['fecha_ultimo_pago__max'],
        }

    @staticmethod
    def _calcular_dashboard_global():
        """Calcula métricas globales del dashboard"""
        return {
            'total_cartera': SaldoCliente.objects.aggregate(Sum('saldo_pendiente'))['saldo_pendiente__sum'] or 0,
            'clientes_con_saldo': SaldoCliente.objects.values('cliente').distinct().count(),
            'facturas_pendientes': SaldoCliente.objects.exclude(estado='PAGADO').count(),
            'cartera_vencida': SaldoCliente.objects.filter(estado='VENCIDO').aggregate(Sum('saldo_pendiente'))['saldo_pendiente__sum'] or 0,
        }
```

---

## 📋 Interfaces de Administración

### Django Admin Extensions

```python
# ventas/admin.py - EXTENSIONES

@admin.register(SaldoCliente)
class SaldoClienteAdmin(admin.ModelAdmin):
    list_display = [
        'cliente', 'venta', 'monto_original', 'saldo_pendiente',
        'porcentaje_pagado', 'dias_vencido', 'estado', 'categoria_antiguedad'
    ]
    list_filter = [
        'estado', 'moneda', 'fecha_creacion',
        ('fecha_vencimiento', admin.DateFieldListFilter),
    ]
    search_fields = ['cliente__nombre', 'venta__numero_factura']
    readonly_fields = ['fecha_creacion', 'creado_por']

    fieldsets = (
        ('Información General', {
            'fields': ('cliente', 'venta', 'estado')
        }),
        ('Montos y Fechas', {
            'fields': ('monto_original', 'saldo_pendiente', 'moneda', 'fecha_vencimiento', 'fecha_ultimo_pago')
        }),
        ('Metadatos', {
            'fields': ('notas', 'fecha_creacion', 'creado_por'),
            'classes': ('collapse',)
        })
    )

    def porcentaje_pagado(self, obj):
        return f"{obj.porcentaje_pagado():.1f}%"
    porcentaje_pagado.short_description = "% Pagado"

    def categoria_antiguedad(self, obj):
        return obj.categoria_antiguedad()
    categoria_antiguedad.short_description = "Antigüedad"

@admin.register(AntigüedadSaldo)
class AntigüedadSaldoAdmin(admin.ModelAdmin):
    list_display = [
        'cliente', 'fecha_calculo', 'total_saldo', 'porcentaje_corriente',
        'riesgo_cobranza', 'numero_facturas'
    ]
    list_filter = ['fecha_calculo', 'moneda']
    search_fields = ['cliente__nombre']
    date_hierarchy = 'fecha_calculo'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('cliente')

@admin.register(EstadoCuentaCliente)
class EstadoCuentaClienteAdmin(admin.ModelAdmin):
    list_display = [
        'cliente', 'periodo_inicio', 'periodo_fin', 'saldo_final',
        'numero_facturas', 'formato_generado', 'fecha_generacion'
    ]
    list_filter = ['formato_generado', 'fecha_generacion']
    search_fields = ['cliente__nombre']
    readonly_fields = ['fecha_generacion', 'generado_por']

    actions = ['regenerar_estados_cuenta']

    def regenerar_estados_cuenta(self, request, queryset):
        """Acción personalizada para regenerar estados de cuenta"""
        for estado in queryset:
            try:
                CuentasPorCobrarService.generar_estado_cuenta(
                    estado.cliente.id,
                    estado.periodo_inicio,
                    estado.periodo_fin,
                    estado.formato_generado,
                    request.user
                )
                self.message_user(request, f'Estado de cuenta regenerado para {estado.cliente}', level=messages.SUCCESS)
            except Exception as e:
                self.message_user(request, f'Error regenerando {estado.cliente}: {e}', level=messages.ERROR)
```

---

## 📊 APIs y Endpoints

### ViewSets para API REST

```python
# ventas/api/viewsets.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

class SaldoClienteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API para consultar saldos de cuentas por cobrar.
    Solo lectura - las modificaciones se hacen via admin.
    """
    queryset = SaldoCliente.objects.all()
    serializer_class = SaldoClienteSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['cliente', 'estado', 'moneda']

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Endpoint para dashboard de cuentas por cobrar"""
        metricas = CuentasPorCobrarCache.get_dashboard_global()
        return Response(metricas)

    @action(detail=False, methods=['get'])
    def aging_report(self, request):
        """Reporte de aging consolidado"""
        fecha_corte = request.query_params.get('fecha_corte', timezone.now().date())

        # Calcular aging por cliente
        aging_data = []
        for cliente in Cliente.objects.filter(saldos_cxc__isnull=False).distinct():
            aging = CuentasPorCobrarService.calcular_antiguedad_cliente(cliente.id, fecha_corte)
            aging_data.append({
                'cliente': cliente.nombre,
                'corriente': aging.corriente,
                'vencido_1': aging.vencido_1,
                'vencido_2': aging.vencido_2,
                'vencido_3': aging.vencido_3,
                'total': aging.total_saldo,
                'riesgo': aging.riesgo_cobranza
            })

        return Response({
            'fecha_corte': fecha_corte,
            'clientes': aging_data
        })

class EstadoCuentaViewSet(viewsets.ReadOnlyModelViewSet):
    """API para estados de cuenta de clientes"""
    queryset = EstadoCuentaCliente.objects.all()
    serializer_class = EstadoCuentaSerializer

    @action(detail=False, methods=['post'])
    def generar(self, request):
        """Generar nuevo estado de cuenta"""
        serializer = GenerarEstadoCuentaSerializer(data=request.data)

        if serializer.is_valid():
            try:
                resultado = CuentasPorCobrarService.generar_estado_cuenta(
                    cliente_id=serializer.validated_data['cliente_id'],
                    fecha_inicio=serializer.validated_data['fecha_inicio'],
                    fecha_fin=serializer.validated_data['fecha_fin'],
                    formato=serializer.validated_data.get('formato', 'WEB'),
                    usuario=request.user
                )

                return Response({
                    'estado_cuenta_id': resultado['estado_cuenta'].id,
                    'mensaje': 'Estado de cuenta generado exitosamente'
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                return Response({
                    'error': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

---

## 📈 Métricas y Monitoreo

### KPIs del Sistema

```python
# ventas/metrics.py

class CuentasPorCobrarMetrics:
    """
    Clase para calcular métricas y KPIs del sistema de cuentas por cobrar.
    Se integra con el sistema de reportes existente.
    """

    @staticmethod
    def calcular_dso(periodo_dias=30):
        """
        Days Sales Outstanding - Métrica clave de eficiencia de cobranza
        DSO = (Cuentas por Cobrar / Ventas a Crédito) * Número de Días
        """
        fecha_fin = timezone.now().date()
        fecha_inicio = fecha_fin - timedelta(days=periodo_dias)

        # Total de cuentas por cobrar
        total_cxc = SaldoCliente.objects.aggregate(
            total=Sum('saldo_pendiente')
        )['total'] or 0

        # Ventas a crédito del período
        ventas_credito = Ventas.objects.filter(
            fecha_venta__range=[fecha_inicio, fecha_fin],
            modalidad_pago__in=['Crédito', 'Mixto']
        ).aggregate(
            total=Sum('total_venta')
        )['total'] or 0

        if ventas_credito > 0:
            dso = (total_cxc / ventas_credito) * periodo_dias
        else:
            dso = 0

        return {
            'dso': round(dso, 2),
            'total_cxc': total_cxc,
            'ventas_credito_periodo': ventas_credito,
            'periodo_dias': periodo_dias
        }

    @staticmethod
    def distribucion_aging():
        """Distribución porcentual de cartera por antigüedad"""
        totales = AntigüedadSaldo.objects.filter(
            fecha_calculo=timezone.now().date()
        ).aggregate(
            corriente=Sum('corriente'),
            vencido_1=Sum('vencido_1'),
            vencido_2=Sum('vencido_2'),
            vencido_3=Sum('vencido_3'),
            total=Sum('total_saldo')
        )

        total = totales['total'] or 0
        if total > 0:
            return {
                'corriente_pct': round((totales['corriente'] / total) * 100, 2),
                'vencido_1_pct': round((totales['vencido_1'] / total) * 100, 2),
                'vencido_2_pct': round((totales['vencido_2'] / total) * 100, 2),
                'vencido_3_pct': round((totales['vencido_3'] / total) * 100, 2),
                'total_cartera': total
            }

        return {'mensaje': 'No hay cartera para analizar'}

    @staticmethod
    def top_deudores(limite=10):
        """Top N clientes con mayor saldo pendiente"""
        return SaldoCliente.objects.values('cliente__nombre').annotate(
            total_saldo=Sum('saldo_pendiente'),
            numero_facturas=Count('id'),
            promedio_dias_vencido=Avg('dias_vencido')
        ).order_by('-total_saldo')[:limite]

    @staticmethod
    def eficiencia_cobranza_mensual():
        """Análisis de eficiencia de cobranza por mes"""
        # Obtener pagos de los últimos 12 meses
        fecha_limite = timezone.now().date() - timedelta(days=365)

        pagos_mensuales = PagoVenta.objects.filter(
            fecha_pago__gte=fecha_limite
        ).extra({
            'mes': "DATE_FORMAT(fecha_pago, '%%Y-%%m')"
        }).values('mes').annotate(
            total_cobrado=Sum('monto'),
            numero_pagos=Count('id')
        ).order_by('mes')

        return list(pagos_mensuales)
```

---

## 🔄 Tareas Programadas

### Celery Tasks (Si está disponible)

```python
# ventas/tasks.py

from celery import shared_task
from django.core.mail import send_mail
from .services.cuentas_por_cobrar_service import CuentasPorCobrarService

@shared_task
def calcular_aging_automatico():
    """
    Tarea que calcula aging de todos los clientes.
    Programada para ejecutarse diariamente a las 2:00 AM.
    """
    try:
        clientes_procesados = 0
        errores = 0

        for cliente in Cliente.objects.filter(saldos_cxc__isnull=False).distinct():
            try:
                CuentasPorCobrarService.calcular_antiguedad_cliente(cliente.id)
                clientes_procesados += 1
            except Exception as e:
                logger.error(f"Error calculando aging cliente {cliente.id}: {e}")
                errores += 1

        # Enviar reporte por email
        mensaje = f"""
        Cálculo automático de aging completado:
        - Clientes procesados: {clientes_procesados}
        - Errores: {errores}
        - Fecha: {timezone.now()}
        """

        config = ConfiguracionCuentasPorCobrar.objects.first()
        if config and config.email_responsable_cobranza:
            send_mail(
                'Reporte Aging Automático',
                mensaje,
                'sistema@empresa.com',
                [config.email_responsable_cobranza]
            )

        return {
            'procesados': clientes_procesados,
            'errores': errores
        }

    except Exception as e:
        logger.error(f"Error en tarea aging automático: {e}")
        raise

@shared_task
def generar_alertas_vencimiento():
    """
    Genera alertas para facturas próximas a vencer.
    """
    config = ConfiguracionCuentasPorCobrar.objects.first()
    if not config or not config.enviar_alertas_vencimiento:
        return {'mensaje': 'Alertas deshabilitadas'}

    fecha_limite = timezone.now().date() + timedelta(days=config.dias_previos_alerta)

    saldos_proximos = SaldoCliente.objects.filter(
        estado__in=['PENDIENTE', 'PARCIAL'],
        fecha_vencimiento__lte=fecha_limite,
        fecha_vencimiento__gte=timezone.now().date()
    )

    alertas_enviadas = 0
    for saldo in saldos_proximos:
        try:
            # Enviar alerta (email, notificación interna, etc.)
            mensaje = f"""
            Alerta de vencimiento próximo:
            Cliente: {saldo.cliente.nombre}
            Factura: {saldo.venta.numero_factura}
            Monto pendiente: {saldo.saldo_pendiente}
            Fecha vencimiento: {saldo.fecha_vencimiento}
            """

            if config.email_responsable_cobranza:
                send_mail(
                    f'Alerta Vencimiento - {saldo.cliente.nombre}',
                    mensaje,
                    'sistema@empresa.com',
                    [config.email_responsable_cobranza]
                )

            alertas_enviadas += 1

        except Exception as e:
            logger.error(f"Error enviando alerta saldo {saldo.id}: {e}")

    return {'alertas_enviadas': alertas_enviadas}
```

---

## 🧪 Testing y Calidad

### Test Suite Básico

```python
# ventas/tests/test_cuentas_por_cobrar.py

class CuentasPorCobrarTestCase(TestCase):
    """
    Suite de pruebas para el sistema de cuentas por cobrar.
    Cubre los 4 requerimientos funcionales principales.
    """

    def setUp(self):
        # Crear datos de prueba
        self.cliente = Cliente.objects.create(
            nombre="Cliente Test",
            limite_credito=Money(100000, 'MXN')
        )

        self.venta = Ventas.objects.create(
            cliente=self.cliente,
            modalidad_pago='Crédito',
            total_venta=Money(10000, 'MXN'),
            fecha_venta=timezone.now().date(),
            fecha_vencimiento=timezone.now().date() + timedelta(days=30)
        )

    def test_rf1_sincronizacion_deuda_automatica(self):
        """RF1: Sincronización automática de deuda por venta a crédito"""

        # Verificar que se creó saldo automáticamente
        self.assertTrue(hasattr(self.venta, 'saldo_cxc'))

        saldo = self.venta.saldo_cxc
        self.assertEqual(saldo.cliente, self.cliente)
        self.assertEqual(saldo.monto_original, Money(10000, 'MXN'))
        self.assertEqual(saldo.saldo_pendiente, Money(10000, 'MXN'))
        self.assertEqual(saldo.estado, 'PENDIENTE')

    def test_rf2_registro_abonos_multiforma(self):
        """RF2: Registro de abonos con actualización instantánea"""

        saldo = self.venta.saldo_cxc

        # Registrar abono parcial
        pago, saldo_actualizado = CuentasPorCobrarService.registrar_abono(
            saldo.id,
            Money(3000, 'MXN'),
            'transferencia',
            referencia='TXN123'
        )

        # Verificar actualización
        saldo_actualizado.refresh_from_db()
        self.assertEqual(saldo_actualizado.saldo_pendiente, Money(7000, 'MXN'))
        self.assertEqual(saldo_actualizado.estado, 'PARCIAL')

        # Registrar pago completo
        CuentasPorCobrarService.registrar_abono(
            saldo.id,
            Money(7000, 'MXN'),
            'efectivo'
        )

        saldo_actualizado.refresh_from_db()
        self.assertEqual(saldo_actualizado.saldo_pendiente, Money(0, 'MXN'))
        self.assertEqual(saldo_actualizado.estado, 'PAGADO')

    def test_rf3_calculo_antiguedad_saldos(self):
        """RF3: Cálculo de antigüedad en rangos estándar"""

        # Simular vencimiento (mover fecha hacia atrás)
        self.venta.fecha_vencimiento = timezone.now().date() - timedelta(days=45)
        self.venta.save()
        self.venta.saldo_cxc.fecha_vencimiento = self.venta.fecha_vencimiento
        self.venta.saldo_cxc.save()

        # Calcular aging
        aging = CuentasPorCobrarService.calcular_antiguedad_cliente(self.cliente.id)

        # Verificar clasificación (45 días = vencido_1)
        self.assertEqual(aging.vencido_1, Money(10000, 'MXN'))
        self.assertEqual(aging.corriente, Money(0, 'MXN'))
        self.assertEqual(aging.total_saldo, Money(10000, 'MXN'))

    def test_rf4_estado_cuenta_historico(self):
        """RF4: Generación de estado de cuenta con historial"""

        # Simular algunos pagos
        CuentasPorCobrarService.registrar_abono(
            self.venta.saldo_cxc.id,
            Money(2000, 'MXN'),
            'transferencia'
        )

        # Generar estado de cuenta
        fecha_inicio = timezone.now().date() - timedelta(days=30)
        fecha_fin = timezone.now().date()

        resultado = CuentasPorCobrarService.generar_estado_cuenta(
            self.cliente.id,
            fecha_inicio,
            fecha_fin
        )

        # Verificar estructura del resultado
        self.assertIn('estado_cuenta', resultado)
        self.assertIn('movimientos', resultado)
        self.assertIn('resumen', resultado)

        # Verificar cálculos
        resumen = resultado['resumen']
        self.assertEqual(resumen['saldo_final'], Money(8000, 'MXN'))
        self.assertEqual(len(resultado['movimientos']), 2)  # 1 venta + 1 pago

    def test_validacion_limite_credito(self):
        """Validación de límites de crédito en tiempo real"""

        # Intentar venta que excede límite
        with self.assertRaises(ValidationError):
            venta_grande = Ventas(
                cliente=self.cliente,
                modalidad_pago='Crédito',
                total_venta=Money(150000, 'MXN')  # Excede límite de 100,000
            )
            venta_grande.full_clean()
```

---

## 📋 Checklist de Implementación

### Fase 1: Modelos y Servicios Base

- [ ] Crear modelos: SaldoCliente, AntigüedadSaldo, EstadoCuentaCliente, ConfiguracionCuentasPorCobrar
- [ ] Implementar servicios: CuentasPorCobrarService con métodos principales
- [ ] Configurar signals para hooks automáticos
- [ ] Crear migraciones de base de datos
- [ ] Implementar cache strategy con Redis

### Fase 2: Interfaces de Usuario

- [ ] Extender Django Admin con nuevos modelos
- [ ] Crear vistas personalizadas para dashboard
- [ ] Implementar acciones masivas en admin
- [ ] Diseñar formularios de búsqueda y filtros
- [ ] Crear templates para reportes

### Fase 3: APIs y Integraciones

- [ ] Desarrollar ViewSets de Django REST Framework
- [ ] Implementar endpoints para dashboard y aging
- [ ] Integrar con sistema de reportes Excel existente
- [ ] Configurar serializers para APIs
- [ ] Documentar endpoints con Swagger/OpenAPI

### Fase 4: Automatización y Tareas

- [ ] Configurar tareas Celery para cálculos automáticos
- [ ] Implementar sistema de alertas por email
- [ ] Crear comandos de management para operaciones batch
- [ ] Configurar monitoreo y logging específico
- [ ] Implementar backup automático de reportes

### Fase 5: Testing y Documentación

- [ ] Escribir test suite completo (unitarios + integración)
- [ ] Crear documentación de usuario final
- [ ] Configurar CI/CD para tests automáticos
- [ ] Realizar testing de performance y carga
- [ ] Preparar scripts de migración de datos históricos

### Fase 6: Deployment y Capacitación

- [ ] Deploy en ambiente de staging
- [ ] Migración de datos históricos
- [ ] Capacitación a usuarios finales
- [ ] Configuración de monitoreo en producción
- [ ] Go-live y soporte post-implementación

---

## 📞 Soporte y Mantenimiento

### Logs y Monitoreo

- **Ubicación logs**: `logs/cuentas_por_cobrar.log`
- **Nivel mínimo**: INFO para operaciones normales, DEBUG para troubleshooting
- **Rotación**: Diaria con retención de 30 días
- **Alertas**: Errores críticos notifican por email

### Performance Benchmarks

- **Sincronización de deuda**: < 100ms por venta
- **Cálculo aging individual**: < 500ms por cliente
- **Dashboard global**: < 2s con cache, < 10s sin cache
- **Estado de cuenta**: < 3s para períodos de 1 año

### Troubleshooting Común

1. **Saldos inconsistentes**: Ejecutar comando `python manage.py recalcular_saldos`
2. **Cache obsoleto**: Usar `python manage.py invalidar_cache_cxc`
3. **Aging incorrecto**: Verificar configuración de días en ConfiguracionCuentasPorCobrar
4. **Emails no enviados**: Revisar configuración SMTP y logs de Celery

---

**Siguiente paso**: Implementar modelos base y servicios principales según especificaciones técnicas.
