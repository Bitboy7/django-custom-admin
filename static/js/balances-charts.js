// Inicialización de gráficos para balances
var gastosChart = null;
var distribucionChart = null;

/**
 * Genera un color único para cada índice usando el ángulo áureo (137.5°).
 * Garantiza máxima separación perceptual sin importar cuántas categorías haya.
 * Los primeros 12 índices usan una paleta curada; el resto se genera dinámicamente.
 */
// Paleta profesional: azules, teals y neutros cálidos — sin colores estridentes
var _curatedPalette = [
  [30, 86, 179], // blue-700
  [56, 178, 172], // teal-400
  [99, 149, 199], // steel blue
  [15, 118, 110], // teal-700
  [2, 132, 199], // sky-700
  [71, 132, 164], // cadet blue
  [14, 99, 115], // cyan-800
  [147, 179, 216], // muted blue
  [52, 152, 219], // belize hole
  [26, 188, 156], // turquoise
  [96, 125, 139], // blue-grey
  [46, 134, 193], // mid blue
  [93, 173, 226], // soft blue
  [39, 174, 148], // medium teal
  [100, 116, 139], // slate-500
  [180, 138, 90], // warm gold
  [22, 91, 121], // dark teal
  [127, 140, 141], // medium grey
  [155, 182, 196], // pale steel
  [41, 50, 56], // dark navy
];

function generateColor(index, alpha) {
  alpha = alpha !== undefined ? alpha : 0.75;
  if (index < _curatedPalette.length) {
    var c = _curatedPalette[index];
    return "rgba(" + c[0] + "," + c[1] + "," + c[2] + "," + alpha + ")";
  }
  // Golden angle hue rotation para índices más allá de la paleta
  var hue = (index * 137.508) % 360;
  var sat = 55 + (index % 3) * 10; // alterna entre 55%, 65%, 75%
  var lit = 50 + (index % 2) * 8; // alterna entre 50% y 58%
  return "hsla(" + hue.toFixed(1) + "," + sat + "%," + lit + "%," + alpha + ")";
}

function buildColorArrays(count) {
  var bg = [],
    border = [];
  for (var i = 0; i < count; i++) {
    bg.push(generateColor(i, 0.75));
    border.push(generateColor(i, 1));
  }
  return { bg: bg, border: border };
}

/** Convierte HSL a hex (para pdfMake). */
function hslToHex(h, s, l) {
  s /= 100;
  l /= 100;
  var a = s * Math.min(l, 1 - l);
  function f(n) {
    var k = (n + h / 30) % 12;
    var color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
    var hex = Math.round(255 * color).toString(16);
    return hex.length === 1 ? "0" + hex : hex;
  }
  return "#" + f(0) + f(8) + f(4);
}

/** Devuelve el color de la paleta en formato hex (requerido por pdfMake fillColor). */
function paletteHex(index) {
  if (index < _curatedPalette.length) {
    var c = _curatedPalette[index];
    function h(v) {
      var s = v.toString(16);
      return s.length === 1 ? "0" + s : s;
    }
    return "#" + h(c[0]) + h(c[1]) + h(c[2]);
  }
  var hue = (index * 137.508) % 360;
  return hslToHex(hue, 55, 50);
}

/**
 * Lee los filtros activos desde el DOM y los devuelve como array { label, value }.
 * Usado para incluirlos en el encabezado del PDF.
 */
function getFilterSummary() {
  var parts = [];
  var cuentaEl = document.getElementById("cuenta_id");
  if (cuentaEl && cuentaEl.selectedIndex >= 0) {
    parts.push({
      label: "Cuenta",
      value: cuentaEl.options[cuentaEl.selectedIndex].text,
    });
  }
  var sucursalEl = document.getElementById("sucursal_id");
  if (sucursalEl && sucursalEl.selectedIndex >= 0) {
    parts.push({
      label: "Sucursal",
      value: sucursalEl.options[sucursalEl.selectedIndex].text,
    });
  }
  var yearEl = document.getElementById("year");
  if (yearEl) {
    parts.push({ label: "Año", value: yearEl.value });
  }
  var monthsEl = document.getElementById("month-selector-text");
  if (monthsEl) {
    parts.push({ label: "Meses", value: monthsEl.innerText.trim() });
  }
  var periodoEl = document.getElementById("periodo");
  if (periodoEl && periodoEl.selectedIndex >= 0) {
    parts.push({
      label: "Periodo",
      value: periodoEl.options[periodoEl.selectedIndex].text,
    });
  }
  return parts;
}

