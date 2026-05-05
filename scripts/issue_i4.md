## Historias de usuario
- **US-04**: Como *contador*, quiero registrar pagos parciales de una venta a crédito con integridad transaccional.
- **US-15**: Como *auditor*, quiero que cada cambio de estado de cobranza se registre en el log de actividad.

## Prácticas XP
- TDD en código crítico
- Pair Programming SIEMPRE en operaciones financieras
- Diseño Simple

## Estándares Bancarios (RF01-RF06)
| Estándar | Descripción | Test |
|----------|-------------|------|
| RF01 | Un pago solo pertenece a UNA venta | ForeignKey + related_name='pagos' |
| RF02 | No pagar ventas ya completadas | ValidationError si estado=Pagado |
| RF03 | Sin sobrepagos | ValidationError si monto_pago > saldo |
| RF04 | Transacción atómica | `select_for_update()` + `transaction.atomic()` |
| RF05 | Auditoría completa | `LogActividad` creado tras cada pago |
| RF06 | Validación multi-nivel | Form + Modelo + BD |

## Modelos a crear
- `PagoVenta`: venta, fecha_pago, monto_pago, cuenta_destino, metodo_pago, referencia, notas, comprobante_pago

## Tests clave
- `test_pago_a_venta_pagado_falla()` (RF02)
- `test_pago_no_sobrepaga_saldo()` (RF03)
- `test_pago_concurrente_no_sobrepaga()` (RF04 — race condition)
- `test_auditoria_log_creado_tras_pago()` (RF05)

## Refactorización
- Extraer `derive_estado_desde_totales()` como fuente de verdad única

## Definition of Done
- [ ] Todos los tests RF01-RF06 pasan
- [ ] Cobertura ≥ 88%
- [ ] Auditoría automática funcional

## Estimación
**11 puntos**

## Métricas objetivo
- Tests nuevos: 18
- Cobertura: 88%
