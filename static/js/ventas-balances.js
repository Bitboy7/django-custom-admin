/**
 * Configuración específica para el módulo de ventas
 * Maneja DataTables, gráficos y filtros
 */

// Configuración global para DataTables en ventas
$.extend(true, $.fn.dataTable.defaults, {
  responsive: true,
  pageLength: 25,
  lengthMenu: [
    [10, 25, 50, 100, -1],
    [10, 25, 50, 100, "Todos"],
  ],
  language: {
    url: "/static/js/datatables-spanish.json",
  },
  dom: "Bfrtip",
  buttons: [
    {
      extend: "excel",
      title: "Reporte de Ventas",
      text: '<i class="fas fa-file-excel"></i> Excel',
      className: "btn btn-success btn-sm",
      exportOptions: {
        columns: ":visible:not(.no-export)",
      },
    },
    {
      extend: "pdf",
      title: "Reporte de Ventas",
      text: '<i class="fas fa-file-pdf"></i> PDF',
      className: "btn btn-danger btn-sm",
      orientation: "landscape",
      pageSize: "A4",
      exportOptions: {
        columns: ":visible:not(.no-export)",
      },
    },
    {
      extend: "print",
      title: "Reporte de Ventas",
      text: '<i class="fas fa-print"></i> Imprimir',
      className: "btn btn-info btn-sm",
      exportOptions: {
        columns: ":visible:not(.no-export)",
      },
    },
  ],
});

// Función para formatear números como moneda
function formatCurrency(value, currency = "USD") {
  if (value === null || value === undefined || isNaN(value)) {
    return "$0.00";
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(parseFloat(value));
}

// Función para obtener valor numérico de celdas de DataTable
function getNumericValueFromNode(node) {
  if (!node) return 0;

  let text = node.textContent || node.innerText || "";

  // Remover símbolos de moneda, espacios y comas
  let cleanNumber = text.replace(/[\$\s,€£¥₹₽]/g, "");

  // Convertir a número
  let value = parseFloat(cleanNumber);

  return isNaN(value) ? 0 : value;
}

// Función para inicializar gráficos de ventas
function initializeVentasCharts() {
  // Configuración por defecto para todos los gráficos
  Chart.defaults.font.family = "'Inter', 'Segoe UI', 'Arial', sans-serif";
  Chart.defaults.font.size = 12;
  Chart.defaults.color = "#374151";

  // Paleta de colores personalizada
  const colorPalette = {
    primary: "#10B981",
    secondary: "#3B82F6",
    success: "#059669",
    warning: "#F59E0B",
    danger: "#EF4444",
    info: "#06B6D4",
    purple: "#8B5CF6",
    gray: "#6B7280",
  };

  // Gráfico de modalidades de pago
  const modalidadCtx = document.getElementById("modalidadChart");
  if (
    modalidadCtx &&
    window.ventasModalidadData &&
    window.ventasModalidadData.length > 0
  ) {
    const modalidadLabels = window.ventasModalidadData.map((item) =>
      item.modalidad_pago === "Contado" ? "Contado" : "Crédito"
    );
    const modalidadValues = window.ventasModalidadData.map((item) =>
      parseFloat(item.total || 0)
    );

    new Chart(modalidadCtx, {
      type: "doughnut",
      data: {
        labels: modalidadLabels,
        datasets: [
          {
            data: modalidadValues,
            backgroundColor: [colorPalette.success, colorPalette.warning],
            hoverBackgroundColor: ["#047857", "#D97706"],
            borderWidth: 2,
            borderColor: "#ffffff",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              padding: 15,
              usePointStyle: true,
              pointStyle: "circle",
            },
          },
          tooltip: {
            callbacks: {
              label: function (context) {
                const label = context.label || "";
                const value = formatCurrency(context.parsed);
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = ((context.parsed / total) * 100).toFixed(1);
                return `${label}: ${value} (${percentage}%)`;
              },
            },
          },
        },
        animation: {
          animateRotate: true,
          animateScale: false,
          duration: 1000,
        },
      },
    });
  }

  // Gráfico de estados de cobranza
  const estadosCtx = document.getElementById("estadosChart");
  if (
    estadosCtx &&
    window.ventasEstadosData &&
    window.ventasEstadosData.length > 0
  ) {
    const estadosLabels = window.ventasEstadosData.map((item) => {
      const estado = item.estado_cobranza;
      const displayNames = {
        Pagado: "Pagado",
        Pendiente: "Pendiente",
        Parcial: "Parcial",
        Vencido: "Vencido",
        Incobrable: "Incobrable",
      };
      return displayNames[estado] || estado;
    });

    const estadosValues = window.ventasEstadosData.map((item) =>
      parseFloat(item.total || 0)
    );

    const estadosColors = window.ventasEstadosData.map((item) => {
      const estado = item.estado_cobranza;
      const colorMap = {
        Pagado: colorPalette.success,
        Pendiente: colorPalette.warning,
        Parcial: colorPalette.info,
        Vencido: colorPalette.danger,
        Incobrable: colorPalette.gray,
      };
      return colorMap[estado] || colorPalette.purple;
    });

    new Chart(estadosCtx, {
      type: "pie",
      data: {
        labels: estadosLabels,
        datasets: [
          {
            data: estadosValues,
            backgroundColor: estadosColors,
            borderWidth: 2,
            borderColor: "#ffffff",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              padding: 15,
              usePointStyle: true,
              pointStyle: "circle",
            },
          },
          tooltip: {
            callbacks: {
              label: function (context) {
                const label = context.label || "";
                const value = formatCurrency(context.parsed);
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = ((context.parsed / total) * 100).toFixed(1);
                return `${label}: ${value} (${percentage}%)`;
              },
            },
          },
        },
        animation: {
          animateRotate: true,
          animateScale: false,
          duration: 1000,
        },
      },
    });
  }

  // Gráfico de top clientes
  const clientesCtx = document.getElementById("clientesChart");
  if (
    clientesCtx &&
    window.ventasClientesData &&
    window.ventasClientesData.length > 0
  ) {
    const clientesLabels = window.ventasClientesData.map((item) => {
      const nombre = item.cliente__nombre || "Sin nombre";
      return nombre.length > 20 ? nombre.substring(0, 17) + "..." : nombre;
    });

    const clientesValues = window.ventasClientesData.map((item) =>
      parseFloat(item.total || 0)
    );

    // Crear gradiente para las barras
    const gradient = clientesCtx
      .getContext("2d")
      .createLinearGradient(0, 0, 400, 0);
    gradient.addColorStop(0, colorPalette.primary);
    gradient.addColorStop(1, colorPalette.success);

    new Chart(clientesCtx, {
      type: "bar",
      data: {
        labels: clientesLabels,
        datasets: [
          {
            label: "Ventas",
            data: clientesValues,
            backgroundColor: gradient,
            borderColor: colorPalette.primary,
            borderWidth: 1,
            borderRadius: 4,
            borderSkipped: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: "y",
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            callbacks: {
              title: function (context) {
                // Mostrar el nombre completo en el tooltip
                const index = context[0].dataIndex;
                return window.ventasClientesData[index].cliente__nombre;
              },
              label: function (context) {
                return "Ventas: " + formatCurrency(context.parsed.x);
              },
            },
          },
        },
        scales: {
          x: {
            beginAtZero: true,
            ticks: {
              callback: function (value) {
                return formatCurrency(value);
              },
            },
            grid: {
              color: "rgba(0, 0, 0, 0.05)",
            },
          },
          y: {
            grid: {
              display: false,
            },
          },
        },
        animation: {
          duration: 1500,
          easing: "easeOutQuart",
        },
      },
    });
  }
}

