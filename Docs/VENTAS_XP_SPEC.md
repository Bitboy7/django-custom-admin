# Especificacion Tecnica y Funcional XP del Modulo de Ventas

## 1. Vision del sistema

El Modulo de Ventas es el sistema nervioso comercial de la operacion. Su responsabilidad es registrar transacciones, proteger el flujo de caja, controlar riesgo crediticio y ofrecer visibilidad inmediata del estado de cartera para que las areas comercial, financiera y administrativa trabajen sobre la misma fuente de verdad.

## 2. Requisitos del sistema

### 2.1 Requisitos funcionales

#### RF-01 Gestion de clientes comerciales

El sistema debe permitir registrar clientes con datos de contacto, pais, mercado destino, tipo de cliente, limite de credito, termino de credito predeterminado y calificacion crediticia para soportar decisiones comerciales y financieras.

#### RF-02 Registro de ventas operativas

El sistema debe permitir registrar ventas nacionales o de exportacion con producto, cantidad, monto, sucursal, cuenta, agente, tipo de registro, modalidad de pago, moneda e Incoterm para asegurar trazabilidad completa de la transaccion.

#### RF-03 Calculo automatico de vencimientos

El sistema debe calcular automaticamente la fecha de vencimiento de una venta a credito usando `fecha_deposito + dias_credito` para reducir errores manuales y homogeneizar las reglas de cobranza.

#### RF-04 Control de credito en tiempo real

El sistema debe calcular el credito disponible del cliente con base en saldos pendientes y advertir o bloquear operaciones que excedan el limite definido para minimizar exposicion financiera.

#### RF-05 Gestion de pagos y abonos

El sistema debe registrar pagos parciales o totales por venta, con metodo, referencia y cuenta destino, actualizando automaticamente el monto pagado y el estado de cobranza.

#### RF-06 Gestion de anticipos

El sistema debe permitir registrar anticipos de clientes y controlar su estado para facilitar su aplicacion posterior a ventas pendientes.

#### RF-07 Seguimiento de cobranza

El sistema debe clasificar cada venta en estados `Pagado`, `Pendiente`, `Parcial`, `Vencido` o `Incobrable` para soportar gestion operativa y priorizacion de cobranza.

#### RF-08 Saldos por cobrar sincronizados

El sistema debe mantener un registro sincronizado de `SaldoCliente` por cada venta a credito para garantizar consulta rapida y consistencia entre ventas, pagos y reportes.

#### RF-09 Analitica de cartera

El sistema debe generar analisis de antiguedad de saldos, DSO, distribucion por estado de cobranza y clientes con mayor exposicion para fortalecer la toma de decisiones financieras.

#### RF-10 Reportes operativos y ejecutivos

El sistema debe ofrecer balances filtrables, reporte global de cobranza, dashboard de ventas y reportes detallados por cliente para monitoreo diario y seguimiento gerencial.

#### RF-11 Exportacion operativa

El sistema debe exportar balances y reportes relevantes a Excel para habilitar uso operativo, conciliacion y presentacion ejecutiva sin reprocesamiento manual.

#### RF-12 Parametrizacion de negocio

El sistema debe permitir administrar terminos de credito y mercados de destino sin cambios de codigo para adaptarse rapidamente a nuevas condiciones comerciales.

### 2.2 Requisitos no funcionales

#### RNF-01 Seguridad

- Todas las vistas funcionales del modulo deben requerir autenticacion.
- Las acciones deben respetar permisos de Django por recurso y operacion.
- Los endpoints JSON internos del admin deben quedar protegidos por `admin_view`.
- Las operaciones relevantes de cobranza y cambios de estado deben ser auditables.

#### RNF-02 Escalabilidad

- El modulo debe soportar crecimiento en clientes, ventas, pagos y snapshots de aging sin degradacion severa.
- La consulta operativa debe apoyarse en indices por `cliente`, `estado_cobranza`, `fecha_vencimiento` y combinaciones de filtros frecuentes.
- Los calculos ejecutivos costosos deben poder cachearse o preagregarse por servicio.

#### RNF-03 Concurrencia

- Los pagos concurrentes no deben dejar estados inconsistentes en `Ventas` ni en `SaldoCliente`.
- Las operaciones que actualizan montos y saldos deben diseñarse para ser idempotentes o transaccionales.
- Los reportes deben tolerar lectura concurrente sin bloquear la operacion de captura.

#### RNF-04 Rendimiento

- Consultas interactivas de dashboard y balances deben responder idealmente en menos de 2 segundos con volumen operativo normal.
- Exportaciones de reporte deben iniciar en menos de 5 segundos para filtros comunes.
- Endpoints JSON de apoyo al formulario deben responder en menos de 300 ms en condiciones nominales.

