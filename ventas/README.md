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
