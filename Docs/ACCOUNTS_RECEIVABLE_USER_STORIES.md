# Historias de Usuario - Sistema de Cuentas por Cobrar

## Información del Proyecto

- **Proyecto**: Sistema de Administración Personalizado Django
- **Módulo**: Extensión de Cuentas por Cobrar (ventas/)
- **Fecha de Creación**: 11 de marzo, 2026
- **Cronograma**: 15 semanas (según cronograma de actividades del proyecto)

## Cronograma de Desarrollo

### FASE 1: Sincronización y Registro de Pagos (Semanas 1-8)

**Objetivo**: Establecer la base automática de gestión de deuda y pagos parciales

### FASE 2: Análisis y Reportería (Semanas 9-12)

**Objetivo**: Implementar análisis de antigüedad y reportes históricos detallados

---

## 📋 FASE 1: HISTORIAS DE USUARIO PRIORITARIAS

### Historia 1: Sincronización Automática de Deuda por Ventas a Crédito

**Como** administrador de cuentas por cobrar  
**Quiero** que el sistema registre automáticamente un saldo en la tabla de cuentas por cobrar cada vez que se registre una venta "a crédito"  
**Para** mantener un control preciso y automático de todas las deudas pendientes sin intervención manual

#### Criterios de Aceptación:

- [ ] **Dado** que un usuario registra una nueva venta con modalidad_pago = "Crédito"
- [ ] **Cuando** se guarda el registro de venta exitosamente
- [ ] **Entonces** el sistema debe crear automáticamente un registro en SaldoCliente con:
  - cliente_id vinculado a la venta
  - monto_original = total de la venta
  - saldo_pendiente = monto_original (inicialmente)
  - fecha_vencimiento = fecha_venta + término de crédito del cliente
  - estado = "Pendiente"
  - referencia_venta = ID de la venta origen

#### Escenarios Adicionales:

- **Escenario 2**: Ventas en modalidad "Mixto" deben registrar solo la porción a crédito
- **Escenario 3**: Ventas en modalidad "Contado" no deben generar registro de saldo
- **Escenario 4**: Si falla la creación del saldo, debe revertir la venta (transacción atómica)

#### Estimación: 5 Story Points

#### Prioridad: Alta

#### Sprint: 1-2

---

### Historia 2: Registro de Abonos Multiforma con Actualización Instantánea

**Como** usuario del departamento de cobranza  
**Quiero** registrar abonos parciales utilizando diferentes métodos de pago (efectivo, transferencia, tarjeta)  
**Para** actualizar instantáneamente el saldo pendiente y mantener un historial detallado de todos los pagos recibidos

#### Criterios de Aceptación:

- [ ] **Dado** que existe un saldo pendiente para un cliente
- [ ] **Cuando** registro un nuevo pago parcial especificando:
  - Monto del abono
  - Método de pago (efectivo, transferencia, tarjeta, cheque)
  - Fecha del pago
  - Referencia/comprobante (opcional)
- [ ] **Entonces** el sistema debe:
  - Crear un registro en PagoVenta vinculado a la venta original
  - Actualizar saldo_pendiente = saldo_actual - monto_abono
  - Cambiar estado del SaldoCliente según nueva condición:
    - "Pagado" si saldo_pendiente = 0
    - "Parcial" si 0 < saldo_pendiente < monto_original
    - Mantener "Pendiente" si no hay cambios significativos
  - Registrar timestamp de la transacción

#### Escenarios Adicionales:

- **Escenario 2**: Abono mayor al saldo debe generar alerta y requerir confirmación
- **Escenario 3**: Múltiples abonos en un día deben consolidarse en el historial
- **Escenario 4**: Modificación/anulación de abono debe recalcular saldo automáticamente

#### Estimación: 8 Story Points

#### Prioridad: Alta

#### Sprint: 2-3

---

### Historia 3: Validación de Límites de Crédito en Tiempo Real

**Como** vendedor o administrador  
**Quiero** que el sistema valide el límite de crédito disponible antes de autorizar una venta a crédito  
**Para** prevenir otorgar crédito excesivo y mantener el riesgo financiero dentro de parámetros aceptables

#### Criterios de Aceptación:

- [ ] **Dado** que un cliente tiene un límite de crédito establecido
- [ ] **Cuando** intento registrar una venta a crédito
- [ ] **Entonces** el sistema debe:
  - Calcular crédito_disponible = límite_crédito - suma(saldos_pendientes)
  - Permitir la venta si monto_venta <= crédito_disponible
  - Mostrar alerta con opciones si monto_venta > crédito_disponible:
    - Rechazar venta
    - Solicitar autorización de supervisor
    - Modificar a venta parcial (parte contado, parte crédito)