#### RNF-05 Disponibilidad y resiliencia

- El modulo debe degradarse de forma controlada ante fallos de cache o servicios auxiliares.
- La generacion de reportes no debe comprometer la captura de ventas y pagos.

#### RNF-06 Mantenibilidad

- La logica de negocio critica debe estar respaldada por pruebas automatizadas.
- Los cambios funcionales deben partir de historias de usuario pequenas y trazables.
- La documentacion debe evolucionar junto con el comportamiento observable del sistema.

## 3. Artefactos XP

### 3.1 Metafora del sistema

El sistema funciona como una linea de embarque con control financiero integrado:

- `Cliente` es la cuenta comercial autorizada para comprar.
- `Ventas` es la orden embarcada que genera ingreso esperado.
- `PagoVenta` es el abono que descarga deuda real.
- `SaldoCliente` es el tablero vivo de lo que aun esta pendiente.
- `AntiguedadSaldo` es la fotografia periodica del riesgo acumulado.

La metafora ayuda a entender una regla central: cada venta a credito crea una deuda viva, cada pago la reduce, y cada reporte solo debe leer la misma verdad financiera.

### 3.2 Historias de usuario y criterios de aceptacion

Las historias se redactan para ser pequenas, negociables, valiosas, estimables, verificables e independientes en la mayor medida posible.

#### US-01 Registrar venta a contado

Como ejecutivo comercial, quiero registrar una venta de contado, para dejar cerrada la operacion sin deuda pendiente.

Criterios de aceptacion:

- Dado un cliente activo, cuando registro una venta con modalidad `Contado`, entonces la venta queda guardada con estado de cobranza `Pagado`.
- Dado un monto valido, cuando la venta se guarda, entonces `monto_pagado` debe igualar al monto total.
- Dado que la venta es de contado, cuando consulto balances y reportes, entonces no debe generar saldo por cobrar.

#### US-02 Registrar venta a credito

Como responsable de ventas, quiero registrar una venta a credito, para formalizar una operacion cuya cobranza ocurrira despues.

Criterios de aceptacion:

- Dado un cliente con termino de credito valido, cuando registro la venta a credito, entonces se calcula `fecha_vencimiento` automaticamente.
- Dado que la venta es nueva y aun no tiene pagos, cuando se guarda, entonces su estado inicial es `Pendiente`.
- Dado que la venta es a credito, cuando se persiste correctamente, entonces debe existir un saldo por cobrar sincronizable con la venta.

#### US-03 Validar limite de credito

Como analista financiero, quiero validar el credito disponible del cliente antes de autorizar una venta, para evitar sobreexposicion.

Criterios de aceptacion:

- Dado un cliente con ventas pendientes, cuando consulto su credito disponible, entonces el sistema descuenta el saldo vigente de su limite.
- Dado un monto superior al credito disponible, cuando intento aprobar la venta, entonces el sistema debe advertir o bloquear la operacion segun politica.
- Dado un cliente de contado, cuando consulto credito disponible, entonces el resultado es cero.

#### US-04 Registrar pago parcial

Como auxiliar de cobranza, quiero registrar un pago parcial, para reflejar el avance real de recuperacion.

Criterios de aceptacion:

- Dado una venta a credito pendiente, cuando registro un abono menor al saldo, entonces `monto_pagado` aumenta y el estado cambia a `Parcial` o `Vencido` segun fecha.
- Dado un pago parcial, cuando consulto la venta y el saldo asociado, entonces ambos muestran el mismo saldo pendiente.
- Dado un pago con referencia y cuenta destino, cuando se guarda, entonces el sistema conserva la trazabilidad del movimiento.

#### US-05 Liquidar venta con pago total

Como auxiliar de cuentas por cobrar, quiero registrar el pago final de una venta, para cerrarla financieramente.

Criterios de aceptacion:

- Dado una venta con saldo pendiente, cuando la suma de pagos alcanza el total, entonces el estado cambia a `Pagado`.
- Dado una venta liquidada, cuando consulto su saldo, entonces el saldo pendiente es cero o menor por tolerancia de redondeo.
- Dado el cierre de la venta, cuando reviso el dashboard o reporte, entonces deja de contarse como cartera abierta.

#### US-06 Consultar reporte global de cobranza

Como gerente financiero, quiero consultar el reporte global de cobranza, para priorizar seguimiento y riesgo.

Criterios de aceptacion:

- Dado un periodo y filtros operativos, cuando genero el reporte, entonces veo totales, distribucion por estado y detalle por cliente o venta segun contexto.
- Dado ventas vencidas, cuando consulto el reporte, entonces estas se identifican claramente.
- Dado un segundo acceso con los mismos filtros, cuando existe cache valida, entonces la respuesta no debe degradarse.

#### US-07 Exportar balances

