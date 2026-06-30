(function () {
  "use strict";

  window.balancesCategoriasLabels = window.balancesCategoriasLabels || [];
  window.balancesCategoriasData = window.balancesCategoriasData || [];

  function getPageRoot() {
    return document.querySelector("[data-balances-page]");
  }

  function getAjaxUrl() {
    var root = getPageRoot();
    return root ? root.getAttribute("data-ajax-url") : "";
  }

  function formatCurrencyAjax(value) {
    return new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(parseFloat(value) || 0);
  }

  function updateKpis(kpis) {
    var el;
    el = document.getElementById("kpi-total-gastos");
    if (el) el.textContent = "$" + formatCurrencyAjax(kpis.total_gastos);
    el = document.getElementById("kpi-promedio");
    if (el) el.textContent = "$" + formatCurrencyAjax(kpis.promedio_gastos);
    el = document.getElementById("kpi-transacciones");
    if (el) el.textContent = kpis.numero_transacciones;
    el = document.getElementById("kpi-maximo");
    if (el) el.textContent = "$" + formatCurrencyAjax(kpis.gasto_maximo);
    el = document.getElementById("kpi-sub-maximo");
    if (el) el.textContent = kpis.categoria_gasto_maximo;
    el = document.getElementById("kpi-minimo");
    if (el) el.textContent = "$" + formatCurrencyAjax(kpis.gasto_minimo);
    el = document.getElementById("kpi-sub-minimo");
    if (el) el.textContent = kpis.categoria_gasto_minimo;
    el = document.getElementById("kpi-mediano");
    if (el) el.textContent = "$" + formatCurrencyAjax(kpis.gasto_mediano);
  }

  function dispatchChartsUpdate(delay) {
    setTimeout(function () {
      updateChartsData();
      window.dispatchEvent(new Event("chartsDataUpdated"));
    }, delay || 100);
  }

  function updateChartsData() {
    var categorias = {};

    if (!window.jQuery || !jQuery.fn.DataTable || !jQuery.fn.DataTable.isDataTable("#gastosTable")) {
      updateChartsDataFromPlainTable();
      return;
    }

    var table = jQuery("#gastosTable").DataTable();
    if (!table || table.data().length === 0) {
      window.balancesCategoriasLabels = [];
      window.balancesCategoriasData = [];
      return;
    }

    var data = table.rows({ search: "applied" }).data();
    for (var i = 0; i < data.length; i++) {
      var categoryHtml = data[i][2];
      var tempDiv = document.createElement("div");
      tempDiv.innerHTML = categoryHtml;
      var categoria = (tempDiv.textContent || tempDiv.innerText || categoryHtml).trim();
      var totalValue = 0;
      var totalCell = table.cell(i, 6).node();

      if (totalCell) {
        if (typeof window.getNumericValueFromNode === "function") {
          totalValue = window.getNumericValueFromNode(totalCell) || 0;
        } else {
          totalValue = parseFloat((totalCell.textContent || "").replace(/[$\s,]/g, "")) || 0;
        }
      }

      categorias[categoria] = (categorias[categoria] || 0) + totalValue;
    }

    window.balancesCategoriasLabels = [];
    window.balancesCategoriasData = [];

    Object.keys(categorias).forEach(function (key) {
      if (key.trim() !== "") {
        window.balancesCategoriasLabels.push(key);
        window.balancesCategoriasData.push(categorias[key]);
      }
    });
  }

  function parseMoneyText(text) {
    return parseFloat(String(text || "").replace(/[$\s,]/g, "")) || 0;
  }

  function updateChartsDataFromPlainTable() {
    var table = document.getElementById("gastosTable");
    var categorias = {};

    if (!table || !table.tBodies.length) {
      return;
    }

    Array.prototype.forEach.call(table.tBodies[0].rows, function (row) {
      var categoryCell = row.cells[2];
      var totalCell = row.cells[6];

      if (!categoryCell || !totalCell) {
        return;
      }

      var categoria = (categoryCell.textContent || "").trim();
      var totalValue = parseMoneyText(totalCell.textContent);

      if (categoria) {
        categorias[categoria] = (categorias[categoria] || 0) + totalValue;
      }
    });

    window.balancesCategoriasLabels = [];
    window.balancesCategoriasData = [];

    Object.keys(categorias).forEach(function (key) {
      window.balancesCategoriasLabels.push(key);
      window.balancesCategoriasData.push(categorias[key]);
    });
  }

  function initDailyFilters() {
    if (!window.jQuery) return;

    var $ = window.jQuery;

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

    if ($("#periodo").val() === "diario") {
      $("#filtro-diario-opciones").show();
    } else {
      $("#filtro-diario-opciones").hide();
    }
  }

  function bindChartsDataUpdates() {
    dispatchChartsUpdate(1000);

    if (window.jQuery) {
      jQuery(document).off("draw.dt.gastosBalances", "#gastosTable");
      jQuery(document).on("draw.dt.gastosBalances", "#gastosTable", function () {
        dispatchChartsUpdate(100);
      });
    }
  }

  function reinitGastosDataTable() {
    if (typeof window.initBalancesDataTable === "function") {
      window.initBalancesDataTable();
      bindChartsDataUpdates();
      dispatchChartsUpdate(300);
    }
  }

  function doAjaxFilter(form) {
    var ajaxUrl = getAjaxUrl();
    if (!ajaxUrl) return;

    var params = new URLSearchParams(new FormData(form));
    var container = document.getElementById("gastos-table-container");

    if (container) {
      container.style.opacity = "0.5";
      container.style.pointerEvents = "none";
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

        if (container) {
          if (window.jQuery && jQuery.fn.DataTable.isDataTable("#gastosTable")) {
            jQuery("#gastosTable").DataTable().destroy();
          }

          container.innerHTML = data.table_html;
          container.style.opacity = "";
          container.style.pointerEvents = "";
          reinitGastosDataTable();
        }

        if (typeof window.showToast === "function") {
          window.showToast("Filtros aplicados", "La informacion ha sido filtrada segun los criterios seleccionados.");
        }

        history.replaceState(null, "", "?" + params.toString());
      })
      .catch(function (err) {
        if (container) {
          container.style.opacity = "";
          container.style.pointerEvents = "";
        }
        console.error("AJAX error:", err);
      });
  }

  function initLegacyAjaxFallback() {
    var form = document.querySelector('form[action*="gastos_balances"]');
    if (!form || typeof window.htmx !== "undefined") return;

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      doAjaxFilter(form);
    });

    form.submit = function () {
      doAjaxFilter(form);
    };
  }

  function initToastDismiss() {
    document.addEventListener("click", function (event) {
      if (event.target.closest("[data-toast-dismiss]") && typeof window.hideToast === "function") {
        window.hideToast();
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initDailyFilters();
    initToastDismiss();
    bindChartsDataUpdates();
    initLegacyAjaxFallback();
  });

  document.addEventListener("htmx:afterSwap", function (event) {
    if (event.detail.target && event.detail.target.id === "balances-results") {
      reinitGastosDataTable();
    }
  });

  window.updateChartsData = updateChartsData;
  window.updateGastosBalancesKpis = updateKpis;
})();
