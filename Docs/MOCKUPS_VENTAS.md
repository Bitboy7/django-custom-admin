# Mockups del Módulo de Ventas

> Documento visual con wireframes, diagramas de flujo y mockups de pantallas del módulo **ventas**.  
> Generado con base en los modelos, admin, vistas, forms y services actuales del repositorio.

---

## 1. Modelo de Datos (Entidades principales)

```mermaid
erDiagram
    CLIENTE ||--o{ VENTAS : realiza
    CLIENTE ||--o{ ANTICIPO : genera
    CLIENTE ||--o{ SALDO_CLIENTE : posee
    CLIENTE ||--o{ ANTIGUEDAD_SALDO : analiza
    CLIENTE ||--o{ ESTADO_CUENTA_CLIENTE : reporta
    VENTAS ||--|| SALDO_CLIENTE : origina
    VENTAS ||--o{ PAGO_VENTA : recibe
    VENTAS ||--o| ANTICIPO : aplica
    AGENTE ||--o{ VENTAS : gestiona
    TERMINO_CREDITO ||--o{ VENTAS : define
    MERCADO_DESTINO ||--o{ CLIENTE : clasifica
    MERCADO_DESTINO ||--o{ VENTAS : destina
    PRODUCTO ||--o{ VENTAS : comercializa
    SUCURSAL ||--o{ VENTAS : opera
    CUENTA ||--o{ VENTAS : deposita
    CUENTA ||--o{ PAGO_VENTA : recibe
    CUENTA ||--o{ ANTICIPO : recibe
    CONFIGURACION_CXC ||--o{ ESTADO_CUENTA_CLIENTE : parametriza

    CLIENTE {
        string nombre
        string telefono
        string correo
        string direccion
        string tipo_cliente "Contado|Credito|Mixto"
        decimal limite_credito
        string calificacion_credito "A+|A|B|C"
        boolean activo
    }

    AGENTE {
        string nombre
        string telefono
        string correo
        date fecha_registro
    }

    TERMINO_CREDITO {
        string nombre
        int dias_credito
        decimal tasa_interes_mensual
        boolean activo
    }

    MERCADO_DESTINO {
        string nombre
        string moneda_preferida
        decimal factor_riesgo
        boolean requiere_documentacion_especial
    }

    ANTICIPO {
        money monto
        money monto_aplicado
        date fecha
        string estado_anticipo "Pendiente|Aplicado|Cancelado"
        string folio_factura_anticipo
    }

    VENTAS {
        date fecha_salida_manifiesto
        date fecha_deposito
        string pedimento
        string carga
        string PO
        decimal cantidad
        money monto
        string descripcion
        string tipo_venta "Nacional|Exportacion"
        string modalidad_pago "Contado|Credito"
        string estado_cobranza "Pagado|Pendiente|Parcial|Vencido|Incobrable"
        money monto_pagado
        date fecha_vencimiento
        string incoterm
        string moneda_venta
        decimal tipo_cambio
        string tipo_registro "VENTA|MAQUILA"
        string folio_factura
        string cfdi_cancelado
        string nota_credito
        string nota_cargo
        string numero_carga_comprador
        decimal ajuste
        date fecha_emision_cfdi
    }

    PAGO_VENTA {
        date fecha_pago
        money monto_pago
        string metodo_pago "Efectivo|Transferencia|Cheque|Tarjeta"
        string referencia
        string notas
        file comprobante_pago
    }

    SALDO_CLIENTE {
        money monto_original
        money saldo_pendiente
        date fecha_vencimiento
        date fecha_ultimo_pago
        string estado "PENDIENTE|PARCIAL|PAGADO|VENCIDO|INCOBRABLE"
        string moneda
        string notas
    }

    ANTIGUEDAD_SALDO {
        date fecha_calculo
        money corriente
        money vencido_1 "31-60d"
        money vencido_2 "61-90d"
        money vencido_3 "+90d"
        money total_saldo
        int numero_facturas
        float promedio_dias_pago
        string calculado_por
    }

    ESTADO_CUENTA_CLIENTE {
        date periodo_inicio
        date periodo_fin
        money total_ventas
        money total_abonos
        money saldo_final
        int numero_facturas
        string formato_generado "WEB|PDF|EXCEL"
        file archivo_generado
        string generado_por
    }

    CONFIGURACION_CXC {
        int dias_corriente default_30
        int dias_vencido_1 default_60
        int dias_vencido_2 default_90
        boolean calculo_automatico_aging
        time hora_calculo_aging
        string frecuencia_calculo "DIARIO|SEMANAL"
        boolean enviar_alertas_vencimiento
        int dias_previos_alerta
        string email_responsable_cobranza
        boolean permitir_sobregiro_credito
        float porcentaje_sobregiro_permitido
        decimal tipo_cambio_usd
    }
```

