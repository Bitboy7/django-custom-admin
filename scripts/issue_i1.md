## Historias de usuario
- **US-01**: Como *vendedor*, quiero registrar un cliente con datos básicos y límite de crédito.
- **US-10**: Como *vendedor*, quiero clasificar clientes por mercado de destino (Nacional, USA, etc.).

## Prácticas XP
- TDD (Ping-Pong Pairing)
- Diseño Simple
- Pair Programming Driver-Navigator

## Modelos a crear
- `Cliente`: nombre, teléfono, correo, dirección, tipo_cliente (Contado|Crédito|Mixto), límite_credito, calificación_credito (A+|A|B|C), activo
- `MercadoDestino`: nombre, países (M2M), moneda_preferida, factor_riesgo, requiere_documentacion_especial

## Tests clave (TDD)
- `test_cliente_se_crea_con_limite_credito()`
- `test_cliente_contado_no_tiene_credito()`
- `test_mercado_destino_clasifica_paises()`

## Definition of Done
- [ ] Admin funcional con filtros por tipo y calificación
- [ ] Cobertura de tests ≥ 85%
- [ ] Demo al cliente: crear cliente, asignar mercado, ver límite

## Estimación
**8 puntos**

## Métricas objetivo
- Tests nuevos: 12
- Cobertura: 85%
