# Diseño — Conciliación multimoneda y exportación automática (Ventas)

Fecha: 2026-10-08
Estado: propuesto (pendiente de revisión)

## 1. Objetivo

Corregir el manejo de moneda en pagos de venta y automatizar la detección de
exportación, para que:

1. Una venta a un cliente extranjero quede como **Exportación** sin que el
   usuario lo seleccione (en admin, importación CFDI y altas programáticas).
2. Los pagos en moneda extranjera (p. ej. USD) conserven su moneda y registren
   un **tipo de cambio proporcionado por el usuario**, con el que se calcula su
   equivalente en MXN.
3. La conciliación por cliente muestre los cobros en su **moneda real** (no como
   "cobro de contado MXN").

### Problema reportado

Cliente `WORLD PRODUCE TRADING CORP` (país Estados Unidos). Dos pagos de venta
de $20,000.00 y $16,000.00 USD (sin PDF/XML) aparecen en la conciliación como
cobro de contado en **pesos mexicanos**, y varias ventas a ese cliente quedaron
como **Nacional** por defecto.

## 2. Decisiones aprobadas

- **La moneda de la venta es la fuente de verdad**: la venta y sus pagos viven
  en su moneda (p. ej. USD). El MXN se muestra como equivalencia usando el tipo
  de cambio capturado. No se convierte el monto original a MXN.
- Los **pagos manuales sin REP se suman a la columna "Pagos (REP)"** de la
  conciliación, en su moneda real.

## 3. Causa raíz (hallazgos)

| # | Problema | Evidencia |
| --- | --- | --- |
| 1 | `Ventas.monto_pagado` es `MoneyField(default_currency='MXN')` y recibe montos de pagos sin convertir | `ventas/models.py:542`, `:812` |
| 2 | `registrar_abono` vuelca `Sum('monto_pago')` al campo MXN | `ventas/services/cuentas_por_cobrar_service.py:210-213` |
| 3 | `saldo_por_cobrar` resta `monto` (USD) − `monto_pagado` (MXN) sin convertir | `ventas/models.py:720-725` |
| 4 | La conciliación lee `monto_pagado` (siempre MXN) en vez de `PagoVenta` | `ventas/services/conciliacion_service.py:48-56` |
| 5 | `tipo_venta` se resuelve distinto en cada ruta (parser/CFDI/JS/form) | `cfdi_parser.py:221-226`, `cfdi_import_service.py:500`, `ventas_form_logic.js:433-445`, `forms.py:124-133` |
| 6 | No existe tipo de cambio por pago | `ventas/models.py` (PagoVenta), `forms_banking.py` |

## 4. Cambios de modelo y migración

### 4.1 `PagoVenta`
- Nuevo campo `tipo_cambio` = `DecimalField(max_digits=10, decimal_places=4, default=Decimal('1.0000'))`.
  - Semántica: MXN por 1 unidad de `monto_pago.currency`.
  - Requerido (> 0) cuando `moneda != MXN`; en MXN debe ser 1.0.
- Nueva propiedad `monto_pago_mxn` → `amount * tipo_cambio` (o `amount` si es MXN).

### 4.2 `Ventas`
- `monto_pagado` se mantiene **en la moneda de la venta**
  (`monto.currency` / `moneda_venta`).
- `actualizar_estado_cobranza()`: sumar pagos convirtiendo a la moneda de la
  venta; asignar `Money(total, moneda_venta)`.
- `saldo_por_cobrar()`: operar en una sola moneda (la de la venta).
- Forzar `tipo_venta` en `save()`/`clean()` según `cliente.es_extranjero`.

### 4.3 `Cliente`
- `es_extranjero` robusta (reemplaza `es_internacional` / comparaciones de texto):
  1. `residencia_fiscal` presente → `!= 'MEX'`.
  2. si no, `pais.nombre` normalizado (sin acentos, upper) `!= 'MEXICO'`.
  3. si no, `mercado_destino.nombre != 'Nacional'`.

### 4.4 Migración
- `000X_pagoventa_tipo_cambio` (schema).
- Sin migración de datos automática. La reparación histórica se hace con el
  comando descrito en §7.

## 5. Comportamiento

### 5.1 Exportación automática
- `Ventas.save()` (o `clean()`) calcula `tipo_venta` desde `cliente.es_extranjero`.
- Se elimina la lógica duplicada en `VentasAdminForm.clean()`.
- Se corrige el bug del JS: cliente extranjero **siempre** deja `Exportación`
  aunque tenga `mercado_destino` (`ventas_form_logic.js:433-445`).
