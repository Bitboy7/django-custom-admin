// Inicialización de gráficos para balances
var gastosChart = null;
var distribucionChart = null;

function createGastosCategoriasChart() {
  // Verificar que el elemento canvas exista
  var ctxCategorias = document.getElementById("gastosCategoriasChart");
  if (!ctxCategorias) {
    console.log("Elemento canvas no encontrado aún, intentando de nuevo...");
    return false;
  }

  // Verificar que los datos estén disponibles
  if (
    !window.balancesCategoriasLabels ||
    !window.balancesCategoriasData ||
    window.balancesCategoriasLabels.length === 0
  ) {
    console.log("Datos de gráfico no disponibles aún, intentando de nuevo...");
    return false;
  }

  ctxCategorias = ctxCategorias.getContext("2d");

  var colors = [
    "rgba(54, 162, 235, 0.7)",
    "rgba(255, 99, 132, 0.7)",
    "rgba(255, 206, 86, 0.7)",
    "rgba(75, 192, 192, 0.7)",
    "rgba(153, 102, 255, 0.7)",
    "rgba(255, 159, 64, 0.7)",
    "rgba(199, 199, 199, 0.7)",
    "rgba(83, 102, 255, 0.7)",
    "rgba(40, 159, 64, 0.7)",
    "rgba(210, 199, 199, 0.7)",
  ];

  var labels = window.balancesCategoriasLabels;
  var data = window.balancesCategoriasData;
  var backgroundColors = [];

  for (var i = 0; i < labels.length; i++) {
    backgroundColors.push(colors[i % colors.length]);
  }

  // Ordenar los datos de mayor a menor
  var combinado = [];
  for (var j = 0; j < labels.length; j++) {
    combinado.push({
      label: labels[j],
      data: data[j],
      color: backgroundColors[j],
    });
  }
  combinado.sort(function (a, b) {
    return b.data - a.data;
  });

  labels = combinado.map(function (item) {
    return item.label;
  });
  data = combinado.map(function (item) {
    return item.data;
  });
  backgroundColors = combinado.map(function (item) {
    return item.color;
  });

  if (labels.length > 0) {
    try {
      // Destruir gráfico anterior si existe
      if (gastosChart) {
        gastosChart.destroy();
      }

      gastosChart = new Chart(ctxCategorias, {
        type: "bar",
        data: {
          labels: labels,
          datasets: [
            {
              label: "Gastos por Categoría",
              data: data,
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
              callbacks: {
                label: function (context) {
                  return (
                    "$" +
                    new Intl.NumberFormat("es-MX", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 4,
                    }).format(context.parsed.x)
                  );
                },
              },
            },
          },
          scales: {
            x: {
              beginAtZero: true,
              ticks: {
                callback: function (value) {
                  return (
                    "$" +
                    new Intl.NumberFormat("es-MX", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 4,
                    }).format(value)
                  );
                },
              },
            },
            y: {
              ticks: { font: { weight: "bold" } },
            },
          },
          animation: {
            duration: 2000,
            easing: "easeOutQuart",
          },
        },
      });
      console.log("Gráfico de categorías creado exitosamente");
      return true;
    } catch (error) {
      console.error("Error al crear el gráfico de barras:", error);
      return false;
    }
  } else {
    document.querySelector("#gastosCategoriasChart").closest("div").innerHTML =
      '<div class="flex flex-col items-center justify-center h-full"><i class="fas fa-info-circle text-gray-300 text-4xl mb-2"></i><p class="text-gray-500">No hay datos disponibles para mostrar</p></div>';
    return true;
  }
}

function createDistribucionGastosChart() {
  // Gráfico de distribución de gastos (pie chart)
  var ctxDistribucion = document.getElementById("distribucionGastosChart");

  if (!ctxDistribucion) {
    console.log("Elemento canvas de distribución no encontrado aún");
    return false;
  }

  if (
    !window.balancesCategoriasLabels ||
    !window.balancesCategoriasData ||
    window.balancesCategoriasLabels.length === 0
  ) {
    console.log("Datos para gráfico de distribución no disponibles aún");
    return false;
  }

  ctxDistribucion = ctxDistribucion.getContext("2d");
  var labels = window.balancesCategoriasLabels;
  var data = window.balancesCategoriasData;
  var colors = [
    "rgba(54, 162, 235, 0.7)",
    "rgba(255, 99, 132, 0.7)",
    "rgba(255, 206, 86, 0.7)",
    "rgba(75, 192, 192, 0.7)",
    "rgba(153, 102, 255, 0.7)",
    "rgba(255, 159, 64, 0.7)",
    "rgba(199, 199, 199, 0.7)",
    "rgba(83, 102, 255, 0.7)",
    "rgba(40, 159, 64, 0.7)",
    "rgba(210, 199, 199, 0.7)",
  ];

  var backgroundColors = [];
  for (var i = 0; i < labels.length; i++) {
    backgroundColors.push(colors[i % colors.length]);
  }

  try {
    // Destruir gráfico anterior si existe
    if (distribucionChart) {
      distribucionChart.destroy();
    }

    distribucionChart = new Chart(ctxDistribucion, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [
          {
            data: data,
            backgroundColor: backgroundColors,
            borderColor: backgroundColors.map((color) =>
              color.replace("0.7", "1")
            ),
            borderWidth: 1,
            hoverOffset: 10,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "right",
            labels: { boxWidth: 12, padding: 10 },
          },
          tooltip: {
            callbacks: {
              label: function (context) {
                var label = context.label || "";
                var value = context.parsed || 0;
                var total = context.dataset.data.reduce((a, b) => a + b, 0);
                var percentage = ((value * 100) / total).toFixed(1);
                return (
                  label +
                  ": $" +
                  new Intl.NumberFormat("en-US", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  }).format(value) +
                  " (" +
                  percentage +
                  "%)"
                );
              },
            },
          },
        },
        animation: {
          animateRotate: true,
          animateScale: true,
          duration: 1500,
        },
      },
    });
    console.log("Gráfico de distribución creado exitosamente");
    return true;
  } catch (error) {
    console.error("Error al crear el gráfico de distribución:", error);
    return false;
  }
}

// Función para intentar crear los gráficos con reintentos
function tryCreateCharts(retries = 10) {
  console.log("Intentando crear gráficos... intentos restantes:", retries);

  var categoriasSuccess = createGastosCategoriasChart();
  var distribucionSuccess = createDistribucionGastosChart();

  if (!categoriasSuccess || !distribucionSuccess) {
    if (retries > 0) {
      console.log("Reintentando crear gráficos en 500ms...");
      setTimeout(function () {
        tryCreateCharts(retries - 1);
      }, 500);
    } else {
      console.warn(
        "No se pudieron crear todos los gráficos después de varios intentos"
      );
    }
  } else {
    console.log("Ambos gráficos creados exitosamente");
  }
}

document.addEventListener("DOMContentLoaded", function () {
  // Usar el sistema de reintentos
  setTimeout(function () {
    tryCreateCharts();
  }, 100);
});

// Escuchar evento para actualizar gráficos cuando cambien los datos
window.addEventListener("chartsDataUpdated", function () {
  tryCreateCharts(3); // Menos reintentos para actualizaciones
});
