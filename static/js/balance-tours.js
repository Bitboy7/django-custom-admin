(function (root, factory) {
  "use strict";

  var api = factory(root);

  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }

  if (root) {
    root.BalanceTours = api;
  }
})(typeof window !== "undefined" ? window : globalThis, function (root) {
  "use strict";

  var TOUR_VERSION = "v1";
  var STORAGE_PREFIX = "balance-tour:" + TOUR_VERSION + ":";

  function gettext_noop(message) {
    return message;
  }

  function translate(message) {
    return root && typeof root.gettext === "function" ? root.gettext(message) : message;
  }

  function getStorageKey(pageName) {
    return STORAGE_PREFIX + pageName + ":completed";
  }

  function getStorage(storage) {
    if (storage) return storage;
    try {
      return root.localStorage;
    } catch (error) {
      return null;
    }
  }

  function isCompleted(pageName, storage) {
    var targetStorage = getStorage(storage);
    if (!targetStorage) return false;

    try {
      return targetStorage.getItem(getStorageKey(pageName)) === "1";
    } catch (error) {
      return false;
    }
  }

  function markCompleted(pageName, storage) {
    var targetStorage = getStorage(storage);
    if (!targetStorage) return false;

    try {
      targetStorage.setItem(getStorageKey(pageName), "1");
      return true;
    } catch (error) {
      return false;
    }
  }

  function selector(pageName, target) {
    return '[data-balance-tour="' + pageName + '"] [data-tour="' + target + '"]';
  }

  function step(pageName, target, title, description, side) {
    return {
      element: selector(pageName, target),
      popover: {
        title: translate(title),
        description: translate(description),
        side: side || "bottom",
        align: "start",
      },
    };
  }

  function getGastosSteps() {
    return [
      step("gastos", "help", gettext_noop("Guía del balance de gastos"), gettext_noop("Este recorrido explica cómo delimitar la consulta, interpretar los resultados y generar un reporte. Puede repetirlo en cualquier momento desde este botón."), "bottom"),
      step("gastos", "filters", gettext_noop("1. Delimite la consulta"), gettext_noop("Los filtros se combinan entre sí. Cuenta y sucursal reducen el origen del gasto; si deja una opción en ‘Todas’, no se restringe por ese criterio."), "bottom"),
      step("gastos", "calendar", gettext_noop("2. Año, meses y periodo"), gettext_noop("Use Semanal o Mensual para analizar el año y los meses elegidos. En Diario puede consultar la fecha actual, un día específico o un rango de fechas."), "bottom"),
      step("gastos", "actions", gettext_noop("3. Aplique o limpie"), gettext_noop("Aplicar filtros actualiza indicadores, gráficas y tabla sin salir de la página. Limpiar restablece la selección de meses y conserva los demás criterios del formulario."), "top"),
      step("gastos", "metrics", gettext_noop("4. Revise los indicadores"), gettext_noop("Acumulado, promedio, número de transacciones, máximo, mínimo y mediana resumen exactamente el conjunto filtrado."), "bottom"),
      step("gastos", "charts", gettext_noop("5. Interprete la distribución"), gettext_noop("Las gráficas muestran qué categorías concentran el gasto. Cambian junto con los filtros y con la búsqueda aplicada sobre la tabla."), "top"),
      step("gastos", "exports", gettext_noop("6. Genere el reporte"), gettext_noop("Puede exportar un PDF visual. En la barra de la tabla también encontrará Copiar, CSV, Excel, Resumen Excel e Imprimir; revise siempre los filtros antes de compartir el archivo."), "bottom"),
      step("gastos", "detail", gettext_noop("7. Explore el detalle"), gettext_noop("Use Buscar para localizar una categoría, cuenta o sucursal; ordene por encabezados y elija cuántos registros mostrar. Las exportaciones respetan el conjunto filtrado."), "top"),
    ];
  }

  function getVentasSteps() {
    return [
      step("ventas", "help", gettext_noop("Guía del balance de ventas"), gettext_noop("Este recorrido explica los filtros de ventas, la lectura de cobranza y las opciones para generar reportes. Puede iniciarlo de nuevo desde este botón."), "bottom"),
      step("ventas", "filters", gettext_noop("1. Defina el alcance"), gettext_noop("Cliente, cuenta, sucursal y mercado permiten estudiar una operación concreta. Las opciones ‘Todas’ conservan todos los registros disponibles."), "bottom"),
      step("ventas", "sales-filters", gettext_noop("2. Analice venta y cobranza"), gettext_noop("Modalidad de pago separa contado y crédito; Estado de cobranza permite identificar operaciones pagadas, pendientes o vencidas según los valores disponibles."), "bottom"),
      step("ventas", "calendar", gettext_noop("3. Elija el periodo"), gettext_noop("En Semanal o Mensual se utilizan el año y los meses elegidos. En Diario puede consultar un día o un rango usando la fecha de depósito."), "bottom"),
      step("ventas", "actions", gettext_noop("4. Aplique los filtros"), gettext_noop("La consulta actualiza indicadores, gráficas y detalle sin recargar toda la pantalla. La dirección del navegador conserva los criterios para poder volver a la misma vista."), "top"),
      step("ventas", "metrics", gettext_noop("5. Revise la situación de cobranza"), gettext_noop("Compare Total ventas, Total pagado y Pendiente. Transacciones, Venta máxima y Promedio ayudan a dimensionar el conjunto analizado."), "bottom"),
      step("ventas", "charts", gettext_noop("6. Detecte concentraciones"), gettext_noop("Las gráficas resumen modalidad, estado de cobranza y los diez clientes con mayor monto dentro de la consulta."), "top"),
      step("ventas", "exports", gettext_noop("7. Exporte el análisis"), gettext_noop("Exportar PDF genera la presentación visual. La tabla ofrece además Excel, PDF e Imprimir para el detalle; confirme los filtros activos antes de distribuirlo."), "bottom"),
      step("ventas", "detail", gettext_noop("8. Consulte el detalle"), gettext_noop("Busque y ordene las filas para revisar cliente, cuenta, fechas, total pagado, saldo pendiente, estado y acumulado."), "top"),
    ];
  }

  function getSteps(pageName) {
    return pageName === "ventas" ? getVentasSteps() : getGastosSteps();
  }

  function getDriverFactory() {
    return root && root.driver && root.driver.js && root.driver.js.driver;
  }

  function appendManualLink(pageElement, steps) {
    var manualUrl = pageElement.getAttribute("data-manual-url");
    if (!manualUrl || !steps.length) return steps;

    var lastStep = steps[steps.length - 1];
    lastStep.popover.description +=
      ' <a href="' + manualUrl + '">' + translate(gettext_noop("Abrir el manual completo")) + "</a>.";
    return steps;
  }

  function start(pageElement) {
    var driverFactory = getDriverFactory();
    if (!pageElement || typeof driverFactory !== "function") return false;

    var pageName = pageElement.getAttribute("data-balance-tour");
    if (!pageName) return false;

    var tour;
    var finish = function () {
      markCompleted(pageName);
      if (tour) tour.destroy();
    };

    tour = driverFactory({
      animate: !(root.matchMedia && root.matchMedia("(prefers-reduced-motion: reduce)").matches),
      allowClose: true,
      allowKeyboardControl: true,
      disableActiveInteraction: true,
      overlayOpacity: 0.62,
      showProgress: true,
      progressText: translate(gettext_noop("Paso {{current}} de {{total}}")),
      nextBtnText: translate(gettext_noop("Siguiente")),
      prevBtnText: translate(gettext_noop("Anterior")),
      doneBtnText: translate(gettext_noop("Finalizar")),
      popoverClass: "balance-tour-popover",
      stagePadding: 8,
      stageRadius: 8,
      skipMissingElement: true,
      onCloseClick: finish,
      onDoneClick: finish,
      onPopoverRender: function (popover) {
        popover.closeButton.setAttribute("aria-label", translate(gettext_noop("Omitir guía")));
        popover.closeButton.setAttribute("title", translate(gettext_noop("Omitir guía")));
      },
      steps: appendManualLink(pageElement, getSteps(pageName)),
    });

    tour.drive();
    return true;
  }

  function init() {
    if (!root.document) return;

    var pageElement = root.document.querySelector("[data-balance-tour]");
    if (!pageElement) return;

    var pageName = pageElement.getAttribute("data-balance-tour");
    var startButton = pageElement.querySelector("[data-balance-tour-start]");

    if (startButton) {
      startButton.addEventListener("click", function () {
        start(pageElement);
      });
    }

    var forceStart = false;
    try {
      forceStart = new URLSearchParams(root.location.search).get("guia") === "1";
    } catch (error) {
      forceStart = false;
    }

    if (forceStart || !isCompleted(pageName)) {
      root.setTimeout(function () {
        start(pageElement);
      }, 900);
    }
  }

  if (root.document && typeof root.document.addEventListener === "function") {
    if (root.document.readyState === "loading") {
      root.document.addEventListener("DOMContentLoaded", init);
    } else {
      init();
    }
  }

  return {
    TOUR_VERSION: TOUR_VERSION,
    getStorageKey: getStorageKey,
    isCompleted: isCompleted,
    markCompleted: markCompleted,
    getSteps: getSteps,
    start: start,
    init: init,
  };
});
