// Función para extraer texto limpio de HTML
function getCleanTextFromHTML(htmlContent) {
  if (!htmlContent) return "";

  // Si ya es texto plano, devolverlo
  if (typeof htmlContent === "string" && !htmlContent.includes("<")) {
    return htmlContent.trim();
  }

  var tempDiv = document.createElement("div");
  tempDiv.innerHTML = htmlContent;

  // Extraer solo el texto de elementos específicos o todo el texto
  var text = tempDiv.textContent || tempDiv.innerText || "";

  // Limpiar caracteres especiales de formato
  text = text
    .replace(/[\n\r\t]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  return text;
}

// Función para generar el título del reporte según los filtros aplicados
function getReportTitle() {
  var urlParams = new URLSearchParams(window.location.search);
  var titleParts = [];

  // Obtener información de los filtros
  var cuentaId = urlParams.get("cuenta_id");
  var sucursalId = urlParams.get("sucursal_id");
  var year = urlParams.get("year");
  var month = urlParams.get("month");
  var periodo = urlParams.get("periodo");

  // Agregar filtro de cuenta
  if (cuentaId) {
    var cuentaSelect = document.getElementById("cuenta_id");
    if (cuentaSelect && cuentaSelect.selectedIndex >= 0) {
      var selectedOption = cuentaSelect.options[cuentaSelect.selectedIndex];
      if (selectedOption && selectedOption.text !== "Todas") {
        titleParts.push("Cuenta: " + selectedOption.text);
      }
    }
  }

  // Agregar filtro de sucursal
  if (sucursalId) {
    var sucursalSelect = document.getElementById("sucursal_id");
    if (sucursalSelect && sucursalSelect.selectedIndex >= 0) {
      var selectedOption = sucursalSelect.options[sucursalSelect.selectedIndex];
      if (selectedOption && selectedOption.text !== "Todas") {
        titleParts.push("Sucursal: " + selectedOption.text);
      }
    }
  }

  // Agregar filtro de año
  if (year) {
    titleParts.push("Año: " + year);
  }

  // Agregar filtro de mes
  if (month) {
    var monthNames = [
      "Enero",
      "Febrero",
      "Marzo",
      "Abril",
      "Mayo",
      "Junio",
      "Julio",
      "Agosto",
      "Septiembre",
      "Octubre",
      "Noviembre",
      "Diciembre",
    ];
    var monthIndex = parseInt(month) - 1;
    if (monthIndex >= 0 && monthIndex < 12) {
      titleParts.push("Mes: " + monthNames[monthIndex]);
    }
  }

  // Agregar filtro de periodo
  if (periodo) {
    var periodos = {
      diario: "Diario",
      semanal: "Semanal",
      mensual: "Mensual",
    };
    titleParts.push("Período: " + (periodos[periodo] || periodo));
  }

  // Construir título completo
  if (titleParts.length > 0) {
    return "Reporte de gastos - " + titleParts.join(" | ");
  } else {
    return "Reporte de gastos - General";
  }
}

// Función para obtener la fecha actual formateada
function getCurrentDateFormatted() {
  var now = new Date();
  var day = String(now.getDate()).padStart(2, "0");
  var month = String(now.getMonth() + 1).padStart(2, "0");
  var year = now.getFullYear();
  var hours = String(now.getHours()).padStart(2, "0");
  var minutes = String(now.getMinutes()).padStart(2, "0");

  return day + "/" + month + "/" + year + " " + hours + ":" + minutes;
}

// Obtiene un valor numérico robusto desde una celda (TD),
// soportando formatos: "1,234.56", "1.234,56", "$ 1,234.56", "MXN 1.234,56", "720 749.86", etc.
function getNumericValueFromNode(node) {
  if (!node) return NaN;
  var dataOrder = node.getAttribute && node.getAttribute("data-order");
  var source = dataOrder || node.textContent || node.innerText || "";
  if (typeof source !== "string") source = String(source);

  // Primero, remover símbolos de moneda y espacios múltiples
  var cleanSource = source
    .replace(/[\$€£¥₹₽]/g, "")
    .replace(/\s+/g, " ")
    .trim();

  // Mantener solo dígitos, separadores y signo negativo
  var s = cleanSource.replace(/[^0-9.,-]/g, "").trim();
  if (!s) return NaN;

  var lastDot = s.lastIndexOf(".");
  var lastComma = s.lastIndexOf(",");

  if (lastDot > -1 && lastComma > -1) {
    // Tiene ambos separadores: el último encontrado se asume como separador decimal
    if (lastDot > lastComma) {
      // Punto como decimal: quitar comas de miles
      s = s.replace(/,/g, "");
    } else {
      // Coma como decimal: quitar puntos de miles y convertir coma a punto
      s = s.replace(/\./g, "").replace(",", ".");
    }
  } else if (lastComma > -1) {
    // Solo coma presente
    if (/,-?\d{1,3}$/.test(s) || /,\d{2}$/.test(s)) {
      // Parece decimal con coma
      s = s.replace(/\./g, "").replace(",", ".");
    } else {
      // Coma como miles
      s = s.replace(/,/g, "");
    }
  } else if (lastDot > -1) {
    // Solo punto presente
    if (/\.-?\d{1,3}$/.test(s) || /\.\d{2}$/.test(s)) {
      // Parece decimal con punto -> ya está bien
    } else {
      // Punto como miles
      s = s.replace(/\./g, "");
    }
  }

  var num = parseFloat(s);
  return isNaN(num) ? NaN : num;
}

// Formatea un node numérico según US, con o sin símbolo, para vistas de impresión/PDF
function formatNumericValue(node, includeSymbol) {
  var numValue = getNumericValueFromNode(node);
  if (!isNaN(numValue)) {
    var formatted = numValue.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
    return includeSymbol ? "$" + formatted : formatted;
  }
  var result = "0.00";
  return includeSymbol ? "$" + result : result;
}

document.addEventListener("DOMContentLoaded", function () {
  try {
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
      columnDefs: [
        {
          // Columna #0: Número secuencial - limpiar HTML de botones
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
            format: {
              body: function (data, row, column, node) {
                // Limpiar HTML de todas las columnas
                var cleanData = getCleanTextFromHTML(data);

                // Para columnas numéricas, asegurar formato correcto
                if (column === 6 || column === 7) {
                  // Total y Acumulado (ahora columnas 6 y 7)
                  var n = getNumericValueFromNode(node);
                  return isNaN(n) ? cleanData : n.toFixed(2);
                }

                return cleanData;
              },
            },
          },
        },
        {
          extend: "csv",
          className: "dt-button btn-csv",
          text: '<i class="fas fa-file-csv mr-1"></i> CSV',
          charset: "utf-8",
          bom: true,
          exportOptions: {
            format: {
              body: function (data, row, column, node) {
                // Limpiar HTML de todas las columnas
                var cleanData = getCleanTextFromHTML(data);

                // Para columnas numéricas, asegurar formato correcto
                if (column === 6 || column === 7) {
                  // Total y Acumulado (ahora columnas 6 y 7)
                  var n = getNumericValueFromNode(node);
                  return isNaN(n) ? cleanData : n.toFixed(2);
                }

                return cleanData;
              },
            },
          },
        },
        {
          extend: "excel",
          className: "dt-button btn-excel",
          text: '<i class="fas fa-file-excel mr-1"></i> Excel',
          filename: function () {
            var now = new Date();
            var pad = (n) => n.toString().padStart(2, "0");
            var fecha =
              now.getFullYear() +
              "-" +
              pad(now.getMonth() + 1) +
              "-" +
              pad(now.getDate());
            var hora =
              pad(now.getHours()) +
              "-" +
              pad(now.getMinutes()) +
              "-" +
              pad(now.getSeconds());
            return "gastos-detalle-" + fecha + "-" + hora;
          },
          exportOptions: {
            format: {
              body: function (data, row, column, node) {
                // Limpiar HTML de todas las columnas
                var cleanData = getCleanTextFromHTML(data);

                // Para columnas numéricas, devolver número puro para Excel
                if (column === 6 || column === 7) {
                  // Total y Acumulado (ahora columnas 6 y 7)
                  var n = getNumericValueFromNode(node);
                  return isNaN(n) ? 0 : n;
                }

                return cleanData;
              },
            },
          },
        },
        {
          text: '<i class="fas fa-chart-pie mr-1"></i> Resumen Excel',
          className: "dt-button btn-summary-excel",
          action: function (e, dt, button, config) {
            var categoryTotals = {};
            var table = $("#gastosTable").DataTable();
            var data = table.rows({ search: "applied" }).data();

            // Procesar cada fila para agrupar por categoría
            for (var i = 0; i < data.length; i++) {
              var rowData = data[i];
              // Extraer texto limpio de la categoría (columna 1)
              var categoryHtml = rowData[1];
              var tempDiv = document.createElement("div");
              tempDiv.innerHTML = categoryHtml;
              var category =
                tempDiv.textContent || tempDiv.innerText || categoryHtml;
              category = category.trim();

              // Obtener el total de la fila (columna 6)
              var totalValue = 0;
              var totalCell = table.cell(i, 6).node();
              if (totalCell) {
                totalValue = getNumericValueFromNode(totalCell);
                if (isNaN(totalValue)) totalValue = 0;
              }

              // Sumar al total de la categoría
              if (categoryTotals[category]) {
                categoryTotals[category] += totalValue;
              } else {
                categoryTotals[category] = totalValue;
              }
            }

            // Convertir a array y ordenar por total descendente
            var sortedCategories = Object.keys(categoryTotals)
              .map(function (category) {
                return [category, categoryTotals[category]];
              })
              .sort(function (a, b) {
                return b[1] - a[1];
              });

            // Calcular gran total
            var grandTotal = sortedCategories.reduce(function (sum, item) {
              return sum + item[1];
            }, 0);

            // Crear datos para Excel usando formato CSV (compatible con Excel)
            var csvData = "\uFEFF"; // BOM para UTF-8
            csvData += "Categoría,Total acumulado\n";
            sortedCategories.forEach(function (item) {
              csvData += '"' + item[0] + '",' + item[1].toFixed(2) + "\n";
            });
            csvData += '"TOTAL GENERAL",' + grandTotal.toFixed(2);

            // Crear nombre de archivo
            var now = new Date();
            var pad = (n) => n.toString().padStart(2, "0");
            var fecha =
              now.getFullYear() +
              "-" +
              pad(now.getMonth() + 1) +
              "-" +
              pad(now.getDate());
            var hora =
              pad(now.getHours()) +
              "-" +
              pad(now.getMinutes()) +
              "-" +
              pad(now.getSeconds());
            var filename =
              "gastos-resumen-categorias-" + fecha + "-" + hora + ".csv";

            // Crear y descargar el archivo
            var blob = new Blob([csvData], { type: "text/csv;charset=utf-8;" });
            var link = document.createElement("a");
            var url = URL.createObjectURL(blob);
            link.setAttribute("href", url);
            link.setAttribute("download", filename);
            link.style.visibility = "hidden";
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
          },
        },
        {
          extend: "pdf",
          className: "dt-button btn-pdf",
          text: '<i class="fas fa-file-pdf mr-1"></i> PDF',
          title: "",
          customize: function (doc) {
            // Configurar el título dinámico
            var reportTitle = getReportTitle();
            var currentDate = getCurrentDateFormatted();

            // Configurar documento
            doc.pageOrientation = "landscape";
            doc.pageMargins = [40, 80, 40, 60];

            // Personalizar encabezado con título
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
                    text: "2025 - Agricola de la Costa San Luis S.P.R de R.L.",
                    alignment: "left",
                    style: "footer",
                    margin: [40, 0, 0, 0],
                  },
                  {
                    text:
                      "Página " + currentPage.toString() + " de " + pageCount,
                    alignment: "right",
                    style: "footer",
                    margin: [0, 0, 40, 0],
                  },
                ],
              };
            };

            // Estilos personalizados
            doc.styles.header = {
              fontSize: 14,
              bold: true,
              color: "#2c3e50",
            };

            doc.styles.subheader = {
              fontSize: 10,
              color: "#7f8c8d",
              italics: true,
            };

            doc.styles.footer = {
              fontSize: 8,
              color: "#95a5a6",
            };

            // Estilo de la tabla
            doc.styles.tableHeader = {
              bold: true,
              fontSize: 10,
              color: "white",
              fillColor: "#34495e",
              alignment: "center",
            };

            doc.defaultStyle = {
              fontSize: 9,
            };

            // Ajustar diseño de la tabla
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
            format: {
              body: function (data, row, column, node) {
                // Limpiar HTML de todas las columnas
                var cleanData = getCleanTextFromHTML(data);

                // Para columnas numéricas con símbolo de moneda
                if (column === 6 || column === 7) {
                  // Total y Acumulado (ahora columnas 6 y 7)
                  return formatNumericValue(node, true);
                }

                return cleanData;
              },
            },
          },
        },
        {
          extend: "print",
          className: "dt-button btn-print",
          text: '<i class="fas fa-print mr-1"></i> Imprimir',
          exportOptions: {
            format: {
              body: function (data, row, column, node) {
                // Limpiar HTML de todas las columnas
                var cleanData = getCleanTextFromHTML(data);

                // Para columnas numéricas con símbolo de moneda
                if (column === 6 || column === 7) {
                  // Total y Acumulado (ahora columnas 6 y 7)
                  return formatNumericValue(node, true);
                }

                return cleanData;
              },
            },
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
