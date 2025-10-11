// *** SISTEMA DE LOGGING SEGURO PARA PRODUCCIÓN ***
const DEBUG_MODE = false; // Cambiar a true solo en desarrollo

// Helper para logging condicional
const logger = {
  log: (...args) => DEBUG_MODE && console.log(...args),
  error: (...args) => console.error(...args), // Siempre mostrar errores
  warn: (...args) => DEBUG_MODE && console.warn(...args),
};

// Funciones para el toast de notificación
function showToast(title, message, duration = 4000) {
  const toast = document.getElementById("toast-notification");
  const toastTitle = document.getElementById("toast-title");
  const toastMessage = document.getElementById("toast-message");

  if (!toast || !toastTitle || !toastMessage) {
    logger.error("Elementos del toast no encontrados");
    return;
  }

  // Actualizar contenido del toast
  toastTitle.textContent = title;
  toastMessage.textContent = message;
  // Mostrar el toast
  toast.classList.remove("translate-x-full", "opacity-0");
  toast.classList.add("translate-x-0", "opacity-100");
  // Auto-ocultar después de la duración especificada
  setTimeout(function () {
    hideToast();
  }, duration);
}

function hideToast() {
  const toast = document.getElementById("toast-notification");
  if (toast) {
    toast.classList.remove("translate-x-0", "opacity-0");
    toast.classList.add("translate-x-full", "opacity-100");
  }
}

// *** SISTEMA DE PERSISTENCIA DE FILTROS ***

// Clave para localStorage
const FILTERS_STORAGE_KEY = "balances_filters";

// Guardar filtros en localStorage
function saveFiltersToStorage() {
  const filterForm = document.querySelector('form[action*="balances"]');
  if (!filterForm) return;

  try {
    const filters = {
      cuenta_id: document.getElementById("cuenta_id")?.value || "",
      sucursal_id: document.getElementById("sucursal_id")?.value || "",
      year: document.getElementById("year")?.value || "",
      month: document.getElementById("month")?.value || "",
      periodo: document.getElementById("periodo")?.value || "",
      dia: document.getElementById("dia")?.value || "",
      fecha_inicio:
        document.querySelector('input[name="fecha_inicio"]')?.value || "",
      fecha_fin: document.querySelector('input[name="fecha_fin"]')?.value || "",
      timestamp: new Date().getTime(),
    };

    localStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify(filters));
    logger.log("Filtros guardados correctamente");
  } catch (error) {
    logger.error("Error al guardar filtros:", error.message);
  }
}

// Cargar filtros desde localStorage
function loadFiltersFromStorage() {
  try {
    const savedFilters = localStorage.getItem(FILTERS_STORAGE_KEY);
    if (!savedFilters) return null;

    const filters = JSON.parse(savedFilters);

    // Verificar que los filtros no sean muy antiguos (más de 24 horas)
    const now = new Date().getTime();
    const maxAge = 24 * 60 * 60 * 1000; // 24 horas en milisegundos

    if (filters.timestamp && now - filters.timestamp > maxAge) {
      localStorage.removeItem(FILTERS_STORAGE_KEY);
      return null;
    }

    return filters;
  } catch (error) {
    logger.error("Error al cargar filtros:", error.message);
    localStorage.removeItem(FILTERS_STORAGE_KEY);
    return null;
  }
}

// Aplicar filtros guardados al formulario
function applyStoredFilters() {
  const urlParams = new URLSearchParams(window.location.search);
  const hasUrlParams = urlParams.toString().length > 0;

  // Si hay parámetros en la URL, sincronizar con localStorage
  if (hasUrlParams) {
    syncUrlParamsWithStorage();
    return;
  }

  const savedFilters = loadFiltersFromStorage();
  if (!savedFilters) return;

  // Aplicar cada filtro al formulario
  Object.keys(savedFilters).forEach((key) => {
    if (key === "timestamp") return;

    const element =
      document.getElementById(key) ||
      document.querySelector(`input[name="${key}"]`);
    if (element && savedFilters[key]) {
      element.value = savedFilters[key];

      // Disparar evento change para actualizar UI si es necesario
      element.dispatchEvent(new Event("change", { bubbles: true }));
    }
  });

  // Mostrar toast indicando que se aplicaron filtros guardados
  setTimeout(() => {
    showToast(
      "🔄 Filtros restaurados",
      "Se han aplicado los filtros de tu sesión anterior. Puedes modificarlos o limpiarlos según necesites.",
      6000
    );
  }, 500);
}

