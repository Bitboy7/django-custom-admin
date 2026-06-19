# Manual de Usuario - Sistema de Cuentas por Cobrar

## 📋 Información General

**Sistema**: Django Custom Admin - Módulo Cuentas por Cobrar  
**Versión**: 1.0.0  
**Fecha**: 11 de marzo, 2026  
**Dirigido a**: Usuarios finales, personal de cobranza y administradores

---

## 🎯 Introducción al Sistema

El Sistema de Cuentas por Cobrar es una extensión del módulo de ventas que permite gestionar automáticamente la deuda de clientes, registrar pagos de forma eficiente y generar reportes detallados para el análisis y seguimiento de cobranza.

### Beneficios Principales

✅ **Automatización total**: No más registro manual de deudas  
✅ **Control en tiempo real**: Saldos actualizados al instante  
✅ **Análisis avanzado**: Reportes de antigüedad y performance  
✅ **Trazabilidad completa**: Historial detallado de todos los movimientos

### Roles y Permisos

- **👤 Vendedor**: Consulta saldos y límites de crédito
- **💼 Ejecutivo de Cobranza**: Registra pagos y genera reportes
- **📊 Supervisor de Cobranza**: Acceso completo a reportes y análisis
- **⚙️ Administrador**: Configuración del sistema y mantenimiento

---

## 🚀 Primeros Pasos

### Acceso al Sistema

1. **Iniciar sesión** en el sistema Django Admin
2. **Navegar** al módulo "Ventas" en el menú principal
3. **Buscar** las nuevas secciones:
   - 📊 **Saldos de Clientes**
   - 📈 **Antigüedad de Saldos**
   - 📄 **Estados de Cuenta**
   - ⚙️ **Configuración CxC**

### Dashboard Principal

El dashboard muestra un resumen ejecutivo con:

- **💰 Total de cartera**: Suma de todos los saldos pendientes
- **👥 Clientes con saldo**: Número de clientes que deben dinero
- **📋 Facturas pendientes**: Cantidad de facturas sin pagar completamente
- **⚠️ Cartera vencida**: Monto de deuda con fechas vencidas

---

## 📘 Guía de Operaciones

### 1️⃣ Gestión Automática de Deuda (RF1)

#### ¿Cómo funciona la sincronización automática?

When a salesperson creates a credit sale, the system automatically:

**✨ Proceso Automático**

```
Nueva Venta a Crédito → Sistema crea Saldo automáticamente → Aparece en Cuentas por Cobrar
```

**📋 Información que se registra automáticamente:**

- Cliente asociado
- Monto original de la deuda
- Fecha de vencimiento (basada en términos de crédito del cliente)
- Estado inicial: "Pendiente"
- Moneda de la transacción

**🔍 Verificar la sincronización:**

1. Ir a **Ventas > Saldos de Clientes**
2. Buscar por número de factura o cliente
3. Verificar que aparezca el nuevo registro

#### Casos Especiales

- **Ventas en efectivo**: No generan saldo (correcto)
- **Ventas mixtas**: Solo la porción a crédito genera saldo
- **Errores de sincronización**: Contactar al administrador del sistema

---

### 2️⃣ Registro de Abonos y Pagos (RF2)

#### Registrar un Pago Parcial

**📝 Paso a paso:**

1. **Localizar el saldo**
   - Ir a **Ventas > Saldos de Clientes**
   - Buscar por cliente o número de factura
   - Hacer clic en el registro correspondiente

2. **Acceder a pagos relacionados**
   - En la página del saldo, buscar sección "Pagos de Venta"
   - Hacer clic en "Agregar pago de venta"

3. **Registrar el pago**
   - **Monto**: Cantidad recibida
   - **Método de pago**: Seleccionar de la lista
     - 💵 Efectivo
     - 🏦 Transferencia bancaria
     - 💳 Tarjeta de crédito/débito
     - 📄 Cheque
   - **Fecha de pago**: Cuándo se recibió el dinero
   - **Referencia**: Número de comprobante, transferencia, etc.
   - **Cuenta bancaria**: Si aplica

