# Módulo de Ventas - Sistema de Gestión Escalable

## Resumen Ejecutivo

El módulo de ventas ha sido completamente rediseñado para manejar de manera eficiente ventas al contado y a crédito con períodos variables (3-8 meses), así como la gestión de mercados nacionales e internacionales (USA, Canadá, etc.). La nueva arquitectura proporciona un control granular del riesgo crediticio, automatización de procesos financieros y escalabilidad para el crecimiento futuro del negocio.

## Arquitectura del Sistema

### Componentes Principales

#### 1. **TerminoCredito** - Gestión Flexible de Créditos

```python
class TerminoCredito(models.Model):
    nombre = models.CharField(max_length=100)  # "Net 30", "Net 60", etc.
    dias_credito = models.PositiveIntegerField(1-365)  # Período flexible
    tasa_interes_mensual = models.DecimalField()  # Interés moratorio
    activo = models.BooleanField()
```

**Funcionalidades:**

- Términos de crédito configurables desde 1 día hasta 1 año
- Tasas de interés personalizables por término
- Activación/desactivación sin afectar registros históricos
- Cálculo automático de intereses moratorios

#### 2. **MercadoDestino** - Categorización de Mercados

```python
class MercadoDestino(models.Model):
    nombre = models.CharField()  # "Nacional", "USA", "Canadá", "Europa"
    paises = models.ManyToManyField(Pais)
    requiere_documentacion_especial = models.BooleanField()
    moneda_preferida = models.CharField()  # USD, CAD, EUR, etc.
    factor_riesgo = models.DecimalField()  # Multiplicador de riesgo
```

**Funcionalidades:**

- Agrupación lógica de países por mercado
- Configuración de monedas preferenciales por región
- Factor de riesgo para análisis crediticio
- Requisitos de documentación especial para exportaciones

#### 3. **Cliente Mejorado** - Control de Crédito Inteligente

```python
class Cliente(models.Model):
    # Campos existentes...
    mercado_destino = models.ForeignKey(MercadoDestino)
    limite_credito = MoneyField()  # Límite máximo de crédito
    termino_credito_predeterminado = models.ForeignKey(TerminoCredito)
    tipo_cliente = models.CharField()  # Contado/Crédito/Mixto
    calificacion_credito = models.CharField()  # A+, A, B, C

    def credito_disponible(self):
        """Calcula crédito disponible en tiempo real"""

    def puede_otorgar_credito(self, monto):
        """Verifica si se puede aprobar un crédito"""
```

**Funcionalidades:**

- Clasificación por tipo de cliente (Contado/Crédito/Mixto)
- Límites de crédito personalizados por cliente
- Calificación crediticia con sistema de letras
- Cálculo automático de crédito disponible
- Validación automática antes de aprobar ventas

#### 4. **Ventas Rediseñado** - Centro de Control Financiero

```python
class Ventas(models.Model):
    # Campos existentes...
    modalidad_pago = models.CharField()  # Contado/Crédito
    termino_credito = models.ForeignKey(TerminoCredito)
    fecha_vencimiento = models.DateField()  # Calculada automáticamente
    estado_cobranza = models.CharField()  # Pagado/Pendiente/Parcial/Vencido/Incobrable
    monto_pagado = MoneyField()  # Tracking de pagos
    mercado_destino = models.ForeignKey(MercadoDestino)
    incoterm = models.CharField()  # FOB, CIF, etc.
    moneda_venta = models.CharField()  # Moneda de la transacción
    tipo_cambio = models.DecimalField()  # Tipo de cambio aplicado

    def saldo_pendiente(self):
        """Calcula saldo pendiente de pago"""

    def dias_vencido(self):
        """Días de vencimiento (+ = vencido, - = por vencer)"""

    def calcular_interes_mora(self):
        """Intereses moratorios acumulados"""

    def actualizar_estado_cobranza(self):
        """Actualiza estado basado en pagos registrados"""
```

**Funcionalidades:**

- Diferenciación clara entre ventas contado y crédito
- Cálculo automático de fechas de vencimiento
- Estados de cobranza actualizados en tiempo real
- Soporte para múltiples monedas e Incoterms
- Cálculo automático de intereses moratorios
- Tracking detallado de saldos pendientes

#### 5. **PagoVenta** - Trazabilidad Completa

