# DataTables Utils - Documentación

## Descripción

Este documento describe cómo usar las utilidades modulares de DataTables para crear páginas con tablas exportables en diferentes módulos (gastos, compras, ventas, etc.).

## Estructura de Archivos

```
static/js/
├── datatables-utils.js          # Utilidades reutilizables
├── balances-datatables.js       # Configuración específica de gastos
├── compras-datatables.js        # (Futuro) Configuración de compras
└── ventas-datatables.js         # (Futuro) Configuración de ventas
```

## Uso Básico

### 1. Incluir las utilidades en tu HTML

```html
<!-- Primero incluir las utilidades -->
<script src="{% static 'js/datatables-utils.js' %}"></script>

<!-- Luego el script específico del módulo -->
<script src="{% static 'js/balances-datatables.js' %}"></script>
```

### 2. Crear un nuevo módulo de DataTables

Para crear un nuevo módulo (por ejemplo, para compras):

```javascript
// compras-datatables.js
$(document).ready(function () {
  // Configuración del título del reporte
  var reportConfig = {
    moduleName: "Reporte de Compras",
    filterFields: ["proveedor_id", "sucursal_id", "year", "month", "periodo"],
  };

  var table = $("#compras-datatable").DataTable({
    // Configuración de DataTable...
    buttons: [
      {
        extend: "csv",
        text: '<i class="fas fa-file-csv mr-1"></i> CSV',
        action: function (e, dt, button, config) {
          // Obtener datos de la tabla
          var headers = ["Proveedor", "Factura", "Total"];
          var data = [];

          dt.rows().every(function () {
            var rowData = this.data();
            data.push([
              rowData.proveedor,
              rowData.factura,
              getNumericValueFromNode(rowData.total),
            ]);
          });

          // Exportar usando la utilidad
          exportToCSV({
            filename: "compras",
            headers: headers,
            data: data,
          });
        },
      },
      {
        extend: "pdf",
        text: '<i class="fas fa-file-pdf mr-1"></i> PDF',
        title: "",
        customize: function (doc) {
          // Generar título dinámico
          var reportTitle = generateReportTitle(reportConfig);

          // Configurar documento con utilidades
          configurePdfDocument(doc, {
            reportTitle: reportTitle,
            systemName: "Sistema de Gestión de Compras",
            orientation: "landscape",
            pageMargins: [40, 80, 40, 60],
          });
        },
      },
    ],
  });
});
```

## Funciones Disponibles

### Extracción y Formateo de Datos

#### `getCleanTextFromHTML(htmlContent)`

Extrae texto limpio de contenido HTML.

```javascript
var cleanText = getCleanTextFromHTML("<span>$1,234.56</span>");
// Resultado: "$1,234.56"
```

#### `getNumericValueFromNode(node)`

Obtiene un valor numérico desde un nodo del DOM.

```javascript
var td = document.querySelector("td.amount");
var value = getNumericValueFromNode(td);
// Resultado: 1234.56
```

#### `formatNumericValue(value, decimals, decimalSep, thousandsSep)`

Formatea un valor numérico.

```javascript
var formatted = formatNumericValue(1234.56, 2, ".", ",");
// Resultado: "1,234.56"
```

### Fecha y Hora

#### `getCurrentDateFormatted(format)`

Obtiene la fecha actual en diferentes formatos.

```javascript
getCurrentDateFormatted("datetime"); // "10/10/2025 15:30"
getCurrentDateFormatted("date"); // "10/10/2025"
getCurrentDateFormatted("time"); // "15:30"
getCurrentDateFormatted("filename"); // "2025-10-10-15-30-45"
```

#### `getMonthName(monthIndex, lang)`

Obtiene el nombre del mes.

```javascript
getMonthName(9, "es"); // "Septiembre"
getMonthName(9, "en"); // "September"
```

### Generación de Títulos

#### `generateReportTitle(config)`

Genera títulos dinámicos basados en filtros de URL.

```javascript
var config = {
  moduleName: "Reporte de Gastos",
  filterFields: ["cuenta_id", "sucursal_id", "year", "month"],
};

var title = generateReportTitle(config);
// Resultado: "Reporte de Gastos - Año: 2024 | Mes: Septiembre | Sucursal: Centro"
```

### Configuración de PDF

#### `configurePdfDocument(doc, options)`

Configura un documento PDF con estilos estándar.

```javascript
customize: function (doc) {
  configurePdfDocument(doc, {
    reportTitle: "Mi Reporte",
    systemName: "Mi Sistema",
    orientation: "landscape",  // o "portrait"
    pageMargins: [40, 80, 40, 60]
  });
}
```

#### `createPdfHeader(reportTitle, currentDate)`

Crea un encabezado personalizado.

```javascript
doc.header = createPdfHeader("Mi Reporte", "10/10/2025 15:30");
```

#### `createPdfFooter(systemName)`