---

## 2. Flujo de Trabajo: Venta Contado vs Crédito

```mermaid
flowchart TD
    A["📝 Registrar Venta"] --> B{"¿Modalidad de pago?"}
    
    B -->|Contado| C["✅ Estado = Pagado<br/>monto_pagado = monto"]
    C --> D["Guardar Venta"]
    D --> E["🧾 Generar CFDI"]
    E --> F["🏁 Fin - Venta completada"]
    
    B -->|Crédito| G{"¿Cliente tiene<br/>límite suficiente?"}
    G -->|Sí| H["⏳ Estado = Pendiente<br/>monto_pagado = 0"]
    G -->|No / Autorización| I["⚠️ Advertencia de<br/>límite excedido"]
    I --> H
    
    H --> J["📅 Calcular fecha_vencimiento<br/>(fecha_deposito + dias_credito)"]
    J --> K["Guardar Venta + Crear SaldoCliente"]
    K --> L["🔄 Ciclo de Cobranza"]
    
    L --> M["📥 Registrar Pago"]
    M --> N{"¿Saldo pendiente = 0?"}
    N -->|Sí| O["✅ Estado = Pagado"]
    N -->|No| P{"¿Vencido?"}
    P -->|Sí| Q["🔴 Estado = Vencido"]
    P -->|No| R["🟡 Estado = Parcial"]
    
    O --> S["Actualizar SaldoCliente"]
    Q --> S
    R --> S
    S --> T["🔄 Seguimiento continuo"]
    T --> L
    
    subgraph "📊 Reportes y Alertas"
        U["Reporte de Cobranza"]
        V["Estado de Cuenta"]
        W["Antigüedad de Saldos"]
    end
    
    T --> U
    T --> V
    T --> W
```

---

## 3. Flujo de Importación CFDI (2 pasos)

```mermaid
flowchart LR
    A["📁 Paso 1: Subir XML"] -->|POST _step=upload| B["🔍 Parsear CFDI"]
    B --> C{"¿Parse exitoso?"}
    C -->|No| D["❌ Mostrar error"]
    D --> A
    C -->|Sí| E["🤖 Match automático:<br/>• Cliente por nombre<br/>• Producto por variedad<br/>• Extraer montos, moneda, etc."]
    
    E --> F["📋 Paso 2: Confirmar datos<br/>(formulario pre-llenado)"]
    F -->|POST _step=confirm| G["✅ Validar formulario"]
    G --> H{"¿Válido?"}
    H -->|No| I["❌ Mostrar errores<br/>mantener datos parseados"]
    I --> F
    H -->|Sí| J["💾 Crear Venta"]
    J --> K["🎉 Redirect a change view<br/>con mensaje de éxito"]
```

---

## 4. Flujo de Anticipos

```mermaid
flowchart TD
    A["💰 Registrar Anticipo"] --> B["Estado = Pendiente"]
    B --> C{"¿Aplicar a venta?"}
    C -->|No| D["📋 Listo - Esperando aplicación"]
    
    C -->|Sí| E{"Validaciones"}
    E --> F["¿Anticipo disponible?"]
    F -->|No| G["❌ Rechazar - Ya aplicado"]
    E --> H["¿Mismo cliente?"]
    H -->|No| I["❌ Rechazar - Cliente no coincide"]
    E --> J["¿Venta no pagada?"]
    J -->|No| K["❌ Rechazar - RF07"]
    
    F -->|Sí| L["✅ Todas las validaciones pasan"]
    H -->|Sí| L
    J -->|Sí| L
    
    L --> M["🔄 Transacción atómica"]
    M --> N["Actualizar anticipo:<br/>• monto_aplicado += monto<br/>• Estado = Aplicado (si saldo=0)"]
    N --> O["Asignar anticipo a Venta"]
    O --> P["📝 Registrar en auditoría"]
    P --> Q["🏁 Aplicación completada"]
```