/* ── Helpers ── */

/** Ajusta el alto del contenedor del gráfico de barras según la cantidad de categorías. */
function resizeBarChart(count) {
  var container = document.getElementById("barChartContainer");
  if (!container) return;
  container.style.height = Math.max(300, count * 34) + "px";
  if (gastosChart) gastosChart.resize();
}

/** Renderiza la leyenda scrollable del donut en #donut-legend. */
function renderDonutLegend(labels, bgColors, data) {
  var el = document.getElementById("donut-legend");
  if (!el) return;
  var total = data.reduce(function (a, b) {
    return a + b;
  }, 0);
  var html = "";
  for (var i = 0; i < labels.length; i++) {
    var pct = total > 0 ? ((data[i] / total) * 100).toFixed(1) : "0.0";
    html +=
      '<div class="donut-legend-item" data-index="' +
      i +
      '" onclick="toggleDonutSlice(' +
      i +
      ')">' +
      '<span class="donut-legend-swatch" style="background:' +
      bgColors[i] +
      '"></span>' +
      '<span class="donut-legend-label" title="' +
      labels[i].replace(/"/g, "&quot;") +
      '">' +
      labels[i] +
      "</span>" +
      '<span class="donut-legend-pct">' +
      pct +
      "%</span>" +
      "</div>";
  }
  el.innerHTML = html;
}

/** Alterna la visibilidad de un segmento del donut al hacer clic en la leyenda. */
function toggleDonutSlice(index) {
  if (!distribucionChart) return;
  var meta = distribucionChart.getDatasetMeta(0);
  var item = meta.data[index];
  item.hidden = !item.hidden;
  distribucionChart.update();
  var el = document.querySelector(
    '.donut-legend-item[data-index="' + index + '"]',
  );
  if (el) el.classList.toggle("hidden-slice", item.hidden);
}

/**
 * Construye las filas de la tabla de categorías para el PDF.
 * El color de la celda swatch se calcula con paletteHex(origIdx) para que coincida
 * con el color que Chart.js asigna a cada categoría según su posición original.
 *
 * @param {string[]} labels - Etiquetas de categorías en el orden original del servidor.
 * @param {number[]} data   - Valores correspondientes (misma longitud que labels).
 * @returns {Array}         - Array de filas pdfMake (incluye fila de encabezado).
 */
function buildCategoryRows(labels, data) {
  var headerRow = [
    { text: "", fillColor: "#1e3a8a", color: "#fff", fontSize: 7 },
    {
      text: "#",
      bold: true,
      fillColor: "#1e3a8a",
      color: "#fff",
      fontSize: 7,
      alignment: "center",
    },
    {
      text: "Categoría",
      bold: true,
      fillColor: "#1e3a8a",
      color: "#fff",
      fontSize: 7,
    },
    {
      text: "Total",
      bold: true,
      fillColor: "#1e3a8a",
      color: "#fff",
      fontSize: 7,
      alignment: "right",
    },
    {
      text: "%",
      bold: true,
      fillColor: "#1e3a8a",
      color: "#fff",
      fontSize: 7,
      alignment: "right",
    },
  ];

  var combined = labels.map(function (l, i) {
    // origIdx preserves the original position so the swatch matches the chart color
    return { l: l, d: data[i], origIdx: i };
  });
  combined.sort(function (a, b) {
    return b.d - a.d;
  });

  var totalData = combined.reduce(function (sum, item) {
    return sum + item.d;
  }, 0);

  var rows = [headerRow];
  combined.forEach(function (item, idx) {
    var formatted =
      "$" +
      new Intl.NumberFormat("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(item.d);
    var pct =
      totalData > 0 ? ((item.d / totalData) * 100).toFixed(1) + "%" : "0.0%";
    // Use origIdx so the hex color matches what Chart.js assigned at that position
    var swatchHex = paletteHex(item.origIdx);
    rows.push([
      { text: " ", fillColor: swatchHex, fontSize: 5 },
      { text: String(idx + 1), fontSize: 7, alignment: "center" },
      { text: item.l, fontSize: 7 },
      { text: formatted, bold: true, fontSize: 7, alignment: "right" },
      { text: pct, fontSize: 7, alignment: "right", color: "#374151" },
    ]);
  });
  return rows;
}

/**
 * Genera un PDF con las estadísticas KPI, ambos gráficos y la tabla de categorías.
 * Requiere pdfMake cargado en la página.
 */
function exportBalancesPDF() {
  if (typeof pdfMake === "undefined") {
    alert(
      "pdfMake no está disponible. Recarga la página e inténtalo de nuevo.",
    );
    return;
  }

  var btn = document.getElementById("btn-export-pdf");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generando...';
  }

  // ─ KPI rows
  var kpiRows = [
    [
      {
        text: "Métrica",
        bold: true,
        fillColor: "#1e3a8a",
        color: "#fff",
        fontSize: 8,
      },
      {
        text: "Valor",
        bold: true,
        fillColor: "#1e3a8a",
        color: "#fff",
        fontSize: 8,
      },
    ],
  ];
  document.querySelectorAll(".kpi-card").forEach(function (card) {
    var label = card.querySelector(".kpi-label")
      ? card.querySelector(".kpi-label").innerText
      : "";
    var value = card.querySelector(".kpi-value")
      ? card.querySelector(".kpi-value").innerText
      : "";
    var sub = card.querySelector(".kpi-sub")
      ? card.querySelector(".kpi-sub").innerText
      : "";
    kpiRows.push([
      { text: label, fontSize: 8 },
      { text: value + (sub ? "  (" + sub + ")" : ""), bold: true, fontSize: 8 },
    ]);
  });

  // ─ Category table rows (swatch | # | Categoría | Total | %)
  var catRows =
    window.balancesCategoriasLabels && window.balancesCategoriasData
      ? buildCategoryRows(
          window.balancesCategoriasLabels,
          window.balancesCategoriasData,
        )
      : [
          [
            { text: "", fillColor: "#1e3a8a", color: "#fff", fontSize: 7 },
            {
              text: "#",
              bold: true,
              fillColor: "#1e3a8a",
              color: "#fff",
              fontSize: 7,
              alignment: "center",
            },
            {
              text: "Categoría",
              bold: true,
              fillColor: "#1e3a8a",
              color: "#fff",
              fontSize: 7,
            },
            {
              text: "Total",
              bold: true,
              fillColor: "#1e3a8a",
              color: "#fff",
              fontSize: 7,
              alignment: "right",
            },
            {
              text: "%",
              bold: true,
              fillColor: "#1e3a8a",
              color: "#fff",
              fontSize: 7,
              alignment: "right",
            },
          ],
        ];

  // ─ Build content
  var now = new Date();
  var dateStr = now.toLocaleDateString("es-MX", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  // ─ Filtros aplicados
  var filterSummary = getFilterSummary();
  var filterRows = filterSummary.map(function (f) {
    return [
      { text: f.label, fontSize: 8, color: "#6b7280", bold: true },
      { text: f.value, fontSize: 8, color: "#111827" },
    ];
  });

  // ─ Portada / página 1: título + filtros + KPIs
  var content = [
    { text: "Reporte de Gastos", style: "header" },
    {
      text: "Generado el " + dateStr,
      style: "subheader",
      margin: [0, 2, 0, 12],
    },
  ];

  if (filterRows.length > 0) {
    content.push({ text: "Filtros aplicados", style: "sectionTitle" });
    content.push({
      table: { widths: [70, "*"], body: filterRows },
      layout: "noBorders",
      margin: [0, 2, 0, 14],
    });
  }

  content.push({ text: "Estadísticas generales", style: "sectionTitle" });
  content.push({
    table: { widths: ["*", "*"], body: kpiRows },
    layout: "lightHorizontalLines",
    margin: [0, 4, 0, 0],
  });

  // ─ Página 2: gráfico de barras
  if (gastosChart) {
    content.push({
      text: "Gastos por Categoría",
      style: "sectionTitle",
      pageBreak: "before",
    });
    content.push({
      image: gastosChart.toBase64Image(),
      width: 490,
      margin: [0, 8, 0, 0],
    });
  }

  // ─ Página 3: donut + tabla de categorías
  if (distribucionChart) {
    content.push({
      text: "Distribución de Gastos",
      style: "sectionTitle",
      pageBreak: "before",
    });
    content.push({
      image: distribucionChart.toBase64Image(),
      width: 300,
      alignment: "center",
      margin: [0, 8, 0, 24],
    });
  } else if (catRows.length > 1) {
    // si no hay donut, la tabla igual arranca en página nueva
    content.push({ text: "", pageBreak: "before" });
  }
  if (catRows.length > 1) {
    content.push({ text: "Detalle por Categoría", style: "sectionTitle" });
    content.push({
      table: { widths: [10, 16, "*", 70, 35], body: catRows },
      layout: "lightHorizontalLines",
      margin: [0, 4, 0, 8],
    });
  }

  var filename = "reporte-gastos-" + now.toISOString().slice(0, 10) + ".pdf";

  pdfMake
    .createPdf({
      pageSize: "LETTER",
      pageMargins: [40, 50, 40, 50],
      content: content,
      styles: {
        header: {
          fontSize: 20,
          bold: true,
          color: "#1e3a8a",
          margin: [0, 0, 0, 2],
        },
        subheader: { fontSize: 9, color: "#6b7280" },
        sectionTitle: {
          fontSize: 11,
          bold: true,
          color: "#1e3a8a",
          margin: [0, 6, 0, 3],
        },
      },
      defaultStyle: { fontSize: 9 },
    })
    .download(filename, function () {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-file-pdf"></i> Exportar PDF';
      }
    });
}

function createGastosCategoriasChart() {
  // Verificar que el elemento canvas exista
  var ctxCategorias = document.getElementById("gastosCategoriasChart");
  if (!ctxCategorias) {
    return false;
  }

  // Verificar que los datos estén disponibles
  if (
    !window.balancesCategoriasLabels ||
    !window.balancesCategoriasData ||
    window.balancesCategoriasLabels.length === 0
  ) {
    return false;
  }

  ctxCategorias = ctxCategorias.getContext("2d");

  var labels = window.balancesCategoriasLabels;
  var data = window.balancesCategoriasData;

  // Ordenar los datos de mayor a menor preservando el índice original
  // para que cada categoría use el mismo color en la barra y en el donut.
  var combinado = [];
  for (var j = 0; j < labels.length; j++) {
    combinado.push({
      label: labels[j],
      data: data[j],
      origIdx: j,
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

  // Usar el índice original para que el color coincida con el del donut chart
  var backgroundColors = combinado.map(function (item) {
    return generateColor(item.origIdx, 0.75);
  });
  var borderColors = combinado.map(function (item) {
    return generateColor(item.origIdx, 1);
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
              borderColor: borderColors,
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
              ticks: { font: { size: 10, weight: "bold" } },
            },
          },
          animation: {
            duration: 2000,
            easing: "easeOutQuart",
          },
        },
      });
      resizeBarChart(labels.length);
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
    return false;
  }

  if (
    !window.balancesCategoriasLabels ||
    !window.balancesCategoriasData ||
    window.balancesCategoriasLabels.length === 0
  ) {
    return false;
  }

  ctxDistribucion = ctxDistribucion.getContext("2d");
  var labels = window.balancesCategoriasLabels;
  var data = window.balancesCategoriasData;
  var donutPalette = buildColorArrays(labels.length);

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
            backgroundColor: donutPalette.bg,
            borderColor: donutPalette.border,
            borderWidth: 1,
            hoverOffset: 10,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
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
    renderDonutLegend(labels, donutPalette.bg, data);
    return true;
  } catch (error) {
    console.error("Error al crear el gráfico de distribución:", error);
    return false;
  }
}

// Función para intentar crear los gráficos con reintentos
function tryCreateCharts(retries = 10) {
  var categoriasSuccess = createGastosCategoriasChart();
  var distribucionSuccess = createDistribucionGastosChart();

  if (!categoriasSuccess || !distribucionSuccess) {
    if (retries > 0) {
      setTimeout(function () {
        tryCreateCharts(retries - 1);
      }, 500);
    }
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

// Exportar funciones puras para pruebas unitarias (Node / Jest)
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    _curatedPalette: _curatedPalette,
    generateColor: generateColor,
    buildColorArrays: buildColorArrays,
    hslToHex: hslToHex,
    paletteHex: paletteHex,
    buildCategoryRows: buildCategoryRows,
  };
}