#### Estimación: 3 Story Points

#### Prioridad: Media

#### Sprint: 1

---

### Historia 4: Dashboard de Resumen de Cuentas por Cobrar

**Como** gerente financiero  
**Quiero** visualizar un dashboard con el resumen consolidado de todas las cuentas por cobrar  
**Para** tomar decisiones informadas sobre políticas de crédito y identificar rápidamente situaciones que requieren atención

#### Criterios de Aceptación:

- [ ] **Dado** que accedo al módulo de cuentas por cobrar
- [ ] **Cuando** visualizo el dashboard principal
- [ ] **Entonces** debe mostrar:
  - Total de saldos pendientes (monto en pesos y dólares)
  - Número total de clientes con saldo pendiente
  - Top 5 clientes con mayor deuda
  - Indicador de crédito total otorgado vs. límites disponibles
  - Alertas de límites de crédito próximos al máximo

#### Estimación: 5 Story Points

#### Prioridad: Media

#### Sprint: 3

---

## 📈 FASE 2: HISTORIAS DE USUARIO ANALÍTICAS

### Historia 5: Cálculo Automático de Antigüedad de Saldos

**Como** analista de crédito y cobranza  
**Quiero** que el sistema clasifique automáticamente los saldos por antigüedad en rangos estándar  
**Para** identificar cuentas morosas y priorizar esfuerzos de cobranza según el nivel de riesgo

#### Criterios de Aceptación:

- [ ] **Dado** que existen saldos pendientes con diferentes fechas de vencimiento
- [ ] **Cuando** ejecuto el proceso de cálculo de antigüedad (manual o automático)
- [ ] **Entonces** el sistema debe clasificar cada saldo en:
  - **Corriente**: 0-30 días desde fecha de vencimiento
  - **Vencido 1**: 31-60 días
  - **Vencido 2**: 61-90 días
  - **Vencido 3**: 91+ días (moroso crítico)
- [ ] **Y** crear/actualizar registros en AntigüedadSaldo con:
  - Fecha de cálculo
  - Distribución por rangos
  - Porcentaje de cada categoría
  - Tendencia vs. período anterior

#### Escenarios Adicionales:

- **Escenario 2**: Cálculo debe considerar días hábiles vs naturales según configuración
- **Escenario 3**: Debe manejar diferentes monedas y convertir a moneda base
- **Escenario 4**: Ejecución automática nocturna o mediante tarea programada

#### Estimación: 8 Story Points

#### Prioridad: Alta

#### Sprint: 4-5

---

### Historia 6: Generación de Estado de Cuenta Histórico por Cliente

**Como** ejecutivo de cobranza  
**Quiero** generar un estado de cuenta detallado que muestre el historial completo de un cliente  
**Para** tener una vista completa de la relación comercial y facilitar negociaciones de pago

#### Criterios de Aceptación:

- [ ] **Dado** que selecciono un cliente específico
- [ ] **Cuando** solicito generar su estado de cuenta histórico
- [ ] **Entonces** el reporte debe incluir:
  - **Encabezado**: Datos del cliente, límite de crédito, crédito disponible
  - **Detalle cronológico**:
    - Fecha | Tipo | Referencia | Venta Original | Abonos | Saldo Pendiente
    - Cálculo: Saldo = Venta Original - Suma de Abonos
  - **Resumen**:
    - Total de ventas a crédito (período)
    - Total de abonos recibidos
    - Saldo total pendiente
    - Distribución por antigüedad
    - Promedio de días de pago histórico

#### Formatos de Salida:

- [ ] Vista web con filtros de fecha
- [ ] Exportación a PDF para envío al cliente
- [ ] Exportación a Excel para análisis

#### Estimación: 13 Story Points

#### Prioridad: Alta

#### Sprint: 5-6

---

### Historia 7: Alertas de Cobranza y Seguimiento

**Como** supervisor de cobranza  
**Quiero** recibir alertas automáticas cuando los saldos cambien de categoría de antigüedad  
**Para** actuar proactivamente en la gestión de cobranza y minimizar cuentas incobrables

#### Criterios de Aceptación:

- [ ] **Dado** que un saldo cambia de categoría de antigüedad
- [ ] **Cuando** se ejecuta el proceso de reclasificación
- [ ] **Entonces** el sistema debe:
  - Generar alerta interna para el equipo de cobranza
  - Enviar notificación por email al responsable del cliente
  - Registrar el evento en el log de actividades de cobranza
  - Sugerir acciones basadas en la nueva categoría:
    - 31-60 días: Llamada de cortesía
    - 61-90 días: Llamada formal + email
    - +90 días: Proceso legal + suspensión de crédito