---

## 5. Flujo de Pagos (RF01-RF06)

```mermaid
sequenceDiagram
    actor Usuario
    participant Venta as Ventas
    participant Pago as PagoVenta
    participant DB as Database
    participant Audit as Auditoria
    
    Usuario->>Venta: Seleccionar venta a crédito
    Usuario->>Pago: Registrar nuevo pago
    
    Pago->>Pago: clean() validaciones
    Note over Pago: RF02: Venta no completada<br/>RF03: Sin sobrepagos<br/>RF06: Monto > 0, fecha no futura
    
    Pago->>DB: BEGIN TRANSACTION
    DB->>Venta: SELECT FOR UPDATE
    Note over DB, Venta: RF04: Bloqueo de concurrencia
    
    Pago->>DB: INSERT PagoVenta
    DB->>Venta: actualizar_estado_cobranza()
    
    alt Saldo = 0
        Venta->>DB: estado = Pagado
    else Pagos > 0 y Vencido
        Venta->>DB: estado = Vencido
    else Pagos > 0 y No vencido
        Venta->>DB: estado = Parcial
    else Sin pagos y Vencido
        Venta->>DB: estado = Vencido
    else Sin pagos y No vencido
        Venta->>DB: estado = Pendiente
    end
    
    Venta->>DB: _sync_saldo_cxc()
    DB->>Audit: LogActividad (RF05)
    Pago->>DB: COMMIT
    
    Pago->>Cache: Invalidar cache dashboard
    Pago-->>Usuario: ✅ Pago registrado
```

---

## 6. Mockup: Lista de Ventas (Admin Change List)

```mermaid
flowchart TB
    subgraph "Admin Ventas - Change List"
        direction TB
        
        subgraph "Header"
            H1["🔍 Buscador: carga, cliente, producto, PO, pedimento"]
            H2["📅 Date hierarchy: fecha_salida_manifiesto"]
        end
        
        subgraph "Filtros Lateral"
            F1["Vencimiento: Hoy / Semana / Mes / Vencido +30/60/90"]
            F2["Rango de Monto"]
            F3["Tipo registro: Venta | Maquila"]
            F4["Modalidad: Contado | Crédito"]
            F5["Estado cobranza"]
            F6["Tipo venta: Nacional | Exportación"]
            F7["Mercado destino"]
            F8["Término crédito"]
            F9["Calificación cliente"]
            F10["Tipo cliente"]
        end
        
        subgraph "Tabla Principal"
            T1["| Fecha Salida | Carga | Cliente & Riesgo | Monto | Modalidad | Estado | Vencimiento | Mercado | Saldo |"]
            T2["| 2024-01-15 | C-001 | 🟢 Cliente A (A+) | $50,000 | Crédito | 🔴 Vencido | +45 días | USA | $50,000 |"]
            T3["| 2024-01-20 | C-002 | 🔴 Cliente B (C) | $12,000 | Contado | 🟢 Pagado | - | Nacional | ✓ |"]
            T4["| 2024-02-01 | C-003 | 🟡 Cliente C (B) | $30,000 | Crédito | 🟡 Parcial | 15 días | Canadá | $15,000 |"]
        end
        
        subgraph "Acciones Masivas"
            A1["📊 Generar reporte por cliente"]
            A2["💰 Marcar como pagado"]
            A3["📄 Generar estado de cuenta"]
            A4["📧 Enviar notificación vencimiento"]
            A5["📤 Exportar cuentas vencidas"]
            A6["📥 Exportar a Excel"]
        end
        
        subgraph "KPIs Cards (Top)"
            K1["💵 Total Ventas: $X"]
            K2["💰 Total Pagado: $X"]
            K3["⚠️ Saldo Pendiente: $X"]
            K4["🔴 Vencidas: $X"]
        end
    end
    
    H1 --> T1
    H2 --> T1
    F1 --> T1
    A1 --> T1
    K1 --> T1
```

---

## 7. Mockup: Formulario de Venta (Admin Change Form)

