# Módulo de Ventas — Arquitectura, Flujos y Mejoras Propuestas

> Documento técnico generado el 4 de abril de 2026.  
> Cubre la arquitectura actual, flujos de negocio, diagrama de modelos y oportunidades de mejora.

---

## Tabla de Contenidos

1. [Visión General](#1-visión-general)
2. [Diagrama de Modelos (ERD)](#2-diagrama-de-modelos-erd)
3. [Flujo 1 — Ciclo de vida de una Venta](#3-flujo-1--ciclo-de-vida-de-una-venta)
4. [Flujo 2 — Gestión de Crédito](#4-flujo-2--gestión-de-crédito)
5. [Flujo 3 — Registro de Pagos y Estado de Cobranza](#5-flujo-3--registro-de-pagos-y-estado-de-cobranza)
6. [Flujo 4 — Anticipos](#6-flujo-4--anticipos)
7. [Flujo 5 — Reporte Global de Cobranza](#7-flujo-5--reporte-global-de-cobranza)
8. [Flujo 6 — Vista de Balances](#8-flujo-6--vista-de-balances)
9. [Arquitectura de Capas](#9-arquitectura-de-capas)
10. [Mejoras Propuestas](#10-mejoras-propuestas)

---

## 1. Visión General

El módulo `ventas` cubre el ciclo completo comercial de una empresa exportadora/importadora:

| Área          | Funcionalidad                                                            |
| ------------- | ------------------------------------------------------------------------ |
| **Clientes**  | Registro con límite de crédito, calificación crediticia, mercado destino |
| **Ventas**    | Nacional / Exportación, Contado / Crédito, Venta / Maquila, multi-moneda |
| **Cobranza**  | Seguimiento de estados (Pendiente → Parcial → Pagado / Vencido)          |
| **Anticipos** | Pagos adelantados aplicados como saldo FVR                               |
| **Reportes**  | Balances filtrados por período + reporte global de cobranza              |
| **Métricas**  | DSO (Days Sales Outstanding), tendencias mensuales                       |

---

## 2. Diagrama de Modelos (ERD)

```mermaid
erDiagram
    TerminoCredito {
        int id PK
        str nombre
        int dias_credito
        decimal tasa_interes_mensual
        bool activo
    }

    MercadoDestino {
        int id PK
        str nombre
        str moneda_preferida
        decimal factor_riesgo
        bool requiere_documentacion_especial
    }

    Pais {
        int id PK
        str nombre
    }

    Cliente {
        int id PK
        str nombre
        str tipo_cliente
        money limite_credito
        str calificacion_credito
        bool activo
    }

    Agente {
        int id PK
        str nombre
    }

    Producto {
        int id PK
        str nombre
    }

    Sucursal {
        int id PK
        str nombre
    }

    Cuenta {
        int id PK
        str numero_cuenta
    }

    Anticipo {
        int id PK
        money monto
        date fecha
        str estado_anticipo
    }

    Ventas {
        int id PK
        date fecha_salida_manifiesto
        date fecha_deposito
        date fecha_vencimiento
        str pedimento
        str carga
        str PO
        str cantidad
        money monto
        money monto_pagado
        str tipo_venta
        str tipo_registro
        str modalidad_pago
        str estado_cobranza
        str moneda_venta
        decimal tipo_cambio
        str incoterm
    }

    PagoVenta {
        int id PK
        date fecha_pago
        money monto_pago
        str metodo_pago
        str referencia
    }

    SaldoCliente {
        int id PK
        money monto_original
        money saldo_pendiente
        date fecha_vencimiento
        str estado
        str moneda
    }

    ObligacionFiscal {
        int id PK
        decimal monto
        date fecha_vencimiento
    }

    Cliente ||--o{ Ventas : "tiene"
    Cliente ||--o{ Anticipo : "recibe"
    Cliente ||--o{ SaldoCliente : "acumula"
    Cliente }o--|| MercadoDestino : "pertenece a"
    Cliente }o--|| Pais : "es de"
    Cliente }o--o| TerminoCredito : "usa por default"
    Ventas }o--|| Agente : "tramita"
    Ventas }o--|| Producto : "incluye"
    Ventas }o--|| Sucursal : "en sucursal"
    Ventas }o--|| Cuenta : "abona a"
    Ventas }o--o| TerminoCredito : "con plazo"
    Ventas }o--o| MercadoDestino : "destino"
    Ventas }o--o| Anticipo : "usa anticipo"
    Ventas ||--o{ PagoVenta : "recibe pagos"
    Ventas ||--o| SaldoCliente : "genera saldo"
    PagoVenta }o--|| Cuenta : "deposita en"
```

---

## 3. Flujo 1 — Ciclo de vida de una Venta

```mermaid
flowchart TD
    A([Inicio: Admin crea Venta]) --> B{Tipo Registro}
    B -- VENTA --> C[TipoVenta: Nacional / Exportación]
    B -- MAQUILA --> C

    C --> D{Modalidad de Pago}

    D -- Contado --> E[estado_cobranza = Pagado\nmonto_pagado = monto]
    D -- Crédito --> F[estado_cobranza = Pendiente\nmonto_pagado = 0]

    F --> G{¿Tiene TerminoCredito?}
    G -- Sí --> H[Calcular fecha_vencimiento\n= fecha_deposito + dias_credito]
    G -- No --> I[fecha_vencimiento manual requerida]
    H --> J[Guardar Venta]
    I --> J
    E --> J

    J --> K{¿Cliente tiene mercado_destino?}
    K -- Sí --> L[Heredar mercado_destino del cliente]
    K -- No --> M[Mercado vacío]
    L --> N([Venta guardada en BD])
    M --> N

    N --> O{¿Venta a crédito?}
    O -- Sí --> P[CuentasPorCobrarService\nsincronizar_deuda_venta]
    O -- No --> Q([Fin: sin CxC])
    P --> R([SaldoCliente creado])
```

---

## 4. Flujo 2 — Gestión de Crédito del Cliente

```mermaid
flowchart TD
    A([Se intenta venta a Crédito]) --> B[Cliente.credito_disponible]
    B --> C{limite_credito - saldo_deuda_activa}
    C --> D{¿credito_disponible >= monto_venta?}

    D -- No --> E[❌ Rechazar / Advertir\nSin crédito suficiente]
    D -- Sí --> F[✅ Aprobar venta a crédito]

    F --> G[Verificar calificacion_credito]
    G -- A+ / A --> H[Crédito sin restricciones]
    G -- B --> I[Notificación de riesgo moderado]
    G -- C --> J[Requiere aprobación manual]

    H --> K[Registrar Venta\ncon TerminoCredito]
    I --> K
    J --> K

    K --> L[Calcular fecha_vencimiento\nautomáticamente en save]
    L --> M([Venta a crédito activa])

    M --> N{Monitoreo periódico}
    N --> O{¿Hoy > fecha_vencimiento?}
    O -- Sí --> P[actualizar_estado_cobranza\n→ VENCIDO]
    O -- No --> Q[Estado: PENDIENTE / PARCIAL]

    P --> R[calcular_interes_mora\ntasa_interes_mensual × meses_mora]
```

---

## 5. Flujo 3 — Registro de Pagos y Estado de Cobranza

```mermaid
flowchart TD
    A([Admin registra PagoVenta]) --> B[monto_pago + metodo_pago\n+ cuenta_destino]
    B --> C[PagoVenta.save]
    C --> D[Llamada automática:\nventa.actualizar_estado_cobranza]

    D --> E[sum de todos los PagoVenta\nassociados a la Venta]
    E --> F[monto_pagado = total_pagos]
    F --> G{saldo_pendiente = monto - monto_pagado}

    G -- saldo <= 0 --> H[estado_cobranza = PAGADO]
    G -- saldo > 0 y hay pagos parciales --> I{¿está vencida?}
    G -- saldo > 0 y sin pagos --> J{¿está vencida?}

    I -- Sí --> K[estado_cobranza = VENCIDO]
    I -- No --> L[estado_cobranza = PARCIAL]
    J -- Sí --> K
    J -- No --> M[estado_cobranza = PENDIENTE]

    H --> N[Venta.save]
    K --> N
    L --> N
    M --> N

    N --> O{¿Tiene SaldoCliente?}
    O -- Sí --> P[Actualizar saldo_pendiente\nen SaldoCliente]
    O -- No --> Q([Fin])
    P --> Q
```

---

## 6. Flujo 4 — Anticipos

```mermaid
flowchart TD
    A([Vista: /anticipos/crear/]) --> B[AnticipoForm\ncliente + sucursal + cuenta + monto + fecha]
    B --> C[form.is_valid]
    C -- No --> D[Mostrar errores]
    C -- Sí --> E[Anticipo.save\nestado = Pendiente]

    E --> F([BD: Anticipo registrado])

    F --> G{¿Se aplica a una Venta?}
    G -- Sí --> H[Ventas.anticipo = FK al anticipo\nestado_anticipo → Aplicado]
    G -- No --> I[Anticipo permanece Pendiente]

    I --> J[Reporte Cobranza:\nAparece como SALDO FVR CLIENTE]
    H --> K([Anticipo consumido])

    style J fill:#fef3c7,stroke:#d97706
    style K fill:#d1fae5,stroke:#059669
```

---

## 7. Flujo 5 — Reporte Global de Cobranza

```mermaid
flowchart TD
    A([Vista: /reporte-cobranza/]) --> B[generar_reporte_cobranza\nfecha_inicio, fecha_fin, tipo_cambio_override]

    B --> C[Filtrar Ventas\nestado_cobranza IN Pendiente, Parcial, Vencido]

    C --> D{Separar por tipo_registro}
    D -- VENTA --> E[qs_ventas]
    D -- MAQUILA --> F[qs_maquila]

    E --> G[_calcular_saldos_por_cliente\nagrupado por cliente x moneda_venta]
    F --> H[_calcular_saldos_por_cliente\nagrupado por cliente x sucursal]

    G --> I[Separar USD / MXN\nCalcular totales por sección]
    H --> J[Tipo cambio promedio\no override manual\nConversión USD → MXN]

    I --> K[ventas_por_cliente\ntotales_ventas_usd\ntotales_ventas_mxn]
    J --> L[maquila_por_cliente\ntotales_maquila]

    B --> M[Anticipos Pendientes\npor cliente → saldo FVR]
    B --> N[ObligacionFiscal\nmás reciente → Impuestos a Pagar]

    K --> O[Context: 3 secciones\nVentas x Cobrar\nMaquila x Cobrar\nImpuestos a Pagar]
    L --> O
    M --> O
    N --> O

    O --> P([Template renderizado])
```

---

## 8. Flujo 6 — Vista de Balances

```mermaid
flowchart TD
    A([Vista: /balances/?filters]) --> B[Leer parámetros GET\ncliente, cuenta, sucursal, mercado\nmodalidad, estado, year, months, periodo]

    B --> C{periodo}
    C -- diario --> D[Filtro por fecha_deposito\ndía exacto o rango]
    C -- semanal --> E[TruncWeek\nagrupar por semana]
    C -- mensual --> F[TruncMonth\nagrupar por mes - default]

    D --> G[GROUP BY fecha, cliente, cuenta, sucursal]
    E --> G
    F --> G

    G --> H[Annotate:\ntotal_ventas, total_pagado\nventa_max, min, promedio\nfecha_vencimiento_proxima]

    H --> I[_derive_estado\nrecalcula estado de cobranza\na partir de totales agregados]

    I --> J[Calcular acumulado lineal]
    J --> K[Armar lista balances\ncon todos los campos]

    K --> L[Context con:\nbalances, filtros activos\nclientes, cuentas, sucursales\nmercados, años disponibles]

    L --> M([Template: ventas_balances.html])

    style I fill:#eff6ff,stroke:#2563eb
```

---

## 9. Arquitectura de Capas

```mermaid
graph TB
    subgraph Presentación
        U1[Admin Django\nVentasAdmin, ClienteAdmin\nPagoVentaAdmin...]
        U2[Vistas personalizadas\nbalances, anticipos, reporte_cobranza]
    end

    subgraph Servicios
        S1[reporte_cobranza_service\nGenera reporte 3 secciones]
        S2[cuentas_por_cobrar_service\nRF1-RF4: deuda, pagos, aging, estados de cuenta]
        S3[metrics_service\nDSO, tendencias, KPIs]
        S4[cache_service\nInvalidación y lectura de caché]
    end

    subgraph Modelos
        M1[Ventas\nmodelo central]
        M2[Cliente / TerminoCredito\nMercadoDestino]
        M3[PagoVenta\nAnticipo]
        M4[SaldoCliente\nAntigüedadSaldo\nEstadoCuentaCliente]
        M5[ObligacionFiscal\nConfiguracionCuentasPorCobrar]
    end

    subgraph Externo
        E1[catalogo.Sucursal\ncatalogo.Producto\ncatalogo.Pais]
        E2[gastos.Cuenta]
        E3[djmoney MoneyField\nMulti-moneda]
    end

    U1 --> S2
    U1 --> S3
    U2 --> S1
    U2 --> M3
    S1 --> M1
    S1 --> M3
    S1 --> M5
    S2 --> M1
    S2 --> M4
    S2 --> S4
    S3 --> M4
    M1 --> M2
    M1 --> E1
    M1 --> E2
    M1 --> E3
```

---

## 10. Mejoras Propuestas

### 10.1 Críticas (impacto alto, esfuerzo moderado)

#### A — Automatización del estado VENCIDO

**Problema actual:** El campo `estado_cobranza` solo se actualiza cuando se registra un `PagoVenta`. Si una venta nunca recibe pagos, su estado nunca pasa a `VENCIDO` automáticamente.

**Propuesta:** Comando de gestión (`management/command`) o tarea Celery periódica que ejecute:

```python
Ventas.objects.filter(
    modalidad_pago='Credito',
    estado_cobranza__in=['Pendiente', 'Parcial'],
    fecha_vencimiento__lt=date.today()
).update(estado_cobranza='Vencido')
```

```mermaid
flowchart LR
    T([Tarea diaria\ncron / Celery]) --> Q[Ventas pendientes\ncon fecha_vencimiento < hoy]
    Q --> U[bulk_update → VENCIDO]
    U --> N[Notificación por correo\nal responsable de cobranza]
```

---

#### B — Aplicación manual de Anticipos a Ventas

**Problema actual:** La FK `Ventas.anticipo` existe pero la lógica de cambiar `estado_anticipo → Aplicado` es manual y no hay validación de que el anticipo no se use en dos ventas.

**Propuesta:** Vista/acción de admin `"Aplicar anticipo"` que:

1. Valide que el anticipo esté `Pendiente`.
2. Reste el monto del anticipo del `monto_pagado` de la venta.
3. Cambie `estado_anticipo → Aplicado` en la misma transacción.

---

### 10.2 Importantes (valor de negocio)

#### C — Alertas tempranas de crédito

**Propuesta:** Enviar notificación cuando una cuenta por cobrar alcance el 80% del plazo sin haberse pagado.

```mermaid
flowchart LR
    D([Tarea diaria]) --> F[Ventas con\n estado=Pendiente\ny dias_restantes <= 20% del plazo]
    F --> E[Enviar email digest\nal equipo de cobranza]
```

---

#### D — Tipo de cambio centralizado

**Problema actual:** `tipo_cambio` se guarda por venta manualmente. No hay fuente de verdad ni tasa de referencia del día.

**Propuesta:** Campo en `ConfiguracionCuentasPorCobrar` con `tipo_cambio_usd_hoy` actualizable desde el admin, o integración ligera con una API pública (Banxico).

---

#### E — Estado real vs. almacenado (consistencia dual)

**Problema actual:** `build_ventas_balances_context` define una función interna `_derive_estado` que recalcula el estado a partir de los totales, lo que implica que el campo `estado_cobranza` almacenado puede diferir del estado real calculado.

**Propuesta:** Mover `_derive_estado` como método de clase en `Ventas` (ya existe como `actualizar_estado_cobranza`) y ejecutarla de forma consistente. Considerar usar el campo almacenado como única fuente de verdad después de asegurar el punto **A**.

---

### 10.3 Deseables (calidad y experiencia)

#### F — Dashboard de cobranza en tiempo real

**Propuesta:** Añadir una sección al dashboard principal con KPIs clave:

| KPI                          | Cálculo                                                                       |
| ---------------------------- | ----------------------------------------------------------------------------- |
| DSO (Days Sales Outstanding) | `CxC promedio / Ventas crédito × días` — ya implementado en `metrics_service` |
| Tasa de morosidad            | `Ventas vencidas / Total cartera crédito`                                     |
| Cartera por antigüedad       | 0-30d / 31-60d / 61-90d / +90d                                                |
| Recuperación mensual         | Total `PagoVenta` del mes vs. mes anterior                                    |

---

#### G — Historial de cambios de estado en Ventas

**Problema actual:** No hay log de cuándo ni por qué cambió `estado_cobranza`.

**Propuesta:** Aprovechar el módulo `auditoria` ya existente en el proyecto para registrar cada cambio de estado de cobranza con timestamp y usuario.

---

#### H — Exportación desde la vista de Balances

**Problema actual:** La vista `/balances/` no tiene botón de exportación a Excel/CSV.

**Propuesta:** Añadir botones DataTables (ya usados en otras vistas) o una acción GET `?export=xlsx` que use `openpyxl` para generar el reporte con los mismos filtros activos.

---

#### I — Validación de límite de crédito en el Admin

**Problema actual:** `Cliente.puede_otorgar_credito()` y `Cliente.credito_disponible()` existen como métodos pero no se llaman al guardar una `Venta` desde el admin.

**Propuesta:** Sobrescribir `VentasAdmin.save_model` para mostrar un `messages.warning` cuando el crédito disponible sea insuficiente.

```python
def save_model(self, request, obj, form, change):
    if obj.modalidad_pago == 'Credito':
        if not obj.cliente.puede_otorgar_credito(obj.monto.amount):
            messages.warning(request,
                f"⚠️ Crédito insuficiente para {obj.cliente}. "
                f"Disponible: {obj.cliente.credito_disponible()}"
            )
    super().save_model(request, obj, form, change)
```

---

### Resumen de prioridades

```mermaid
quadrantChart
    title Prioridad de Mejoras
    x-axis Bajo Esfuerzo --> Alto Esfuerzo
    y-axis Bajo Impacto --> Alto Impacto
    quadrant-1 Hacer primero
    quadrant-2 Planificar
    quadrant-3 Opcional
    quadrant-4 Reevaluar
    A - Auto-vencimiento: [0.25, 0.90]
    B - Aplicar anticipos: [0.35, 0.80]
    I - Validar crédito admin: [0.15, 0.75]
    C - Alertas cobranza: [0.45, 0.70]
    E - Consistencia estado: [0.30, 0.65]
    D - Tipo cambio central: [0.55, 0.60]
    H - Export balances: [0.40, 0.50]
    G - Historial estados: [0.50, 0.45]
    F - Dashboard KPIs: [0.70, 0.65]
```
