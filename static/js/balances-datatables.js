// Inicialización de DataTables para balances

function formatNumericValue(node, includeSymbol) {
  var dataOrder = node.getAttribute("data-order");
  if (dataOrder) {
    var normalizedValue = dataOrder.replace(",", ".");
    var numValue = parseFloat(normalizedValue);
    if (!isNaN(numValue)) {
      var formatted = numValue.toFixed(2);
      return includeSymbol ? "$" + formatted : formatted;
    }
  }
  var textContent = node.textContent || node.innerText || "";
  var cleanNumber = textContent.replace(/[$\s]/g, "");
  if (cleanNumber.indexOf(",") > cleanNumber.lastIndexOf(".")) {
    cleanNumber = cleanNumber.replace(/\./g, "").replace(",", ".");
  } else {
    cleanNumber = cleanNumber.replace(/,/g, "");
  }
  var numValue = parseFloat(cleanNumber);
  var result = isNaN(numValue) ? "0.00" : numValue.toFixed(2);
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
          targets: [5],
          render: function (data, type, row) {
            if (type === "export" || type === "copy") {
              var tempDiv = document.createElement("div");
              tempDiv.innerHTML = data;
              return tempDiv.textContent || tempDiv.innerText || "";
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
                if (column === 5) {
                  var tempDiv = document.createElement("div");
                  tempDiv.innerHTML = data;
                  return tempDiv.textContent || tempDiv.innerText || "";
                }
                if (column === 7 || column === 8) {
                  return formatNumericValue(node, false);
                }
                return data;
              },
            },
          },
        },
        {
          extend: "csv",
          className: "dt-button btn-csv",
          text: '<i class="fas fa-file-csv mr-1"></i> CSV',
          exportOptions: {
            format: {
              body: function (data, row, column, node) {
                if (column === 5) {
                  var tempDiv = document.createElement("div");
                  tempDiv.innerHTML = data;
                  return tempDiv.textContent || tempDiv.innerText || "";
                }
                if (column === 7 || column === 8) {
                  return formatNumericValue(node, false);
                }
                return data;
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
            return "gastos-acumulados-" + fecha + "-" + hora;
          },
          exportOptions: {
            format: {
              body: function (data, row, column, node) {
                if (column === 5) {
                  var tempDiv = document.createElement("div");
                  tempDiv.innerHTML = data;
                  return tempDiv.textContent || tempDiv.innerText || "";
                }
                if (column === 7 || column === 8) {
                  return formatNumericValue(node, false);
                }
                return data;
              },
            },
          },
        },
        {
          extend: "pdf",
          className: "dt-button btn-pdf",
          text: '<i class="fas fa-file-pdf mr-1"></i> PDF',
          exportOptions: {
            format: {
              body: function (data, row, column, node) {
                if (column === 5) {
                  var tempDiv = document.createElement("div");
                  tempDiv.innerHTML = data;
                  return tempDiv.textContent || tempDiv.innerText || "";
                }
                if (column === 7 || column === 8) {
                  return formatNumericValue(node, true);
                }
                return data;
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
                if (column === 5) {
                  var tempDiv = document.createElement("div");
                  tempDiv.innerHTML = data;
                  return tempDiv.textContent || tempDiv.innerText || "";
                }
                if (column === 7 || column === 8) {
                  return formatNumericValue(node, true);
                }
                return data;
              },
            },
          },
        },
      ],
      dom: '<"flex justify-between items-center mb-4"<"flex-1"B><"flex items-center gap-4"l f>>rt<"flex justify-between items-center mt-4"<"flex-1"i><"flex-1 text-center"p>>',
      responsive: true,
      order: [[6, "desc"]],
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
