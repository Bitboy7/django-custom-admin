## Historia de usuario
- **US-13**: Como *vendedor*, quiero exportar balances de ventas a Excel con formato profesional.

## Prácticas XP
- Refactorización final
- Small Release
- Polish

## Exportación Excel (openpyxl)
- Hoja 1: Detalle de ventas (tabla formateada)
- Hoja 2: Resumen ejecutivo de cuentas por cobrar
- Totales, fórmulas, estilos (colores, negritas)

## Code smells a refactorizar
| Smell | Solución |
|-------|----------|
| `Ventas.save()` > 30 líneas | Extraer `VentaEstadoService` |
| Duplicación en cálculo de intereses | Extraer `InteresMoratorioService` |
| Magic numbers en aging | Usar `ConfiguracionCuentasPorCobrar.dias_*` |
| Tests lentos (N+1) | `select_related` + `prefetch_related` |

## Tests clave
- `test_exportar_ventas_a_excel_contiene_dos_hojas()`
- `test_exportar_excel_totales_correctos()`

## Definition of Done
- [ ] Excel exportado con formato profesional
- [ ] Code smells refactorizados
- [ ] Cobertura final ≥ 91%
- [ ] Release candidate listo

## Estimación
**5 puntos**

## Métricas objetivo
- Tests nuevos: 6
- Cobertura: 91%