Como responsable administrativo, quiero exportar balances filtrados a Excel, para conciliacion y analisis fuera del sistema.

Criterios de aceptacion:

- Dado un conjunto de filtros validos, cuando ejecuto la exportacion, entonces el archivo contiene los registros visibles del analisis.
- Dado una exportacion exitosa, cuando abro el archivo, entonces existen columnas de cliente, cuenta, fecha, totales, saldo y estado.
- Dado que no hay registros, cuando exporto, entonces el archivo se genera sin corromper el flujo del usuario.

#### US-08 Consultar datos auxiliares desde el admin

Como usuario del admin, quiero autocompletar datos de cliente y termino de credito, para capturar ventas mas rapido y con menos errores.

Criterios de aceptacion:

- Dado un cliente valido, cuando consulto `api/cliente-info/<id>/`, entonces recibo pais, mercado sugerido y termino de credito predeterminado.
- Dado un termino de credito valido, cuando consulto `api/termino-credito-info/<id>/`, entonces recibo `dias_credito`.
- Dado un identificador inexistente, cuando consulto cualquiera de los endpoints, entonces recibo `404` con payload de error.

### 3.3 Release planning

#### Iteracion 1. Fundacion transaccional

- Registro de clientes con perfil comercial y crediticio.
- Registro de ventas contado y credito.
- Calculo de vencimientos y estado inicial.
- Suite base de pruebas unitarias para modelos `Cliente` y `Ventas`.

Objetivo de negocio: poder capturar operaciones con reglas minimas confiables.

#### Iteracion 2. Cobranza y consistencia financiera

- Registro de `PagoVenta`.
- Sincronizacion de `SaldoCliente`.
- Reglas de transicion de estados `Pendiente`, `Parcial`, `Pagado`, `Vencido`.
- Pruebas de aceptacion para pagos parciales y totales.

Objetivo de negocio: tener verdad financiera actualizada por cada abono.

#### Iteracion 3. Visibilidad ejecutiva

- Dashboard de ventas.
- Reporte global de cobranza.
- Balances filtrables y exportacion a Excel.
- Caching de consultas pesadas.

Objetivo de negocio: habilitar seguimiento gerencial y operativo diario.

#### Iteracion 4. Riesgo y evolucion operacional

- Aging historico y clasificacion de riesgo.
- Reglas de alertas y automatizacion de cobranza.
- Endurecimiento de seguridad, permisos y auditoria.
- Preparacion de contratos API mas formales.

Objetivo de negocio: escalar el modulo sin perder control de riesgo ni calidad.

## 4. Documentacion de API

La superficie actual del modulo no es un servicio REST puro; combina vistas renderizadas y endpoints JSON internos para el admin. A continuacion se documentan los contratos principales observables.

### 4.1 Vistas autenticadas del modulo

#### GET /en/ventas/balances/

Descripcion: muestra balances de ventas con filtros por cliente, cuenta, sucursal, mercado, modalidad, estado y periodo.

Parametros principales:

- `cliente_id`
- `cuenta_id`
- `sucursal_id`
- `mercado_id`
- `modalidad_pago`
- `estado_cobranza`
- `year`
- `months`
- `periodo=diario|semanal|mensual`

Ejemplo:

```http
GET /en/ventas/balances/?year=2026&periodo=mensual&modalidad_pago=Credito
```

Respuesta: HTML renderizado con tabla de balances, graficas y metricas agregadas.

#### GET /en/ventas/balances/export/

Descripcion: exporta el resultado filtrado actual a un archivo XLSX.

Ejemplo:

```http
GET /en/ventas/balances/export/?year=2026&mercado_id=2
```

Respuesta:

```http
200 OK
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
```

#### GET /en/ventas/reporte-cobranza/

Descripcion: genera el reporte global de cobranza con soporte para filtros operativos.

Ejemplo:

```http
GET /en/ventas/reporte-cobranza/?sucursal_id=1
```

Respuesta: HTML renderizado con KPIs, resumen de cobranza y detalle analitico.

### 4.2 Endpoints JSON internos del admin

#### GET /admin/ventas/ventas/api/cliente-info/{id}/

Descripcion: entrega datos auxiliares para autocompletar el formulario administrativo de ventas.

Request:

```http
GET /admin/ventas/ventas/api/cliente-info/15/
```

Response 200:

```json
{
  "es_extranjero": true,
  "pais_nombre": "Estados Unidos",
  "mercado_destino_id": 2,
  "termino_credito_id": 3
}
```

Response 404:

```json
{
  "error": "Not found"
}
```

#### GET /admin/ventas/ventas/api/termino-credito-info/{id}/

Descripcion: retorna `dias_credito` para calcular fecha de vencimiento desde la UI administrativa.

Request:

