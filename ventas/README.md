# Modulo de Ventas

## Descripcion

El modulo `ventas` gestiona el ciclo comercial completo desde la captura de la transaccion hasta la cobranza, el seguimiento del credito y la generacion de reportes operativos. Esta implementacion esta construida sobre Django Admin y servicios de dominio que soportan ventas nacionales y de exportacion, operaciones de contado y credito, pagos parciales, anticipos y analitica de cartera.

El objetivo del modulo es maximizar visibilidad operativa, reducir riesgo crediticio y acelerar la toma de decisiones con datos consistentes en tiempo real.

## Valor de negocio

- Centraliza ventas, pagos, anticipos y saldos por cobrar en un solo flujo operativo.
- Reduce errores manuales al automatizar fechas de vencimiento, estados de cobranza y sincronizacion de saldos.
- Mejora control financiero con limites de credito, aging y reportes ejecutivos.
- Soporta crecimiento comercial con mercados, monedas e Incoterms configurables.

## Capacidades principales

- Gestion de clientes con limite de credito, terminos predeterminados y calificacion crediticia.
- Registro de ventas contado y credito con calculo automatico de fecha de vencimiento.
- Seguimiento de pagos parciales y actualizacion automatica del estado de cobranza.
- Gestion de anticipos aplicables a ventas pendientes.
- Reporte global de cobranza, balances filtrables y dashboard ejecutivo.
- Exportacion a Excel y vistas analiticas integradas en Django Admin.
- Endpoints JSON internos para autocompletado de formularios administrativos.

## Stack tecnologico

- Python 3.12+
- Django 5.x
- MySQL 8
- Django Admin con Jazzmin/AdminLTE
- `django-money` para montos monetarios
- `django-import-export` para carga y exportacion operativa
- Chart.js y DataTables para visualizacion y exploracion de reportes

## Modelo funcional

Las entidades principales del modulo son:

- `Cliente`: define capacidad crediticia, mercado y perfil de riesgo.
- `Ventas`: representa la transaccion comercial y su estado de cobranza.
- `PagoVenta`: registra abonos y dispara la sincronizacion del saldo real.
- `Anticipo`: administra montos adelantados del cliente.
- `SaldoCliente`: mantiene la deuda viva por venta.
- `AntiguedadSaldo`: captura snapshots de aging para analisis historico.
- `TerminoCredito` y `MercadoDestino`: parametrizan reglas del negocio.

## Instalacion rapida

### Requisitos

- Python 3.12 o superior
- MySQL 8 o superior
- Node.js 16+ para assets del frontend
- Entorno virtual configurado

### Pasos

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm install
py manage.py migrate
py manage.py createsuperuser
py manage.py runserver
```

Acceso por defecto:

- Admin: `http://localhost:8000/admin`
- Vistas del modulo: `http://localhost:8000/en/ventas/`

## Superficie funcional actual

### Vistas autenticadas

- `GET /en/ventas/anticipos/`
- `GET|POST /en/ventas/anticipos/crear/`
- `GET /en/ventas/balances/`
- `GET /en/ventas/balances/export/`
- `GET /en/ventas/reporte-cobranza/`

### Vistas administrativas especializadas

- `GET /admin/ventas/ventas/dashboard-ventas/`
- `GET /admin/ventas/ventas/balances/`
- `GET /admin/ventas/ventas/balances/export/`
- `GET /admin/ventas/ventas/reporte-cobranza/`
- `GET /admin/ventas/ventas/reporte-cliente/<id>/`
- `GET /admin/ventas/ventas/api/cliente-info/<id>/`
- `GET /admin/ventas/ventas/api/termino-credito-info/<id>/`

## Conciliacion de CFDI por cliente

Vista: `/es/admin/ventas/cliente/conciliacion/` — servicio
`ventas/services/conciliacion_service.py`.

Cruza el ledger fiscal (`DocumentoCFDI`, solo documentos **vigentes**) contra los
registros operativos (`Ventas`, `PagoVenta`, `Anticipo`) y produce, por cliente,
un desglose por moneda y un saldo conciliado. `fecha_inicio`/`fecha_fin` filtran
por fecha de emision (CFDI), fecha de pago (`PagoVenta`) y fecha del anticipo.

### Formula del saldo conciliado

Por cada moneda:

```
saldo = facturado + notas_cargo - notas_credito
        - recibos_pago - cobros_contado - anticipos_disponibles
```