```mermaid
flowchart TB
    subgraph "Formulario Venta - 7 Fieldsets"
        direction TB
        
        subgraph "FS1: Información Básica"
            I1["📅 fecha_salida_manifiesto *"]
            I2["👤 agente_id * (Agente aduanal)"]
            I3["📅 fecha_deposito"]
            I4["📄 carga"]
            I5["📝 PO (Purchase Order)"]
            I6["🔢 pedimento"]
        end
        
        subgraph "FS2: Documentación Fiscal [collapse]"
            D1["📅 fecha_emision_cfdi"]
            D2["📄 folio_factura (ej: B 1996)"]
            D3["❌ cfdi_cancelado"]
            D4["📝 nota_credito"]
            D5["📝 nota_cargo"]
        end
        
        subgraph "FS3: Producto y Cliente"
            P1["📦 producto *"]
            P2["⚖️ cantidad * (ej: 1500.000 kg)"]
            P3["💵 monto *"]
            P4["👥 cliente *"]
            P5["🏢 sucursal_id *"]
            P6["📝 descripcion"]
        end
        
        subgraph "FS4: Modalidad de Pago [wide]"
            M1["💳 modalidad_pago * [Contado|Crédito]"]
            M2["📅 termino_credito (solo crédito)"]
            M3["📅 fecha_vencimiento (auto-calculada)"]
            M4["📊 estado_cobranza"]
            M5["💰 monto_pagado (readonly)"]
        end
        
        subgraph "FS5: Mercado y Exportación [collapse]"
            E1["🌍 tipo_venta [Nacional|Exportación]"]
            E2["🌐 mercado_destino"]
            E3["📋 incoterm (FOB, CIF, etc.)"]
            E4["💱 moneda_venta (default MXN)"]
            E5["📈 tipo_cambio (default 1.0000)"]
            E6["📦 numero_carga_comprador"]
        end
        
        subgraph "FS6: Contabilidad [collapse]"
            C1["🏦 cuenta (bancaria)"]
            C2["💰 anticipo (filtrado por cliente)"]
            C3["📊 ajuste (+cargo / -descuento)"]
        end
        
        subgraph "FS7: Tipo de Registro"
            R1["📋 tipo_registro [VENTA|MAQUILA]"]
        end
        
        subgraph "Inline: Pagos de Venta"
            IL1["| fecha_pago | monto_pago | cuenta_destino | metodo_pago | referencia |"]
            IL2["| 2024-03-01 | $25,000 | Cuenta BBVA | Transferencia | REF-001 |"]
        end
        
        subgraph "Botones de Acción"
            B1["💾 Guardar"]
            B2["💾 Guardar y añadir otro"]
            B3["📥 Guardar y continuar editando"]
            B4["🤖 Importar desde CFDI"]
            B5["📊 Análisis de ventas"]
            B6["📄 Reporte de cobranza"]
        end
    end
    
    FS1 --> FS2 --> FS3 --> FS4 --> FS5 --> FS6 --> FS7 --> Inline
```

---

## 8. Mockup: Importación CFDI (2 pasos)

### Paso 1 - Subir XML
```mermaid
flowchart TB
    subgraph "Importar desde CFDI - Paso 1"
        A1["📤 Arrastrar o seleccionar archivo XML"]
        A2["ℹ️ Máximo 1 MB. Formato CFDI válido."]
        A3["🔘 Subir y analizar"]
        
        A1 --> A3
        A2 --> A3
    end
```

### Paso 2 - Confirmar Datos
```mermaid
flowchart TB
    subgraph "Importar desde CFDI - Paso 2"
        direction TB
        
        B0["📋 Datos extraídos del XML"]
        
        subgraph "Sección CFDI (pre-llenada)"
            C1["📄 folio_factura: B 1996"]
            C2["📅 fecha_emision_cfdi: 2024-01-15"]
            C3["💵 monto: $45,000"]
            C4["💱 moneda_venta: USD"]
            C5["📈 tipo_cambio: 17.50"]
            C6["📋 incoterm: FOB"]
            C7["⚖️ cantidad: 1500"]
            C8["📝 descripcion: Mango Ataulfo..."]
        end
        
        subgraph "Sección Cliente/Producto (match automático)"
            CP1["👥 cliente: [Cliente A ▼] (sugerido por nombre CFDI)"]
            CP2["📦 producto: [Mango Ataulfo ▼] (sugerido por descripción)"]
        end
        
        subgraph "Sección Manual (requerida)"
            M1["📅 fecha_salida_manifiesto *"]
            M2["📅 fecha_deposito *"]
            M3["👤 agente_id *"]
            M4["🏢 sucursal_id *"]
            M5["🏦 cuenta"]
            M6["📦 carga"]
            M7["📝 PO"]
            M8["📋 tipo_venta [auto por país]"]
            M9["💳 modalidad_pago"]
            M10["📅 termino_credito (si crédito)"]
        end
        
        B0 --> C1
        C1 --> CP1
        CP1 --> M1
        
        subgraph "Acciones"
            ACT1["🔙 Volver"]
            ACT2["✅ Confirmar y guardar venta"]
        end
        
        M1 --> ACT2
    end
```