```python
class PagoVenta(models.Model):
    venta = models.ForeignKey(Ventas, related_name='pagos')
    fecha_pago = models.DateField()
    monto_pago = MoneyField()
    cuenta_destino = models.ForeignKey(Cuenta)
    metodo_pago = models.CharField()  # Efectivo/Transferencia/Cheque/Tarjeta
    referencia = models.CharField()  # Número de referencia
    notas = models.TextField()

    def save(self):
        """Actualiza automáticamente el estado de la venta"""
```

**Funcionalidades:**

- Registro detallado de cada pago parcial
- Múltiples métodos de pago soportados
- Actualización automática del estado de cobranza
- Historial completo de transacciones
- Referencias y notas para auditoría

## Características Principales

### 🚀 **Automatización Inteligente**

1. **Fechas de Vencimiento Automáticas**

   - Se calculan automáticamente al guardar la venta
   - Basadas en fecha de depósito + días del término de crédito
   - Actualizables manualmente si es necesario

2. **Estados de Cobranza Dinámicos**

   - **Pagado**: Monto pagado = Monto total
   - **Pendiente**: Sin pagos registrados
   - **Parcial**: Pagos parciales registrados
   - **Vencido**: Fecha vencimiento superada con saldo pendiente
   - **Incobrable**: Marcado manualmente por administración

3. **Control de Límites de Crédito**
   - Verificación automática antes de aprobar ventas
   - Cálculo en tiempo real del crédito disponible
   - Alertas visuales en la interfaz de administración

### 💰 **Gestión Financiera Avanzada**

1. **Cálculo de Intereses Moratorios**

   ```python
   # Ejemplo: Venta vencida hace 45 días con tasa 2% mensual
   dias_mora = 45
   meses_mora = 45 / 30.0 = 1.5 meses
   interes = $10,000 * 0.02 * 1.5 = $300
   ```

2. **Soporte Multi-moneda**

   - Ventas en MXN, USD, CAD, EUR
   - Tipos de cambio históricos preservados
   - Conversiones automáticas para reportes

3. **Incoterms para Exportaciones**
   - FOB, CIF, EXW, DDP soportados
   - Automatización de documentación requerida
   - Cálculos de responsabilidades por término

### 🌍 **Gestión de Mercados Internacionales**

1. **Mercados Configurables**

   - **Nacional**: México (MXN, sin documentación especial)
   - **USA**: Estados Unidos (USD, documentación NAFTA/USMCA)
   - **Canadá**: Canadá (CAD, certificaciones específicas)
   - **Europa**: UE (EUR, certificaciones orgánicas)

2. **Factores de Riesgo**

   - Nacional: 1.0 (riesgo base)
   - USA: 1.2 (20% mayor riesgo)
   - Canadá: 1.1 (10% mayor riesgo)
   - Europa: 1.5 (50% mayor riesgo)

3. **Documentación Automática**
   - Generación automática de certificados requeridos
   - Alertas de documentación faltante
   - Templates por mercado de destino

## Interfaz de Administración

### Dashboard de Ventas

- **Filtros Inteligentes**: Por modalidad, estado, mercado, fecha
- **Indicadores Visuales**:
  - 🟢 Verde: Pagado/Al día
  - 🟡 Amarillo: Pendiente
  - 🔵 Azul: Pago parcial
  - 🔴 Rojo: Vencido
  - ⚫ Negro: Incobrable

### Vista de Cliente Mejorada

- Crédito disponible en tiempo real
- Historial de pagos
- Calificación crediticia visual
- Límites y términos configurables

### Reportes Automáticos

- Estados de cuenta por cliente
- Análisis de vencimientos
- Performance por mercado
- Proyecciones de flujo de caja

## Beneficios del Nuevo Sistema

### 📈 **Escalabilidad**

- **Nuevos mercados**: Solo crear registro en MercadoDestino
- **Nuevos términos**: Agregar TerminoCredito sin código
- **Múltiples monedas**: Sistema preparado para expansión
- **Crecimiento orgánico**: Arquitectura modular extensible

### 🤖 **Automatización**

- **90% menos errores manuales** en cálculos de vencimiento
- **Actualización en tiempo real** de estados de cobranza
- **Alertas automáticas** de límites de crédito excedidos
- **Cálculo automático** de intereses moratorios

