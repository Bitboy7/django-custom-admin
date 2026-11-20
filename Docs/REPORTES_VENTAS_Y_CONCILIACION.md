# Reportes de Análisis de ventas y Conciliación CFDI (Excel y PDF)

Fecha del cambio: 2026-11-19 · Rama: `fix/conciliacion-rep-auditoria`

## Resumen

Las pantallas **Análisis de ventas** y **Conciliación de CFDI** permiten descargar un reporte en **Excel** y en **PDF**. Cada reporte usa los mismos filtros activos en pantalla, de modo que el archivo siempre corresponde a lo que el usuario ve.

Antes solo existía un Excel básico de balances (una hoja con la tabla de detalle) y un botón que disparaba el PDF de DataTables. Ahora los reportes incluyen indicadores, hallazgos automáticos y las incidencias que hay que resolver.

## Dónde se descargan

| Pantalla | Botones | Ubicación |
|---|---|---|
| Análisis de ventas (`/admin/ventas/ventas/balances/`) | **Reporte Excel**, **Reporte PDF** | Arriba de las gráficas (sustituyen a «Exportar PDF») |
| Conciliación CFDI (`/admin/ventas/cliente/conciliacion/`) | **Excel**, **PDF** | Junto al botón *Filtrar* |

Los enlaces de descarga llevan la query string actual (`request.GET.urlencode`). Los filtros por rango de meses, día, rango de fechas, cliente, cuenta, sucursal, mercado, modalidad y estado se respetan.

## Rutas

| Nombre | URL |
|---|---|
| `admin:ventas_exportar_balances_xlsx` | `/admin/ventas/ventas/balances/export/` |
| `admin:ventas_exportar_balances_pdf` | `/admin/ventas/ventas/balances/export/pdf/` |
| `admin:ventas_cliente_conciliacion_excel` | `/admin/ventas/cliente/conciliacion/export-excel/` |
| `admin:ventas_cliente_conciliacion_pdf` | `/admin/ventas/cliente/conciliacion/export-pdf/` |
| `ventas:exportar_balances_pdf` | `/ventas/balances/export/pdf/` |

Permiso requerido en las vistas públicas: `ventas.view_ventas`. En el admin aplica `admin_view`.

## Contenido del reporte de Análisis de ventas

**Excel** (hojas): Resumen · Tendencia mensual · Clientes ABC · Antigüedad de cartera · Productos · Sucursales · Ventas sin CFDI · Detalle de ventas.
**PDF**: hallazgos, indicadores, tendencia, ABC, antigüedad, productos, sucursales, ventas sin CFDI y detalle (máximo 300 ventas, las de mayor saldo; el completo está en el Excel).

| Indicador | Cálculo |
|---|---|
| Ventas / operaciones / ticket promedio | Suma de `monto`, conteo y promedio, por moneda |
| Cobrado y % cobrado | `monto_pagado` entre ventas |
| Saldo por cobrar | `Ventas.saldo_por_cobrar()`: monto + cargos − créditos − pagado. Solo se cuentan ventas con saldo > 0.005 |
| Vencido / vencido > 90 días | Saldo de ventas con `fecha_vencimiento` pasada. Los días se cuentan desde el vencimiento |
| Antigüedad | Cubetas: por vencer, 1-30, 31-60, 61-90, más de 90 días |
| Días promedio de cobro | Solo ventas a crédito: promedio ponderado por importe de (`fecha_pago` − `fecha_deposito`) de cada pago en la misma moneda |
| Clientes ABC | Pareto por moneda: A hasta 80 % acumulado, B hasta 95 %, C el resto |
| Ventas sin CFDI | Ventas sin factura vigente (venta nacional/exportación/servicio/mixto) con UUID |
| Vendido vs. facturado | Se compara contra los CFDI vigentes de ingreso en el mismo periodo y cliente |
| Tendencia mensual | Ventas, cobrado y saldo por mes y moneda, con variación contra el mes anterior |

