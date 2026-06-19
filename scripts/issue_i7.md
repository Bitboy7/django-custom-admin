## Historia de usuario
- **US-07**: Como *vendedor*, quiero importar datos de una factura CFDI XML para evitar captura manual.

## Prácticas XP
- TDD
- Spike (parser XML)
- Diseño Simple — 2 pasos

## Flujo (2 pasos)
1. **Paso 1**: Subir XML → parsear → matching automático
2. **Paso 2**: Confirmar datos → guardar Venta

## Matching automático
- Cliente: match por nombre exacto o parcial del receptor
- Producto: match por variedad encontrada en descripción
- Monto, moneda, tipo_cambio: extraídos del XML

## Tests clave
- `test_parse_cfdi_extrae_monto_y_moneda()`
- `test_match_cliente_por_nombre_exacto()`
- `test_match_producto_por_variedad_en_descripcion()`
- `test_importacion_dos_pasos_crea_venta()`

## Definition of Done
- [ ] Upload + parse + confirm funcional
- [ ] Matching automático con fallback manual
- [ ] Cobertura ≥ 85%

## Estimación
**8 puntos**

## Métricas objetivo
- Tests nuevos: 10
- Cobertura: 85%
