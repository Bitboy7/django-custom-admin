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
  moduleName: "Reporte de Gastos",
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

document.addEventListener("DOMContentLoaded", function () {
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
        { data: 0 }, // #
        { data: 1 }, // Categoría
        { data: 2 }, // N° Cuenta
        { data: 3 }, // Banco
        { data: 4 }, // Sucursal
        { data: 5 }, // Fecha
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
          // Columna #0: Número secuencial - limpiar HTML
          targets: [0],
          render: function (data, type, row) {
            if (type === "export" || type === "copy") {
              return getCleanTextFromHTML(data);
            }
            return data;
          },
        },
        {
          // Columna #1: Categoría - limpiar HTML de spans y badges
          targets: [1],
          render: function (data, type, row) {
            if (type === "export" || type === "copy") {
              return getCleanTextFromHTML(data);
            }
            return data;
          },
        },
        {
          // Columnas #2-4: Cuenta, Banco, Sucursal - limpiar HTML
          targets: [2, 3, 4],
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
            columns: ":visible",
            orthogonal: "export",
          },
        },
        {
          extend: "csv",
          className: "dt-button btn-csv",
          text: '<i class="fas fa-file-csv mr-1"></i> CSV',
          charset: "utf-8",
          bom: true,
          exportOptions: {
            columns: ":visible",
            orthogonal: "export",
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
            columns: ":visible",
            orthogonal: "export",
          },
          customize: function (xlsx) {
            console.log("Iniciando customize...");
            console.log("Estructura xlsx:", Object.keys(xlsx));
            console.log("Estructura xlsx.xl:", Object.keys(xlsx.xl));

            // Por ahora, solo retornar sin hacer cambios para verificar que funcione
            // Una vez que funcione, agregaremos la segunda hoja
            console.log("Excel exportado sin modificaciones");
          },
        },
        {
          text: '<i class="fas fa-chart-pie mr-1"></i> Resumen Excel',
          className: "dt-button btn-summary-excel",
          action: function (e, dt, button, config) {
            // Procesar datos para el resumen
            var sucursalData = {};
            var table = $("#gastosTable").DataTable();
            var data = table.rows({ search: "applied" }).data();

            // Agrupar por sucursal → cuenta → categoría
            for (var i = 0; i < data.length; i++) {
              var rowData = data[i];
              var tempDiv = document.createElement("div");

              tempDiv.innerHTML = rowData[4];
              var sucursal = (
                tempDiv.textContent ||
                tempDiv.innerText ||
                rowData[4]
              ).trim();

              tempDiv.innerHTML = rowData[2];
              var cuenta = (
                tempDiv.textContent ||
                tempDiv.innerText ||
                rowData[2]
              ).trim();

              tempDiv.innerHTML = rowData[1];
              var categoria = (
                tempDiv.textContent ||
                tempDiv.innerText ||
                rowData[1]
              ).trim();

              var totalCell = table.cell(i, 6).node();
              var cellText = (
                totalCell.textContent ||
                totalCell.innerText ||
                ""
              ).trim();
              var totalValue = parseFloat(cellText.replace(/[$\s]/g, ""));
              if (isNaN(totalValue)) totalValue = 0;

              if (!sucursalData[sucursal]) {
                sucursalData[sucursal] = { cuentas: {}, total: 0 };
              }
              if (!sucursalData[sucursal].cuentas[cuenta]) {
                sucursalData[sucursal].cuentas[cuenta] = {
                  categorias: {},
                  total: 0,
                };
              }
              if (
                !sucursalData[sucursal].cuentas[cuenta].categorias[categoria]
              ) {
                sucursalData[sucursal].cuentas[cuenta].categorias[
                  categoria
                ] = 0;
              }

              sucursalData[sucursal].cuentas[cuenta].categorias[categoria] +=
                totalValue;
              sucursalData[sucursal].cuentas[cuenta].total += totalValue;
              sucursalData[sucursal].total += totalValue;
            }

            // Preparar datos para exportación HTML
            var headers = ["Sucursal", "Cuenta", "Categoría", "Total"];
            var htmlData = [];
            var grandTotal = 0;

            // Ordenar sucursales por total descendente
            var sortedSucursales = Object.keys(sucursalData).sort(function (
              a,
              b
            ) {
              return sucursalData[b].total - sucursalData[a].total;
            });

            // Construir HTML para cada fila
            sortedSucursales.forEach(function (sucursal) {
              var sucData = sucursalData[sucursal];
              var sortedCuentas = Object.keys(sucData.cuentas).sort(function (
                a,
                b
              ) {
                return sucData.cuentas[b].total - sucData.cuentas[a].total;
              });

              sortedCuentas.forEach(function (cuenta) {
                var cuentaData = sucData.cuentas[cuenta];
                var sortedCategorias = Object.keys(cuentaData.categorias).sort(
                  function (a, b) {
                    return cuentaData.categorias[b] - cuentaData.categorias[a];
                  }
                );

                // Agregar categorías
                sortedCategorias.forEach(function (categoria) {
                  htmlData.push({
                    sucursal: sucursal,
                    cuenta: cuenta,
                    categoria: categoria,
                    total: cuentaData.categorias[categoria],
                    isSubtotal: false,
                  });
                });

                // Subtotal de cuenta
                htmlData.push({
                  sucursal: sucursal,
                  cuenta: cuenta + " - SUBTOTAL",
                  categoria: "",
                  total: cuentaData.total,
                  isSubtotal: true,
                });
              });

              // Subtotal de sucursal
              htmlData.push({
                sucursal: sucursal + " - SUBTOTAL",
                cuenta: "",
                categoria: "",
                total: sucData.total,
                isSubtotal: true,
              });

              // Línea en blanco
              htmlData.push({
                sucursal: "",
                cuenta: "",
                categoria: "",
                total: "",
                isSubtotal: false,
              });

              grandTotal += sucData.total;
            });

            // Total general
            htmlData.push({
              sucursal: "TOTAL GENERAL",
              cuenta: "",
              categoria: "",
              total: grandTotal,
              isSubtotal: true,
            });

            // Crear tabla HTML con encoding UTF-8
            var html = '<html><head><meta charset="UTF-8"></head><body>';
            html += "<table>";
            html += "<thead><tr>";
            html +=
              "<th>Sucursal</th><th>Cuenta</th><th>Categoría</th><th>Total</th>";
            html += "</tr></thead><tbody>";

            htmlData.forEach(function (row) {
              var style = row.isSubtotal
                ? ' style="background-color: #E6F3FF; font-weight: bold;"'
                : "";
              html += "<tr" + style + ">";
              html += "<td>" + row.sucursal + "</td>";
              html += "<td>" + row.cuenta + "</td>";
              html += "<td>" + row.categoria + "</td>";
              html +=
                "<td>" +
                (row.total !== ""
                  ? "$" +
                    row.total.toLocaleString("en-US", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })
                  : "") +
                "</td>";
              html += "</tr>";
            });

            html += "</tbody></table></body></html>";

            // Crear blob con BOM para UTF-8 y descargar
            var BOM = "\uFEFF";
            var blob = new Blob([BOM + html], {
              type: "application/vnd.ms-excel;charset=utf-8",
            });
            var link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = "gastos-resumen-detallado.xls";
            link.click();
          },
        },
        {
          extend: "pdf",
          className: "dt-button btn-pdf",
          text: '<i class="fas fa-file-pdf mr-1"></i> PDF',
          title: "",
          customize: function (doc) {
            // Obtener título dinámico basado en filtros
            var reportTitle = getReportTitle();

            // Configurar documento usando utilidades
            configurePdfDocument(doc, {
              reportTitle: reportTitle,
              systemName: "2025 - Agricola de la Costa San Luis S.P.R de R.L.",
              orientation: "landscape",
              pageMargins: [40, 80, 40, 60],
            });

            // Personalización adicional específica de gastos
            if (doc.content[0].table) {
              doc.content[0].table.widths = [
                "auto",
                "*",
                "auto",
                "auto",
                "auto",
                "auto",
                "auto",
                "auto",
              ];
              doc.content[0].table.headerRows = 1;

              // Alternar colores de las filas
              doc.content[0].layout = {
                fillColor: function (rowIndex) {
                  return rowIndex === 0
                    ? "#34495e"
                    : rowIndex % 2 === 0
                    ? "#ecf0f1"
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
                  return "#bdc3c7";
                },
                vLineColor: function () {
                  return "#bdc3c7";
                },
              };
            }
          },
          exportOptions: {
            columns: ":visible",
            orthogonal: "export",
          },
        },
        {
          extend: "print",
          className: "dt-button btn-print",
          text: '<i class="fas fa-print mr-1"></i> Imprimir',
          exportOptions: {
            columns: ":visible",
            orthogonal: "export",
          },
        },
      ],
      dom: '<"flex justify-between items-center mb-4"<"flex-1"B><"flex items-center gap-4"l f>>rt<"flex justify-between items-center mt-4"<"flex-1"i><"flex-1 text-center"p>>',
      responsive: true,
      order: [[7, "asc"]], // Ordenar por Total Gastos (ahora columna 6) ascendente
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
        var buttonsContainer = document.querySelector(".dt-buttons");
        if (buttonsContainer) {
          buttonsContainer.style.display = "flex";
          buttonsContainer.style.flexWrap = "wrap";
          buttonsContainer.style.gap = "8px";
        }
        setTimeout(function () {
          document.querySelectorAll(".dt-button").forEach(function (btn) {
            btn.style.fontFamily = "inherit";
            btn.style.fontSize = "14px";
            btn.style.lineHeight = "1.5";
            btn.style.transition = "all 0.2s ease";
            btn.style.cursor = "pointer";
          });
          stylePaginationControls();
          styleLengthMenu();
        }, 100);
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
        paginateContainer.style.display = "block";
        paginateContainer.style.textAlign = "center";
      }
      document.querySelectorAll(".paginate_button").forEach(function (button) {
        button.style.display = "inline-block";
        button.style.visibility = "visible";
      });
    }
    function styleLengthMenu() {
      var lengthSelect = document.querySelector(".dataTables_length select");
      if (lengthSelect) {
        lengthSelect.style.backgroundColor = "white";
        lengthSelect.style.border = "1px solid #d1d5db";
        lengthSelect.style.borderRadius = "6px";
        lengthSelect.style.padding = "6px 12px";
        lengthSelect.style.fontSize = "14px";
        lengthSelect.style.color = "#374151";
        lengthSelect.style.marginLeft = "8px";
        lengthSelect.style.marginRight = "8px";
      }
      var lengthLabel = document.querySelector(".dataTables_length");
      if (lengthLabel) {
        lengthLabel.style.fontSize = "14px";
        lengthLabel.style.color = "#6b7280";
        lengthLabel.style.fontWeight = "500";
      }
    }
    setTimeout(function () {
      var copyBtn = document.querySelector(".dt-button.btn-copy");
      if (copyBtn) {
        copyBtn.style.backgroundColor = "#3B82F6";
        copyBtn.style.color = "white";
        copyBtn.style.border = "none";
        copyBtn.style.padding = "6px 12px";
        copyBtn.style.borderRadius = "6px";
        copyBtn.style.marginRight = "8px";
        copyBtn.style.fontWeight = "500";
      }
      var csvBtn = document.querySelector(".dt-button.btn-csv");
      if (csvBtn) {
        csvBtn.style.backgroundColor = "#10B981";
        csvBtn.style.color = "white";
        csvBtn.style.border = "none";
        csvBtn.style.padding = "6px 12px";
        csvBtn.style.borderRadius = "6px";
        csvBtn.style.marginRight = "8px";
        csvBtn.style.fontWeight = "500";
      }
      var excelBtn = document.querySelector(".dt-button.btn-excel");
      if (excelBtn) {
        excelBtn.style.backgroundColor = "#059669";
        excelBtn.style.color = "white";
        excelBtn.style.border = "none";
        excelBtn.style.padding = "6px 12px";
        excelBtn.style.borderRadius = "6px";
        excelBtn.style.marginRight = "8px";
        excelBtn.style.fontWeight = "500";
      }
      var pdfBtn = document.querySelector(".dt-button.btn-pdf");
      if (pdfBtn) {
        pdfBtn.style.backgroundColor = "#EF4444";
        pdfBtn.style.color = "white";
        pdfBtn.style.border = "none";
        pdfBtn.style.padding = "6px 12px";
        pdfBtn.style.borderRadius = "6px";
        pdfBtn.style.marginRight = "8px";
        pdfBtn.style.fontWeight = "500";
      }
      var printBtn = document.querySelector(".dt-button.btn-print");
      if (printBtn) {
        printBtn.style.backgroundColor = "#8B5CF6";
        printBtn.style.color = "white";
        printBtn.style.border = "none";
        printBtn.style.padding = "6px 12px";
        printBtn.style.borderRadius = "6px";
        printBtn.style.marginRight = "8px";
        printBtn.style.fontWeight = "500";
      }
    }, 100);
  } catch (error) {
    console.error("Error al inicializar DataTable:", error);
  }
});