// Sincronizar parámetros URL con localStorage
function syncUrlParamsWithStorage() {
  const urlParams = new URLSearchParams(window.location.search);

  const currentFilters = {
    cuenta_id: urlParams.get("cuenta_id") || "",
    sucursal_id: urlParams.get("sucursal_id") || "",
    year: urlParams.get("year") || "",
    month: urlParams.get("month") || "",
    periodo: urlParams.get("periodo") || "",
    dia: urlParams.get("dia") || "",
    fecha_inicio: urlParams.get("fecha_inicio") || "",
    fecha_fin: urlParams.get("fecha_fin") || "",
    timestamp: new Date().getTime(),
  };

  // Solo guardar si hay al menos un filtro aplicado
  const hasFilters = Object.keys(currentFilters).some(
    (key) => key !== "timestamp" && currentFilters[key] !== ""
  );

  try {
    if (hasFilters) {
      localStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify(currentFilters));
      logger.log("Filtros sincronizados con URL");
    } else {
      localStorage.removeItem(FILTERS_STORAGE_KEY);
    }
  } catch (error) {
    logger.error("Error al sincronizar filtros:", error.message);
  }

  // Actualizar los inputs del formulario
  updateFormInputsFromUrl();
}

// Actualizar inputs del formulario con valores de la URL
function updateFormInputsFromUrl() {
  const urlParams = new URLSearchParams(window.location.search);

  // Mapear parámetros URL a elementos del formulario
  const urlToFormMapping = {
    cuenta_id: "cuenta_id",
    sucursal_id: "sucursal_id",
    year: "year",
    month: "month",
    periodo: "periodo",
    dia: "dia",
    fecha_inicio: "fecha_inicio",
    fecha_fin: "fecha_fin",
  };

  Object.keys(urlToFormMapping).forEach((urlParam) => {
    const formElementId = urlToFormMapping[urlParam];
    const element =
      document.getElementById(formElementId) ||
      document.querySelector(`input[name="${formElementId}"]`);

    if (element) {
      const urlValue = urlParams.get(urlParam);

      if (urlValue) {
        element.value = urlValue;
        element.dispatchEvent(new Event("change", { bubbles: true }));
      }
    }
  });

  // Manejar el contenedor de día específicamente para el periodo
  const periodoValue = urlParams.get("periodo");
  const diaContainer = document.getElementById("dia-container");
  if (diaContainer) {
    diaContainer.style.display = periodoValue === "diario" ? "flex" : "none";
  }
}

// Limpiar filtros guardados
function clearStoredFilters() {
  try {
    localStorage.removeItem(FILTERS_STORAGE_KEY);
    showToast(
      "🗑️ Filtros limpiados",
      "Los filtros guardados han sido eliminados. La próxima vez comenzarás con valores por defecto.",
      4000
    );
  } catch (error) {
    logger.error("Error al limpiar filtros:", error.message);
  }
}

// Verificar si hay filtros guardados y mostrar indicador
function checkStoredFiltersStatus() {
  const savedFilters = loadFiltersFromStorage();
  const clearBtn = document.getElementById("clear-stored-filters-btn");

  if (savedFilters && clearBtn) {
    // Hay filtros guardados - mostrar el botón con un estilo más llamativo
    clearBtn.classList.remove("opacity-50");
    clearBtn.classList.add("ring-2", "ring-orange-300");
    clearBtn.title =
      "Hay filtros guardados automáticamente - haz clic para limpiarlos";

    // Agregar un pequeño indicador visual
    if (!clearBtn.querySelector(".saved-indicator")) {
      const indicator = document.createElement("span");
      indicator.className =
        "saved-indicator absolute -top-1 -right-1 h-3 w-3 bg-red-500 rounded-full animate-pulse";
      clearBtn.style.position = "relative";
      clearBtn.appendChild(indicator);
    }
  } else if (clearBtn) {
    // No hay filtros guardados - mostrar el botón desactivado
    clearBtn.classList.add("opacity-50");
    clearBtn.classList.remove("ring-2", "ring-orange-300");
    clearBtn.title = "No hay filtros guardados automáticamente";

    // Remover indicador si existe
    const indicator = clearBtn.querySelector(".saved-indicator");
    if (indicator) {
      indicator.remove();
    }
  }
}

