# Plan XP — Módulo de Ventas

> Planificación ágil basada en **Extreme Programming (XP)** para el desarrollo del módulo `ventas` del ERP *Agrícola de la Costa*.  
> Aplica prácticas de las skills: `mermaid-diagrams` y `xp-practices`.

---

## 1. Metáfora del Sistema

**Metáfora**: *"El módulo de ventas es el libro mayor digital del comerciante agrícola: registra cada carga que sale del campo, quién la compró, cuánto debe, cuándo vence, y alerta cuando alguien no ha pagado."*

---

## 2. Visión

Permitir al equipo comercial registrar, rastrear y cobrar ventas de productos agrícolas (nacionales y de exportación), gestionar la cartera de clientes, anticipos y cuentas por cobrar, con auditoría completa e integración con facturación electrónica CFDI.

---

## 3. Product Backlog — Historias de Usuario

| ID | Historia | Valor | Riesgo | Est. (pts) |
|----|----------|-------|--------|------------|
| US-01 | Como *vendedor*, quiero registrar un cliente con datos básicos y límite de crédito. | Alto | Bajo | 3 |
| US-02 | Como *vendedor*, quiero registrar una venta de contado con producto, cantidad y monto. | Alto | Bajo | 5 |
| US-03 | Como *vendedor*, quiero registrar una venta a crédito con fecha de vencimiento auto-calculada. | Alto | Medio | 8 |
| US-04 | Como *contador*, quiero registrar pagos parciales de una venta a crédito con integridad transaccional. | Alto | Alto | 8 |
| US-05 | Como *vendedor*, quiero registrar un anticipo de cliente y aplicarlo a una venta. | Alto | Alto | 8 |
| US-06 | Como *gerente*, quiero ver un reporte de cobranza con saldos pendientes, vencidos y aging. | Alto | Medio | 13 |
| US-07 | Como *vendedor*, quiero importar datos de una factura CFDI XML para evitar captura manual. | Medio | Medio | 8 |
| US-08 | Como *contador*, quiero generar un estado de cuenta por cliente con movimientos del período. | Medio | Medio | 8 |
| US-09 | Como *gerente*, quiero ver análisis de antigüedad de saldos (aging) para evaluar riesgo crediticio. | Medio | Medio | 8 |
| US-10 | Como *vendedor*, quiero clasificar clientes por mercado de destino (Nacional, USA, etc.). | Medio | Bajo | 5 |
| US-11 | Como *sistema*, quiero calcular automáticamente intereses moratorios en ventas vencidas. | Medio | Medio | 5 |
| US-12 | Como *administrador*, quiero configurar días de aging y alertas de vencimiento. | Bajo | Bajo | 3 |
| US-13 | Como *vendedor*, quiero exportar balances de ventas a Excel con formato profesional. | Medio | Bajo | 5 |
| US-14 | Como *sistema*, quiero invalidar caché automáticamente al registrar pagos para datos actualizados. | Medio | Medio | 5 |
| US-15 | Como *auditor*, quiero que cada cambio de estado de cobranza se registre en el log de actividad. | Alto | Bajo | 3 |

**Total estimado**: 97 puntos  
**Velocidad esperada**: ~10 pts/iteración → **~10 iteraciones de 1 semana**

---

## 4. Prácticas XP Aplicadas

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e1f5fe', 'primaryTextColor': '#01579b', 'primaryBorderColor': '#0288d1', 'lineColor': '#0288d1', 'secondaryColor': '#fff3e0', 'tertiaryColor': '#e8f5e9'}}}%%
mindmap
  root((Prácticas XP<br/>Módulo Ventas))
    Planificación
      Planning Game con cliente onsite
      Historias pequeñas y estimables
      Iteraciones de 1 semana
      Velocidad medible
    Desarrollo
      TDD — Test Driven Development
      Pair Programming Driver-Navigator
      Diseño Simple — YAGNI
      Refactorización continua
    Calidad
      Integración Continua
      Pruebas de aceptación automatizadas
      Estándares de codificación
      Métricas de cobertura
    Comunicación
      Cliente in situ
      Metáfora del sistema
      Historias de usuario
      Revisión de código colectiva