```http
GET /admin/ventas/ventas/api/termino-credito-info/3/
```

Response 200:

```json
{
  "dias_credito": 30
}
```

Response 404:

```json
{
  "error": "Not found"
}
```

### 4.3 Evolucion recomendada del contrato

Si el modulo evoluciona hacia API de servicio, la siguiente base REST es la recomendada:

- `GET /api/ventas/`
- `POST /api/ventas/`
- `GET /api/ventas/{id}/`
- `PUT /api/ventas/{id}/`
- `DELETE /api/ventas/{id}/`
- `POST /api/ventas/{id}/pagos/`
- `GET /api/clientes/{id}/credito-disponible/`
- `GET /api/reportes/cobranza/`

Ejemplo de request propuesto para crear venta:

```json
{
  "cliente_id": 15,
  "producto_id": 8,
  "sucursal_id": 2,
  "agente_id": 4,
  "tipo_venta": "Exportacion",
  "modalidad_pago": "Credito",
  "termino_credito_id": 3,
  "monto": "245000.00",
  "moneda_venta": "USD",
  "fecha_deposito": "2026-04-10"
}
```

Ejemplo de response propuesta:

```json
{
  "id": 802,
  "estado_cobranza": "Pendiente",
  "fecha_vencimiento": "2026-05-10",
  "saldo_pendiente": "245000.00",
  "moneda": "USD"
}
```

## 5. Plan de pruebas unitarias y de aceptacion

### 5.1 Enfoque TDD

Primero se escriben pruebas de dominio para las reglas que cambian dinero, fechas o estados:

- `Cliente.credito_disponible()`
- `Cliente.puede_otorgar_credito()`
- `Ventas.save()` para contado y credito
- `Ventas.actualizar_estado_cobranza()`
- `Ventas.calcular_interes_mora()`
- `SaldoCliente.categoria_antiguedad()`

Secuencia recomendada:

1. Escribir prueba fallando para la regla critica.
2. Implementar la minima solucion correcta.
3. Refactorizar manteniendo cobertura.

### 5.2 Enfoque BDD

Escenarios de aceptacion prioritarios:

- Registrar venta a contado y verificar cierre inmediato.
- Registrar venta a credito y verificar deuda inicial.
- Registrar pago parcial y verificar saldo sincronizado.
- Registrar pago final y verificar cierre de cobranza.
- Consultar balances con filtros y exportar Excel.
- Consultar reporte global de cobranza bajo distintos filtros.
- Consultar endpoints JSON del admin con casos felices y 404.

### 5.3 Matriz minima de pruebas

- Unitarias: reglas de negocio puras y calculos monetarios.
- Integracion: modelos con persistencia, servicios y sincronizacion de saldos.
- Funcionales: vistas autenticadas, filtros y exportaciones.
- Seguridad: autenticacion, permisos y acceso restringido a endpoints internos.
- Regresion: estados de cobranza, indices criticos y consistencia de reportes.

## 6. Pair programming sugerido

### PP-01 Dominio financiero

Componentes: `Ventas`, `PagoVenta`, `SaldoCliente`.

Motivo: concentran reglas con impacto directo en dinero, estados y auditoria.

### PP-02 Reporte global de cobranza

Componentes: `ventas/services/reporte_cobranza_service.py`, vistas y templates asociados.

Motivo: mezcla agregacion, filtros, performance y lectura ejecutiva del negocio.

### PP-03 Dashboard y metricas ejecutivas

Componentes: `ventas/services/metrics_service.py` y vistas de dashboard.

Motivo: riesgo alto de consultas costosas, duplicacion de reglas y regresiones de KPI.

### PP-04 Seguridad y contratos internos

Componentes: vistas autenticadas, endpoints JSON del admin, permisos y auditoria.

Motivo: cualquier omision aqui expone datos sensibles o genera flujos sin control.

## 7. README y estandar de contribucion para GitHub

La estructura recomendada del paquete documental del modulo queda asi:

- `ventas/README.md`: entrada rapida para desarrolladores.
- `Docs/VENTAS_XP_SPEC.md`: especificacion funcional y tecnica alineada con XP.
- `.github/PULL_REQUEST_TEMPLATE.md`: control de calidad y trazabilidad del cambio.
- `.github/ISSUE_TEMPLATE/*`: captura estandar de bugs, features e historias.

## 8. Definicion de hecho para historias del modulo

Una historia del Modulo de Ventas se considera terminada cuando:

- Existe una historia de usuario clara con criterios de aceptacion verificables.
- La implementacion incluye pruebas automatizadas relevantes.
- La seguridad y permisos se mantienen o mejoran.
- La documentacion observable del comportamiento fue actualizada.
- El cambio fue revisado mediante pair programming o code review segun criticidad.
