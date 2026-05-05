## Objetivo
Sentar las bases técnicas antes de escribir lógica de negocio del módulo ventas.

## Prácticas XP
- **Spike**: Validar tecnologías críticas antes de comprometerse
- **TDD setup**: Configurar pytest y fixtures reutilizables
- **CI pipeline**: Pipeline verde desde el día 1

## Tareas
- [ ] Configurar app `ventas` en `INSTALLED_APPS`
- [ ] **Spike**: validar `django-money` + `MoneyField` (monetario crítico)
- [ ] Configurar `pytest` con `DJANGO_SETTINGS_MODULE` y fixtures base
- [ ] Crear factory de datos: `Pais`, `Estado`, `Sucursal`, `Producto`, `Banco`, `Cuenta`
- [ ] CI pipeline: ejecutar `pytest` + `flake8` en cada push
- [ ] Definir contrato de modelos con cliente (dueño del producto)

## Definition of Done
- [ ] `pytest` ejecuta sin errores de configuración
- [ ] Fixture base crea objetos reutilizables en `< 100 ms`
- [ ] Spike documenta decisión: "Usamos `MoneyField` en vez de `Decimal` para evitar inconsistencias de moneda"

## Historias relacionadas
Ninguna (inversión técnica)

## Estimación
**0 puntos** (spike / foundation)

## Métricas objetivo
- Tests nuevos: 3
- Cobertura: N/A
