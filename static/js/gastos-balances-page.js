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
      window.balancesCategoriasLabels = [];
      window.balancesCategoriasData = [];
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

      if ($(this).val() === "mensual") {
        $("#filtro-mensual-opciones").slideDown(300);
      } else {
        $("#filtro-mensual-opciones").slideUp(300);
      }

      toggleMonthlyMode();
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

    if ($("#periodo").val() === "mensual") {
      $("#filtro-mensual-opciones").show();
    } else {
      $("#filtro-mensual-opciones").hide();
    }
  }

  function clearMonthSelection() {
    var $months = $("#months");
    if ($months.length) {
      $months.val("");
    }
    if (window.jQuery) {
      jQuery(".month-checkbox").prop("checked", false);
      var $monthAll = jQuery("#month-all");
      if ($monthAll.length) {
        $monthAll.prop("checked", true);
      }
    }
    var monthText = document.getElementById("month-selector-text");
    if (monthText) {
      monthText.textContent = "Todos los meses";
    }
  }

  function toggleMonthlyMode() {
    if (!window.jQuery) return;

    var $ = window.jQuery;
    var esMensual = $("#periodo").val() === "mensual";
    var esRango = esMensual && $('input[name="tipo_mes"]:checked').val() === "rango";

    // En "Rango de meses" (solo dentro del período mensual) los filtros de
    // Año y Meses no se toman en cuenta, así que se ocultan para no confundir
    // al usuario. En cualquier otro caso permanecen visibles.
    if (esRango) {
      $("#filtro-year-wrap").hide();
      $("#filtro-meses-wrap").hide();
      $("#campos-rango-meses").show();
      clearMonthSelection();
    } else {
      $("#filtro-year-wrap").show();
      $("#filtro-meses-wrap").show();
      $("#campos-rango-meses").hide();
      $("#mes_inicio").val("");
      $("#mes_fin").val("");
    }
  }

  function initMonthlyFilters() {
    if (!window.jQuery) return;

    var $ = window.jQuery;

    $('input[name="tipo_mes"]').on("change", toggleMonthlyMode);

    // Estado inicial según el período y el modo seleccionados.
    toggleMonthlyMode();
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

  function initClearFilters() {
    var clearBtn = document.getElementById("clear-filters");
    if (!clearBtn) return;

    clearBtn.addEventListener("click", function () {
      try {
        localStorage.removeItem("balances_filters");
      } catch (e) {}

      var monthsInput = document.getElementById("months");
      if (monthsInput) {
        monthsInput.value = "";
      }

      var ajaxUrl = getAjaxUrl();
      window.location.href = ajaxUrl || window.location.pathname;
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initDailyFilters();
    initMonthlyFilters();
    initClearFilters();
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
