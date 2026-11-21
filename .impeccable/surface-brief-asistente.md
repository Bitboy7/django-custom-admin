# Asistente MCP — /asistente/

## Scope

Dedicated Operate surface inside the established ERP. A read-only MCP chat client for ventas,
cartera, gastos, compras and saldos. Spanish (es-MX), staff/2FA only. Answers combine narrative,
compact data tables and an auditable tool trace. No write actions.

## Direction contract

**THESIS.** Cada pregunta es un asunto: historial y consultas sugeridas a la izquierda, la
conversación al centro, los datos citados y la traza MCP a la derecha. Rechaza el chatbot de
burbujas sueltas y el dashboard de tarjetas idénticas.

**OWN-WORLD.** Marco charcoal-blue #2f4550, suelo ghost-white #f4f4f9, superficies blancas,
marca del asistente light-blue #b8dbd9, alertas en harvest #f2a51a. Inter con cifras tabulares,
bordes de 1px, radios 8–12px, sombras suaves con offset. Iconos SVG de trazo consistente, nunca glifos.

**STORY.** El usuario pregunta en lenguaje natural, entiende la respuesta en segundos, verifica
cada cifra en una tabla y confía porque ve qué herramienta de solo lectura la produjo.

**FIRST VIEWPORT.** Dentro del admin: barra superior con "Asistente de datos", sello Solo lectura,
modelo y acción Nueva consulta. Tres paneles a altura completa: consultas sugeridas (izquierda),
hilo activo con compositor fijo (centro), Datos citados con tabla y traza (derecha).
En tablet el panel izquierdo se vuelve cajón; en móvil el hilo ocupa todo y los datos se abren como hoja.

**FORM.** Composición de bandeja de consultas (correo de oficina); posición 1 de la tirada;
seed key `e82484ae49442acfc56c9ddf5eb59a7b`.

**FINISH.** unreviewed and undocumented is unfinished; this build ends with the finish review,
the verdict, DESIGN.md, and every shipping raster carrying its provenance.
