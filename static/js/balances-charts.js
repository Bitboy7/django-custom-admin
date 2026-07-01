// Inicialización de gráficos para balances
var gastosChart = null;
var distribucionChart = null;
var MAX_CATEGORIAS_GRAFICO = 12;

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
  var cuentaLabel = document
    .querySelector("[data-bank-account-current]")
    ?.textContent.replace(/\s+/g, " ")
    .trim();
  if (cuentaEl && cuentaLabel) {
    parts.push({
      label: "Cuenta",
      value: cuentaLabel,
    });
  } else if (cuentaEl && cuentaEl.selectedIndex >= 0) {
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
  var fechaInicioEl = document.getElementById("fecha_inicio");
  var fechaFinEl = document.getElementById("fecha_fin");
  var diaEl = document.getElementById("dia");
  if (fechaInicioEl && fechaFinEl && fechaInicioEl.value && fechaFinEl.value) {
    parts.push({ label: "Rango", value: fechaInicioEl.value + " a " + fechaFinEl.value });
  } else if (diaEl && diaEl.value) {
    parts.push({ label: "Dia", value: diaEl.value });
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
    { text: "", fillColor: "#2f4550", color: "#fff", fontSize: 7 },
    {
      text: "#",
      bold: true,
      fillColor: "#2f4550",
      color: "#fff",
      fontSize: 7,
      alignment: "center",
    },
    {
      text: "Categoría",
      bold: true,
      fillColor: "#2f4550",
      color: "#fff",
      fontSize: 7,
    },
    {
      text: "Total",
      bold: true,
      fillColor: "#2f4550",
      color: "#fff",
      fontSize: 7,
      alignment: "right",
    },
    {
      text: "%",
      bold: true,
      fillColor: "#2f4550",
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
      { text: pct, fontSize: 7, alignment: "right", color: "#586f7c" },
    ]);
  });
  return rows;
}

function cleanPdfText(value) {
  if (value == null) return "";
  if (typeof value === "object") {
    value = value.display || value._ || value.sort || value["@data-order"] || value["data-order"] || "";
  }
  if (typeof getCleanTextFromHTML === "function") {
    return getCleanTextFromHTML(value).trim();
  }
  var temp = document.createElement("div");
  temp.innerHTML = String(value || "");
  return (temp.textContent || temp.innerText || String(value || "")).trim();
}

function parsePdfMoney(value) {
  var text = cleanPdfText(value);
  if (typeof parseNumericString === "function") {
    var parsed = parseNumericString(text);
    return isNaN(parsed) ? 0 : parsed;
  }
  return parseFloat(text.replace(/[$,\s]/g, "")) || 0;
}

function formatPdfMoney(value) {
  return "$" + new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value || 0);
}

function getKpiText(selector) {
  var element = document.querySelector(selector);
  return element ? element.textContent.trim() : "";
}

function readBalancesRowsForPdf() {
  var rows = [];

  if (window.jQuery && jQuery.fn.DataTable && jQuery.fn.DataTable.isDataTable("#gastosTable")) {
    var table = jQuery("#gastosTable").DataTable();

    function getPdfCellText(rowIndex, columnIndex) {
      var cell = table.cell(rowIndex, columnIndex);
      var node = cell.node();
      if (node) {
        return (node.textContent || node.innerText || "").trim();
      }
      return cleanPdfText(cell.render("display"));
    }

    function getPdfCellNumber(rowIndex, columnIndex) {
      var node = table.cell(rowIndex, columnIndex).node();
      if (node && typeof getNumericValueFromNode === "function") {
        var nodeValue = getNumericValueFromNode(node);
        if (!isNaN(nodeValue)) return nodeValue;
      }
      return parsePdfMoney(getPdfCellText(rowIndex, columnIndex));
    }

    table.rows({ search: "applied" }).every(function () {
      var rowIndex = this.index();
      rows.push({
        fecha: getPdfCellText(rowIndex, 0),
        numero: getPdfCellText(rowIndex, 1),
        categoria: getPdfCellText(rowIndex, 2),
        cuenta: getPdfCellText(rowIndex, 3),
        banco: getPdfCellText(rowIndex, 4),
        sucursal: getPdfCellText(rowIndex, 5),
        total: getPdfCellNumber(rowIndex, 6),
        acumulado: getPdfCellNumber(rowIndex, 7),
      });
    });

    return rows;
  }

  var tableElement = document.getElementById("gastosTable");
  if (!tableElement || !tableElement.tBodies.length) return rows;

  Array.prototype.forEach.call(tableElement.tBodies[0].rows, function (row) {
    rows.push({
      fecha: cleanPdfText(row.cells[0] ? row.cells[0].innerHTML : ""),
      numero: cleanPdfText(row.cells[1] ? row.cells[1].innerHTML : ""),
      categoria: cleanPdfText(row.cells[2] ? row.cells[2].innerHTML : ""),
      cuenta: cleanPdfText(row.cells[3] ? row.cells[3].innerHTML : ""),
      banco: cleanPdfText(row.cells[4] ? row.cells[4].innerHTML : ""),
      sucursal: cleanPdfText(row.cells[5] ? row.cells[5].innerHTML : ""),
      total: parsePdfMoney(row.cells[6] ? row.cells[6].innerHTML : ""),
      acumulado: parsePdfMoney(row.cells[7] ? row.cells[7].innerHTML : ""),
    });
  });

  return rows;
}

