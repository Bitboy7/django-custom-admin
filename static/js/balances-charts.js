// Inicialización de gráficos para balances

document.addEventListener("DOMContentLoaded", function () {
  // Crear gráfico de barras horizontal para categorías
  var ctxCategorias = document.getElementById("gastosCategoriasChart");
  if (!ctxCategorias) {
    console.error(
      "No se encontró el elemento canvas para el gráfico de categorías"
    );
    return;
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
  var categorias = {};
  // Los datos de balances se deben inyectar como variables JS desde Django si se quiere separar completamente
  // Aquí se asume que el template sigue generando el bloque de extracción de datos
  // ...
  // Este bloque debe ser reemplazado por un script inline que defina window.balancesCategoriasData y window.balancesCategoriasLabels
  // ...
  // Para mantener la separación, aquí solo va la lógica de gráficos
  if (window.balancesCategoriasLabels && window.balancesCategoriasData) {
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
        new Chart(ctxCategorias, {
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
                      new Intl.NumberFormat("en-US").format(
                        context.parsed.x.toFixed(2)
                      )
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
                    return "$" + value.toLocaleString();
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
      } catch (error) {
        console.error("Error al crear el gráfico de barras:", error);
      }
    } else {
      document
        .querySelector("#gastosCategoriasChart")
        .closest("div").innerHTML =
        '<div class="flex flex-col items-center justify-center h-full"><i class="fas fa-info-circle text-gray-300 text-4xl mb-2"></i><p class="text-gray-500">No hay datos disponibles para mostrar</p></div>';
    }
  }
  // Gráfico de distribución de gastos (pie chart)
  var ctxDistribucion = document.getElementById("distribucionGastosChart");
  if (
    ctxDistribucion &&
    window.balancesCategoriasLabels &&
    window.balancesCategoriasLabels.length > 0
  ) {
    ctxDistribucion = ctxDistribucion.getContext("2d");
    var labels = window.balancesCategoriasLabels;
    var data = window.balancesCategoriasData;
    var backgroundColors = [];
    for (var i = 0; i < labels.length; i++) {
      backgroundColors.push(colors[i % colors.length]);
    }
    try {
      new Chart(ctxDistribucion, {
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
                    value.toLocaleString() +
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
    } catch (error) {
      console.error("Error al crear el gráfico de distribución:", error);
    }
  } else if (ctxDistribucion) {
    document
      .querySelector("#distribucionGastosChart")
      .closest("div").innerHTML =
      '<div class="flex flex-col items-center justify-center h-full"><i class="fas fa-info-circle text-gray-300 text-4xl mb-2"></i><p class="text-gray-500">No hay datos disponibles para mostrar</p></div>';
  }
});