4. **Guardar y verificar**
   - Hacer clic en "Guardar"
   - El sistema actualiza automáticamente:
     - ✅ Saldo pendiente se reduce
     - 🔄 Estado cambia a "Parcial" o "Pagado"
     - 📅 Fecha del último pago se actualiza

#### Métodos de Pago Disponibles

| Método            | Descripción                        | Requiere Referencia      |
| ----------------- | ---------------------------------- | ------------------------ |
| **Efectivo**      | Pago en moneda física              | No                       |
| **Transferencia** | Depósito bancario electrónico      | Sí (No. de operación)    |
| **Tarjeta**       | Pago con tarjeta de crédito/débito | Sí (No. de autorización) |
| **Cheque**        | Pago con cheque personal o de caja | Sí (No. de cheque)       |

#### Estados del Saldo tras Registrar Pagos

- **🟡 Pendiente**: No se han registrado pagos (saldo = monto original)
- **🔵 Parcial**: Se han registrado pagos parciales (0 < saldo < monto original)
- **🟢 Pagado**: Saldo completamente liquidado (saldo = 0)
- **🔴 Vencido**: Fecha de pago rebasada sin liquidación completa

---

### 3️⃣ Análisis de Antigüedad de Saldos (RF3)

#### Acceder al Reporte de Antigüedad

**📊 Navegación:**

1. Ir a **Ventas > Antigüedad de Saldos**
2. Filtrar por fecha de cálculo (más reciente por defecto)
3. Buscar cliente específico si es necesario

#### Interpretar los Rangos de Antigüedad

**📈 Categorías estándar:**

- **🟢 Corriente (0-30 días)**: Deuda normal, dentro del plazo
- **🟡 Vencido 1 (31-60 días)**: Requiere seguimiento básico
- **🟠 Vencido 2 (61-90 días)**: Requiere llamadas y emails
- **🔴 Vencido 3 (+90 días)**: Moroso crítico, proceso legal

**💡 Cómo usar esta información:**

**Para Ejecutivos de Cobranza:**

- Priorizar clientes en categoría "Vencido 2" y "Vencido 3"
- Contactar clientes en "Vencido 1" preventivamente
- Monitorear que los clientes "Corrientes" no pasen a vencido

**Para Supervisores:**

- Revisar distribución porcentual mensual
- Identificar tendencias (¿está empeorando el aging?)
- Asignar casos más complejos al equipo

#### Generar Reporte de Antigüedad

**🎯 Opciones de reporte:**

1. **Por cliente individual**
   - Seleccionar cliente específico
   - Ver evolución histórica de su aging
   - Generar PDF para envío al cliente

2. **Consolidado general**
   - Todos los clientes en una vista
   - Exportar a Excel para análisis
   - Comparar con períodos anteriores

**📋 Información incluida en reportes:**

- Distribución por rangos de antigüedad
- Total de cartera por cliente
- Número de facturas pendientes
- Porcentaje de cada categoría
- Tendencia vs período anterior
- Clasificación de riesgo (Alto/Medio/Bajo)

---

### 4️⃣ Estados de Cuenta Históricos (RF4)

#### Generar Estado de Cuenta de Cliente

**📄 Proceso completo:**

1. **Seleccionar cliente**
   - Ir a **Ventas > Estados de Cuenta Cliente**
   - Hacer clic en "Agregar estado de cuenta cliente"
   - Seleccionar el cliente de la lista

2. **Configurar período**
   - **Fecha inicio**: Desde cuándo incluir movimientos
   - **Fecha fin**: Hasta cuándo incluir movimientos
   - **Formato**: Web, PDF o Excel