---

## 9. Mockup: Balances y Análisis de Ventas

```mermaid
flowchart TB
    subgraph "Análisis de Ventas - Dashboard"
        direction TB
        
        subgraph "Panel de Filtros"
            FF1["👥 Cliente ▼"]
            FF2["🏦 Cuenta ▼"]
            FF3["🏢 Sucursal ▼"]
            FF4["🌐 Mercado ▼"]
            FF5["💳 Modalidad ▼"]
            FF6["📊 Estado ▼"]
            FF7["📅 Año ▼"]
            FF8["📅 Meses [✓Ene ✓Feb ...]"]
            FF9["📊 Período [Diario|Semanal|Mensual]"]
            FF10["🔍 Aplicar filtros"]
            FF11["📤 Exportar XLSX"]
        end
        
        subgraph "KPIs Principales"
            KK1["💵 Total Ventas: $1,250,000"]
            KK2["💰 Total Pagado: $980,000"]
            KK3["⚠️ Saldo Pendiente: $270,000"]
            KK4["📊 N° Transacciones: 45"]
            KK5["📈 Venta Máxima: $85,000"]
            KK6["📉 Venta Mínima: $5,000"]
            KK7["📊 Promedio: $27,777"]
        end
        
        subgraph "Gráficos"
            G1["🥧 Modalidad de Pago<br/>Contado 60% | Crédito 40%"]
            G2["📊 Estado de Cobranza<br/>Pagado 70% | Pendiente 15% | Parcial 10% | Vencido 5%"]
            G3["📈 Top 10 Clientes<br/>[Barras horizontales]"]
        end
        
        subgraph "Tabla de Balances"
            TB1["| # | Cliente | Cuenta | Banco | Sucursal | Fecha | Total | Pagado | Saldo | Estado | Vencimiento | Acumulado |"]
            TB2["| 1 | Cliente A | 1234 | BBVA | Culiacán | Ene-24 | $50k | $0 | $50k | 🔴 Vencido | 15/02/24 | $50k |"]
            TB3["| 2 | Cliente B | 5678 | Santander | Mazatlán | Ene-24 | $30k | $30k | $0 | 🟢 Pagado | - | $80k |"]
            TB4["| 3 | Cliente C | 9012 | Banorte | Los Mochis | Feb-24 | $25k | $10k | $15k | 🟡 Parcial | 20/03/24 | $95k |"]
        end
        
        subgraph "Resumen por Modalidad"
            RM1["💵 Contado: $750,000 (30 ventas)"]
            RM2["💳 Crédito: $500,000 (15 ventas)"]
        end
        
        subgraph "Alertas"
            AL1["🔴 Vencidas: $45,000 (3 ventas)"]
        end
        
        FF1 --> KK1
        KK1 --> G1
        G1 --> TB1
        TB1 --> RM1
        RM1 --> AL1
    end
```

---

## 10. Mockup: Reporte de Cobranza Global