function aggregatePdfRows(rows, field) {
  var map = {};
  rows.forEach(function (row) {
    var key = row[field] || "Sin especificar";
    map[key] = (map[key] || 0) + (row.total || 0);
  });
  return Object.keys(map)
    .map(function (key) {
      return { label: key, value: map[key] };
    })
    .sort(function (a, b) {
      return b.value - a.value;
    });
}

function buildPdfSummaryTable(title, items, total, limit) {
  var body = [[
    { text: title, bold: true, color: "#f4f4f9", fillColor: "#2f4550", fontSize: 8 },
    { text: "Total", bold: true, color: "#f4f4f9", fillColor: "#2f4550", fontSize: 8, alignment: "right" },
    { text: "%", bold: true, color: "#f4f4f9", fillColor: "#2f4550", fontSize: 8, alignment: "right" },
  ]];

  items.slice(0, limit || 6).forEach(function (item, index) {
    body.push([
      { text: String(index + 1) + ". " + item.label, fontSize: 7, color: "#2f4550" },
      { text: formatPdfMoney(item.value), fontSize: 7, bold: true, alignment: "right", color: "#2f4550" },
      { text: total > 0 ? ((item.value / total) * 100).toFixed(1) + "%" : "0.0%", fontSize: 7, alignment: "right", color: "#586f7c" },
    ]);
  });

  return body;
}

function buildPdfDetailRows(rows) {
  var body = [[
    { text: "Fecha", style: "tableHeader" },
    { text: "Categoria", style: "tableHeader" },
    { text: "Sucursal", style: "tableHeader" },
    { text: "Cuenta", style: "tableHeader" },
    { text: "Total", style: "tableHeader", alignment: "right" },
  ]];

  rows.slice(0, 22).forEach(function (row) {
    body.push([
      { text: row.fecha || "-", fontSize: 7, color: "#2f4550" },
      { text: row.categoria || "-", fontSize: 7, color: "#2f4550" },
      { text: row.sucursal || "-", fontSize: 7, color: "#2f4550" },
      { text: row.cuenta || "-", fontSize: 7, color: "#2f4550" },
      { text: formatPdfMoney(row.total), fontSize: 7, bold: true, alignment: "right", color: "#2f4550" },
    ]);
  });

  return body;
}

/**
 * Genera un PDF con las estadísticas KPI, ambos gráficos y la tabla de categorías.
 * Requiere pdfMake cargado en la página.
 */
