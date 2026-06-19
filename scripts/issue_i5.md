## Historia de usuario
- **US-05**: Como *vendedor*, quiero registrar un anticipo de cliente y aplicarlo a una venta.

## Prácticas XP
- TDD
- State Machine (máquina de estados)
- Pair Programming

## Reglas de negocio (RF07-RF10)
| Regla | Descripción |
|-------|-------------|
| RF07 | No aplicar anticipo a venta ya pagada |
| RF08 | Un anticipo solo puede estar en un estado a la vez |
| RF09 | Consistencia entre estado y saldo disponible |
| RF10 | Auditoría de cambios de estado |

## Estados del anticipo
```
Pendiente → Aplicado → (Venta completada)
Pendiente → Cancelado → (Reembolso)
```

## Modelos a crear
- `Anticipo`: cliente, cuenta, monto, monto_aplicado, fecha, estado_anticipo, folio_factura_anticipo

## Tests clave
- `test_anticipo_aplicado_mismo_cliente()`
- `test_anticipo_no_aplicable_a_venta_pagada()` (RF07)
- `test_saldo_disponible_legacy()` (datos legacy sin monto_aplicado)
- `test_auditoria_cambio_estado_anticipo()` (RF10)

## Definition of Done
- [ ] Máquina de estados funcional
- [ ] Transacción atómica en aplicación
- [ ] Cobertura ≥ 87%

## Estimación
**8 puntos**

## Métricas objetivo
- Tests nuevos: 14
- Cobertura: 87%