```mermaid
flowchart TB
    subgraph "Reporte Global de Cobranza"
        direction TB
        
        subgraph "Filtros de Período"
            RC1["📅 Fecha inicio: [2024-01-01]"]
            RC2["📅 Fecha fin: [2024-12-31]"]
            RC3["💱 Tipo de cambio USD→MXN: [17.50]"]
            RC4["🔍 Generar reporte"]
            RC5["📤 Exportar Excel"]
            RC6["📄 Exportar PDF"]
        end
        
        subgraph "Resumen Ejecutivo"
            RE1["💵 Total Facturado: $2,500,000"]
            RE2["💰 Total Cobrado: $1,800,000"]
            RE3["⚠️ Saldo por Cobrar: $700,000"]
            RE4["🔴 Saldo Vencido: $250,000"]
            RE5["📊 % Recuperación: 72%"]
        end
        
        subgraph "Distribución por Estado"
            DE1["🟢 Pagado: $1,800,000 (72%) - 45 facturas"]
            DE2["🟡 Parcial: $300,000 (12%) - 8 facturas"]
            DE3["🟠 Pendiente: $150,000 (6%) - 5 facturas"]
            DE4["🔴 Vencido: $250,000 (10%) - 7 facturas"]
        end
        
        subgraph "Antigüedad de Saldos (Aging)"
            AG1["✅ Corriente (0-30d): $400,000 | 10 facturas"]
            AG2["🟡 1-30 días: $150,000 | 4 facturas"]
            AG3["🟠 31-60 días: $80,000 | 3 facturas"]
            AG4["🔴 61-90 días: $45,000 | 2 facturas"]
            AG5["🚨 +90 días: $25,000 | 1 factura"]
        end
        
        subgraph "Detalle por Cliente"
            DC1["| Cliente | Facturas | Total | Pagado | Pendiente | Vencido | % Recup | Riesgo |"]
            DC2["| Cliente A | 15 | $800k | $600k | $200k | $50k | 75% | 🟢 Bajo |"]
            DC3["| Cliente B | 10 | $500k | $400k | $100k | $100k | 80% | 🔴 Alto |"]
            DC4["| Cliente C | 8 | $400k | $300k | $100k | $0 | 75% | 🟡 Medio |"]
        end
        
        RC1 --> RE1
        RE1 --> DE1
        DE1 --> AG1
        AG1 --> DC1
    end
```

---

## 11. Mockup: Perfil de Cliente (Reporte Completo)

```mermaid
flowchart TB
    subgraph "Perfil del Cliente - Reporte Completo"
        direction TB
        
        subgraph "Header del Cliente"
            HH1["🖼️ Avatar / Logotipo"]
            HH2["🏢 Nombre: Cliente A"]
            HH3["🌍 País: Estados Unidos 🇺🇸"]
            HH4["🌐 Mercado: USA"]
            HH5["📊 Calificación: A+ (Excelente)"]
            HH6["💳 Tipo: Mixto (Contado y Crédito)"]
            HH7["💰 Límite de Crédito: $500,000"]
            HH8["💵 Crédito Disponible: $350,000"]
        end
        
        subgraph "Métricas de Ventas"
            MV1["📊 Total Ventas: $2,000,000"]
            MV2["📈 N° Ventas: 35"]
            MV3["📉 Promedio: $57,142"]
            MV4["🟢 Pagado: $1,500,000"]
            MV5["🔴 Pendiente: $500,000"]
        end
        
        subgraph "Distribución por Estado"
            DS1["🟢 Pagado: $1,500,000 (75%)"]
            DS2["🟡 Parcial: $300,000 (15%)"]
            DS3["🟠 Pendiente: $150,000 (7.5%)"]
            DS4["🔴 Vencido: $50,000 (2.5%)"]
        end
        
        subgraph "Historial de Ventas"
            HV1["| Fecha | Carga | Producto | Monto | Modalidad | Estado | Saldo |"]
            HV2["| 2024-01-15 | C-001 | Mango | $50k | Crédito | 🔴 Vencido | $50k |"]
            HV3["| 2024-02-01 | C-002 | Tomate | $30k | Contado | 🟢 Pagado | $0 |"]
            HV4["| 2024-03-10 | C-003 | Pepino | $45k | Crédito | 🟡 Parcial | $20k |"]
        end
        
        subgraph "Acciones"
            AC1["📄 Generar Estado de Cuenta"]
            AC2["📧 Enviar Recordatorio"]
            AC3["📊 Ver Análisis de Aging"]
        end
        
        HH1 --> MV1
        MV1 --> DS1
        DS1 --> HV1
        HV1 --> AC1
    end
```

---

## 12. Mockup: Estado de Cuenta del Cliente