Los hallazgos son frases generadas a partir de esos indicadores (cobranza, vencido, días de cobro, ventas sin factura, concentración, mejor mes y diferencia contra lo facturado).

## Contenido del reporte de Conciliación

**Excel** (hojas): Resumen · Conciliación · Concentración cartera · Incidencias · Cobros contado-sin REP · Aplicaciones REP.
**PDF**: hallazgos, totales por moneda, conciliación por cliente, concentración de cartera e incidencias.

La conciliación por cliente conserva la fórmula de la pantalla:

```
Saldo = Facturado + Notas de cargo − Notas de crédito − REP
        − Cobros contado / sin REP − Anticipos disponibles
```

Las **incidencias** incluyen una acción sugerida:

| Tipo | Acción sugerida |
|---|---|
| Documento sin venta (nota de crédito, nota de cargo, recibo de pago) | Si no tiene UUID: sustituir por el XML real y ligarlo a su venta. Si lo tiene: importar la factura relacionada o ligarlo |
| Cobro sin CFDI | Emitir o importar la factura de la venta |
| REP por revisar | Revisar el UUID de la factura que paga el REP |
| Saldo a favor del cliente | Aplicar a ventas pendientes, documentar el anticipo o reembolsar |

## Reglas de negocio

- **Sin mezcla de monedas.** Todos los importes se agrupan por moneda; nunca se suman MXN con USD.
- **Mismos filtros que la pantalla.** Se leen con `leer_filtros_balances` / `q_ventas_balances` (ventas) y `_conciliacion_filtrada` (conciliación).
- **Saldo neto de notas de crédito.** Las ventas usan `saldo_por_cobrar()`, que solo descuenta notas en la misma moneda de la venta.
- **PDF con Helvetica.** Esta fuente no incluye el signo menos «−» (U+2212): en el PDF se imprime como «-».

## Código

| Archivo | Cambio |
|---|---|
| `ventas/services/reportes_export.py` (nuevo) | `datos_reporte_ventas`, `datos_reporte_conciliacion`, generadores `reporte_*_xlsx` y `reporte_*_pdf` |
| `ventas/views.py` | `leer_filtros_balances`, `q_ventas_balances`, `describir_filtros_balances`, `exportar_balances_xlsx` (reescrita) y `exportar_balances_pdf` |
| `ventas/admin.py` | Rutas de descarga; `conciliacion_view` se separa en `_conciliacion_filtrada`, `conciliacion_excel_view` y `conciliacion_pdf_view` |
| `ventas/urls.py` | Ruta `balances/export/pdf/` |
| `templates/admin/ventas/partials/ventas_balances_results.html` | Botones de reporte |
| `templates/admin/ventas/conciliacion.html` | Botones Excel y PDF |
| `static/css/ventas-balances.css`, `static/css/conciliacion.css` | Estilos de los botones |
| `static/js/balance-tours.js` | Texto del paso «Exporte el análisis» de la guía |

## Pruebas

`ventas/tests.py::ReportesExportTest` (9 pruebas): KPIs por moneda sin mezclar divisas, antigüedad con saldo neto de notas de crédito, ventas sin CFDI y días de cobro, Pareto ABC y tendencia, Excel que respeta filtros, PDF válido, enlaces con filtros actuales, conciliación del reporte contra `conciliacion_cliente` y descargas de conciliación.

Ejecución: `pytest ventas/ app/tests/test_integration.py app/tests/test_security.py` → 243 passed, 3 skipped.

## Limitaciones

- El PDF de ventas lista como máximo 300 ventas; el Excel trae todas.
- Los reportes se calculan al momento de la descarga; el de conciliación aprovecha el caché de `conciliacion_global`.
- El PDF no se revisó visualmente en esta sesión (solo se validó su texto); conviene abrir un ejemplo antes de distribuirlo.