3. **Generar reporte**
   - Hacer clic en "Guardar"
   - El sistema procesa la información
   - Se crea el estado de cuenta

4. **Revisar y descargar**
   - Ver resumen en pantalla
   - Descargar archivo si se eligió PDF/Excel
   - Enviar por email al cliente si es necesario

#### Contenido del Estado de Cuenta

**📊 Estructura del reporte:**

**🔝 Encabezado:**

- Datos del cliente (nombre, dirección, contacto)
- Límite de crédito autorizado
- Crédito disponible actual
- Período del reporte

**📋 Detalle cronológico:**
| Fecha | Tipo | Referencia | Concepto | Cargo | Abono | Saldo |
|-------|------|------------|----------|--------|--------|-------|
| 01/03/26 | VENTA | FAC-001 | Venta a crédito | $10,000 | - | $10,000 |
| 05/03/26 | PAGO | TXN-123 | Pago transferencia | - | $3,000 | $7,000 |
| 10/03/26 | PAGO | EF-001 | Pago efectivo | - | $7,000 | $0 |

**📈 Resumen final:**

- Total de ventas a crédito en el período
- Total de abonos recibidos
- Saldo pendiente final
- Distribución por antigüedad actual
- Promedio histórico de días de pago

#### Casos de Uso Comunes

**👤 Para Ejecutivos de Cobranza:**

- Generar antes de llamada de cobranza
- Tener vista completa de la relación comercial
- Identificar patrones de pago del cliente
- Justificar acciones de cobranza

**📧 Para Envío a Clientes:**

- Formato PDF profesional
- Anexar a emails de cobranza
- Facilitar negociaciones de pago
- Documentar acuerdos de pago

---

## 🔧 Configuración del Sistema

### Ajustar Parámetros de Cuentas por Cobrar

**⚙️ Acceso a configuración:**

1. Ir a **Ventas > Configuración CxC**
2. Editar el registro existente (solo debe haber uno)

**📋 Parámetros configurables:**

#### Rangos de Antigüedad

- **Días corriente**: Por defecto 30 días
- **Días vencido 1**: Por defecto 60 días
- **Días vencido 2**: Por defecto 90 días
- (Todo lo mayor a 90 días es "Vencido 3" automáticamente)

#### Automatización

- **✅ Cálculo automático aging**: Activar cálculo diario
- **⏰ Hora de cálculo**: A qué hora ejecutar (ej: 02:00 AM)
- **📅 Frecuencia**: Diario o semanal

#### Alertas y Notificaciones

- **✅ Enviar alertas de vencimiento**: Activar notificaciones
- **📧 Email responsable cobranza**: Dirección para recibir alertas
- **📆 Días previos alerta**: Cuántos días antes avisar

#### Límites y Validaciones

- **✅ Permitir sobregiro crédito**: Con autorización especial
- **📊 % sobregiro permitido**: Hasta quanto permitir exceder

---

## 📊 Dashboard y Reportes

### dashboard Principal de Cuentas por Cobrar

**🎯 Métricas clave mostradas:**

#### Indicadores Financieros

- **💰 Total Cartera**: Suma de todos los saldos pendientes
- **💵 Cartera en Pesos**: Saldos en moneda nacional
- **💲 Cartera en Dólares**: Saldos en moneda extranjera
- **📈 Crecimiento vs mes anterior**: Porcentaje de cambio

#### Indicadores de Gestión

- **👥 Clientes con saldo**: Cantidad de clientes que deben
- **📄 Facturas pendientes**: Total de facturas sin liquidar
- **⏱️ DSO promedio**: Days Sales Outstanding (días promedio de cobranza)
- **🎯 Eficiencia de cobranza**: Porcentaje de recuperación

#### Alertas y Acciones

- **🚨 Facturas próximas a vencer**: En los próximos 5 días
- **⚠️ Clientes sobre límite**: Exceden su límite de crédito
- **🔴 Cartera crítica**: Más de 90 días vencida
- **📞 Acciones pendientes**: Llamadas y seguimientos requeridos

