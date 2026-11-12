/*
 * Conciliación de CFDI — filtros por fecha.
 *
 * - Aplica el filtro automáticamente al cambiar las fechas (sin pulsar Filtrar).
 * - Recuerda los últimos filtros en localStorage y los reaplica al volver a la
 *   página (cuando se entra sin parámetros en la URL).
 */
(function () {
  "use strict";

  var STORAGE_KEY = "conciliacion_filtros";

  function onReady(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  function read() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    } catch (e) {
      return null;
    }
  }

  function save(ini, fin) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ ini: ini, fin: fin }));
    } catch (e) {
      /* localStorage no disponible */
    }
  }

  function clear() {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (e) {
      /* noop */
    }
  }

  onReady(function () {
    var form = document.querySelector("form.conc-filters");
    if (!form) return;

    var iniEl = form.querySelector('input[name="fecha_inicio"]');
    var finEl = form.querySelector('input[name="fecha_fin"]');
    if (!iniEl || !finEl) return;

    var params = new URLSearchParams(window.location.search);
    var hasUrl = params.has("fecha_inicio") || params.has("fecha_fin");
    var stored = read();

    if (hasUrl) {
      /* Recordar el filtro activo. */
      save(iniEl.value || "", finEl.value || "");
    } else if (stored && (stored.ini || stored.fin)) {
      /* Al volver a la página, reaplicar los últimos filtros. */
      iniEl.value = stored.ini || "";
      finEl.value = stored.fin || "";
      form.submit();
      return;
    }

    /* Aplicar automáticamente al cambiar una fecha. */
    function apply() {
      save(iniEl.value || "", finEl.value || "");
      form.submit();
    }
    iniEl.addEventListener("change", apply);
    finEl.addEventListener("change", apply);

    /* "Limpiar" olvida los filtros guardados. */
    var clearLink = form.querySelector(".conc-filter-clear");
    if (clearLink) {
      clearLink.addEventListener("click", function () {
        clear();
      });
    }
  });
})();