```

### Pair Programming — Modalidad

**Driver-Navigator** en lógica de negocio crítica (pagos, anticipos, reportes).  
**Ping-Pong TDD** en servicios de cálculo:

```
Dev A: Escribe test rojo
Dev B: Hace pasar + refactor + escribe siguiente test rojo
Dev A: Hace pasar + refactor + escribe siguiente test rojo
... (rotar cada 20-30 min)
```

---

## 5. Arquitectura del Dominio — ERD

```mermaid
%%{init: {'theme': 'base'}}%%
erDiagram
    PAIS ||--o{ CLIENTE : "pertenece"
    PAIS ||--o{ MERCADO_DESTINO : "agrupa"
    MERCADO_DESTINO ||--o{ CLIENTE : "clasifica"
    TERMINO_CREDITO ||--o{ CLIENTE : "predeterminado"
    TERMINO_CREDITO ||--o{ VENTAS : "define"
    CLIENTE ||--o{ VENTAS : "realiza"
    CLIENTE ||--o{ ANTICIPO : "genera"
    CLIENTE ||--o{ SALDO_CLIENTE : "posee"
    CLIENTE ||--o{ ANTIGUEDAD_SALDO : "analiza"
    CLIENTE ||--o{ ESTADO_CUENTA_CLIENTE : "reporta"
    AGENTE ||--o{ VENTAS : "gestiona"
    PRODUCTO ||--o{ VENTAS : "comercializa"
    SUCURSAL ||--o{ VENTAS : "opera"
    CUENTA ||--o{ VENTAS : "deposita"
    CUENTA ||--o{ PAGO_VENTA : "recibe"
    CUENTA ||--o{ ANTICIPO : "recibe"
    VENTAS ||--o{ PAGO_VENTA : "recibe"
    VENTAS ||--o| ANTICIPO : "aplica"
    VENTAS ||--|| SALDO_CLIENTE : "origina"
    CONFIGURACION_CXC ||--o{ ESTADO_CUENTA_CLIENTE : "parametriza"

    CLIENTE {
        int id PK
        string nombre
        string telefono
        string correo
        string direccion
        string tipo_cliente
        decimal limite_credito
        string calificacion_credito
        boolean activo
    }

    MERCADO_DESTINO {
        int id PK
        string nombre
        string moneda_preferida
        decimal factor_riesgo
        boolean requiere_documentacion_especial
    }

    TERMINO_CREDITO {
        int id PK
        string nombre
        int dias_credito
        decimal tasa_interes_mensual
        boolean activo
    }

    AGENTE {
        int id PK
        string nombre
        string telefono
        string correo
        date fecha_registro
    }

    ANTICIPO {
        int id PK
        decimal monto
        decimal monto_aplicado
        date fecha
        string estado_anticipo
        string folio_factura_anticipo
    }

    VENTAS {
        int id PK
        date fecha_salida_manifiesto
        date fecha_deposito
        string pedimento
        string carga
        string po
        decimal cantidad
        decimal monto
        string descripcion
        string tipo_venta
        string modalidad_pago
        string estado_cobranza
        decimal monto_pagado
        date fecha_vencimiento
        string incoterm
        string moneda_venta
        decimal tipo_cambio
        string tipo_registro
        string folio_factura
        decimal ajuste
    }

    PAGO_VENTA {
        int id PK
        date fecha_pago
        decimal monto_pago
        string metodo_pago
        string referencia
        string notas
    }

    SALDO_CLIENTE {
        int id PK
        decimal monto_original
        decimal saldo_pendiente
        date fecha_vencimiento
        date fecha_ultimo_pago
        string estado
        string moneda
    }

    ANTIGUEDAD_SALDO {
        int id PK
        date fecha_calculo
        decimal corriente
        decimal vencido_1
        decimal vencido_2
        decimal vencido_3
        decimal total_saldo
        int numero_facturas
        float promedio_dias_pago
    }

    ESTADO_CUENTA_CLIENTE {
        int id PK
        date periodo_inicio
        date periodo_fin
        decimal total_ventas
        decimal total_abonos
        decimal saldo_final
        int numero_facturas
        string formato_generado
    }

    CONFIGURACION_CXC {
        int id PK
        int dias_corriente
        int dias_vencido_1
        int dias_vencido_2
        boolean calculo_automatico_aging
        time hora_calculo_aging
        string frecuencia_calculo
        boolean enviar_alertas_vencimiento
        int dias_previos_alerta
        string email_responsable_cobranza
        boolean permitir_sobregiro_credito
        float porcentaje_sobregiro_permitido
        decimal tipo_cambio_usd
    }
```

---

## 6. Iteraciones

### Iteración 0 — Foundation (Spike)

**Duración**: 1 semana  
**Puntos**: 0 (inversión técnica)  
**Prácticas XP**: Spike, TDD setup, CI pipeline

#### Objetivo
Sentar bases técnicas antes de escribir lógica de negocio.

#### Tareas
- [ ] Configurar app `ventas` en `INSTALLED_APPS`
- [ ] Spike: validar `django-money` + `MoneyField` (monetario crítico)
- [ ] Configurar `pytest` con `DJANGO_SETTINGS_MODULE` y fixtures base
- [ ] Crear factory de datos: `Pais`, `Estado`, `Sucursal`, `Producto`, `Banco`, `Cuenta`
- [ ] CI pipeline: ejecutar `pytest` + `flake8` en cada push
- [ ] Definir contrato de modelos con cliente (dueño del producto)

#### Definition of Done
- [ ] `pytest` ejecuta sin errores de configuración
- [ ] Fixture base crea objetos reutilizables en `< 100 ms`
- [ ] Spike documenta decisión: "Usamos `MoneyField` en vez de `Decimal` para evitar inconsistencias de moneda"

```mermaid
%%{init: {'theme': 'base'}}%%
flowchart LR
    A["Iteración 0<br/>Foundation"] --> B["Spike: MoneyField<br/>+ django-money"]
    A --> C["Spike: pytest<br/>+ fixtures base"]
    A --> D["Contrato de<br/>modelos con cliente"]
    A --> E["CI pipeline<br/>pytest + lint"]
```

---

### Iteración 1 — Catálogo de Clientes (US-01, US-10)

**Duración**: 1 semana  
**Puntos**: 8  
**Prácticas XP**: TDD, Pair Programming, Diseño Simple

#### Historias
- **US-01**: CRUD de `Cliente` + límite de crédito + calificación
- **US-10**: Clasificación por `MercadoDestino` + `País`

#### TDD — Ping-Pong Pairing

```mermaid
%%{init: {'theme': 'base'}}%%
sequenceDiagram
    actor DevA
    actor DevB
    participant Test
    participant Model

    DevA->>Test: Escribe test rojo:<br/>Cliente se crea con nombre, país, límite crédito
    Test->>DevA: ❌ FAIL — modelo no existe

    DevA->>DevB: Cambio de rol: DevA Navigator, DevB Driver
    DevB->>Model: Implementa modelo Cliente + migración
    Model->>Test: ✅ PASS

    DevB->>DevA: Cambio de rol: DevB Navigator, DevA Driver
    DevA->>Test: Escribe test rojo:<br/>cliente_contado no tiene crédito
    Test->>DevA: ❌ FAIL
    DevA->>Model: Implementa credito_disponible()
    Model->>Test: ✅ PASS

    DevA->>DevA: Refactor: extraer validación a método privado
    DevA->>Test: ✅ PASS (regresión)
```

#### Tests clave
```python
class ClienteTest(TestCase):
    def test_cliente_se_crea_con_limite_credito(self):
        cliente = Cliente.objects.create(
            nombre="Cliente A", pais=self.pais_mx,
            limite_credito=Money('50000', 'MXN')
        )
        self.assertEqual(str(cliente), "Cliente A - México")
        self.assertEqual(cliente.credito_disponible(), 50000.0)

    def test_cliente_contado_no_tiene_credito(self):
        cliente = Cliente.objects.create(
            nombre="Cliente B", pais=self.pais_mx, tipo_cliente='Contado'
        )
        self.assertEqual(cliente.credito_disponible(), 0)
```

#### DoD
- [ ] Admin funcional con filtros por tipo y calificación
- [ ] Cobertura ≥ 85%
- [ ] Demo al cliente: crear cliente, asignar mercado, ver límite

---

### Iteración 2 — Ventas de Contado (US-02)

**Duración**: 1 semana  
**Puntos**: 5  
**Prácticas XP**: TDD, Refactorización continua

#### Historia
- **US-02**: Venta con producto, cantidad, monto. Al guardar → estado = `Pagado`.

#### TDD — Ciclo Rojo-Verde-Refactor

```mermaid
%%{init: {'theme': 'base'}}%%
flowchart TB
    subgraph "🔴 Rojo"
        R1["test: Venta contado → estado Pagado automático"]
        R2["test: Venta contado → monto_pagado = monto"]
        R3["test: Venta contado → no requiere término crédito"]
    end

    subgraph "🟢 Verde"
        V1["Modelo Ventas + override save()"]
    end

    subgraph "🔵 Refactor"
        F1["Extraer lógica a VentaEstadoService"]
        F2["Agregar índice: modalidad_pago + estado_cobranza"]
    end

    R1 --> V1
    R2 --> V1
    R3 --> V1
    V1 --> F1
    F1 --> F2
```

#### Refactorización — Extracción de servicio
```python
class VentaEstadoService:
    @staticmethod
    def establecer_estado_inicial(venta):
        if venta.modalidad_pago == Ventas.ModalidadPago.CONTADO:
            venta.estado_cobranza = Ventas.EstadoCobranza.PAGADO
            venta.monto_pagado = venta.monto
```

---

### Iteración 3 — Ventas a Crédito (US-03)

**Duración**: 1 semana  
**Puntos**: 8  
**Prácticas XP**: TDD, Cliente onsite, Diseño Simple

#### Historia
- **US-03**: Venta a crédito + `TerminoCredito` + `fecha_vencimiento` auto-calculada

#### TDD — Cliente onsite

```mermaid
%%{init: {'theme': 'base'}}%%
sequenceDiagram
    actor ClienteOnSite
    actor DevPair
    participant Test
    participant Model

    ClienteOnSite->>DevPair: "Si vendo a 30 días, el sistema debe calcular vencimiento"
    DevPair->>Test: Escribe test: fecha_vencimiento = fecha_deposito + 30 días
    Test->>DevPair: ❌ FAIL — TerminoCredito no existe
    DevPair->>Model: Crea TerminoCredito + lógica en save()
    Model->>Test: ✅ PASS

    ClienteOnSite->>DevPair: "¿Y si cambio el término después de guardar?"
    DevPair->>Test: Escribe test: cambio de término actualiza vencimiento
    Test->>DevPair: ⚠️ Discusión: ¿recalcular o bloquear?
    DevPair->>ClienteOnSite: "Solo en creación, para evitar inconsistencias en pagos"
    ClienteOnSite->>DevPair: "OK, documentar esa regla de negocio"
    DevPair->>Model: Agrega comentario + validación en clean()
    Model->>Test: ✅ PASS
```

#### DoD
- [ ] Validación en `clean()`: crédito requiere término
- [ ] `fecha_vencimiento` se calcula automáticamente en `save()`
- [ ] Cobertura ≥ 84%

---

### Iteración 4 — Pagos con Integridad Transaccional (US-04, US-15)

**Duración**: 1 semana  
**Puntos**: 11  
**Prácticas XP**: TDD, Pair Programming (siempre en código crítico), Diseño Simple

#### Historias
- **US-04**: `PagoVenta` con estándares bancarios RF01-RF06
- **US-15**: Auditoría automática de cambio de estado

#### TDD — Estándares Bancarios

```mermaid
%%{init: {'theme': 'base'}}%%
flowchart LR
    subgraph "RF01: 1 pago = 1 venta"
        T1["test: ForeignKey venta"]
    end
    subgraph "RF02: No pagar completadas"
        T2["test: Pago a venta Pagado → ValidationError"]
    end
    subgraph "RF03: Sin sobrepagos"
        T3["test: Pago > saldo → ValidationError"]
    end
    subgraph "RF04: Transacción atómica"
        T4["test: Race condition con concurrent payments"]
    end
    subgraph "RF05: Auditoría"
        T5["test: LogActividad creado tras pago"]
    end
    subgraph "RF06: Validación multi-nivel"
        T6["test: Form + Model + BD validan monto > 0"]
    end

    T1 --> T2 --> T3 --> T4 --> T5 --> T6
```

#### Test crítico — RF04 Race Condition
```python
def test_pago_concurrente_no_sobrepaga(self):
    """RF04: select_for_update previene race condition."""
    venta = self._venta_credito(monto='10000.00')

    from concurrent.futures import ThreadPoolExecutor
    def intentar_pago(monto):
        try:
            with transaction.atomic():
                PagoVenta.objects.create(
                    venta=venta, monto_pago=Money(monto, 'MXN'),
                    cuenta_destino=self.cuenta,
                    metodo_pago='Transferencia', fecha_pago=date.today()
                )
            return 'ok'
        except ValidationError:
            return 'rejected'

    with ThreadPoolExecutor(max_workers=2) as ex:
        r1 = ex.submit(intentar_pago, '6000.00')
        r2 = ex.submit(intentar_pago, '6000.00')
        resultados = [r1.result(), r2.result()]

    self.assertIn('rejected', resultados)
    venta.refresh_from_db()
    self.assertLessEqual(venta.monto_pagado.amount, 10000)
```

#### Refactorización — Fuente de verdad única
```python
@staticmethod
def derive_estado_desde_totales(total_ventas, total_pagado, fecha_vencimiento):
    """Fuente de verdad única para estado de cobranza."""
    saldo = total_ventas - total_pagado
    if saldo <= 0:
        return 'Pagado'
    vencida = fecha_vencimiento and fecha_vencimiento < timezone.now().date()
    if total_pagado > 0:
        return 'Vencido' if vencida else 'Parcial'
    return 'Vencido' if vencida else 'Pendiente'
```

---

### Iteración 5 — Anticipos y Aplicación (US-05)

**Duración**: 1 semana  
**Puntos**: 8  
**Prácticas XP**: TDD, Pair Programming, State Machine

#### Historia
- **US-05**: CRUD `Anticipo` + aplicación a venta (RF07-RF10)

#### Diagrama de estados — Anticipo

```mermaid
%%{init: {'theme': 'base'}}%%
stateDiagram-v2
    [*] --> Pendiente: Cliente entrega anticipo
    Pendiente --> Aplicado: Asigna a venta válida
    Pendiente --> Cancelado: Anulación explícita
    Aplicado --> [*]: Venta completada
    Cancelado --> [*]: Reembolso / anulación

    note right of Pendiente
        saldo_disponible() = monto - monto_aplicado
    end note
    note right of Aplicado
        Regla RF07: no aplicar a venta ya pagada
        Regla RF09: consistencia entre estado y saldo
    end note
```

#### Tests clave — RF07-RF10
```python
def test_anticipo_aplicado_mismo_cliente(self):
    cliente_a = self._cliente('Cliente A')
    cliente_b = self._cliente('Cliente B')
    anticipo = self._anticipo(cliente_a, '5000.00')
    venta = self._venta_credito(cliente_b, monto='10000.00')
    with self.assertRaises(ValidationError):
        anticipo.aplicar_a_venta(venta)

def test_saldo_disponible_legacy(self):
    """Legacy: anticipo Aplicado sin monto_aplicado → saldo 0."""
    anticipo = self._anticipo(self.cliente, '10000.00', estado='Aplicado')
    anticipo.monto_aplicado = Money('0.00', 'MXN')
    anticipo.save()
    self.assertEqual(anticipo.saldo_disponible(), 0.0)
```

---

### Iteración 6 — Reporte de Cobranza Global (US-06)

**Duración**: 1 semana  
**Puntos**: 13  
**Prácticas XP**: TDD, Diseño Emergente, Refactorización

#### Historia
- **US-06**: Dashboard ejecutivo con saldos, aging, anticipos, exportación

#### TDD — Servicio de reporte (Diseño Emergente)

```mermaid
%%{init: {'theme': 'base'}}%%
flowchart TB
    subgraph "Tests unitarios"
        S1["test: reporte con ventas + pagos → saldo correcto"]
        S2["test: anticipos pendientes → saldo a favor"]
        S3["test: excedente anticipo aplicado → saldo a favor"]
        S4["test: filtro por fechas excluye fuera de rango"]
        S5["test: tipo de cambio USD→MXN correcto"]
        S6["test: aging buckets correctos"]
    end

    subgraph "Refactor — Emergencia de servicios"
        R1["Extraer: reporte_cobranza_service.py"]
        R2["Extraer: CuentasPorCobrarMetrics"]
        R3["Extraer: CuentasPorCobrarCache"]
    end

    S1 --> R1
    S2 --> R1
    S3 --> R1
    S4 --> R1
    S5 --> R1
    S6 --> R2
    R1 --> R3
```

> **XP — Diseño Simple**: "La mejor arquitectura es la que no existe todavía." Solo extraemos servicios cuando 3 tests duplican la misma lógica.

#### Test — Saldo a favor con acumulación
```python
def test_anticipo_pendiente_y_excedente_se_acumulan(self):
    cliente = self._cliente('Cliente Combo')
    self._anticipo(cliente, '3000.00')  # pendiente
    anticipo_app = self._anticipo(cliente, '10000.00')
    self._venta_credito(cliente, '8500.00', anticipo=anticipo_app)
    self._aplicar_anticipo(anticipo_app)  # excedente $1,500

    datos = generar_reporte_cobranza()
    self.assertAlmostEqual(datos['anticipos_por_cliente'][cliente.id], 4500.0)
```

---

### Iteración 7 — Importación CFDI (US-07)

**Duración**: 1 semana  
**Puntos**: 8  
**Prácticas XP**: TDD, Spike (parser), Diseño Simple

#### Historia
- **US-07**: Importar CFDI XML en 2 pasos (upload → confirmar → guardar)

#### Flujo — 2 pasos

```mermaid
%%{init: {'theme': 'base'}}%%
flowchart LR
    A["📁 Paso 1:<br/>Subir XML"] -->|POST _step=upload| B["🔍 parse_cfdi()"]
    B --> C{"¿Parse exitoso?"}
    C -->|No| D["❌ Error + reintentar"]
    D --> A
    C -->|Sí| E["🤖 Matching:<br/>• Cliente por nombre<br/>• Producto por variedad"]
    E --> F["📋 Paso 2:<br/>Confirmar datos"]
    F -->|POST _step=confirm| G["✅ Validar + Guardar"]
    G --> H["🎉 Redirect a change view"]
```

#### Tests
```python
def test_parse_cfdi_extrae_monto_y_moneda(self):
    xml = b'<cfdi:Comprobante Total="45000.00" Moneda="USD" ...>'
    parsed = parse_cfdi(xml)
    self.assertEqual(parsed['monto'], Decimal('45000.00'))
    self.assertEqual(parsed['moneda_venta'], 'USD')

def test_match_cliente_por_nombre_exacto(self):
    Cliente.objects.create(nombre="EXPORTADORA DEL PACIFICO SA")
    parsed = {'_receptor_nombre': 'EXPORTADORA DEL PACIFICO SA'}
    self.assertIsNotNone(match_cliente(parsed))
```

---

### Iteración 8 — Estado de Cuenta y Configuración (US-08, US-12)

**Duración**: 1 semana  
**Puntos**: 11  
**Prácticas XP**: TDD, Configuración parametrizable

#### Historias
- **US-08**: `EstadoCuentaCliente` con movimientos del período
- **US-12**: `ConfiguracionCuentasPorCobrar` singleton

#### Cálculo del estado de cuenta

```mermaid
%%{init: {'theme': 'base'}}%%
flowchart TB
    A["Período: inicio → fin"] --> B["Sumar ventas a crédito"]
    B --> C["Sumar pagos recibidos"]
    C --> D["Saldo final = Ventas - Pagos"]
    D --> E["N° facturas incluidas"]
    E --> F["Generar archivo:<br/>WEB / PDF / EXCEL"]
```

#### Tests
```python
def test_estado_cuenta_calcula_saldo_correcto(self):
    cliente = self._cliente('Cliente EC')
    self._venta_credito(cliente, monto='50000.00', fecha=date(2024, 1, 15))
    self._pago_venta(cliente, monto='20000.00', fecha=date(2024, 2, 1))

    ec = EstadoCuentaCliente.objects.create(
        cliente=cliente,
        periodo_inicio=date(2024, 1, 1), periodo_fin=date(2024, 3, 31),
        total_ventas=Money('50000', 'MXN'), total_abonos=Money('20000', 'MXN'),
        saldo_final=Money('30000', 'MXN'), numero_facturas=1, generado_por='test'
    )
    self.assertEqual(ec.porcentaje_recuperacion, 40.0)
```

---

### Iteración 9 — Aging y Caché (US-09, US-14)

**Duración**: 1 semana  
**Puntos**: 13  
**Prácticas XP**: TDD, Performance, Refactorización

#### Historias
- **US-09**: `AntigüedadSaldo` (snapshot diario/semanal)
- **US-14**: Cache automático e invalidación

#### Aging — Buckets

```mermaid
%%{init: {'theme': 'base'}}%%
flowchart LR
    V["Venta vencida"] --> dias["dias_vencido()"]
    dias --> bucket{"¿Días?"}
    bucket -->|≤30| A["Corriente"]
    bucket -->|31-60| B["Vencido 1"]
    bucket -->|61-90| C["Vencido 2"]
    bucket -->|>90| D["Vencido 3"]
```

#### Test — Cache invalidation
```python
@override_settings(CACHES={
    'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}
})
def test_cache_dashboard_se_invalida_al_registrar_pago(self):
    venta = self._venta_credito(monto='10000.00')
    cache.set('cxc_dashboard_ventas_principal', {'total': 10000}, 300)

    PagoVenta.objects.create(
        venta=venta, monto_pago=Money('5000', 'MXN'),
        cuenta_destino=self.cuenta, metodo_pago='Transferencia',
        fecha_pago=date.today()
    )
    self.assertIsNone(cache.get('cxc_dashboard_ventas_principal'))
```

---

### Iteración 10 — Exportación y Polish (US-13)

**Duración**: 1 semana  
**Puntos**: 5  
**Prácticas XP**: Refactorización final, Small Release

#### Historia
- **US-13**: Exportar a Excel con formato profesional (2 hojas: detalle + resumen)

#### Refactorización — Code smells detectados

```mermaid
%%{init: {'theme': 'base'}}%%
flowchart TB
    subgraph "Code smells"
        CS1["Ventas.save() > 30 líneas"]
        CS2["Duplicación en cálculo de intereses"]
        CS3["Magic numbers en aging"]
        CS4["Tests lentos → N+1 queries"]
    end

    subgraph "Refactor aplicado"
        R1["Extraer VentaEstadoService"]
        R2["Extraer InteresMoratorioService"]
        R3["Usar ConfiguracionCuentasPorCobrar.dias_*"]
        R4["Agregar select_related + prefetch_related"]
    end

    CS1 --> R1
    CS2 --> R2
    CS3 --> R3
    CS4 --> R4
```

---

## 7. Roadmap Visual (Gantt)

```mermaid
%%{init: {'theme': 'base'}}%%
gantt
    title Roadmap XP — Módulo de Ventas (10 iteraciones)
    dateFormat  YYYY-MM-DD
    axisFormat  %d/%m

    section Foundation
    Iteración 0 :done, i0, 2024-01-01, 7d

    section Core
    Iteración 1 :active, i1, after i0, 7d
    Iteración 2 :i2, after i1, 7d
    Iteración 3 :i3, after i2, 7d

    section Pagos
    Iteración 4 :i4, after i3, 7d
    Iteración 5 :i5, after i4, 7d

    section Reportes
    Iteración 6 :i6, after i5, 7d
    Iteración 7 :i7, after i6, 7d

    section Avanzado
    Iteración 8 :i8, after i7, 7d
    Iteración 9 :i9, after i8, 7d
    Iteración 10 :i10, after i9, 7d

    section Release
    Release v1.0 :milestone, after i10, 0d
```

---

## 8. Integración Continua — Pipeline

```mermaid
%%{init: {'theme': 'base'}}%%
flowchart LR
    A["Commit / Push"] --> B["pytest app/tests/test_security.py"]
    B --> C["pytest ventas/tests.py"]
    C --> D["pytest ventas/tests_integration.py"]
    D --> E{"¿Pass?"}
    E -->|Sí| F["pytest app/tests/test_cache_service.py"]
    E -->|No| G["🔴 Revert / Fix"]
    F --> H{"¿Pass?"}
    H -->|Sí| I["🟢 Merge OK"]
    H -->|No| G
```

---

## 9. Métricas por Iteración

| Iteración | Velocidad (pts) | Tests nuevos | Cobertura | Deuda técnica abordada |
|-----------|-----------------|--------------|-----------|------------------------|
| 0 | 0 (spike) | 3 | — | Base técnica |
| 1 | 8 | 12 | 85% | — |
| 2 | 5 | 8 | 82% | — |
| 3 | 8 | 10 | 84% | Refactor `save()` |
| 4 | 11 | 18 | 88% | Extraer `derive_estado()` |
| 5 | 8 | 14 | 87% | — |
| 6 | 13 | 22 | 90% | Servicios de reporte |
| 7 | 8 | 10 | 85% | — |
| 8 | 11 | 12 | 86% | — |
| 9 | 13 | 16 | 89% | Cache abstraction |
| 10 | 5 | 6 | 91% | Polish |

**Velocidad promedio**: 9.9 pts/iteración  
**Tests totales**: ~131  
**Cobertura final objetivo**: ≥ 90%

---

## 10. Roles XP

| Rol | Responsabilidad | Quién |
|-----|-----------------|-------|
| **Cliente (Product Owner)** | Define historias, prioriza, acepta demos | Gerente comercial |
| **Programadores** | TDD, implementan, refactorizan | Dev team |
| **Testers** | Tests de aceptación, exploratorio | Dev team (TDD) |
| **Tracker** | Mide velocidad, identifica bloqueos | Dev lead |
| **Coach XP** | Facilita prácticas, enseña TDD/pairing | Dev lead senior |

---

## 11. Checklist de Calidad XP

### Inicio de iteración
- [ ] Planning Game con cliente (30 min)
- [ ] Historias en tarjetas visibles
- [ ] Tests de aceptación acordados

### Durante la iteración
- [ ] Pair programming en lógica crítica (pagos, anticipos)
- [ ] TDD: rojo → verde → refactor (mínimo 1 ciclo/hora)
- [ ] Push frecuente (cada par de horas)
- [ ] CI verde antes de cada merge
- [ ] Refactorización: mínimo 1 al día

### Fin de iteración
- [ ] Demo funcional al cliente (15 min)
- [ ] Retrospectiva: ¿Qué funcionó? ¿Qué mejorar?
- [ ] Actualizar métricas de velocidad
- [ ] Revisar cobertura de tests (`pytest --cov`)

---

*Documento generado aplicando skills: `mermaid-diagrams` + `xp-practices`.*