### Reportes Disponibles

#### 📈 Reporte de Aging Consolidado

**Contenido:**

- Distribución de cartera por rangos de antigüedad
- Comparativo con períodos anteriores
- Gráfico de evolución mensual
- Lista de top 10 deudores

**Uso recomendado:**

- Revisión mensual con gerencia
- Análisis de tendencias de cobranza
- Identificación de deterioro en cartera

#### 📊 Análisis de Performance de Cobranza

**Contenido:**

- DSO (Days Sales Outstanding) histórico
- Tasa de recuperación por período
- Efectividad por ejecutivo de cobranza
- Comparativo con metas establecidas

**Uso recomendado:**

- Evaluación de desempeño del equipo
- Identificar oportunidades de mejora
- Reporting a dirección general

#### 🎯 Reporte de Clientes Morosos

**Contenido:**

- Clientes con saldos vencidos +60 días
- Historial de pagos y comportamiento
- Acciones de cobranza realizadas
- Recomendaciones de escalación

**Uso recomendado:**

- Priorización de esfuerzos de cobranza
- Decisiones de suspensión de crédito
- Evaluación para proceso legal

---

## 🚨 Alertas y Notificaciones

### Tipos de Alertas

#### 📧 Alertas por Email

**Se envían automáticamente cuando:**

- ✉️ Facturas próximas a vencer (5 días antes)
- 🚨 Clientes rebasan límite de crédito
- 📊 Cálculo de aging completado
- ❌ Errores en procesos automáticos

#### 🔔 Alertas en Sistema

**Aparecen en el dashboard:**

- 🟡 Facturas que vencen hoy
- 🔴 Clientes morosos críticos (+90 días)
- 🔵 Pagos registrados hoy
- 🟢 Saldos liquidados recientemente

### Configurar Notificaciones

**📧 Email settings:**

1. Ir a **Ventas > Configuración CxC**
2. Editar campo "Email responsable cobranza"
3. Guardar cambios
4. Verificar recepción con una alerta de prueba

**🔔 Preferencias de alerta:**

- Activar/desactivar alertas de vencimiento
- Configurar días de anticipación
- Personalizar frecuencia de notificaciones

---

## 💡 Casos de Uso Prácticos

### Escenario 1: Cliente con Pago Vencido

**🎯 Situación:**
El cliente "Distribuidora Norte S.A." tiene una factura vencida hace 45 días por $25,000 MXN.

**📋 Proceso de cobranza:**

1. **Localizar en sistema**
   - Buscar en "Saldos de Clientes"
   - Filtrar por estado "Vencido"
   - Identificar la factura específica

2. **Revisar historial**
   - Generar estado de cuenta del último año
   - Verificar patrón de pagos histórico
   - Identificar frecuencia de retrasos

3. **Contactar al cliente**
   - Llamar usando información del estado de cuenta
   - Enviar PDF del estado de cuenta por email
   - Negociar plan de pago si es necesario

4. **Registrar gestión**
   - Agregar notas en el campo "Notas" del saldo
   - Si hay acuerdo, registrar fecha compromiso
   - Programar seguimiento en calendario

5. **Registrar pago cuando llegue**
   - Ir a "Pagos de Venta" de la factura
   - Registrar método, monto y referencia
   - Verificar que saldo se actualice automáticamente

### Escenario 2: Análisis Mensual de Cartera

**🎯 Situación:**
Es fin de mes y necesitas preparar el reporte mensual de cuentas por cobrar.

**📊 Proceso de análisis:**

1. **Generar aging consolidado**
   - Ir a "Antigüedad de Saldos"
   - Filtrar por fecha del último día del mes
   - Exportar a Excel para análisis

2. **Calcular métricas clave**
   - DSO del mes vs mes anterior
   - Distribución porcentual por aging
   - Identificar deterioro en categorías

