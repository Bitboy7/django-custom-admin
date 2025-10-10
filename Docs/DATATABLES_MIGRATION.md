# Guía de Migración - balances-datatables.js

## Estado Actual

El archivo `balances-datatables.js` contiene funciones duplicadas que ahora están en `datatables-utils.js`. Esta guía muestra cómo simplificar el código.

## Funciones que se pueden eliminar

Las siguientes funciones YA están disponibles en `datatables-utils.js` y se pueden eliminar de `balances-datatables.js`:

1. **`getCleanTextFromHTML()`** - Disponible en utils
2. **`getCurrentDateFormatted()`** - Disponible en utils (con más opciones)
3. **`getNumericValueFromNode()`** - Disponible en utils
4. **La lógica de formateo de números** - Disponible como `parseNumericString()` y `formatNumericValue()`

## Función que se puede reemplazar

La función `getReportTitle()` se puede reemplazar con `generateReportTitle()` de las utilidades.

### Antes (código actual):

```javascript
function getReportTitle() {
  var urlParams = new URLSearchParams(window.location.search);
  var titleParts = [];

  // Obtener información de los filtros
  var cuentaId = urlParams.get("cuenta_id");
  var sucursalId = urlParams.get("sucursal_id");
  var year = urlParams.get("year");
  var month = urlParams.get("month");
  var periodo = urlParams.get("periodo");

  // ... mucho código para construir el título ...

  if (titleParts.length > 0) {
    return "Reporte de gastos - " + titleParts.join(" | ");
  } else {
    return "Reporte de gastos - General";
  }
}
```

### Después (usando utilidades):

```javascript
// Configuración del reporte
var reportConfig = {
  moduleName: "Reporte de Gastos",
  filterFields: ["cuenta_id", "sucursal_id", "year", "month", "periodo"],
};

// La función se simplifica a:
function getReportTitle() {
  return generateReportTitle(reportConfig);
}
```

## Simplificación del botón PDF

### Antes:

```javascript
{
  extend: "pdf",
  className: "dt-button btn-pdf",
  text: '<i class="fas fa-file-pdf mr-1"></i> PDF',
  title: "",
  customize: function (doc) {
    var reportTitle = getReportTitle();
    var currentDate = getCurrentDateFormatted();

    // Configurar documento
    doc.pageOrientation = "landscape";
    doc.pageMargins = [40, 80, 40, 60];

    // Personalizar encabezado
    doc.header = function (currentPage, pageCount) {
      return {
        stack: [
          {
            text: reportTitle,
            style: "header",
            alignment: "center",
            margin: [0, 30, 0, 5],
          },
          {
            text: "Fecha de generación: " + currentDate,
            style: "subheader",
            alignment: "center",
          },
        ],
        margin: [40, 20, 40, 0],
      };
    };

    // Personalizar pie de página
    doc.footer = function (currentPage, pageCount) {
      return {
        columns: [
          {
            text: "Sistema de Gestión de Gastos",
            alignment: "left",
            style: "footer",
            margin: [40, 0, 0, 0],
          },
          {
            text: "Página " + currentPage.toString() + " de " + pageCount,
            alignment: "right",
            style: "footer",
            margin: [0, 0, 40, 0],
          },
        ],
        margin: [0, 10, 0, 0],
      };
    };

    // Estilos
    doc.styles = {
      header: {
        fontSize: 18,
        bold: true,
        color: "#2c3e50",
      },
      subheader: {
        fontSize: 11,
        color: "#7f8c8d",
        italics: true,
      },
      tableHeader: {
        bold: true,
        fontSize: 11,
        color: "white",
        fillColor: "#34495e",
        alignment: "center",
      },
      footer: {
        fontSize: 9,
        color: "#95a5a6",
      },
    };
  }
}
```

### Después (usando utilidades):

```javascript
{
  extend: "pdf",
  className: "dt-button btn-pdf",
  text: '<i class="fas fa-file-pdf mr-1"></i> PDF',
  title: "",
  customize: function (doc) {
    var reportTitle = getReportTitle();

    // Una sola línea para configurar todo
    configurePdfDocument(doc, {
      reportTitle: reportTitle,
      systemName: "Sistema de Gestión de Gastos",
      orientation: "landscape",
      pageMargins: [40, 80, 40, 60]
    });
  }
}
```