- `cfdi_import_service._crear_venta` respeta `cliente.es_extranjero`
  (la marca del parser pasa a ser secundaria; el cliente manda).
- El campo se muestra bloqueado para el usuario (ya existe el mecanismo).

### 5.2 Tipo de cambio por pago
- Captura en:
  - `PagoVentaInline` (modal de pagos) — agregar `tipo_cambio` a `fields`.
  - `PagoVentaForm` (`forms_banking.py`).
  - Importación CFDI: desde `TipoCambioP` del REP; si falta, `venta.tipo_cambio`.
- Validación: si `monto_pago.currency != 'MXN'`, `tipo_cambio > 0` obligatorio.
- `default` en el form = `venta.tipo_cambio` (precio al que se vendió), editable.

### 5.3 Conciliación (`conciliacion_service.py`)
- `cobros_no_rep` se reescribe para agregar **`PagoVenta`** (moneda +
  `tipo_cambio`) en lugar de `Ventas.monto_pagado`.
- Los pagos manuales sin REP se suman **dentro de la llave `detalle['recibos_pago']`**,
  agrupados por la moneda real del pago. `cobros_contado` **se elimina** del
  detalle y la plantilla (`conciliacion.html` deja de mostrar esa columna).
- `saldo_por_moneda` permanece agrupado por moneda; la fórmula de saldo ya no
  resta `cobros_contado` (los manuales van en `recibos_pago`).

## 6. Consumidores afectados de `monto_pagado`

- `ventas/views.py:193,235,277,313` (`Sum('monto_pagado')`).
- `ventas/admin.py:1696,1751,3130` (reportes/Excel).
- `ventas/services/cache_service.py:521` (solo `only()`).
- `ventas/services/reporte_cobranza_service.py` (usa `tipo_cambio_usd` global).
- Regla: cada reporte que agregue varias ventas debe agrupar por moneda o
  convertir a MXN con el tipo de cambio correspondiente, y dejarlo explícito.

## 7. Reparación de datos históricos

Comando idempotente:

```
python manage.py reparar_moneda_pagos [--cliente-id N] [--dry-run]
```

- Recalcula `Ventas.monto_pagado` desde `PagoVenta` en la moneda de la venta.
- Rellena `PagoVenta.tipo_cambio` faltante usando `Ventas.tipo_cambio`.
- Reporta filas cambiadas; `--dry-run` no escribe.

## 8. `forms.py`

- Quitar la lógica de exportación (queda en el modelo).
- `tipo_cambio`: mostrar y validar solo cuando `moneda_venta != 'MXN'`
  (widget condicional vía `__init__`).
- `CFDIConfirmForm.tipo_venta`: derivar del cliente; no pedirlo (o solo lectura).
- `PagoVentaForm`: incluir `tipo_cambio`.

## 9. Pruebas

- `Cliente.es_extranjero` para MEX/USA/sin residencia y por `mercado_destino`.
- `Ventas.save()` fuerza `Exportación` con cliente extranjero (todas las rutas).
- `PagoVenta.monto_pago_mxn` y validación de `tipo_cambio`.
- `Ventas.monto_pagado` queda en moneda de la venta tras varios pagos USD.
- `saldo_por_cobrar` de venta USD pagada totalmente = 0 (sin mezcla de moneda).
- `conciliacion_cliente` de cliente USD: cobros en USD, saldo en USD.
- `reparar_moneda_pagos` idempotente y correcto en `--dry-run`.

## 10. Fuera de alcance / riesgos

- No se convierte el monto original de la venta a MXN de forma persistente.
- Cambia la semántica de `monto_pagado` (de MXN a moneda de venta): hay que
  revisar todos los consumidores (§6) en el mismo cambio.
- El tipo de cambio capturado es responsabilidad del usuario (no hay API de
  tipo de cambio en tiempo real).

## 11. Archivos previstos

- `ventas/models.py` (Cliente, Ventas, PagoVenta)
- `ventas/forms.py`, `ventas/forms_banking.py`
- `ventas/admin.py` (inline + reportes)
- `ventas/services/conciliacion_service.py`
- `ventas/services/cfdi_import_service.py`
- `ventas/services/cuentas_por_cobrar_service.py`
- `ventas/views.py`
- `ventas/migrations/00XX_pagoventa_tipo_cambio.py`
- `ventas/management/commands/reparar_moneda_pagos.py`
- `static/js/ventas_form_logic.js`
- Tests en `ventas/tests.py` / `ventas/tests_integration.py`
