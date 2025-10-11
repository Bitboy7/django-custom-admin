/**
 * Compras DataTables Configuration
 *
 * Configuración de DataTables para el módulo de compras
 * Utiliza datatables-utils.js para funcionalidad reutilizable
 *
 * @requires jQuery
 * @requires DataTables
 * @requires datatables-utils.js
 */

// ============================================================================
// CONFIGURACIÓN DEL MÓDULO
// ============================================================================

var reportConfig = {
  moduleName: "Reporte de Compras",
  filterFields: [
    "cuenta_id",
    "sucursal_id",
    "productor_id",
    "producto_id",
    "tipo_pago",
    "year",
    "month",
    "periodo",
  ],
};

// ============================================================================
// FUNCIONES AUXILIARES ESPECÍFICAS DEL MÓDULO
// ============================================================================

/**
 * Genera el título del reporte basado en filtros
 */
function getReportTitle() {
  return generateReportTitle(reportConfig);
}

/**
 * Formatea un valor numérico con símbolo de moneda opcional
 *
 * @param {HTMLElement|number} node - Nodo del DOM o valor numérico
 * @param {boolean} includeSymbol - Si se debe incluir el símbolo $
 * @returns {string} Valor formateado
 */
function formatNumericValue(node, includeSymbol) {
  var numValue;

  // Si es un nodo del DOM, extraer el valor
  if (node && node.nodeType) {
    numValue = getNumericValueFromNode(node);
  } else if (typeof node === "number") {
    numValue = node;
  } else {
    numValue = parseFloat(node);
  }

  if (isNaN(numValue)) {
    return includeSymbol ? "$0.00" : "0.00";
  }

  var formatted = numValue.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  return includeSymbol ? "$" + formatted : formatted;
}

// ============================================================================
// INICIALIZACIÓN DE DATATABLE
// ============================================================================