// Función para manejar filtros dinámicos
function handleVentasFilters() {
  // Manejar cambio de período
  $("#periodo").on("change", function () {
    const periodo = $(this).val();

    if (periodo === "diario") {
      $("#filtro-diario-opciones").slideDown(300);
    } else {
      $("#filtro-diario-opciones").slideUp(300);
    }
  });

  // Manejar radio buttons para día específico vs rango
  $('input[name="tipo_fecha"]').on("change", function () {
    const tipoCambiado = $(this).val();

    if (tipoCambiado === "dia") {
      $("#campo-dia-especifico").slideDown(300);
      $("#campos-rango-fechas").slideUp(300);
      // Limpiar campos de rango
      $("#fecha_inicio").val("");
      $("#fecha_fin").val("");
    } else if (tipoCambiado === "rango") {
      $("#campo-dia-especifico").slideUp(300);
      $("#campos-rango-fechas").slideDown(300);
      // Limpiar campo de día específico
      $("#dia").val("");
    }
  });

  // Validación de rango de fechas
  $("#fecha_inicio, #fecha_fin").on("change", function () {
    const fechaInicio = $("#fecha_inicio").val();
    const fechaFin = $("#fecha_fin").val();

    if (fechaInicio && fechaFin) {
      const inicio = new Date(fechaInicio);
      const fin = new Date(fechaFin);

      if (inicio > fin) {
        alert("La fecha de inicio no puede ser posterior a la fecha de fin.");
        $(this).val("");
      }
    }
  });
}