#### Estimación: 5 Story Points

#### Prioridad: Media

#### Sprint: 6

---

### Historia 8: Reportes Ejecutivos de Análisis de Cobranza

**Como** director financiero  
**Quiero** acceder a reportes ejecutivos con métricas clave de desempeño en cobranza  
**Para** evaluar la efectividad de las políticas de crédito y tomar decisiones estratégicas

#### Criterios de Aceptación:

- [ ] **Dado** que accedo a la sección de reportes ejecutivos
- [ ] **Cuando** selecciono el período de análisis
- [ ] **Entonces** debe generar reporte con:
  - **KPIs principales**:
    - DSO (Days Sales Outstanding)
    - Tasa de recuperación de cartera
    - % de cartera por antigüedad
    - Evolución mensual de saldos
  - **Análisis de tendencias**:
    - Comparativo vs período anterior
    - Proyección de flujo de caja
    - Clientes que mejoraron/empeoraron perfil de pago
  - **Gráficos visuales**:
    - Aging de cartera (gráfico de barras)
    - Evolución de DSO (línea de tiempo)
    - Top deudores (gráfico circular)

#### Estimación: 8 Story Points

#### Prioridad: Media

#### Sprint: 7

---

## 🔧 ESPECIFICACIONES TÉCNICAS

### Modelos de Datos Requeridos

#### SaldoCliente

```python
class SaldoCliente(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    venta = models.ForeignKey(Ventas, on_delete=models.PROTECT)
    monto_original = MoneyField(max_digits=12, decimal_places=2)
    saldo_pendiente = MoneyField(max_digits=12, decimal_places=2)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateField()
    estado = models.CharField(max_length=20)  # Pendiente, Parcial, Pagado, Vencido
    moneda = models.CharField(max_length=3, default='MXN')
```

#### AntigüedadSaldo

```python
class AntigüedadSaldo(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    fecha_calculo = models.DateField()
    corriente = MoneyField(default=0)      # 0-30 días
    vencido_1 = MoneyField(default=0)      # 31-60 días
    vencido_2 = MoneyField(default=0)      # 61-90 días
    vencido_3 = MoneyField(default=0)      # +90 días
    total = MoneyField(default=0)
```

### Integraciones Requeridas

- **Módulo ventas**: Hook en post_save de Ventas para crear SaldoCliente
- **Módulo pagos**: Hook en post_save de PagoVenta para actualizar saldos
- **Sistema de cache**: Usar Redis existente para métricas calculadas
- **Sistema de reportes**: Integrar con Excel export existente
- **Logs de auditoría**: Usar LogActividad existente para tracking

### Criterios de Performance

- Cálculo de antigüedad: < 5 segundos para 10,000 registros
- Dashboard de resumen: < 2 segundos usando cache
- Estado de cuenta: < 3 segundos por cliente
- Validación de límite de crédito: < 500ms en tiempo real

---

## 📅 CRONOGRAMA DE ENTREGA

| Sprint       | Semanas | Historias     | Entregables                                    |
| ------------ | ------- | ------------- | ---------------------------------------------- |
| **Sprint 1** | 1-2     | Historia 1, 3 | Sincronización automática + validación crédito |
| **Sprint 2** | 3-4     | Historia 2    | Registro abonos multiforma                     |
| **Sprint 3** | 5-6     | Historia 4    | Dashboard resumen + refinamiento               |
| **Sprint 4** | 7-8     | Historia 5    | Cálculo antigüedad de saldos                   |
| **Sprint 5** | 9-10    | Historia 6    | Estados de cuenta históricos                   |
| **Sprint 6** | 11-12   | Historia 7, 8 | Alertas + reportes ejecutivos                  |
| **Sprint 7** | 13-14   | -             | Testing integral + documentación               |
| **Sprint 8** | 15      | -             | Capacitación + go-live                         |

---

## ✅ DEFINICIÓN DE COMPLETADO (Definition of Done)

Para cada historia de usuario:

- [ ] Código implementado y review aprobado
- [ ] Tests unitarios con cobertura > 80%
- [ ] Tests de integración funcionales
- [ ] Documentación técnica actualizada
- [ ] Interface de usuario validada por stakeholders
- [ ] Performance cumple criterios establecidos
- [ ] Deploy en ambiente de staging exitoso
- [ ] Datos de prueba migrados correctamente

---

**Próximos pasos**: Crear documentación técnica detallada y manual de usuario para importar a Notion junto con estas historias de usuario.
