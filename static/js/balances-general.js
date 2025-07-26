// Funciones para el toast de notificación
function showToast(title, message, duration = 4000) {
  const toast = document.getElementById("toast-notification");
  const toastTitle = document.getElementById("toast-title");
  const toastMessage = document.getElementById("toast-message");
  // Actualizar contenido del toast
  toastTitle.textContent = title;
  toastMessage.textContent = message;
  // Mostrar el toast
  toast.classList.remove("translate-x-full", "opacity-0");
  toast.classList.add("translate-x-0", "opacity-100");
  // Auto-ocultar después de 4 segundos
  setTimeout(function () {
    hideToast();
  }, duration);
}

function hideToast() {
  const toast = document.getElementById("toast-notification");
  toast.classList.remove("translate-x-0", "opacity-0");
  toast.classList.add("translate-x-full", "opacity-100");
}

// Mostrar toast al cargar la página si hay parámetros de filtro
function checkAndShowFilterToast() {
  const urlParams = new URLSearchParams(window.location.search);
  const hasFilters =
    urlParams.has("cuenta_id") ||
    urlParams.has("year") ||
    urlParams.has("month") ||
    urlParams.has("periodo") ||
    urlParams.has("dia") ||
    urlParams.has("fecha_inicio") ||
    urlParams.has("fecha_fin");
  if (hasFilters) {
    const activeFilters = [];
    if (urlParams.get("cuenta_id")) {
      const cuentaSelect = document.getElementById("cuenta_id");
      const selectedOption = cuentaSelect.options[cuentaSelect.selectedIndex];
      activeFilters.push(`Cuenta: ${selectedOption.text}`);
    }
    if (urlParams.get("year")) {
      activeFilters.push(`Año: ${urlParams.get("year")}`);
    }
    if (urlParams.get("month")) {
      const monthNames = [
        "Enero",
        "Febrero",
        "Marzo",
        "Abril",
        "Mayo",
        "Junio",
        "Julio",
        "Agosto",
        "Septiembre",
        "Octubre",
        "Noviembre",
        "Diciembre",
      ];
      const monthIndex = parseInt(urlParams.get("month")) - 1;
      if (monthIndex >= 0 && monthIndex < 12) {
        activeFilters.push(`Mes: ${monthNames[monthIndex]}`);
      }
    }
    if (urlParams.get("periodo")) {
      const periodos = {
        diario: "Diario",
        semanal: "Semanal",
        mensual: "Mensual",
      };
      activeFilters.push(
        `Periodo: ${
          periodos[urlParams.get("periodo")] || urlParams.get("periodo")
        }`
      );
    }
    if (urlParams.get("dia")) {
      activeFilters.push(`Día: ${urlParams.get("dia")}`);
    }
    if (urlParams.get("fecha_inicio") && urlParams.get("fecha_fin")) {
      activeFilters.push(
        `Rango: ${urlParams.get("fecha_inicio")} - ${urlParams.get(
          "fecha_fin"
        )}`
      );
    }
    let message = "Filtros aplicados: " + activeFilters.join(", ");
    if (message.length > 100) {
      message = `${activeFilters.length} filtros aplicados correctamente.`;
    }
    setTimeout(function () {
      showToast("¡Filtros aplicados!", message);
    }, 500);
  }
}

document.addEventListener("DOMContentLoaded", function () {
  // Ocultar el mensaje de advertencia después de 5 segundos
  setTimeout(function () {
    document.getElementById("warning-message").style.display = "none";
  }, 5000);
  // Gestionar la visualización de los filtros de fecha según el periodo
  document.getElementById("periodo").addEventListener("change", function () {
    const diaContainer = document.getElementById("dia-container");
    if (this.value === "diario") {
      diaContainer.style.display = "flex";
    } else {
      diaContainer.style.display = "none";
    }
  });
  // Mostrar notificación toast cuando se aplican filtros (al enviar el formulario)
  const filterForm = document.querySelector('form[action="/balances/"]');
  if (filterForm) {
    filterForm.addEventListener("submit", function (e) {
      // Limpiar valores del formulario antes de enviar
      cleanFormValues(this);
      // Mostrar toast de carga inmediatamente
      showToast(
        "Aplicando filtros...",
        "Actualizando la información según los criterios seleccionados."
      );
    });
  }
  // Función para limpiar valores del formulario
  function cleanFormValues(form) {
    // Limpiar espacios no rompibles y caracteres especiales del año
    const yearSelect = form.querySelector("#year");
    if (yearSelect && yearSelect.value) {
      yearSelect.value = yearSelect.value.replace(/[\u00A0\s]/g, "").trim();
    }
    // Limpiar mes
    const monthSelect = form.querySelector("#month");
    if (monthSelect && monthSelect.value) {
      monthSelect.value = monthSelect.value.replace(/[\u00A0\s]/g, "").trim();
    }
    // Limpiar cuenta_id
    const cuentaSelect = form.querySelector("#cuenta_id");
    if (cuentaSelect && cuentaSelect.value) {
      cuentaSelect.value = cuentaSelect.value.replace(/[\u00A0\s]/g, "").trim();
    }
  }
  // Mostrar toast si hay filtros aplicados al cargar la página
  checkAndShowFilterToast();
});