function exportBalancesPDF() {
  if (typeof pdfMake === "undefined") {
    alert("pdfMake no esta disponible. Recarga la pagina e intentalo de nuevo.");
    return;
  }

  var btn = document.getElementById("btn-export-pdf");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generando...';
  }

  if (!gastosChart && typeof createGastosCategoriasChart === "function") {
    createGastosCategoriasChart();
  }
  if (!distribucionChart && typeof createDistribucionGastosChart === "function") {
    createDistribucionGastosChart();
  }

  var now = new Date();
  var rows = readBalancesRowsForPdf();
  var totalGastos = rows.reduce(function (sum, row) { return sum + row.total; }, 0);
  var totalKpi = parsePdfMoney(getKpiText("#kpi-total-gastos"));
  if (totalKpi > 0) totalGastos = totalKpi;

  var categoryTotals = aggregatePdfRows(rows, "categoria");
  var branchTotals = aggregatePdfRows(rows, "sucursal");
  var accountTotals = aggregatePdfRows(rows, "cuenta");
  var topCategory = categoryTotals[0] || { label: "Sin datos", value: 0 };
  var topBranch = branchTotals[0] || { label: "Sin datos", value: 0 };
  var concentration = totalGastos > 0 ? (topCategory.value / totalGastos) * 100 : 0;
  var averageTicket = rows.length > 0 ? totalGastos / rows.length : 0;
  var maxRow = rows.reduce(function (max, row) {
    return row.total > (max.total || 0) ? row : max;
  }, {});

  var dateStr = now.toLocaleDateString("es-MX", { year: "numeric", month: "long", day: "numeric" });
  var filterSummary = getFilterSummary();
  var filterText = filterSummary.length
    ? filterSummary.map(function (f) { return f.label + ": " + f.value; }).join("   |   ")
    : "Sin filtros adicionales";

  var kpiCards = [
    { label: "Acumulado", value: formatPdfMoney(totalGastos), note: "Gasto total del periodo" },
    { label: "Promedio", value: getKpiText("#kpi-promedio") || formatPdfMoney(averageTicket), note: "Promedio registrado" },
    { label: "Transacciones", value: getKpiText("#kpi-transacciones") || String(rows.length), note: "Registros filtrados" },
    { label: "Categoria lider", value: topCategory.label, note: formatPdfMoney(topCategory.value) },
    { label: "Sucursal lider", value: topBranch.label, note: formatPdfMoney(topBranch.value) },
    { label: "Concentracion", value: concentration.toFixed(1) + "%", note: "Peso de la categoria principal" },
  ];

  var kpiBody = [];
  for (var i = 0; i < kpiCards.length; i += 3) {
    kpiBody.push(kpiCards.slice(i, i + 3).map(function (card) {
      return {
        stack: [
          { text: card.label.toUpperCase(), fontSize: 6.5, bold: true, color: "#586f7c", margin: [0, 0, 0, 3] },
          { text: card.value || "-", fontSize: 13, bold: true, color: "#2f4550", margin: [0, 0, 0, 2] },
          { text: card.note || "", fontSize: 7, color: "#586f7c" },
        ],
        fillColor: "#f8fafc",
        margin: [8, 7, 8, 7],
      };
    }));
  }

  var insightBullets = [
    "La categoria con mayor gasto es " + topCategory.label + " con " + formatPdfMoney(topCategory.value) + ".",
    "La sucursal con mayor participacion es " + topBranch.label + " con " + formatPdfMoney(topBranch.value) + ".",
    "El gasto promedio por registro es " + formatPdfMoney(averageTicket) + ".",
  ];
  if (maxRow.categoria) {
    insightBullets.push("El registro individual mas alto corresponde a " + maxRow.categoria + " por " + formatPdfMoney(maxRow.total) + ".");
  }

  var content = [
    {
      table: {
        widths: ["*"],
        body: [[{
          stack: [
            { text: "REPORTE EJECUTIVO DE GASTOS", fontSize: 18, bold: true, color: "#f4f4f9" },
            { text: "Agricola de la Costa San Luis S.P.R de R.L.", fontSize: 9, color: "#b8dbd9", margin: [0, 3, 0, 0] },
            { text: "Generado el " + dateStr, fontSize: 8, color: "#d8dce6", margin: [0, 8, 0, 0] },
          ],
          fillColor: "#2f4550",
          border: [false, false, false, false],
          margin: [18, 16, 18, 16],
        }]],
      },
      layout: "noBorders",
      margin: [0, 0, 0, 12],
    },
    { text: filterText, fontSize: 7.5, color: "#586f7c", margin: [0, 0, 0, 10] },
    { table: { widths: ["*", "*", "*"], body: kpiBody }, layout: { hLineColor: function () { return "#d8dce6"; }, vLineColor: function () { return "#d8dce6"; } }, margin: [0, 0, 0, 12] },
    { text: "Lectura ejecutiva", style: "sectionTitle" },
    { ul: insightBullets.map(function (text) { return { text: text, fontSize: 8, margin: [0, 1, 0, 1] }; }), margin: [0, 0, 0, 10] },
  ];

  if (gastosChart || distribucionChart) {
    var chartColumns = [];
    if (gastosChart) {
      chartColumns.push({ stack: [{ text: "Gastos por categoria", style: "miniTitle" }, { image: gastosChart.toBase64Image(), width: 430, margin: [0, 4, 10, 0] }] });
    }
    if (distribucionChart) {
      chartColumns.push({ stack: [{ text: "Distribucion", style: "miniTitle", alignment: "center" }, { image: distribucionChart.toBase64Image(), width: 210, alignment: "center", margin: [0, 4, 0, 0] }] });
    }
    content.push({ columns: chartColumns, columnGap: 14, margin: [0, 2, 0, 12] });
  }

  content.push({ columns: [
    { stack: [{ text: "Top categorias", style: "sectionTitle" }, { table: { widths: ["*", 70, 35], body: buildPdfSummaryTable("Categoria", categoryTotals, totalGastos, 7) }, layout: "lightHorizontalLines" }] },
    { stack: [{ text: "Top sucursales", style: "sectionTitle" }, { table: { widths: ["*", 70, 35], body: buildPdfSummaryTable("Sucursal", branchTotals, totalGastos, 7) }, layout: "lightHorizontalLines" }] },
  ], columnGap: 16, margin: [0, 0, 0, 10] });

  if (accountTotals.length > 0) {
    content.push({ text: "Cuentas con mayor salida", style: "sectionTitle" });
    content.push({ table: { widths: ["*", 90, 45], body: buildPdfSummaryTable("Cuenta", accountTotals, totalGastos, 5) }, layout: "lightHorizontalLines", margin: [0, 0, 0, 10] });
  }

  if (rows.length > 0) {
    content.push({ text: "Detalle operativo filtrado", style: "sectionTitle", pageBreak: "before" });
    content.push({ text: "Se muestran los primeros 22 registros del resultado filtrado. Para detalle completo use Excel o CSV.", fontSize: 7, color: "#586f7c", margin: [0, 0, 0, 6] });
    content.push({ table: { headerRows: 1, widths: [50, "*", 85, 80, 70], body: buildPdfDetailRows(rows) }, layout: "lightHorizontalLines" });
  }

  var filename = "reporte-ejecutivo-gastos-" + now.toISOString().slice(0, 10) + ".pdf";
  pdfMake.createPdf({
    pageSize: "LETTER",
    pageOrientation: "landscape",
    pageMargins: [34, 36, 34, 34],
    content: content,
    footer: function (currentPage, pageCount) {
      return {
        columns: [
          { text: "Agricola de la Costa San Luis S.P.R de R.L.", color: "#8a9aa5", fontSize: 7, margin: [34, 0, 0, 0] },
          { text: "Pagina " + currentPage + " de " + pageCount, color: "#8a9aa5", fontSize: 7, alignment: "right", margin: [0, 0, 34, 0] },
        ],
      };
    },
    styles: {
      sectionTitle: { fontSize: 10, bold: true, color: "#2f4550", margin: [0, 4, 0, 5] },
      miniTitle: { fontSize: 8, bold: true, color: "#2f4550", margin: [0, 0, 0, 3] },
      tableHeader: { bold: true, color: "#f4f4f9", fillColor: "#2f4550", fontSize: 7 },
    },
    defaultStyle: { fontSize: 8, color: "#2f4550" },
  }).download(filename, function () {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fas fa-file-pdf"></i> Exportar PDF';
    }
  });
}

window.exportBalancesPDF = exportBalancesPDF;

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

  combinado = combinado.slice(0, MAX_CATEGORIAS_GRAFICO);

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
      '<div class="flex flex-col items-center justify-center h-full"><i class="fas fa-info-circle text-[#b8dbd9] text-4xl mb-2"></i><p class="text-[#586f7c]">No hay datos disponibles para mostrar</p></div>';
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
