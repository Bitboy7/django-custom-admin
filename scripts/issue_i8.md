## Historias de usuario
- **US-08**: Como *contador*, quiero generar un estado de cuenta por cliente con movimientos del período.
- **US-12**: Como *administrador*, quiero configurar días de aging y alertas de vencimiento.

## Prácticas XP
- TDD
- Configuración parametrizable (sin hardcodear)

## Modelos a crear
- `EstadoCuentaCliente`: cliente, periodo_inicio/fin, total_ventas, total_abonos, saldo_final, numero_facturas, formato_generado
- `ConfiguracionCuentasPorCobrar` (singleton): dias_corriente, dias_vencido_1, dias_vencido_2, calculo_automatico_aging, alertas, tipo_cambio_usd

## Cálculo del estado de cuenta
```
Saldo final = Total Ventas - Total Abonos
% Recuperación = (Abonos / Ventas) × 100
```

## Tests clave
- `test_estado_cuenta_calcula_saldo_correcto()`
- `test_configuracion_singleton_siempre_retorna_mismo_registro()`
- `test_estado_cuenta_porcentaje_recuperacion()`

## Definition of Done
- [ ] Estado de cuenta calcula saldo correcto
- [ ] Configuración singleton funcional
- [ ] Cobertura ≥ 86%

## Estimación
**11 puntos**

## Métricas objetivo
- Tests nuevos: 12
- Cobertura: 86%