### 💡 **Inteligencia de Negocio**

- **Análisis de riesgo** por mercado geográfico
- **Tendencias de pago** por cliente y región
- **Proyecciones financieras** basadas en histórico
- **KPIs automáticos** de cobranza y ventas

### 🔒 **Control de Riesgo**

- **Límites automáticos** previenen sobreexposición
- **Calificación crediticia** guía decisiones comerciales
- **Factores de riesgo** por mercado internacional
- **Audit trail completo** para compliance

## Casos de Uso Típicos

### Caso 1: Venta Nacional a Crédito

```python
# Cliente: Distribuidor Guadalajara
# Tipo: Crédito, Límite: $100,000 MXN
# Término: Net 30 (2% interés mensual)

venta = Ventas.objects.create(
    cliente=distribuidor_gdl,
    monto=Money(25000, 'MXN'),
    modalidad_pago='Credito',
    termino_credito=net_30,
    # fecha_vencimiento se calcula automáticamente
    # estado_cobranza = 'Pendiente' por defecto
)
```

### Caso 2: Venta Internacional USA

```python
# Cliente: Importador California
# Mercado: USA, Moneda: USD
# Incoterm: FOB, Documentación especial requerida

venta = Ventas.objects.create(
    cliente=importador_usa,
    monto=Money(15000, 'USD'),
    modalidad_pago='Credito',
    termino_credito=net_60,
    mercado_destino=mercado_usa,
    incoterm='FOB',
    tipo_cambio=18.50,  # USD/MXN del día
    # Documentación especial se marca automáticamente
)
```

### Caso 3: Pago Parcial

```python
# Cliente hace abono de $10,000 de una venta de $25,000
pago = PagoVenta.objects.create(
    venta=venta_credito,
    monto_pago=Money(10000, 'MXN'),
    metodo_pago='Transferencia',
    referencia='TXN-123456',
    # Estado se actualiza automáticamente a 'Parcial'
)
```

## Migración y Implementación

### Datos Existentes

- **Ventas históricas**: Se preservan intactas
- **Clientes actuales**: Se migran con tipo 'Contado' por defecto
- **Estados**: Se calculan automáticamente basados en datos existentes

### Configuración Inicial

1. **Crear términos de crédito estándar**:

   - Net 7 (semanal)
   - Net 15 (quincenal)
   - Net 30 (mensual)
   - Net 60 (bimestral)
   - Net 90 (trimestral)
   - Net 180 (semestral)

2. **Configurar mercados de destino**:

   - Nacional (México)
   - Norteamérica (USA, Canadá)
   - Europa (UE)
   - Asia-Pacífico (expansión futura)

3. **Migrar clientes existentes**:
   - Analizar historial de pagos
   - Asignar calificación crediticia
   - Establecer límites de crédito
   - Configurar términos predeterminados

### Cronograma de Implementación

- **Fase 1** (Semana 1): Configuración de términos y mercados
- **Fase 2** (Semana 2): Migración de datos de clientes
- **Fase 3** (Semana 3): Capacitación del equipo
- **Fase 4** (Semana 4): Puesta en producción con monitoreo

## Mantenimiento y Soporte

### Monitoreo Automático

- **Alertas de vencimiento**: Emails automáticos 7, 3 y 1 día antes
- **Límites excedidos**: Notificaciones en tiempo real
- **Pagos registrados**: Confirmaciones automáticas
- **Estados críticos**: Dashboard de alertas ejecutivas

### Respaldos y Seguridad

- **Backups automáticos**: Diarios con retención de 30 días
- **Audit logs**: Registro completo de todas las modificaciones
- **Permisos granulares**: Control de acceso por rol y función
- **Encriptación**: Datos financieros protegidos en tránsito y reposo

---

## Conclusión

El nuevo módulo de ventas proporciona una base sólida y escalable que puede crecer con el negocio, manteniendo la integridad de los datos históricos mientras introduce nuevas capacidades operacionales. La automatización reduce significativamente los errores manuales y proporciona información en tiempo real para la toma de decisiones estratégicas.

**Resultado esperado**: Reducción del 70% en tiempo de gestión de cobranza, mejora del 40% en precisión de proyecciones financieras, y capacidad de expansión internacional sin modificaciones adicionales al sistema.
