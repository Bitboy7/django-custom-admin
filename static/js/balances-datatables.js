/**
 * Balances DataTables Configuration
 *
 * Configuración de DataTables para el módulo de gastos/balances
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
  moduleName: "Reporte de gastos",
  filterFields: ["cuenta_id", "sucursal_id", "year", "month", "periodo"],
};

// ============================================================================
// FUNCIONES AUXILIARES ESPECÍFICAS DEL MÓDULO
// ============================================================================

/**
 * Genera el título del reporte basado en filtros
 * Usa la función genérica de datatables-utils.js
 */
function getReportTitle() {
  return generateReportTitle(reportConfig);
}

/**
 * Formatea un valor numérico con símbolo de moneda opcional
 * Wrapper para compatibilidad con código existente
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

function initBalancesDataTable() {
  if (!document.getElementById("gastosTable")) {
    return;
  }

  if (!window.jQuery || !jQuery.fn || !jQuery.fn.DataTable) {
    console.warn("DataTables no esta disponible todavia para #gastosTable");
    return;
  }

  try {
    // Verificar si ya está inicializado y destruirlo
    if ($.fn.DataTable.isDataTable("#gastosTable")) {
      $("#gastosTable").DataTable().destroy();
      console.log("⚠️ DataTable anterior destruido");
    }

    $("#gastosTable").DataTable({
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
        {
          // Fecha
          data: 0,
          className: "balances-date-cell text-left",
          render: function (data, type, row, meta) {
            var dateText = getCleanTextFromHTML(data).trim();

            if (type === "display") {
              return dateText || "—";
            }

            return dateText;
          },
        },
        { data: 1 }, // #
        { data: 2 }, // Categoría
        { data: 3 }, // N° Cuenta
        { data: 4 }, // Banco
        { data: 5 }, // Sucursal
        {
          // Total
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
          // Acumulado
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
      ],
      columnDefs: [
        {
          // Columnas numéricas - alineación derecha
          targets: [6, 7],
          className: "text-right",
        },
        {
          // Columna #1: Número secuencial - limpiar HTML
          targets: [1],
          render: function (data, type, row) {
            if (type === "export" || type === "copy") {
              return getCleanTextFromHTML(data);
            }
            return data;
          },
        },
        {
          // Columna #2: Categoría - limpiar HTML de spans y badges
          targets: [2],
          render: function (data, type, row) {
            if (type === "export" || type === "copy") {
              return getCleanTextFromHTML(data);
            }
            return data;
          },
        },
        {
          // Columnas #3-5: Cuenta, Banco, Sucursal - limpiar HTML
          targets: [3, 4, 5],
          render: function (data, type, row) {
            if (type === "export" || type === "copy") {
              return getCleanTextFromHTML(data);
            }
            return data;
          },
        },
      ],
      buttons: [
        {
          extend: "copy",
          className: "dt-button btn-copy",
          text: '<i class="fas fa-copy mr-1"></i> Copiar',
          exportOptions: {
            columns: [0, 1, 2, 3, 4, 5, 6, 7],
            orthogonal: "export",
            footer: true,
          },
        },
        {
          extend: "csv",
          className: "dt-button btn-csv",
          text: '<i class="fas fa-file-csv mr-1"></i> CSV',
          charset: "utf-8",
          bom: true,
          exportOptions: {
            columns: [0, 1, 2, 3, 4, 5, 6, 7],
            orthogonal: "export",
            footer: true,
          },
        },
        {
          extend: "excel",
          className: "dt-button btn-excel",
          text: '<i class="fas fa-file-excel mr-1"></i> Excel',
          title: function () {
            return getReportTitle();
          },
          filename: function () {
            return "gastos-detalle-" + getCurrentDateFormatted("filename");
          },
          exportOptions: {
            columns: [0, 1, 2, 3, 4, 5, 6, 7],
            orthogonal: "export",
            footer: true,
          },
          customize: function (xlsx) {
            // Footer con total se incluye via exportOptions.footer:true
          },
        },
        {
          text: '<i class="fas fa-chart-pie mr-1"></i> Resumen Excel',
          className: "dt-button btn-summary-excel",
          action: function (e, dt, button, config) {
            var wrapper = document.querySelector("[data-balances-page]");
            var baseUrl = wrapper ? wrapper.getAttribute("data-resumen-excel-url") : "";
            if (!baseUrl) {
              console.error("URL de exportación de resumen no disponible");
              return;
            }
            var form = document.getElementById("balances-filter-form") ||
              document.querySelector("form[hx-get]");
            var params = "";
            if (form) {
              params = new URLSearchParams(new FormData(form)).toString();
            }
            window.location.href = baseUrl + (params ? "?" + params : "");
          },
        },
        {
          className: "dt-button btn-pdf",
          text: '<i class="fas fa-file-pdf mr-1"></i> PDF',
          action: function () {
            if (typeof window.exportBalancesPDF === "function") {
              window.exportBalancesPDF();
            } else {
              console.error("exportBalancesPDF no esta disponible");
            }
          },
        },
        {
          extend: "print",
          className: "dt-button btn-print",
          text: '<i class="fas fa-print mr-1"></i> Imprimir',
          exportOptions: {
            columns: [0, 1, 2, 3, 4, 5, 6, 7],
            orthogonal: "export",
            footer: true,
          },
        },
      ],
      dom: '<"gastos-dt-toolbar"<"gastos-dt-actions"B><"gastos-dt-controls"lf>>rt<"gastos-dt-footer"ip>',
      responsive: true,
      order: [[0, "asc"]], // Ordenar por Fecha ascendente
      paging: true,
      pageLength: 25,
      lengthMenu: [
        [10, 25, 50, 100, -1],
        [10, 25, 50, 100, "Todos"],
      ],
      pagingType: "full_numbers",
      processing: false,
      searching: true,
      info: true,
      pagingInfo: true,
      initComplete: function () {
        setTimeout(function () {
          stylePaginationControls();
          styleLengthMenu();
        }, 100);
        setTimeout(function () {
          if (typeof window.updateChartsData === "function") {
            window.updateChartsData();
            window.dispatchEvent(new Event("chartsDataUpdated"));
          }
        }, 150);
      },
      drawCallback: function () {
        setTimeout(function () {
          stylePaginationControls();
        }, 50);
      },
    });
    function stylePaginationControls() {
      var paginateContainer = document.querySelector(".dataTables_paginate");
      if (paginateContainer) {
        paginateContainer.style.visibility = "visible";
      }
      document.querySelectorAll(".paginate_button").forEach(function (button) {
        button.style.display = "inline-block";
        button.style.visibility = "visible";
      });
    }
    function styleLengthMenu() {
      var lengthSelect = document.querySelector(".dataTables_length select");
      if (lengthSelect) {
        lengthSelect.style.visibility = "visible";
      }
      var lengthLabel = document.querySelector(".dataTables_length");
      if (lengthLabel) {
        lengthLabel.style.visibility = "visible";
      }
    }
  } catch (error) {
    console.error("Error al inicializar DataTable:", error);
  }
}

window.initBalancesDataTable = initBalancesDataTable;

function initBalancesDataTableWithRetry(retries) {
  if (window.jQuery && jQuery.fn && jQuery.fn.DataTable) {
    initBalancesDataTable();
    return;
  }

  if (retries > 0) {
    setTimeout(function () {
      initBalancesDataTableWithRetry(retries - 1);
    }, 250);
  } else {
    console.error("DataTables no se pudo cargar. Revise la conexion CDN o los archivos estaticos.");
  }
}

document.addEventListener("DOMContentLoaded", function () {
  initBalancesDataTableWithRetry(12);
});