Crea un pie de página personalizado.

```javascript
doc.footer = createPdfFooter("Sistema de Gestión");
```

#### `getPdfStyles()`

Obtiene los estilos estándar para PDFs.

```javascript
doc.styles = getPdfStyles();
```

### Exportación CSV

#### `exportToCSV(config)`

Genera y descarga un archivo CSV.

```javascript
exportToCSV({
  filename: "mi-reporte",
  headers: ["Columna 1", "Columna 2", "Total"],
  data: [
    ["Valor 1", "Valor 2", 100.5],
    ["Valor 3", "Valor 4", 200.75],
  ],
  separator: ",", // Opcional, por defecto es ','
});
```

## Filtros Soportados

Los filtros que se pueden usar en `generateReportTitle`:

- `cuenta_id`: Cuenta bancaria
- `sucursal_id`: Sucursal
- `proveedor_id`: Proveedor
- `cliente_id`: Cliente
- `year`: Año
- `month`: Mes (se convierte automáticamente a nombre)
- `periodo`: Período (diario, semanal, mensual)

## Ejemplo Completo: Módulo de Ventas

```javascript
// ventas-datatables.js
$(document).ready(function () {
  var reportConfig = {
    moduleName: "Reporte de Ventas",
    filterFields: ["cliente_id", "sucursal_id", "year", "month"],
  };

  var table = $("#ventas-datatable").DataTable({
    language: {
      url: "//cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json",
    },
    responsive: true,
    dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6 text-right"B>>rtip',
    buttons: [
      {
        extend: "csv",
        className: "dt-button btn-csv",
        text: '<i class="fas fa-file-csv mr-1"></i> CSV',
        action: function (e, dt, button, config) {
          var rows = dt.rows({ search: "applied" }).nodes();
          var headers = ["Cliente", "Factura", "Fecha", "Total"];
          var data = [];

          $(rows).each(function () {
            var tds = $(this).find("td");
            data.push([
              getCleanTextFromHTML(tds.eq(0).html()),
              getCleanTextFromHTML(tds.eq(1).html()),
              getCleanTextFromHTML(tds.eq(2).html()),
              getNumericValueFromNode(tds[3]),
            ]);
          });

          exportToCSV({
            filename: "ventas",
            headers: headers,
            data: data,
          });
        },
      },
      {
        extend: "excel",
        className: "dt-button btn-excel",
        text: '<i class="fas fa-file-excel mr-1"></i> Excel',
      },
      {
        extend: "pdf",
        className: "dt-button btn-pdf",
        text: '<i class="fas fa-file-pdf mr-1"></i> PDF',
        title: "",
        customize: function (doc) {
          var reportTitle = generateReportTitle(reportConfig);

          configurePdfDocument(doc, {
            reportTitle: reportTitle,
            systemName: "Sistema de Gestión de Ventas",
            orientation: "landscape",
          });
        },
      },
      {
        extend: "print",
        className: "dt-button btn-print",
        text: '<i class="fas fa-print mr-1"></i> Imprimir',
      },
    ],
  });
});
```

## Plantilla HTML

```html
{% load static %}

<!-- CSS de DataTables -->
<link
  rel="stylesheet"
  href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap4.min.css"
/>
<link
  rel="stylesheet"
  href="https://cdn.datatables.net/buttons/2.4.1/css/buttons.bootstrap4.min.css"
/>

<!-- Scripts de DataTables -->
<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap4.min.js"></script>
<script src="https://cdn.datatables.net/buttons/2.4.1/js/dataTables.buttons.min.js"></script>
<script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.bootstrap4.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.2.7/pdfmake.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.2.7/vfs_fonts.js"></script>
<script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.html5.min.js"></script>
<script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.print.min.js"></script>

<!-- Utilidades y script específico -->
<script src="{% static 'js/datatables-utils.js' %}"></script>
<script src="{% static 'js/ventas-datatables.js' %}"></script>
```

## Notas Importantes

1. **Orden de carga**: Siempre cargar `datatables-utils.js` ANTES del script específico del módulo.

2. **Compatibilidad**: Las utilidades funcionan con jQuery y DataTables 1.13.6+.

3. **Personalización**: Puedes sobrescribir cualquier función en tu script específico si necesitas comportamiento personalizado.

4. **Debug Mode**: Las utilidades respetan el modo DEBUG si está definido globalmente.

## Migración de Código Existente

Para migrar código existente a usar las utilidades:

1. Incluir `datatables-utils.js` en el HTML
2. Reemplazar funciones duplicadas con las utilidades
3. Usar `generateReportTitle()` para títulos dinámicos
4. Usar `configurePdfDocument()` para PDFs
5. Usar `exportToCSV()` para exportaciones CSV personalizadas

## Soporte

Para más información, consulta el código fuente de `datatables-utils.js` que está completamente documentado con comentarios JSDoc.
