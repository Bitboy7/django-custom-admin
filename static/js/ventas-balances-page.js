(function () {
  "use strict";

  var pageRoot = document.getElementById("ventas-balances-page");

  function readJsonData(attributeName) {
    if (!pageRoot) return [];

    var rawValue = pageRoot.getAttribute(attributeName);
    if (!rawValue) return [];

    try {
      return JSON.parse(rawValue);
    } catch (error) {
      console.error("No se pudo leer el JSON de " + attributeName + ":", error);
      return [];
    }
  }

  window.ventasModalidadData = readJsonData("data-ventas-modalidad");
  window.ventasEstadosData = readJsonData("data-ventas-estados");
  window.ventasClientesData = readJsonData("data-ventas-clientes");

  function formatCurrencyAjax(value) {
    return new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(parseFloat(value) || 0);
  }

  function updateKpis(kpis) {
    var el;
    el = document.getElementById("kpi-total-ventas");
    if (el) el.textContent = "$" + formatCurrencyAjax(kpis.total_ventas);
    el = document.getElementById("kpi-total-pagado");
    if (el) el.textContent = "$" + formatCurrencyAjax(kpis.total_pagado);
    el = document.getElementById("kpi-saldo-pendiente");
    if (el) el.textContent = "$" + formatCurrencyAjax(kpis.saldo_pendiente_total);
    el = document.getElementById("kpi-transacciones");
    if (el) el.textContent = kpis.numero_transacciones;
    el = document.getElementById("kpi-venta-maxima");
    if (el) el.textContent = "$" + formatCurrencyAjax(kpis.venta_maxima);
    el = document.getElementById("kpi-promedio");
    if (el) el.textContent = "$" + formatCurrencyAjax(kpis.promedio_ventas);
  }

  function destroyVentasCharts() {
    ["modalidadChart", "estadosChart", "clientesChart"].forEach(function (id) {
      var canvas = document.getElementById(id);
      if (canvas && window.Chart) {
        var existing = Chart.getChart(canvas);
        if (existing) existing.destroy();
      }
    });
  }

  function reinitVentasDataTable() {
    if ($.fn.DataTable.isDataTable("#ventasTable")) {
      $("#ventasTable").DataTable().destroy();
    }
    if ($("#ventasTable").length) {
      $("#ventasTable").DataTable({
        responsive: true,
        pageLength: 25,
        lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "Todos"]],
        order: [[0, "asc"]],
        columnDefs: [
          { targets: [6, 7, 8, 10], type: "num-fmt", className: "text-right" },
          { targets: [9], className: "text-center" },
        ],
        dom: "Bfrtip",
        language: { url: "/static/js/datatables-spanish.json" },
        buttons: [
          {
            extend: "excel", title: "Análisis de Ventas",
            text: '<i class="fas fa-file-excel"></i> Excel',
            className: "btn btn-success btn-sm",
            exportOptions: { columns: ":visible" },
          },
          {
            extend: "pdf", title: "Análisis de Ventas",
            text: '<i class="fas fa-file-pdf"></i> PDF',
            className: "btn btn-danger btn-sm",
            orientation: "landscape", pageSize: "A4",
            exportOptions: { columns: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] },
          },
          {
            extend: "print", title: "Análisis de Ventas",
            text: '<i class="fas fa-print"></i> Imprimir',
            className: "btn btn-info btn-sm",
            exportOptions: { columns: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] },
          },
        ],
      });
    }
  }

  function doAjaxFilter(form) {
    var params = new URLSearchParams(new FormData(form));
    var container = document.getElementById("ventas-table-container");
    var submitBtn = form.querySelector('button[type="submit"]');
    var originalBtnHtml = submitBtn ? submitBtn.innerHTML : null;
    var ajaxUrl = form.getAttribute("action") || window.location.pathname;

    if (container) {
      container.style.opacity = "0.5";
      container.style.pointerEvents = "none";
    }

    function restoreBtn() {
      if (submitBtn && originalBtnHtml !== null) {
        submitBtn.innerHTML = originalBtnHtml;
        submitBtn.disabled = false;
      }
    }

    fetch(ajaxUrl + "?" + params.toString(), {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (response) {
        if (!response.ok) throw new Error("Error " + response.status);
        return response.json();
      })
      .then(function (data) {
        updateKpis(data.kpis);

        window.ventasModalidadData = data.chart_data.modalidad;
        window.ventasEstadosData = data.chart_data.estados;
        window.ventasClientesData = data.chart_data.clientes;
        destroyVentasCharts();
        setTimeout(function () { initializeVentasCharts(); }, 50);

        if (container) {
          container.innerHTML = data.table_html;
          container.style.opacity = "";
          container.style.pointerEvents = "";
          reinitVentasDataTable();
        }

        restoreBtn();

        if (typeof showToast === "function") {
          showToast("¡Filtros aplicados!", "Los datos han sido actualizados.");
        }

        history.replaceState(null, "", "?" + params.toString());
      })
      .catch(function (err) {
        if (container) {
          container.style.opacity = "";
          container.style.pointerEvents = "";
        }
        restoreBtn();
        console.error("AJAX error:", err);
      });
  }

  function exportVentasPDF() {
    var btn = document.getElementById("btn-export-pdf");
    if (btn) { btn.disabled = true; }
    try {
      var table = $("#ventasTable").DataTable();
      if (table) {
        table.button(".buttons-pdf").trigger();
      }
    } catch (e) {}
    setTimeout(function () { if (btn) btn.disabled = false; }, 2000);
  }

  function initPeriodControls() {
    $("#periodo").on("change", function () {
      if ($(this).val() === "diario") {
        $("#filtro-diario-opciones").slideDown(300);
      } else {
        $("#filtro-diario-opciones").slideUp(300);
      }
    });

    $('input[name="tipo_fecha"]').on("change", function () {
      if ($(this).val() === "dia") {
        $("#campo-dia-especifico").slideDown(300);
        $("#campos-rango-fechas").slideUp(300);
        $("#fecha_inicio").val("");
        $("#fecha_fin").val("");
      } else {
        $("#campo-dia-especifico").slideUp(300);
        $("#campos-rango-fechas").slideDown(300);
        $("#dia").val("");
      }
    });

    if ($("#periodo").val() !== "diario") {
      $("#filtro-diario-opciones").hide();
    }

    var urlParams = new URLSearchParams(window.location.search);
    if (urlParams.toString() && typeof showToast === "function") {
      showToast("¡Filtros aplicados!", "Los datos han sido filtrados según sus criterios.");
    }
  }

  window.exportVentasPDF = exportVentasPDF;

  $(document).ready(initPeriodControls);

  document.addEventListener("DOMContentLoaded", function () {
    var exportBtn = document.getElementById("btn-export-pdf");
    if (exportBtn) {
      exportBtn.addEventListener("click", exportVentasPDF);
    }

    var closeToastBtn = document.getElementById("toast-close-button");
    if (closeToastBtn) {
      closeToastBtn.addEventListener("click", function () {
        if (typeof hideToast === "function") hideToast();
      });
    }

    var form = document.querySelector('form[action*="ventas/balances"]') ||
      document.querySelector("#ventas-balances-page form");
    if (!form) return;

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      doAjaxFilter(form);
    });

    form.submit = function () {
      doAjaxFilter(form);
    };
  });
})();