3. **Identificar casos críticos**
   - Clientes que migraron a "Vencido 3"
   - Nuevos clientes en mora
   - Montos significativos vencidos

4. **Preparar reporte ejecutivo**
   - Resumen de métricas principales
   - Gráficos de tendencias
   - Plan de acciones para próximo mes
   - Recomendaciones de política de crédito

### Escenario 3: Validación de Límite de Crédito

**🎯 Situación:**
Un vendedor quiere hacer una venta a crédito pero el sistema alerta sobre límite.

**⚠️ Proceso de validación:**

1. **Revisar alerta del sistema**
   - Verificar límite de crédito del cliente
   - Calcular crédito disponible actual
   - Determinar monto de excedente

2. **Analizar historial del cliente**
   - Generar estado de cuenta reciente
   - Revisar patrón de pagos
   - Verificar si hay pagos pendientes de aplicar

3. **Tomar decisión**
   - **Si es buen pagador**: Autorizar excepción temporal
   - **Si es moroso**: Rechazar o sugerir pago parcial
   - **Si es nuevo**: Reducir monto o pedir garantías

4. **Registrar decisión**
   - Agregar notas justificando la decisión
   - Si se autoriza, modificar temporalmente el límite
   - Programar revisión del límite en 30 días

---

## ❓ Preguntas Frecuentes (FAQ)

### Sobre Funcionamiento General

**❓ ¿Por qué no aparece un saldo para una venta que hice?**

- Verificar que la modalidad de pago sea "Crédito" o "Mixto"
- Las ventas en "Contado" no generan saldo automáticamente
- Si es crédito y no aparece, contactar al administrador del sistema

**❓ ¿Puedo modificar un saldo después de creado?**

- Los saldos se actualizan automáticamente con los pagos
- No se deben modificar manualmente los montos
- Si hay error, contactar al administrador para corrección

**❓ ¿Qué pasa si registro un pago por error?**

- El administrador puede anular el pago específico
- El saldo se recalculará automáticamente
- Se mantiene historial de la corrección para auditoría

### Sobre Pagos y Abonos

**❓ ¿Puedo registrar un pago mayor al saldo pendiente?**

- Por defecto no, el sistema lo impide
- El administrador puede configurar permitir sobrepagos
- Los sobrepagos quedan como crédito a favor del cliente

**❓ ¿Cómo registrar un pago que cubre múltiples facturas?**

- Distribuir el pago entre las facturas correspondientes
- Registrar un pago parcial en cada factura
- Usar la misma referencia para identificar que fue un solo pago

**❓ ¿Puedo modificar un pago ya registrado?**

- Los pagos no se pueden modificar directamente
- Se debe anular el pago incorrecto y registrar uno nuevo
- Contactar al administrador para estas operaciones

### Sobre Reportes y Análisis

**❓ ¿Con qué frecuencia se actualiza el aging?**

- Por defecto se calcula automáticamente cada día a las 2:00 AM
- También se puede generar manualmente en cualquier momento
- La configuración se puede cambiar en "Configuración CxC"

**❓ ¿Por qué no coinciden los totales en diferentes reportes?**

- Verificar que estén usando el mismo período de fechas
- Considerar diferencias de tiempo (algunos reportes incluyen transacciones del día actual)
- El cache puede mostrar datos levemente desactualizados (se actualiza cada 15 minutos)

**❓ ¿Puedo exportar reportes a Excel?**

- Sí, la mayoría de reportes tienen opción de exportación
- Los estados de cuenta pueden generarse en PDF o Excel
- El aging consolidado incluye gráficos en Excel

### Sobre Configuración y Permisos

**❓ ¿Quién puede cambiar la configuración del sistema?**

- Solo usuarios con rol de "Administrador"
- Los cambios afectan a todo el sistema globalmente
- Se recomienda coordinar cambios con el equipo de TI

