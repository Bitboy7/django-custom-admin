(function () {
  "use strict";

  var pageRoot = document.getElementById("ventas-balances-page");

  function showToast(title, message, duration) {
    duration = duration || 4000;
    var toast = document.getElementById("toast-notification");
    var toastTitle = document.getElementById("toast-title");
    var toastMessage = document.getElementById("toast-message");
    if (!toast || !toastTitle || !toastMessage) return;
    toastTitle.textContent = title;
    toastMessage.textContent = message;
    toast.classList.remove("translate-x-full", "opacity-0");
    toast.classList.add("translate-x-0", "opacity-100");
    setTimeout(function () { hideToast(); }, duration);
  }

  function hideToast() {
    var toast = document.getElementById("toast-notification");
    if (toast) {
      toast.classList.remove("translate-x-0", "opacity-100");
      toast.classList.add("translate-x-full", "opacity-0");
    }
  }

  window.showToast = showToast;
  window.hideToast = hideToast;

  function formatCurrencyAjax(value) {
    return new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(parseFloat(value) || 0);
  }

  function updateKpis(kpis) {
    var ids = {
      "kpi-total-ventas": "$" + formatCurrencyAjax(kpis.total_ventas),
      "kpi-total-pagado": "$" + formatCurrencyAjax(kpis.total_pagado),
      "kpi-saldo-pendiente": "$" + formatCurrencyAjax(kpis.saldo_pendiente_total),
      "kpi-transacciones": kpis.numero_transacciones,
      "kpi-venta-maxima": "$" + formatCurrencyAjax(kpis.venta_maxima),
      "kpi-promedio": "$" + formatCurrencyAjax(kpis.promedio_ventas),
      "kpi-total-facturado-cfdi": "$" + formatCurrencyAjax(kpis.total_facturado_cfdi),
      "kpi-total-notas-credito-cfdi": "$" + formatCurrencyAjax(kpis.total_notas_credito_cfdi),
      "kpi-total-recibos-pago-cfdi": "$" + formatCurrencyAjax(kpis.total_recibos_pago_cfdi),
      "kpi-numero-cfdis": kpis.numero_cfdis,
    };
    Object.keys(ids).forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.textContent = ids[id];
    });
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
    if (!window.jQuery) return;
    if ($.fn.DataTable.isDataTable("#ventasTable")) {
      $("#ventasTable").DataTable().destroy();
    }
    if ($("#ventasTable").length) {
      $("#ventasTable").DataTable({
        responsive: false,
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
          { extend: "excel", title: "Análisis de Ventas", text: '<i class="fas fa-file-excel"></i> Excel', className: "btn-export btn-export-excel", exportOptions: { columns: ":visible" } },
          { extend: "pdf", title: "Análisis de Ventas", text: '<i class="fas fa-file-pdf"></i> PDF', className: "btn-export btn-export-pdf", orientation: "landscape", pageSize: "A4", exportOptions: { columns: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] } },
          { extend: "print", title: "Análisis de Ventas", text: '<i class="fas fa-print"></i> Imprimir', className: "btn-export btn-export-print", exportOptions: { columns: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] } },
        ],
      });
    }
  }

  function reinitializeResults() {
    destroyVentasCharts();
    setTimeout(function () {
      if (typeof initializeVentasCharts === "function") {
        initializeVentasCharts();
      }
      reinitVentasDataTable();
    }, 50);
  }

  function exportVentasPDF() {
    var btn = document.getElementById("btn-export-pdf");
    if (btn) btn.disabled = true;
    try {
      var table = $("#ventasTable").DataTable();
      if (table) table.button(".buttons-pdf").trigger();
    } catch (e) {}
    setTimeout(function () { if (btn) btn.disabled = false; }, 2000);
  }

  function setHidden(id, hidden) {
    var el = document.getElementById(id);
    if (el) el.classList.toggle("is-hidden", hidden);
  }

  function clearValue(id) {
    var el = document.getElementById(id);
    if (el) el.value = "";
  }

  function checkedValue(name) {
    var el = document.querySelector('input[name="' + name + '"]:checked');
    return el ? el.value : "";
  }

  function clearMonthSelection() {
    clearValue("months");
    document.querySelectorAll(".month-checkbox").forEach(function (cb) {
      cb.checked = false;
    });
    var all = document.getElementById("month-all");
    if (all) all.checked = true;
    var text = document.getElementById("month-selector-text");
    if (text) text.textContent = "Todos los meses";
  }

  // Sincroniza la visibilidad de los controles de fecha con el período y el
  // modo elegidos. Año y Meses solo aplican a "Año y meses" (mensual) y a
  // semanal; en Diario y en "Rango de meses" se ocultan porque no se usan.
  function syncDateFilters() {
    var periodo = (document.getElementById("periodo") || {}).value;
    var esDiario = periodo === "diario";
    var esMensual = periodo === "mensual";
    var esRangoMes = esMensual && checkedValue("tipo_mes") === "rango";
    var esRangoFecha = checkedValue("tipo_fecha") === "rango";

    setHidden("filtro-diario-opciones", !esDiario);
    setHidden("filtro-mensual-opciones", !esMensual);
    setHidden("campo-dia-especifico", esRangoFecha);
    setHidden("campos-rango-fechas", !esRangoFecha);
    setHidden("campos-rango-meses", !esRangoMes);
    setHidden("filtro-year-wrap", esDiario || esRangoMes);
    setHidden("filtro-meses-wrap", esDiario || esRangoMes);
  }

  function initPeriodControls() {
    var periodo = document.getElementById("periodo");
    if (periodo) periodo.addEventListener("change", syncDateFilters);

    document.querySelectorAll('input[name="tipo_fecha"]').forEach(function (radio) {
      radio.addEventListener("change", function () {
        if (this.value === "dia") {
          clearValue("fecha_inicio");
          clearValue("fecha_fin");
        } else {
          clearValue("dia");
        }
        syncDateFilters();
      });
    });

    document.querySelectorAll('input[name="tipo_mes"]').forEach(function (radio) {
      radio.addEventListener("change", function () {
        if (this.value === "rango") {
          clearMonthSelection();
        } else {
          clearValue("mes_inicio");
          clearValue("mes_fin");
        }
        syncDateFilters();
      });
    });

    syncDateFilters();
  }

  function bindExportButton() {
    var exportBtn = document.getElementById("btn-export-pdf");
    if (exportBtn) {
      exportBtn.addEventListener("click", exportVentasPDF);
    }
  }

  function initToastClose() {
    var closeToastBtn = document.getElementById("toast-close-button");
    if (closeToastBtn && typeof hideToast === "function") {
      closeToastBtn.addEventListener("click", hideToast);
    }
  }

  function doAjaxFilter(form) {
    var params = new URLSearchParams(new FormData(form));
    var resultsContainer = document.getElementById("balances-results");
    var submitBtn = form.querySelector('button[type="submit"]');
    var originalBtnHtml = submitBtn ? submitBtn.innerHTML : null;
    var ajaxUrl = form.getAttribute("action") || window.location.pathname;

    if (resultsContainer) {
      resultsContainer.style.opacity = "0.5";
      resultsContainer.style.pointerEvents = "none";
    }
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Procesando...';
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
        if (resultsContainer) {
          resultsContainer.innerHTML = data.results_html;
          resultsContainer.style.opacity = "";
          resultsContainer.style.pointerEvents = "";
        }
        reinitializeResults();
        if (typeof showToast === "function") {
          showToast("¡Filtros aplicados!", "Los datos han sido actualizados.");
        }
        history.replaceState(null, "", "?" + params.toString());
      })
      .catch(function (err) {
        if (resultsContainer) {
          resultsContainer.style.opacity = "";
          resultsContainer.style.pointerEvents = "";
        }
        console.error("AJAX error:", err);
      })
      .finally(function () {
        if (submitBtn && originalBtnHtml !== null) {
          submitBtn.innerHTML = originalBtnHtml;
          submitBtn.disabled = false;
        }
      });
  }

  function initLegacyAjaxFallback() {
    var form = document.querySelector('form[action*="ventas/balances"]') ||
      document.querySelector("#ventas-balances-page form");
    if (!form || typeof window.htmx !== "undefined") return;

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      doAjaxFilter(form);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initPeriodControls();
    bindExportButton();
    initToastClose();
    initLegacyAjaxFallback();
  });

  document.addEventListener("htmx:afterSwap", function (event) {
    if (event.detail.target && event.detail.target.id === "balances-results") {
      reinitializeResults();
    }
  });

  window.exportVentasPDF = exportVentasPDF;
  window.updateVentasBalancesKpis = updateKpis;
})();