```mermaid
flowchart TB
    subgraph "Estado de Cuenta - Vista Web"
        direction TB
        
        subgraph "Encabezado"
            EC1["📋 ESTADO DE CUENTA"]
            EC2["🏢 Cliente: Cliente A"]
            EC3["📅 Período: 01/01/2024 - 31/03/2024"]
            EC4["📊 Generado: 05/04/2024 por admin"]
        end
        
        subgraph "Resumen"
            RS1["💵 Total Ventas: $500,000"]
            RS2["💰 Total Abonos: $350,000"]
            RS3["⚠️ Saldo Final: $150,000"]
            RS4["📄 N° Facturas: 10"]
            RS5["📈 % Recuperación: 70%"]
            RS6["💵 Promedio/Factura: $50,000"]
        end
        
        subgraph "Detalle de Movimientos"
            DM1["| Fecha | Concepto | Folio | Cargo | Abono | Saldo |"]
            DM2["| 01/01/24 | Venta - Carga C-001 | B-1996 | $50,000 | - | $50,000 |"]
            DM3["| 15/01/24 | Pago - Transferencia | REF-001 | - | $30,000 | $20,000 |"]
            DM4["| 01/02/24 | Venta - Carga C-002 | B-2001 | $45,000 | - | $65,000 |"]
            DM5["| 10/02/24 | Nota de Crédito | NC-001 | - | $5,000 | $60,000 |"]
            DM6["| 01/03/24 | Venta - Carga C-003 | B-2015 | $55,000 | - | $115,000 |"]
            DM7["| 15/03/24 | Pago - Cheque | CH-002 | - | $40,000 | $75,000 |"]
        end
        
        subgraph "Pie"
            PI1["📄 Descargar PDF"]
            PI2["📊 Descargar Excel"]
            PI3["📧 Enviar por correo"]
        end
        
        EC1 --> RS1
        RS1 --> DM1
        DM1 --> PI1
    end
```

---

## 13. Mockup: Dashboard de Ventas (Admin)

```mermaid
flowchart TB
    subgraph "Dashboard de Ventas"
        direction TB
        
        subgraph "KPIs Superior"
            DK1["💵 Ventas del Mes: $450,000<br/>↗️ +12% vs mes anterior"]
            DK2["💰 Cobranza del Mes: $380,000<br/>↗️ +8% vs mes anterior"]
            DK3["⚠️ Cuentas por Cobrar: $270,000<br/>↘️ -5% vs mes anterior"]
            DK4["🔴 Vencidas: $45,000<br/>↗️ +2% vs mes anterior"]
        end
        
        subgraph "Gráfico de Tendencia (6 meses)"
            GT1["📈 Línea: Ventas vs Cobranza<br/>Ene: $400k | Feb: $380k | Mar: $450k | Abr: $420k | May: $480k | Jun: $500k"]
        end
        
        subgraph "Gráfico por Categoría"
            GC1["🥧 Pastel: Ventas por producto<br/>Mango 40% | Tomate 30% | Pepino 20% | Otros 10%"]
        end
        
        subgraph "Gráfico por Mercado"
            GM1["🗺️ Barras: Ventas por mercado<br/>Nacional $300k | USA $400k | Canadá $150k | Europa $100k"]
        end
        
        subgraph "Actividad Reciente"
            AR1["📝 Últimas 5 ventas registradas"]
            AR2["💰 Últimos 5 pagos recibidos"]
        end
        
        subgraph "Alertas y Vencimientos"
            AV1["🔔 Vencen esta semana: 3 facturas ($35,000)"]
            AV2["🔴 Vencidas +30 días: 2 facturas ($25,000)"]
            AV3["⚠️ Clientes con límite excedido: 1"]
        end
        
        DK1 --> GT1
        GT1 --> GC1
        GC1 --> GM1
        GM1 --> AR1
        AR1 --> AV1
    end
```

---

## 14. Mockup: Configuración Cuentas por Cobrar

