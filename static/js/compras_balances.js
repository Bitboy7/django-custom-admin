$(document).ready(function () {
  // Mostrar notificación toast si se han aplicado filtros
  if (window.hasFilters) {
    showToast(
      "¡Filtros aplicados!",
      "La información ha sido filtrada según los criterios seleccionados."
    );
  }

  // Funciones para el manejo del toast
  function showToast(title, message, duration = 5000) {
    const toast = document.getElementById("toast-notification");
    if (toast) {
      document.getElementById("toast-title").textContent = title;
      document.getElementById("toast-message").textContent = message;
      toast.classList.remove("translate-x-full", "opacity-0");
      toast.classList.add("translate-x-0", "opacity-100");
      setTimeout(() => {
        hideToast();
      }, duration);
    }
  }

  window.hideToast = function () {
    const toast = document.getElementById("toast-notification");
    if (toast) {
      toast.classList.add("translate-x-full", "opacity-0");
      toast.classList.remove("translate-x-0", "opacity-100");
    }
  };

  // Función auxiliar para formatear valores numéricos en exportaciones
  function formatNumericValue(node, includeSymbol = false) {
    var dataOrder = node.getAttribute("data-order");
    if (dataOrder) {
      // Limpiar el valor data-order de cualquier texto adicional (MXN, $, etc.)
      var cleanValue = dataOrder.toString().replace(/[^0-9.-]/g, "");
      var numValue = parseFloat(cleanValue);
      if (!isNaN(numValue)) {
        var formatted = numValue.toLocaleString("en-US", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        });
        return includeSymbol ? "$" + formatted : formatted;
      }
    }

    var textContent = node.textContent || node.innerText || "";

    // Limpiar el texto de símbolos y espacios
    var cleanNumber = textContent.replace(/[$\s]/g, "");

    // Si ya está en formato US (1,234.56), convertir a número
    if (cleanNumber.match(/^\d{1,3}(,\d{3})*(\.\d{2})?$/)) {
      // Formato US válido: remover comas para parseFloat
      var numValue = parseFloat(cleanNumber.replace(/,/g, ""));
      if (!isNaN(numValue)) {
        var formatted = numValue.toLocaleString("en-US", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        });
        return includeSymbol ? "$" + formatted : formatted;
      }
    }

    // Fallback: intentar parsear directamente removiendo todas las comas
    var numValue = parseFloat(cleanNumber.replace(/,/g, ""));
    if (!isNaN(numValue)) {
      var formatted = numValue.toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
      return includeSymbol ? "$" + formatted : formatted;
    }

    return includeSymbol ? "$0.00" : "0.00";
  }

  // Inicializar DataTable
  $("#comprasTable").DataTable({
    responsive: true,
    pageLength: 25,
    language: {
      url: "//cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json",
    },
    columnDefs: [
      { responsivePriority: 1, targets: [0, 1, 7, 8] },
      { responsivePriority: 2, targets: [2, 3, 4] },
      { responsivePriority: 3, targets: [5, 6] },
    ],
    dom: "Bfrtip",
    buttons: [
      {
        extend: "copy",
        className: "dt-button btn-copy",
        text: '<i class="fas fa-copy mr-1"></i> Copiar',
        exportOptions: {
          format: {
            body: function (data, row, column, node) {
              if (column === 3) {
                return node.textContent.trim();
              } else if (column === 5) {
                return formatNumericValue(node, false);
              } else if (column === 6 || column === 7 || column === 8) {
                return formatNumericValue(node, true);
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
              if (column === 3) {
                return node.textContent.trim();
              } else if (column === 5) {
                return formatNumericValue(node, false);
              } else if (column === 6 || column === 7 || column === 8) {
                return formatNumericValue(node, true);
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
        exportOptions: {
          format: {
            body: function (data, row, column, node) {
              if (column === 3) {
                return node.textContent.trim();
              } else if (column === 5) {
                return formatNumericValue(node, false);
              } else if (column === 6 || column === 7 || column === 8) {
                return formatNumericValue(node, true);
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
              if (column === 3) {
                return node.textContent.trim();
              } else if (column === 5) {
                return formatNumericValue(node, false);
              } else if (column === 6 || column === 7 || column === 8) {
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
              if (column === 3) {
                return node.textContent.trim();
              } else if (column === 5) {
                return formatNumericValue(node, false);
              } else if (column === 6 || column === 7 || column === 8) {
                return formatNumericValue(node, true);
              }
              return data;
            },
          },
        },
      },
    ],
  });

  // Manejar cambios en el periodo seleccionado
  $(".periodo-select").change(function () {
    var periodo = $(this).val();
    if (periodo === "diario") {
      $("#filtro-diario, #filtro-rango").removeClass("hidden");
    } else {
      $("#filtro-diario, #filtro-rango").addClass("hidden");
    }
  });

  // Gráfico de compras mensuales mejorado - AHORA HORIZONTAL
  var ctx = document.getElementById("comprasMensualesChart").getContext("2d");
  var mesesLabels = window.mesesLabels || [];
  var datosCompras = window.datosCompras || [];

  // Generar colores dinámicamente
  var backgroundColors = datosCompras.map((value, index) => {
    const hue = 200 + ((index * 10) % 60);
    return `hsla(${hue}, 70%, 60%, 0.7)`;
  });

  new Chart(ctx, {
    type: "bar",
    data: {
      labels: mesesLabels,
      datasets: [
        {
          label: "Compras por Mes",
          data: datosCompras,
          backgroundColor: backgroundColors,
          borderColor: backgroundColors.map((color) =>
            color.replace("0.7", "1")
          ),
          borderWidth: 1,
          borderRadius: 4,
          maxBarThickness: 30,
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "rgba(0, 0, 0, 0.8)",
          titleFont: { size: 14 },
          bodyFont: { size: 13 },
          callbacks: {
            label: function (context) {
              let label = context.dataset.label || "";
              if (label) {
                label += ": ";
              }
              if (context.parsed.x !== null) {
                label += new Intl.NumberFormat("en-US", {
                  style: "currency",
                  currency: "USD",
                }).format(context.parsed.x);
              }
              return label;
            },
          },
        },
      },
      scales: {
        x: {
          beginAtZero: true,
          grid: { color: "rgba(200, 200, 200, 0.2)" },
          ticks: {
            callback: function (value) {
              return "$" + value.toLocaleString();
            },
            font: { weight: "bold" },
          },
        },
        y: {
          grid: { display: false },
          ticks: { font: { weight: "bold" } },
        },
      },
      animation: { duration: 2000, easing: "easeOutQuart" },
      hover: { mode: "index", intersect: false },
    },
  });
});