## Simplificación del botón CSV

### Antes:

```javascript
{
  extend: "csv",
  className: "dt-button btn-csv",
  text: '<i class="fas fa-file-csv mr-1"></i> CSV',
  action: function (e, dt, button, config) {
    // ... código largo para construir CSV manualmente ...

    var now = new Date();
    var pad = (n) => n.toString().padStart(2, "0");
    var fecha = now.getFullYear() + "-" + pad(now.getMonth() + 1) + "-" + pad(now.getDate());
    var hora = pad(now.getHours()) + "-" + pad(now.getMinutes()) + "-" + pad(now.getSeconds());
    var filename = "gastos-resumen-categorias-" + fecha + "-" + hora + ".csv";

    var blob = new Blob([csvData], { type: "text/csv;charset=utf-8;" });
    // ... código para descargar ...
  }
}
```

### Después (usando utilidades):

```javascript
{
  extend: "csv",
  className: "dt-button btn-csv",
  text: '<i class="fas fa-file-csv mr-1"></i> CSV',
  action: function (e, dt, button, config) {
    // Recolectar datos
    var headers = ["Categoría", "Importe"];
    var data = [];

    sortedCategories.forEach(function (item) {
      data.push([item[0], item[1]]);
    });

    // Exportar usando la utilidad
    exportToCSV({
      filename: "gastos-resumen-categorias",
      headers: headers,
      data: data
    });
  }
}
```

## Beneficios de la Migración

1. **Menos código**: Reduce el archivo de ~700 líneas a ~300 líneas
2. **Más mantenible**: Las funciones comunes están en un solo lugar
3. **Reutilizable**: El mismo código de utilidades se puede usar en compras, ventas, etc.
4. **Mejor documentado**: Las utilidades tienen documentación JSDoc completa
5. **Más flexible**: Las funciones aceptan parámetros de configuración

## Pasos para Migrar

1. ✅ Crear `datatables-utils.js` (ya hecho)
2. ✅ Incluir `datatables-utils.js` en `balances.html` (ya hecho)
3. ⏳ Actualizar `balances-datatables.js` para usar las utilidades
4. 🧪 Probar que todo funcione correctamente
5. 📦 Usar las utilidades en otros módulos (compras, ventas)

## Nota Importante

**NO es necesario migrar inmediatamente**. El código actual seguirá funcionando. La migración se puede hacer gradualmente:

1. Primero, probar que las utilidades funcionan bien
2. Luego, crear nuevos módulos usando las utilidades (compras, ventas)
3. Finalmente, cuando estés seguro, actualizar el módulo de gastos

## Ejemplo de Nuevo Módulo

Para crear un nuevo módulo de compras usando las utilidades desde cero:

```javascript
// compras-datatables.js
$(document).ready(function () {
  var reportConfig = {
    moduleName: "Reporte de Compras",
    filterFields: ["proveedor_id", "sucursal_id", "year", "month"],
  };

  var table = $("#compras-datatable").DataTable({
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
          var headers = ["Proveedor", "Factura", "Total"];
          var data = [];

          $(rows).each(function () {
            var tds = $(this).find("td");
            data.push([
              getCleanTextFromHTML(tds.eq(0).html()),
              getCleanTextFromHTML(tds.eq(1).html()),
              getNumericValueFromNode(tds[2]),
            ]);
          });

          exportToCSV({
            filename: "compras",
            headers: headers,
            data: data,
          });
        },
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
            systemName: "Sistema de Gestión de Compras",
            orientation: "landscape",
          });
        },
      },
    ],
  });
});
```

## Resumen

✅ **Las utilidades están listas para usar**
✅ **El template ya incluye datatables-utils.js**
✅ **El código actual sigue funcionando sin cambios**
🎯 **Puedes empezar a crear nuevos módulos usando las utilidades**
📝 **La migración del código existente es opcional pero recomendada**