// Función para mostrar/ocultar toast de notificación
function showVentasToast(title, message, type = "success") {
  const toast = document.getElementById("toast-notification");
  const toastTitle = document.getElementById("toast-title");
  const toastMessage = document.getElementById("toast-message");

  if (toast && toastTitle && toastMessage) {
    toastTitle.textContent = title;
    toastMessage.textContent = message;

    // Cambiar colores según el tipo
    const toastContent = toast.querySelector("div");
    toastContent.className = toastContent.className.replace(
      /from-\w+-50/g,
      `from-${type === "error" ? "red" : "green"}-50`
    );
    toastContent.className = toastContent.className.replace(
      /to-\w+-50/g,
      `to-${type === "error" ? "red" : "green"}-50`
    );
    toastContent.className = toastContent.className.replace(
      /border-\w+-500/g,
      `border-${type === "error" ? "red" : "green"}-500`
    );

    toast.classList.remove("translate-x-full", "opacity-0");

    setTimeout(() => {
      hideVentasToast();
    }, 5000);
  }
}

function hideVentasToast() {
  const toast = document.getElementById("toast-notification");
  if (toast) {
    toast.classList.add("translate-x-full", "opacity-0");
  }
}

// Inicialización cuando el documento esté listo
$(document).ready(function () {
  // Inicializar filtros
  handleVentasFilters();

  // Inicializar DataTable si existe
  if ($("#ventasTable").length) {
    // Destruir instancia existente si existe
    if ($.fn.DataTable.isDataTable("#ventasTable")) {
      $("#ventasTable").DataTable().destroy();
    }

    const table = $("#ventasTable").DataTable({
      responsive: true,
      pageLength: 25,
      lengthMenu: [
        [10, 25, 50, 100, -1],
        [10, 25, 50, 100, "Todos"],
      ],
      order: [[0, "asc"]],
      columnDefs: [
        {
          targets: [6, 7, 8, 10], // Columnas de moneda
          type: "num-fmt",
          className: "text-right",
        },
        {
          targets: [9], // Columna de estado/fecha límite
          className: "text-center",
        },
      ],
      dom: "Bfrtip",
      buttons: [
        {
          extend: "excel",
          title: "Análisis de Ventas - " + new Date().toLocaleDateString(),
          text: '<i class="fas fa-file-excel"></i> Excel',
          className: "btn btn-success btn-sm",
          exportOptions: {
            columns: ":visible",
          },
        },
        {
          extend: "pdf",
          title: "Análisis de Ventas",
          text: '<i class="fas fa-file-pdf"></i> PDF',
          className: "btn btn-danger btn-sm",
          orientation: "landscape",
          pageSize: "A4",
          exportOptions: {
            columns: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], // Incluir todas las columnas relevantes para PDF
          },
        },
        {
          extend: "print",
          title: "Análisis de Ventas",
          text: '<i class="fas fa-print"></i> Imprimir',
          className: "btn btn-info btn-sm",
          exportOptions: {
            columns: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
          },
        },
      ],
      language: {
        url: "/static/js/datatables-spanish.json",
      },
    });

    // Agregar funcionalidad de búsqueda avanzada
    table.on("search.dt", function () {
      const searchTerm = table.search();
      if (searchTerm.length > 0) {
        showVentasToast("Búsqueda aplicada", `Filtrando por: "${searchTerm}"`);
      }
    });
  }

  // Inicializar gráficos después de un pequeño delay para asegurar que el DOM esté listo
  setTimeout(() => {
    initializeVentasCharts();
  }, 500);

  // Mostrar toast si hay parámetros en la URL (filtros aplicados)
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.toString()) {
    showVentasToast(
      "¡Filtros aplicados!",
      "Los datos han sido filtrados según sus criterios."
    );
  }

  // Manejar envío del formulario con validación
  $("form").on("submit", function (e) {
    const periodo = $("#periodo").val();

    if (periodo === "diario") {
      const tipoFecha = $('input[name="tipo_fecha"]:checked').val();
      const dia = $("#dia").val();
      const fechaInicio = $("#fecha_inicio").val();
      const fechaFin = $("#fecha_fin").val();

      if (tipoFecha === "dia" && !dia) {
        e.preventDefault();
        showVentasToast(
          "Error",
          "Por favor seleccione un día específico.",
          "error"
        );
        return false;
      }

      if (tipoFecha === "rango" && (!fechaInicio || !fechaFin)) {
        e.preventDefault();
        showVentasToast(
          "Error",
          "Por favor complete el rango de fechas.",
          "error"
        );
        return false;
      }
    }

    // Mostrar indicador de carga
    const submitBtn = $(this).find('button[type="submit"]');
    const originalText = submitBtn.html();
    submitBtn
      .html('<i class="fas fa-spinner fa-spin mr-2"></i>Procesando...')
      .prop("disabled", true);

    // Restaurar botón después de un tiempo (por si hay error)
    setTimeout(() => {
      submitBtn.html(originalText).prop("disabled", false);
    }, 10000);
  });
});

// Exponer funciones globalmente para uso en otros scripts
window.VentasModule = {
  formatCurrency: formatCurrency,
  getNumericValueFromNode: getNumericValueFromNode,
  showToast: showVentasToast,
  hideToast: hideVentasToast,
  initCharts: initializeVentasCharts,
};