document.addEventListener("DOMContentLoaded", function () {
  try {
    $("#comprasTable").DataTable({
      language: {
        processing: "",
        search: "Buscar:",
        lengthMenu: "Mostrar _MENU_ registros",
        info: "Mostrando _START_ a _END_ de _TOTAL_ registros",
        infoEmpty: "Mostrando 0 a 0 de 0 registros",
        infoFiltered: "(filtrado de _MAX_ registros totales)",
        loadingRecords: "",
        zeroRecords: "No se encontraron registros coincidentes",
        emptyTable: "No hay datos disponibles en la tabla",
        paginate: {
          first: "Primero",
          previous: "Anterior",
          next: "Siguiente",
          last: "Último",
        },
        buttons: {
          copy: "Copiar",
          print: "Imprimir",
          excel: "Excel",
          pdf: "PDF",
          csv: "CSV",
        },
      },
      columns: [
        { data: 0 }, // Periodo
        { data: 1 }, // Productor
        { data: 2 }, // Producto
        { data: 3 }, // Sucursal
        { data: 4 }, // Cuenta
        {
          // Cantidad
          data: 5,
          render: function (data, type, row, meta) {
            if (type === "display") {
              return data;
            }
            // Para sort, export, filter - extraer el número limpio
            var cleanText = getCleanTextFromHTML(data);
            var numValue = parseNumericString(cleanText);

            if (!isNaN(numValue)) {
              return type === "export" ? numValue.toFixed(2) : numValue;
            }
            return 0;
          },
        },
        {
          // Precio Promedio
          data: 6,
          render: function (data, type, row, meta) {
            if (type === "display") {
              return data;
            }
            // Para sort, export, filter - extraer el número limpio
            var cleanText = getCleanTextFromHTML(data);
            var numValue = parseNumericString(cleanText);
            if (!isNaN(numValue)) {
              return type === "export" ? numValue.toFixed(2) : numValue;
            }
            return 0;
          },
        },
        {
          // Total
          data: 7,
          render: function (data, type, row, meta) {
            if (type === "display") {
              return data;
            }
            // Para sort, export, filter - extraer el número limpio
            var cleanText = getCleanTextFromHTML(data);
            var numValue = parseNumericString(cleanText);

            if (!isNaN(numValue)) {
              return type === "export" ? numValue.toFixed(2) : numValue;
            }
            return 0;
          },
        },
        {
          // Acumulado
          data: 8,
          render: function (data, type, row, meta) {
            if (type === "display") {
              return data;
            }
            // Para sort, export, filter - extraer el número limpio
            var cleanText = getCleanTextFromHTML(data);
            var numValue = parseNumericString(cleanText);
            if (!isNaN(numValue)) {
              return type === "export" ? numValue.toFixed(2) : numValue;
            }
            return 0;
          },
        },
      ],
      columnDefs: [
        {
          // Columnas numéricas - alineación derecha
          targets: [5, 6, 7, 8],
          className: "text-right",
        },
        {
          // Columna de Periodo - exportar limpio
          targets: [0],
          render: function (data, type, row) {
            if (type === "export" || type === "copy") {
              return getCleanTextFromHTML(data);
            }
            return data;
          },
        },
      ],
      order: [[0, "asc"]],
      pageLength: 25,
      lengthMenu: [
        [10, 25, 50, 100, -1],
        [10, 25, 50, 100, "Todos"],
      ],
      dom: "Blfrtip",
      buttons: [
        {
          extend: "copy",
          text: '<i class="fas fa-copy"></i> Copiar',
          className:
            "bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md text-sm shadow-md transition-colors duration-200",
          exportOptions: {
            columns: ":visible",
            orthogonal: "export",
          },
        },
        {
          extend: "excel",
          text: '<i class="fas fa-file-excel"></i> Excel',
          className:
            "bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-md text-sm shadow-md transition-colors duration-200",
          title: function () {
            return getReportTitle();
          },
          filename: function () {
            return "compras_" + getCurrentDateFormatted("filename");
          },
          exportOptions: {
            columns: ":visible",
            orthogonal: "export",
          },
        },
        {
          extend: "pdf",
          text: '<i class="fas fa-file-pdf"></i> PDF',
          className:
            "bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-sm shadow-md transition-colors duration-200",
          title: "",
          filename: function () {
            return "compras_" + getCurrentDateFormatted("filename");
          },
          exportOptions: {
            columns: ":visible",
            orthogonal: "export",
          },
          orientation: "landscape",
          pageSize: "LEGAL",
          customize: function (doc) {
            // Obtener título dinámico basado en filtros
            var reportTitle = getReportTitle();

            // Configurar documento usando utilidades
            configurePdfDocument(doc, {
              reportTitle: reportTitle,
              systemName: "Sistema de Gestión de Compras",
              orientation: "landscape",
              pageMargins: [40, 80, 40, 60],
            });

            // Personalización adicional específica de compras
            if (doc.content[0].table) {
              var colCount = doc.content[0].table.body[0].length;
              var widths = [];
              for (var i = 0; i < colCount; i++) {
                if (i === 0) widths.push("auto"); // Periodo
                else if (i <= 4) widths.push("*"); // Texto
                else widths.push("auto"); // Números
              }
              doc.content[0].table.widths = widths;
              doc.content[0].table.headerRows = 1;

              // Alinear columnas numéricas a la derecha y aplicar estilos
              doc.content[0].table.body.forEach(function (row, rowIndex) {
                row.forEach(function (cell, cellIndex) {
                  if (cellIndex >= 5) {
                    cell.alignment = "right";
                  }
                });
              });

              // Alternar colores de las filas
              doc.content[0].layout = {
                fillColor: function (rowIndex) {
                  return rowIndex === 0
                    ? "#3b82f6"
                    : rowIndex % 2 === 0
                    ? "#f3f4f6"
                    : null;
                },
                hLineWidth: function (i, node) {
                  return i === 0 || i === 1 || i === node.table.body.length
                    ? 1
                    : 0.5;
                },
                vLineWidth: function () {
                  return 0.5;
                },
                hLineColor: function () {
                  return "#d1d5db";
                },
                vLineColor: function () {
                  return "#d1d5db";
                },
              };
            }
          },
        },
        {
          extend: "print",
          text: '<i class="fas fa-print"></i> Imprimir',
          className:
            "bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-md text-sm shadow-md transition-colors duration-200",
          title: function () {
            return getReportTitle();
          },
          exportOptions: {
            columns: ":visible",
            orthogonal: "export",
          },
          customize: function (win) {
            $(win.document.body).css("font-size", "10pt");
            $(win.document.body)
              .find("table")
              .addClass("compact")
              .css("font-size", "inherit");
          },
        },
      ],
      responsive: true,
      processing: false,
      stateSave: false,
      drawCallback: function (settings) {
        // Ocultar cualquier spinner de procesamiento
        $(".dataTables_processing").hide();
      },
    });
  } catch (error) {
    console.error("❌ Error al inicializar DataTable de compras:", error);
  }

  // ============================================================================
  // MANEJO DE FILTROS Y PERÍODO
  // ============================================================================

  // Manejar cambios en el selector de período
  $(".periodo-select").on("change", function () {
    const periodo = $(this).val();

    // Mostrar/ocultar campos según el período seleccionado
    if (periodo === "diario") {
      $("#filtro-dia, #filtro-inicio, #filtro-fin").show();
      $("#multi-month-container").hide();
    } else if (periodo === "mensual") {
      $("#filtro-dia, #filtro-inicio, #filtro-fin").hide();
      $("#multi-month-container").show();
    } else {
      $(
        "#filtro-dia, #filtro-inicio, #filtro-fin, #multi-month-container"
      ).hide();
    }
  });

  // Trigger al cargar para configurar visibilidad inicial
  $(".periodo-select").trigger("change");

  // Ocultar warning después de 5 segundos
  setTimeout(function () {
    $("#warning-message").fadeOut("slow");
  }, 5000);
});

// ============================================================================
// FUNCIONES DE TOAST
// ============================================================================

/**
 * Muestra un mensaje toast
 */
function showToast(title, message) {
  const toast = document.getElementById("toast-notification");
  if (!toast) return;

  document.getElementById("toast-title").textContent = title;
  document.getElementById("toast-message").textContent = message;

  toast.style.transform = "translateX(0)";
  toast.style.opacity = "1";

  setTimeout(() => hideToast(), 5000);
}

/**
 * Oculta el mensaje toast
 */
function hideToast() {
  const toast = document.getElementById("toast-notification");
  if (!toast) return;

  toast.style.transform = "translateX(100%)";
  toast.style.opacity = "0";
}

// Exponer funciones globalmente si es necesario
window.showToast = showToast;
window.hideToast = hideToast;
