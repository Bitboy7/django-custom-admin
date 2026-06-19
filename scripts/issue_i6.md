## Historia de usuario
- **US-06**: Como *gerente*, quiero ver un reporte de cobranza con saldos pendientes, vencidos y aging.

## Prácticas XP
- TDD
- Diseño Emergente — extraer servicios solo cuando hay duplicación
- Refactorización continua

## Servicios a extraer (diseño emergente)
- `reporte_cobranza_service.py` — función principal
- `CuentasPorCobrarMetrics` — métricas y cálculos
- `CuentasPorCobrarCache` — caché de resultados

## Lógica del reporte
- Total ventas, total pagado, saldo pendiente
- Saldos vencidos (por fecha_vencimiento < hoy)
- Distribución por estado de cobranza
- Distribución por cliente (top deudores)
- Saldo a favor del cliente (anticipos pendientes + excedentes)

## Tests clave
- `test_reporte_con_ventas_y_pagos_saldo_correcto()`
- `test_anticipos_pendientes_suman_saldo_a_favor()`
- `test_excedente_anticipo_aplicado_saldo_a_favor()`
- `test_filtro_por_fechas_excluye_fuera_rango()`

## Definition of Done
- [ ] Reporte genera datos correctos con múltiples escenarios
- [ ] Cobertura ≥ 90%
- [ ] Servicios extraídos y testeados

## Estimación
**13 puntos**

## Métricas objetivo
- Tests nuevos: 22
- Cobertura: 90%
