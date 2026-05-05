## Historia de usuario
- **US-02**: Como *vendedor*, quiero registrar una venta de contado con producto, cantidad y monto. Al guardar, estado = Pagado automáticamente.

## Prácticas XP
- TDD (Rojo → Verde → Refactor)
- Refactorización continua

## Modelos a crear / modificar
- `Ventas`: fecha_salida_manifiesto, agente_id, fecha_deposito, pedimento, carga, PO, producto, cantidad, monto, cliente, sucursal_id, cuenta, tipo_venta, modalidad_pago, estado_cobranza, monto_pagado

## Lógica de negocio
- `modalidad_pago='Contado'` → `estado_cobranza='Pagado'` + `monto_pagado=monto`
- Extraer lógica a `VentaEstadoService`

## Tests clave
- `test_venta_contado_esta_pagada_al_crear()`
- `test_venta_contado_monto_pagado_igual_monto()`

## Definition of Done
- [ ] Venta de contado se guarda con estado Pagado
- [ ] Cobertura ≥ 82%
- [ ] Refactor: servicio extraído

## Estimación
**5 puntos**

## Métricas objetivo
- Tests nuevos: 8
- Cobertura: 82%
