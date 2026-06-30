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
            var table = $("#gastosTable").DataTable();
            var data = table.rows({ search: "applied" }).data();
            var totalFiltrado = 0;

            // Extraer cada fila con: fecha, sucursal, cuenta, categoria, total
            var rows = [];
            for (var i = 0; i < data.length; i++) {
              var rowData = data[i];
              var tempDiv = document.createElement("div");

              tempDiv.innerHTML = rowData[0];
              var fecha = (tempDiv.textContent || tempDiv.innerText || rowData[0]).trim();

              tempDiv.innerHTML = rowData[5];
              var sucursal = (tempDiv.textContent || tempDiv.innerText || rowData[5]).trim();

              tempDiv.innerHTML = rowData[3];
              var cuenta = (tempDiv.textContent || tempDiv.innerText || rowData[3]).trim();

              tempDiv.innerHTML = rowData[2];
              var categoria = (tempDiv.textContent || tempDiv.innerText || rowData[2]).trim();

              var totalCell = table.cell(i, 6).node();
              var cellText = (totalCell.textContent || totalCell.innerText || "").trim();
              var totalValue = parseFloat(cellText.replace(/[$\s]/g, ""));
              if (isNaN(totalValue)) totalValue = 0;

              rows.push({
                fecha: fecha,
                sucursal: sucursal,
                cuenta: cuenta,
                categoria: categoria,
                total: totalValue,
              });
              totalFiltrado += totalValue;
            }

            // Ordenar: sucursal → cuenta → fecha descendente
            rows.sort(function (a, b) {
              if (a.sucursal !== b.sucursal) return a.sucursal.localeCompare(b.sucursal);
              if (a.cuenta !== b.cuenta) return a.cuenta.localeCompare(b.cuenta);
              return (b.fecha || "").localeCompare(a.fecha || "");
            });

            // Agrupar por sucursal → cuenta con subtotales
            var htmlData = [];
            var grandTotal = 0;
            var lastSucursal = null;
            var lastCuenta = null;
            var sucTotal = 0;
            var ctaTotal = 0;

            for (var r = 0; r < rows.length; r++) {
              var row = rows[r];

              // Nueva sucursal? Cerrar cuenta y sucursal anterior
              if (lastSucursal && row.sucursal !== lastSucursal) {
                if (lastCuenta) {
                  htmlData.push({ fecha: "", sucursal: "", cuenta: lastCuenta + " - SUBTOTAL", categoria: "", total: ctaTotal, isSubtotal: true });
                  lastCuenta = null;
                }
                htmlData.push({ fecha: "", sucursal: lastSucursal + " - SUBTOTAL", cuenta: "", categoria: "", total: sucTotal, isSubtotal: true });
                htmlData.push({ fecha: "", sucursal: "", cuenta: "", categoria: "", total: "", isSubtotal: false });
                grandTotal += sucTotal;
                sucTotal = 0;
              }

              // Nueva cuenta dentro de la misma sucursal?
              if (lastCuenta && row.cuenta !== lastCuenta && row.sucursal === lastSucursal) {
                htmlData.push({ fecha: "", sucursal: "", cuenta: lastCuenta + " - SUBTOTAL", categoria: "", total: ctaTotal, isSubtotal: true });
                ctaTotal = 0;
              }

              htmlData.push({ fecha: row.fecha, sucursal: row.sucursal, cuenta: row.cuenta, categoria: row.categoria, total: row.total, isSubtotal: false });
              ctaTotal += row.total;
              sucTotal += row.total;
              lastSucursal = row.sucursal;
              lastCuenta = row.cuenta;
            }

            // Cerrar ultimo grupo
            if (lastCuenta) {
              htmlData.push({ fecha: "", sucursal: "", cuenta: lastCuenta + " - SUBTOTAL", categoria: "", total: ctaTotal, isSubtotal: true });
            }
            if (lastSucursal) {
              htmlData.push({ fecha: "", sucursal: lastSucursal + " - SUBTOTAL", cuenta: "", categoria: "", total: sucTotal, isSubtotal: true });
              grandTotal += sucTotal;
            }

            htmlData.push({ fecha: "", sucursal: "TOTAL GENERAL", cuenta: "", categoria: "", total: grandTotal, isSubtotal: true });

            // --- Tabla de categorias (reemplaza los graficos que Excel no puede renderizar) ---
            var categoriasTable = "";
            try {
              if (window.balancesCategoriasLabels && window.balancesCategoriasLabels.length > 0) {
                categoriasTable += '<h2 style="color:#2f4550;font-family:Arial,sans-serif;margin-top:20px;">Gastos por Categor&iacute;a</h2>';
                categoriasTable += '<table><thead><tr><th>#</th><th>Categor&iacute;a</th><th>Total</th><th>%</th></tr></thead><tbody>';
                var catData = window.balancesCategoriasData || [];
                var catTotal = catData.reduce(function(a,b){return a+b;}, 0);
                for (var ci = 0; ci < window.balancesCategoriasLabels.length; ci++) {
                  var pct = catTotal > 0 ? ((catData[ci] / catTotal) * 100).toFixed(1) + "%" : "0.0%";
                  categoriasTable += '<tr><td>' + (ci+1) + '</td><td>' + window.balancesCategoriasLabels[ci] + '</td><td class="num-col">$' + catData[ci].toLocaleString("en-US", {minimumFractionDigits:2,maximumFractionDigits:2}) + '</td><td class="num-col">' + pct + '</td></tr>';
                }
                categoriasTable += '<tr class="subtotal"><td colspan="2"><strong>TOTAL</strong></td><td class="num-col">$' + catTotal.toLocaleString("en-US", {minimumFractionDigits:2,maximumFractionDigits:2}) + '</td><td class="num-col">100.0%</td></tr>';
                categoriasTable += '</tbody></table>';
              }
            } catch(err) {
              categoriasTable = "";
            }

            // --- Sumatoria de gastos filtrados ---
            var sumatoriaHTML = "";
            if (totalFiltrado > 0) {
              var formattedSum = "$" + totalFiltrado.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
              sumatoriaHTML = '<div style="background:#2f4550;color:#fff;padding:10px 16px;border-radius:6px;margin-bottom:16px;font-family:Arial,sans-serif;"><strong>Sumatoria total de gastos filtrados:</strong> ' + formattedSum + '</div>';
            }

            var html = '<html><head><meta charset="UTF-8"><style>' +
              "body{font-family:Arial,sans-serif;margin:20px;color:#2f4550;}" +
              "h1{color:#2f4550;border-bottom:2px solid #b8dbd9;padding-bottom:6px;}" +
              "h2{color:#2f4550;margin-top:24px;}" +
              "table{border-collapse:collapse;width:100%;margin-bottom:20px;}" +
              "th{background:#2f4550;color:#fff;padding:8px 10px;text-align:left;font-size:11px;text-transform:uppercase;}" +
              "td{padding:6px 10px;border:1px solid #d8dce6;font-size:11px;}" +
              "tr:nth-child(even){background:#f8fafc;}" +
              ".subtotal td{background:#E6F3FF;font-weight:bold;}" +
              ".total-general td{background:#2f4550;color:#fff;font-weight:bold;}" +
              ".fecha-col{white-space:nowrap;}" +
              ".num-col{text-align:right;white-space:nowrap;}" +
              "</style></head><body>";

            html += "<h1>" + (getReportTitle ? getReportTitle() : "Resumen de Gastos") + "</h1>";
            html += sumatoriaHTML;

            html += "<table><thead><tr>" +
              "<th>Fecha</th><th>Sucursal</th><th>Cuenta</th><th>Categor&iacute;a</th><th>Total</th>" +
              "</tr></thead><tbody>";

            htmlData.forEach(function (row) {
              var cssClass = "";
              if (row.sucursal === "TOTAL GENERAL") {
                cssClass = ' class="total-general"';
              } else if (row.isSubtotal) {
                cssClass = ' class="subtotal"';
              }
              html += "<tr" + cssClass + ">";
              html += '<td class="fecha-col">' + row.fecha + "</td>";
              html += "<td>" + row.sucursal + "</td>";
              html += "<td>" + row.cuenta + "</td>";
              html += "<td>" + row.categoria + "</td>";
              html += '<td class="num-col">' +
                (row.total !== "" ? "$" + row.total.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "") +
                "</td>";
              html += "</tr>";
            });

            html += "</tbody></table>";

            if (categoriasTable) { html += categoriasTable; }

            html += "</body></html>";

            var BOM = "\uFEFF";
            var blob = new Blob([BOM + html], { type: "application/vnd.ms-excel;charset=utf-8" });
            var link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            var now = new Date();
            link.download = "gastos-resumen-" + now.toISOString().slice(0, 10) + ".xls";
            link.click();
          },
        },
        {
          extend: "pdf",
          className: "dt-button btn-pdf",
          text: '<i class="fas fa-file-pdf mr-1"></i> PDF',
          title: "",
          customize: function (doc) {
            var reportTitle = getReportTitle();

            configurePdfDocument(doc, {
              reportTitle: reportTitle,
              systemName: "2026 - Agricola de la Costa San Luis S.P.R de R.L.",
              orientation: "landscape",
              pageMargins: [40, 80, 40, 60],
            });

            if (doc.content[0].table) {
              // Widths para export: Fecha, #, Categoria, Cuenta, Banco, Sucursal, Total, Acumulado
              doc.content[0].table.widths = [
                "auto",
                "auto",
                "*",
                "auto",
                "auto",
                "auto",
                "auto",
                "auto",
              ];
              doc.content[0].table.headerRows = 1;

              doc.content[0].layout = {
                fillColor: function (rowIndex, node, columnIndex) {
                  if (rowIndex === 0) return "#34495e";
                  // Footer row (data rows + 1 = footer index)
                  var dataRows = doc.content[0].table.body.length - 2;
                  if (rowIndex === dataRows + 1) return "#2f4550";
                  return rowIndex % 2 === 0 ? "#ecf0f1" : null;
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
                  return "#bdc3c7";
                },
                vLineColor: function () {
                  return "#bdc3c7";
                },
              };
            }
          },
          exportOptions: {
            columns: [0, 1, 2, 3, 4, 5, 6, 7],
            orthogonal: "export",
            footer: true,
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
