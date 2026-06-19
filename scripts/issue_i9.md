## Historias de usuario
- **US-09**: Como *gerente*, quiero ver análisis de antigüedad de saldos (aging) para evaluar riesgo crediticio.
- **US-14**: Como *sistema*, quiero invalidar caché automáticamente al registrar pagos para datos actualizados.

## Prácticas XP
- TDD
- Performance testing
- Refactorización

## Modelos a crear
- `AntiguedadSaldo` (snapshot): cliente, fecha_calculo, corriente, vencido_1, vencido_2, vencido_3, total_saldo, numero_facturas, promedio_dias_pago

## Buckets de aging
| Bucket | Días |
|--------|------|
| Corriente | 0-30 |
| Vencido 1 | 31-60 |
| Vencido 2 | 61-90 |
| Vencido 3 | +90 |

## Caché
- Clave: `cxc_dashboard_ventas_principal`
- Invalidación automática en `PagoVenta.save()`
- Fallback a LocMemCache si Redis no disponible

## Tests clave
- `test_aging_buckets_correctos()`
- `test_cache_dashboard_se_invalida_al_registrar_pago()`
- `test_aging_calculado_por_cliente_y_fecha()`

## Definition of Done
- [ ] Aging calcula buckets correctamente
- [ ] Caché se invalida automáticamente
- [ ] Cobertura ≥ 89%

## Estimación
**13 puntos**

## Métricas objetivo
- Tests nuevos: 16
- Cobertura: 89%
