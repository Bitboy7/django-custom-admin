## Historia de usuario
- **US-03**: Como *vendedor*, quiero registrar una venta a crédito con fecha de vencimiento auto-calculada.

## Prácticas XP
- TDD con cliente onsite
- Diseño Simple — solo agregar validaciones cuando el test lo exige

## Modelos a crear
- `TerminoCredito`: nombre, dias_credito, tasa_interes_mensual, activo

## Lógica de negocio
- `fecha_vencimiento = fecha_deposito + termino_credito.dias_credito`
- `modalidad_pago='Credito'` → `estado_cobranza='Pendiente'`
- Validación en `clean()`: crédito requiere término

## Tests clave
- `test_venta_credito_calcula_vencimiento()`
- `test_venta_credito_requiere_termino()`

## Definition of Done
- [ ] Fecha de vencimiento se calcula automáticamente
- [ ] Validación: crédito sin término → ValidationError
- [ ] Cobertura ≥ 84%

## Estimación
**8 puntos**

## Métricas objetivo
- Tests nuevos: 10
- Cobertura: 84%
