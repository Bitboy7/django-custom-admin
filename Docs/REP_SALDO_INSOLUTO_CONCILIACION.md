# Saldo insoluto en REP contabilizado como cobro en conciliación CFDI

## 1. Contexto

El módulo de **Conciliación de CFDI por cliente** (`/admin/ventas/cliente/conciliacion/`) cruza el ledger fiscal (`DocumentoCFDI`) contra los movimientos operativos (`Ventas`, `PagoVenta`, `Anticipo`) para mostrar, por moneda:

```
Saldo conciliado = Facturado
                 + Notas de cargo
                 - Notas de crédito
                 - Pagos (REP)
                 - Cobros contado / sin REP
                 - Anticipos disponibles
```

La columna **“Cobros contado / sin REP”** agrupa:
- Ventas de contado (metodo de pago PUE) sin recibo electrónico de pago.
- Pagos operativos (`PagoVenta`) que no están respaldados por un REP vigente.

## 2. Problema reportado

El cliente **Productos BGA** adjuntó un *Complemento de Pago* (REP) donde consta:

| Concepto | Importe |
|----------|---------|
| Imp. Saldo Ant. (factura) | $446,880.00 |
| Imp. Pagado | $398,840.00 |
| Imp. Saldo Insoluto | $48,040.00 |

El sistema mostraba el importe de **$48,040.00** dentro de la columna **“Cobros contado / sin REP”**, como si ese importe ya hubiera sido cobrado, cuando el REP declara explícitamente que aún está pendiente.

Como consecuencia, el **Saldo conciliado** quedaba en **$0.00** en lugar de reflejar la deuda real de **$48,040.00**.

## 3. Causa raíz

La función `ventas/services/conciliacion_service.py::_cobros_no_rep_con_detalle` calculaba el importe “sin REP” de esta forma:

```python
sin_rep = total_pagos - rep_aplicado
```

Donde:
- `total_pagos` = suma de `PagoVenta` operativos de la venta.
- `rep_aplicado` = suma de los `ImpPagado` de los movimientos REP vinculados a la venta.

Cuando el REP no tenía un vínculo exacto por UUID con el `PagoVenta` (estado `revision_requerida`), el pago operativo seguía considerándose en la fórmula. Si el pago operativo era el importe total de la factura ($446,880.00) y el REP sólo acreditaba $398,840.00, el sistema asumía que los $48,040.00 restantes eran un cobro operativo no respaldado fiscalmente, en lugar de un saldo insoluto declarado por el SAT.

El XML del REP ya informa el `ImpSaldoInsoluto`, pero el servicio no lo utilizaba para proteger el saldo pendiente.

## 4. Comportamiento anterior vs. esperado

### Datos del caso
- Factura: $446,880.00
- PagoVenta operativo: $446,880.00
- REP: `ImpPagado = $398,840.00`, `ImpSaldoInsoluto = $48,040.00`
- Vínculo REP-PagoVenta: `revision_requerida` (no exacto)

### Antes
| Columna | Importe |
|---------|---------|
| Facturado | $446,880.00 |
| Pagos (REP) | -$398,840.00 |
| Cobros contado / sin REP | -$48,040.00 |
| **Saldo conciliado** | **$0.00** |

El saldo insoluto terminaba en “Cobros contado / sin REP”.

### Después
| Columna | Importe |
|---------|---------|
| Facturado | $446,880.00 |
| Pagos (REP) | -$398,840.00 |
| Cobros contado / sin REP | $0.00 |
| **Saldo conciliado** | **$48,040.00** |

El saldo insoluto se respeta como deuda pendiente.

## 5. Solución implementada

### 5.1 Lógica de cálculo (`ventas/services/conciliacion_service.py`)

Se modificó `_cobros_no_rep_con_detalle` para:

1. **Rastrear el `saldo_insoluto` por venta/moneda** proveniente de los movimientos REP que no tienen vínculo exacto.
2. **Usar el menor saldo insoluto** registrado para una misma venta/moneda, ya que representa el saldo más reciente cuando existen pagos parciales múltiples.
3. **Restar el saldo insoluto** al calcular el importe “sin REP”:

```python
saldo_insoluto = min(saldos_insolutos) if saldos_insolutos else Decimal('0')
sin_rep = total_pagos - rep_aplicado - saldo_insoluto
```

4. Incluir `saldo_insoluto_rep` en el desglose devuelto, de modo que la interfaz pueda mostrarlo.

### 5.2 Respaldo por `ImpSaldoAnt` (`_movimientos_rep`)

En producción se detectaron REPs donde `saldo_insoluto` llegó vacío o en cero en el JSON guardado, aunque el XML sí mostraba el importe. Se agregó un respaldo en `_movimientos_rep`:

```python
if saldo_insoluto <= 0 and saldo_anterior > 0:
    saldo_insoluto = max(Decimal('0'), saldo_anterior - monto)
```

Así, si el XML tiene `ImpSaldoAnt = 446,880.00` e `ImpPagado = 398,840.00`, pero `ImpSaldoInsoluto` no se guardó, el sistema deriva `48,040.00` y no lo contabiliza como cobro.

### 5.2 Interfaz (`templates/admin/ventas/conciliacion.html`)

En el popover de origen de cobros se agregó una nueva línea:

> **Saldo insoluto REP**: $48,040.00 MXN