**❓ ¿Puedo personalizar los rangos de aging?**

- Sí, en "Configuración CxC" se pueden modificar los días de cada rango
- Los cambios aplican para todos los cálculos futuros
- No afecta cálculos históricos ya realizados

**❓ ¿Cómo obtener permisos para módulos específicos?**

- Contactar al administrador del sistema
- Especificar qué funcionalidades necesitas
- Los permisos se asignan por rol y por usuario

---

## 📞 Soporte y Contactos

### Escalación de Problemas

#### 🟢 Nivel 1: Problemas Operativos

**👤 Contacto**: Supervisor de Cobranza  
**📧 Email**: cobranza@empresa.com  
**📱 Extensión**: 1234

**Ejemplos**:

- Dudas sobre interpretación de reportes
- Procesos de cobranza específicos
- Capacitación en funcionalidades

#### 🟡 Nivel 2: Problemas Técnicos

**👤 Contacto**: Administrador del Sistema  
**📧 Email**: admin@empresa.com  
**📱 Extensión**: 5678

**Ejemplos**:

- Errores en cálculos automáticos
- Problemas de permisos o acceso
- Configuración de parámetros

#### 🔴 Nivel 3: Problemas Críticos

**👤 Contacto**: Departamento de TI  
**📧 Email**: soporte@empresa.com  
**📱 Extensión**: 9999

**Ejemplos**:

- Sistema no funciona completamente
- Pérdida de datos
- Problemas de rendimiento severos

### Recursos Adicionales

**📚 Documentación**:

- Manual técnico: `CUENTAS_POR_COBRAR_TECHNICAL_DOCUMENTATION.md`
- Historias de usuario: `ACCOUNTS_RECEIVABLE_USER_STORIES.md`
- Base de conocimiento interna: Portal de empleados

**🎓 Capacitación**:

- Sesiones de entrenamiento mensuales
- Videos tutoriales en portal interno
- Documentación de procesos específicos por departamento

**📈 Mejora Continua**:

- Sugerencias de mejora: mejoras@empresa.com
- Evaluación trimestral de funcionalidades
- Participación en actualizaciones del sistema

---

## 📋 Checklist de Entrenamiento

### Para Nuevos Usuarios

**🎯 Nivel Básico (Vendedores)**

- [ ] Entender cómo funciona la sincronización automática
- [ ] Verificar saldos de clientes antes de nueva venta
- [ ] Interpretar alertas de límite de crédito
- [ ] Consultar crédito disponible por cliente

**💼 Nivel Intermedio (Ejecutivos de Cobranza)**

- [ ] Registrar pagos en todos los métodos disponibles
- [ ] Generar estados de cuenta para clientes
- [ ] Interpretar reportes de aging básicos
- [ ] Usar filtros y búsquedas efectivamente

**📊 Nivel Avanzado (Supervisores)**

- [ ] Generar y analizar reportes consolidados
- [ ] Interpretar métricas de performance (DSO, etc.)
- [ ] Configurar alertas y notificaciones
- [ ] Analizar tendencias y tomar decisiones estratégicas

**⚙️ Nivel Administrador (TI/Gerencia)**

- [ ] Configurar parámetros del sistema
- [ ] Gestionar permisos y roles de usuario
- [ ] Monitorear performance y resolver problemas técnicos
- [ ] Interpretar logs y ejecutar mantenimiento

---

**🚀 ¡Listo para usar el Sistema de Cuentas por Cobrar!**

Este manual te guiará paso a paso en el uso efectivo del sistema. Recuerda consultar con tu supervisor ante cualquier duda y utilizar los canales de soporte apropiados según el tipo de problema que enfrentes.

**📝 Próximos pasos**:

1. Completar entrenamiento según tu rol
2. Practicar con datos de prueba
3. Comenzar operación gradual con supervisión
4. Reportar sugerencias de mejora