| Columna | Fuente | Origen del dato |
| --- | --- | --- |
| **Facturado** | `detalle['facturado']` | Suma de `DocumentoCFDI` vigentes subtipo `venta_nacional`, `venta_exportacion`, `ingreso_servicio`, por moneda. |
| **+ Notas de cargo** | `detalle['notas_cargo']` | `DocumentoCFDI` vigentes subtipo `nota_cargo`. |
| **− Notas de credito** | `detalle['notas_credito']` | `DocumentoCFDI` vigentes subtipo `nota_credito`. |
| **− Pagos (REP)** | `detalle['recibos_pago']` | `DocumentoCFDI` vigentes subtipo `recibo_pago` (monto completo del comprobante, en su moneda). |
| **− Cobros de contado** | `detalle['cobros_contado']` | `cobros_no_rep()`: pagos (`PagoVenta`) sin REP asociado + ventas de contado (PUE) sin pago registrado. |
| **− Anticipos** | `detalle['anticipos_disponibles']` | `Anticipo.saldo_disponible()` (monto − aplicado), excluyendo cancelados. |
| **Cobrado en pesos (equiv.)** | `pagos_mxn` | `pagos_total_mxn()` — **no es un dato del CFDI**. |
| **Sin vincular** | `documentos_sin_venta` | `DocumentoCFDI` sin `venta` cuyo subtipo no es de ingreso/remanente; desglose interactivo. |

### De donde sale «Cobrado en pesos (equiv.)»

`pagos_total_mxn()` (no participa en la formula del saldo; es un dato operativo):

```
pagos_mxn = Σ PagoVenta.monto_pago_mxn        # pagos registrados, convertidos a MXN con tipo_cambio
          + Σ (Venta.monto_pagado × Venta.tipo_cambio)   # ventas de contado sin PagoVenta
```

- `PagoVenta.monto_pago_mxn` = `monto_pago.amount × tipo_cambio` (o el monto si es MXN).
- En `PagoVenta`, `tipo_cambio` = MXN por 1 unidad de la moneda del pago; en pesos es `1.0000`.
- Un mismo total en **MXN** no es comparable directo con «Pagos (REP)», que se
  agrupa **por moneda**. Por eso una fila de exportacion (p. ej. USD) muestra en
  «Cobrado en pesos» su equivalente cambiario, y no un importe que exista en el
  CFDI.

### Por que «Pagos (REP)» y «Cobrado en pesos» pueden no coincidir

Son dos fuentes distintas: el primero es fiscal (comprobantes), el segundo es
operativo (pagos capturados). Divergen cuando:

1. Un REP fue importado **sin `PagoVenta`** asociado (importacion legacy, o venta
   que ya no estaba en `Pendiente/Parcial/Vencido`), o
2. El `PagoVenta` quedo **topado al saldo** de la venta al importar el REP
   (`monto_pago = min(monto_rep, saldo)`, en `cfdi_import_service._crear_recibo_pago`).

La diferencia es, intencionalmente, un indicador de deriva entre lo fiscal y lo
operativo.

### Pruebas

`ventas/tests.py`:

- `ConciliacionCFDITest` — formula base del saldo.
- `CobradoMxnOrigenTest` — origen de «Cobrado en pesos» y divergencias con REP
  (casos World Produce y Sergio Ramon).
- `CFDIImportServiceTest.test_recibo_pago_usd_conserva_tipo_cambio_del_complemento`
  — un REP en USD conserva `TipoCambioP` al crear su `PagoVenta`.

## Documentacion complementaria

- Especificacion XP: [Docs/VENTAS_XP_SPEC.md](../Docs/VENTAS_XP_SPEC.md)
- Guia de implementacion previa: [Docs/VENTAS_IMPLEMENTATION_GUIDE.md](../Docs/VENTAS_IMPLEMENTATION_GUIDE.md)
- Arquitectura previa: [Docs/VENTAS_MODULE_ARCHITECTURE.md](../Docs/VENTAS_MODULE_ARCHITECTURE.md)

## Pruebas

Ejecucion recomendada del modulo:

```powershell
.\venv\Scripts\Activate.ps1
py manage.py test ventas.tests ventas.tests_integration --verbosity=2
```

Enfoque de calidad:

- TDD para reglas de credito, cobranza y calculos monetarios.
- BDD para flujos end-to-end de venta, pago, anticipo y reporteo.
- Pruebas de regresion sobre filtros, exportaciones y permisos.

## Guia de contribucion

1. Crea una rama por historia de usuario o bug.
2. Mantiene cambios pequenos, trazables y con pruebas.
3. Aplica TDD en reglas de dominio antes de modificar vistas o admin.
4. Vincula cada cambio con una historia de usuario o issue.
5. Usa las plantillas en `.github` para PRs e incidencias.

## Alineacion con XP

- Historias de usuario pequenas y priorizadas por valor.
- Integracion continua con pruebas automatizadas.
- Refactorizacion segura sobre una suite de pruebas.
- Pair programming en componentes de alto riesgo.
- Release planning incremental por iteraciones cortas.

## Estado

El modulo es funcional y productivo, pero su arquitectura actual combina vistas renderizadas, logica administrativa y endpoints JSON internos. La recomendacion de evolucion es mantener compatibilidad operativa mientras se separan progresivamente las reglas de dominio y los contratos API en servicios mas explicitos.