Esto explica por qué el “Remanente operativo” queda en $0.00 aun cuando el pago operativo supera al REP aplicado.

### 5.3 Estilos (`static/css/conciliacion.css`)

Se amplió el ancho del popover de cobros (`.conc-cobros-pop`) a `min(520px, calc(100vw - 24px))`, igual que el popover REP, para evitar que los importes, UUIDs y fechas se corten.

## 6. Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `ventas/services/conciliacion_service.py` | Resta el saldo insoluto REP al calcular cobros contado/sin REP; expone `saldo_insoluto_rep` en el desglose. |
| `templates/admin/ventas/conciliacion.html` | Muestra “Saldo insoluto REP” en el desglose de cobros. |
| `static/css/conciliacion.css` | Ancho mayor para el popover de cobros. |
| `ventas/tests.py` | Actualiza el test BGA y agrega test de múltiples REPs parciales. |

## 7. Tests

### Test actualizado
- `ConciliacionCFDITest.test_bga_rep_parcial_muestra_diferencia_y_vinculo_pendiente`
  - Ahora espera `cobros_contado['MXN'] = 0.00` y `saldo_por_moneda['MXN'] = 48040.00`.

### Test nuevo
- `ConciliacionCFDITest.test_rep_parcial_multiples_pagos_usa_menor_saldo_insoluto`
  - Verifica que, con dos REPs parciales sobre la misma factura, se use el **menor** saldo insoluto (el más reciente), no la suma.
  - Factura: $500,000.00
  - REP 1: $200,000.00 pagados, saldo insoluto $300,000.00
  - REP 2: $150,000.00 pagados, saldo insoluto $150,000.00
  - Resultado esperado: `recibos_pago = 350,000.00`, `cobros_contado = 0.00`, `saldo = 150,000.00`.

- `ConciliacionCFDITest.test_rep_parcial_sin_saldo_insoluto_lo_deriva_de_saldo_anterior`
  - Simula un REP donde `saldo_insoluto` está vacío en el JSON pero `saldo_anterior` está presente.
  - Verifica que el sistema derive el saldo insoluto (`446,880 - 398,840 = 48,040`) y no lo sume a “Cobros contado / sin REP”.

### Resultado de la suite
```bash
pytest ventas/tests.py ventas/tests_integration.py --tb=short
# 140 passed, 3 skipped
```

## 8. Filtro de sucursal (adicional)

Se agregó un filtro de **Sucursal** en la vista de conciliación para que el usuario pueda ver únicamente la operación correspondiente a una sucursal específica.

### Comportamiento
- Incluye **solo** ventas, pagos (`PagoVenta`) y documentos CFDI vinculados a la sucursal seleccionada.
- Los **anticipos** se excluyen porque el modelo `Anticipo` no tiene sucursal asignada.
- Los documentos **sin venta asignada** se excluyen porque tampoco tienen sucursal.
- La interfaz muestra una nota cuando el filtro está activo:
  > *Al filtrar por sucursal se incluyen únicamente ventas, pagos y documentos vinculados a esa sucursal. Los anticipos y documentos sin venta asignada se excluyen del cálculo.*

### Archivos modificados para el filtro
| Archivo | Cambio |
|---------|--------|
| `ventas/services/conciliacion_service.py` | Parámetro `sucursal_id` en `_documentos_en_periodo`, `_cobros_no_rep_con_detalle`, `cobros_no_rep`, `pagos_total_mxn`, `_calcular`, `saldo_por_moneda`, `conciliacion_cliente` y `conciliacion_global`. |
| `ventas/services/cache_service.py` | La clave de cache de `ConciliacionCache` incluye `sucursal_id`. |
| `ventas/admin.py` | `conciliacion_view` lee `sucursal_id`, lo pasa al servicio y envía `sucursales` al template. |
| `templates/admin/ventas/conciliacion.html` | Nuevo select de sucursal y nota informativa. |
| `ventas/tests.py` | Tests `test_filtro_sucursal_excluye_ventas_y_anticipos_de_otra_sucursal` y `test_vista_aplica_filtro_sucursal_y_excluye_anticipos`. |

## 9. Notas técnicas

- El cambio solo afecta REPs **sin vínculo exacto** (`revision_requerida`). Cuando el vínculo es exacto (`uuid_coincidente`), el `PagoVenta` completo ya se excluía del cálculo y el saldo insoluto se reflejaba correctamente.
- Si el `PagoVenta` operativo excede al importe facturado según el REP (`total_pagos > rep_aplicado + saldo_insoluto`), el excedente sí se sigue contabilizando como “Cobros contado / sin REP”, porque representa un cobro operativo no respaldado fiscalmente.
- El campo `saldo_insoluto_rep` en el desglose permite a futuro agregar alertas o filtros específicos para pagos parciales.

## 10. Recomendaciones operativas

Para evitar que este escenario se repita:

1. Al importar un REP, verificar que el `uuid_rep` del `PagoVenta` coincida con el UUID del CFDI de pago; así el sistema marcará el vínculo como `uuid_coincidente`.
2. Si un pago es parcial, registrar el `PagoVenta` por el importe pagado, no por el total de la factura.
3. Revisar periódicamente los registros marcados con “Revisión requerida” en el desglose REP para corregir vínculos discordantes.

---

**Fecha de documento:** 2026-11-14  
**Módulo:** Ventas / Conciliación CFDI  
**Cliente de referencia:** Productos BGA