// Mostrar toast al cargar la página si hay parámetros de filtro
function checkAndShowFilterToast() {
  const urlParams = new URLSearchParams(window.location.search);
  const hasFilters =
    urlParams.has("cuenta_id") ||
    urlParams.has("sucursal_id") ||
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
    if (urlParams.get("sucursal_id")) {
      const sucursalSelect = document.getElementById("sucursal_id");
      const selectedOption =
        sucursalSelect.options[sucursalSelect.selectedIndex];
      activeFilters.push(`Sucursal: ${selectedOption.text}`);
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
    const warningMessage = document.getElementById("warning-message");
    if (warningMessage) {
      warningMessage.style.display = "none";
    }
  }, 5000);

  // Gestionar la visualización de los filtros de fecha según el periodo
  const periodoSelect = document.getElementById("periodo");
  if (periodoSelect) {
    periodoSelect.addEventListener("change", function () {
      const diaContainer = document.getElementById("dia-container");
      if (diaContainer) {
        if (this.value === "diario") {
          diaContainer.style.display = "flex";
        } else {
          diaContainer.style.display = "none";
        }
      }
    });
  }

  // *** APLICAR FILTROS GUARDADOS AL CARGAR LA PÁGINA ***
  applyStoredFilters();

  // *** ASEGURAR QUE LOS INPUTS ESTÉN ACTUALIZADOS CON LA URL ACTUAL ***
  // Esto es importante para cuando se recarga la página después de aplicar filtros
  setTimeout(() => {
    updateFormInputsFromUrl();
  }, 100);

  // *** VERIFICAR ESTADO DE FILTROS GUARDADOS ***
  checkStoredFiltersStatus();

  // *** GUARDAR FILTROS CUANDO SE ENVÍA EL FORMULARIO ***
  const filterForm = document.querySelector('form[action*="balances"]');
  if (filterForm) {
    filterForm.addEventListener("submit", function (e) {
      // Limpiar valores del formulario antes de enviar
      cleanFormValues(this);

      // Guardar filtros en localStorage ANTES de enviar
      saveFiltersToStorage();

      // Mostrar toast de carga inmediatamente
      showToast(
        "⏳ Aplicando filtros...",
        "Actualizando la información según los criterios seleccionados."
      );
    });
  }

  // *** AGREGAR BOTONES PARA LIMPIAR FILTROS ***
  const clearFiltersBtn = document.querySelector(
    'a[href*="balances"][href$="balances/"]'
  );
  if (clearFiltersBtn) {
    clearFiltersBtn.addEventListener("click", function (e) {
      // Limpiar filtros guardados cuando se hace clic en "Restablecer"
      clearStoredFilters();
    });
  }

  // Botón específico para limpiar solo los filtros guardados
  const clearStoredFiltersBtn = document.getElementById(
    "clear-stored-filters-btn"
  );
  if (clearStoredFiltersBtn) {
    clearStoredFiltersBtn.addEventListener("click", function (e) {
      e.preventDefault();
      clearStoredFilters();

      // Actualizar estado visual del botón
      checkStoredFiltersStatus();

      // Opcional: también limpiar el formulario actual
      const form = document.querySelector('form[action*="balances"]');
      if (form) {
        form.reset();
        // Disparar cambios para actualizar UI
        const periodoSelect = document.getElementById("periodo");
        if (periodoSelect) {
          periodoSelect.dispatchEvent(new Event("change"));
        }
      }
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

  // *** MOSTRAR TOAST SI HAY FILTROS APLICADOS AL CARGAR LA PÁGINA ***
  checkAndShowFilterToast();

  // *** FUNCIONALIDAD EXPANDIR/COLAPSAR CUENTAS ***

  // Manejar clics en botones de expansión
  document.addEventListener("click", function (e) {
    if (e.target.closest(".expand-btn")) {
      e.preventDefault();
      const button = e.target.closest(".expand-btn");
      const categoria = button.getAttribute("data-categoria");
      const icon = button.querySelector("i");

      // Encontrar todas las sub-filas de esta categoría
      const subRows = document.querySelectorAll(
        `.sub-row[data-categoria="${categoria}"]`
      );

      if (subRows.length > 0) {
        const isExpanded = button.classList.contains("expanded");

        if (isExpanded) {
          // Colapsar
          subRows.forEach((row) => {
            row.classList.add("hidden");
          });
          button.classList.remove("expanded");
          icon.classList.remove("fa-minus-circle");
          icon.classList.add("fa-plus-circle");
          button.setAttribute("title", "Expandir cuentas");
        } else {
          // Expandir
          subRows.forEach((row) => {
            row.classList.remove("hidden");
          });
          button.classList.add("expanded");
          icon.classList.remove("fa-plus-circle");
          icon.classList.add("fa-minus-circle");
          button.setAttribute("title", "Colapsar cuentas");
        }
      }
    }
  });

  // Expandir/colapsar todas las categorías
  function expandAllCategories() {
    const allButtons = document.querySelectorAll(".expand-btn");
    allButtons.forEach((button) => {
      const categoria = button.getAttribute("data-categoria");
      const subRows = document.querySelectorAll(
        `.sub-row[data-categoria="${categoria}"]`
      );
      const icon = button.querySelector("i");

      if (subRows.length > 0) {
        subRows.forEach((row) => {
          row.classList.remove("hidden");
        });
        button.classList.add("expanded");
        icon.classList.remove("fa-plus-circle");
        icon.classList.add("fa-minus-circle");
        button.setAttribute("title", "Colapsar cuentas");
      }
    });
  }

  function collapseAllCategories() {
    const allButtons = document.querySelectorAll(".expand-btn");
    allButtons.forEach((button) => {
      const categoria = button.getAttribute("data-categoria");
      const subRows = document.querySelectorAll(
        `.sub-row[data-categoria="${categoria}"]`
      );
      const icon = button.querySelector("i");

      if (subRows.length > 0) {
        subRows.forEach((row) => {
          row.classList.add("hidden");
        });
        button.classList.remove("expanded");
        icon.classList.remove("fa-minus-circle");
        icon.classList.add("fa-plus-circle");
        button.setAttribute("title", "Expandir cuentas");
      }
    });
  }

  // Hacer las funciones disponibles globalmente
  window.expandAllCategories = expandAllCategories;
  window.collapseAllCategories = collapseAllCategories;
});