```mermaid
flowchart TB
    subgraph "Configuración CXC"
        direction TB
        
        subgraph "Parámetros de Aging"
            PA1["📅 Días Corriente: [30]"]
            PA2["📅 Días Vencido 1: [60]"]
            PA3["📅 Días Vencido 2: [90]"]
        end
        
        subgraph "Automatización"
            AU1["☑️ Cálculo automático de aging"]
            AU2["⏰ Hora de cálculo: [02:00]"]
            AU3["📊 Frecuencia: [Diario ▼]"]
        end
        
        subgraph "Alertas"
            AL1["☑️ Enviar alertas de vencimiento"]
            AL2["📅 Días previos alerta: [5]"]
            AL3["📧 Email responsable: [cobranza@empresa.com]"]
        end
        
        subgraph "Límites de Crédito"
            LC1["☑️ Permitir sobregiro (con autorización)"]
            LC2["📊 % Sobregiro permitido: [10%]"]
        end
        
        subgraph "Tipo de Cambio"
            TC1["💱 USD→MXN: [17.0000]"]
            TC2["🔄 Última actualización: Hoy 09:00"]
        end
        
        PA1 --> AU1
        AU1 --> AL1
        AL1 --> LC1
        LC1 --> TC1
    end
```

---

## 15. Diagrama de Estados - Cobranza

```mermaid
stateDiagram-v2
    [*] --> Pendiente: Venta a crédito creada
    [*] --> Pagado: Venta de contado
    
    Pendiente --> Parcial: Primer pago recibido
    Pendiente --> Pagado: Pago completo
    Pendiente --> Vencido: Fecha vencimiento + 1 día
    
    Parcial --> Pagado: Pago completo del saldo
    Parcial --> Vencido: Fecha vencimiento + 1 día
    
    Vencido --> Parcial: Pago parcial recibido
    Vencido --> Pagado: Pago completo (con intereses)
    
    Pagado --> [*]: Venta finalizada
    
    Vencido --> Incobrable: Declaración explícita<br/>(solo admin)
    Incobrable --> [*]: Cuenta dada de baja
    
    note right of Pendiente
        Se calcula automáticamente:
        fecha_vencimiento = fecha_deposito + dias_credito
    end note
    
    note right of Vencido
        Interés moratorio acumulado:
        saldo * tasa_mensual * (dias_vencido/30)
    end note
```

---

## 16. Arquitectura de Servicios (Ventas)

```mermaid
flowchart TB
    subgraph "Capa de Presentación"
        P1["Admin Django (Jazzmin)"]
        P2["Templates HTML + Tailwind"]
        P3["JavaScript (ventas_form_logic.js)"]
    end
    
    subgraph "Capa de Vistas / Controladores"
        V1["ventas/views.py<br/>• ventas_balances<br/>• exportar_balances_xlsx<br/>• reporte_cobranza_global"]
        V2["ventas/admin.py<br/>• VentasAdmin<br/>• ClienteAdmin<br/>• Custom URLs"]
    end
    
    subgraph "Capa de Servicios"
        S1["ventas/services/reporte_cobranza_service.py"]
        S2["ventas/services/cache_service.py<br/>• VentasBalancesCache<br/>• CuentasPorCobrarCache"]
        S3["ventas/services/metrics_service.py<br/>• CuentasPorCobrarMetrics"]
    end
    
    subgraph "Capa de Modelos"
        M1["Cliente"]
        M2["Ventas"]
        M3["PagoVenta"]
        M4["Anticipo"]
        M5["SaldoCliente"]
        M6["AntigüedadSaldo"]
        M7["EstadoCuentaCliente"]
    end
    
    subgraph "Capa de Datos"
        D1["MySQL 8.0"]
        D2["Redis Cache"]
        D3["Media Storage<br/>(comprobantes, CFDIs)"]
    end
    
    P1 --> V2
    P2 --> V1
    P3 --> V1
    
    V1 --> S1
    V1 --> S2
    V2 --> S2
    V2 --> S3
    
    S1 --> M2
    S2 --> D2
    S3 --> M5
    
    V1 --> M2
    V2 --> M1
    V2 --> M2
    V2 --> M3
    V2 --> M4
    
    M1 --> D1
    M2 --> D1
    M3 --> D1
    M4 --> D1
    M5 --> D1
    M6 --> D1
    M7 --> D1
    M3 --> D3
    M4 --> D3
```

---

## Referencias

- Modelos: `ventas/models.py`
- Admin: `ventas/admin.py`
- Vistas: `ventas/views.py`
- Forms: `ventas/forms.py`
- URLs: `ventas/urls.py`
- Servicios: `ventas/services/`
- Templates: `templates/ventas/`

---

*Documento generado para referencia visual del módulo de ventas.*
