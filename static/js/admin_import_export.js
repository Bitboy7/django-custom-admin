// ── Forzar tema claro de Jazzmin ──────────────────────────────────────────────
// El UI Builder de Jazzmin guarda el tema en localStorage bajo la clave "jazzmin".
// Si alguien eligió un tema oscuro en producción, persiste aunque settings.py diga
// "theme: default". Esta función lo resetea a valores claros en cada carga de página.
(function enforceJazzminLightTheme() {
  try {
    var stored = localStorage.getItem("jazzmin");
    if (stored) {
      var tweaks = JSON.parse(stored);
      var DARK_THEMES = ["darkly", "cyborg", "slate", "solar", "superhero"];
      var wasDark = DARK_THEMES.indexOf(tweaks.theme) !== -1;
      // Siempre forzar tema claro, independientemente de lo guardado
      tweaks.theme = "default";
      tweaks.dark_mode_theme = null;
      localStorage.setItem("jazzmin", JSON.stringify(tweaks));
      // Recargar solo si se estaba mostrando un tema oscuro (aplica el cambio visualmente)
      if (wasDark) {
        location.reload();
      }
    }
  } catch (e) {
    /* localStorage no disponible — ignorar */
  }
})();

// Script para reposicionar los botones de import/export en Django Jazzmin
document.addEventListener("DOMContentLoaded", function () {
  function repositionImportExportButtons() {
    // Buscar todos los menús de import/export
    const importExportMenus = document.querySelectorAll(".import_export_menu");

    importExportMenus.forEach((menu) => {
      // Remover cualquier estilo inline que cause posicionamiento absoluto
      menu.style.position = "relative";
      menu.style.top = "auto";
      menu.style.right = "auto";
      menu.style.left = "auto";
      menu.style.bottom = "auto";

      // Buscar el contenedor de herramientas de objeto (botón Add)
      const objectTools = document.querySelector(".object-tools");
      const changelist = document.querySelector("#changelist");

      if (objectTools && changelist) {
        // Mover el menú después de las herramientas de objeto
        if (!menu.classList.contains("repositioned")) {
          objectTools.insertAdjacentElement("afterend", menu);
          menu.classList.add("repositioned");
        }
      }

      // Añadir clases para mejor estilo
      menu.classList.add("custom-positioned");
    });
  }

  // Ejecutar inmediatamente
  repositionImportExportButtons();

  // Ejecutar después de un pequeño delay para asegurar que el DOM esté completamente cargado
  setTimeout(repositionImportExportButtons, 100);

  // Observar cambios en el DOM (para aplicaciones SPA o contenido dinámico)
  const observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (mutation) {
      if (mutation.addedNodes.length > 0) {
        // Verificar si se han añadido nuevos menús de import/export
        const hasImportExportMenu = Array.from(mutation.addedNodes).some(
          (node) =>
            node.nodeType === 1 &&
            (node.classList?.contains("import_export_menu") ||
              node.querySelector?.(".import_export_menu")),
        );

        if (hasImportExportMenu) {
          setTimeout(repositionImportExportButtons, 50);
        }
      }
    });
  });

  // Observar el cuerpo del documento
  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });

  // También añadir estilos dinámicos para botones específicos
  function enhanceButtons() {
    const importButtons = document.querySelectorAll('a[href*="import"]');
    const exportButtons = document.querySelectorAll('a[href*="export"]');

    importButtons.forEach((btn) => {
      if (btn.closest(".import_export_menu")) {
        btn.setAttribute("title", "Importar datos desde archivo");
      }
    });

    exportButtons.forEach((btn) => {
      if (btn.closest(".import_export_menu")) {
        btn.setAttribute("title", "Exportar datos a archivo");
      }
    });
  }

  enhanceButtons();
  setTimeout(enhanceButtons, 500);

  // Funciones adicionales para mejorar la interfaz
  function improveUIExperience() {
    // Mejorar la apariencia de los mensajes
    const messages = document.querySelectorAll(".messagelist li");
    messages.forEach(function (message) {
      message.style.borderRadius = "6px";
      message.style.padding = "12px 16px";
      message.style.margin = "8px 0";
    });

    // Mejorar las tablas de resultados
    const resultTables = document.querySelectorAll(".results table");
    resultTables.forEach(function (table) {
      table.style.borderRadius = "8px";
      table.style.overflow = "hidden";
    });

    // Agregar animaciones sutiles a los botones
    const buttons = document.querySelectorAll(
      '.button, .submit-row input[type="submit"]',
    );
    buttons.forEach(function (button) {
      button.addEventListener("mouseenter", function () {
        this.style.transform = "translateY(-1px)";
        this.style.boxShadow = "0 4px 8px rgba(0, 0, 0, 0.15)";
        this.style.transition = "all 0.2s ease";
      });

      button.addEventListener("mouseleave", function () {
        this.style.transform = "translateY(0)";
        this.style.boxShadow = "0 2px 4px rgba(0, 0, 0, 0.1)";
      });
    });

    // Mejorar los campos de formulario
    const fieldBoxes = document.querySelectorAll(".form-row");
    fieldBoxes.forEach(function (fieldBox) {
      if (!fieldBox.classList.contains("field-box")) {
        fieldBox.classList.add("field-box");
      }
    });
  }

  // Función para mejorar la accesibilidad
  function improveAccessibility() {
    // Agregar roles ARIA apropiados
    const tables = document.querySelectorAll("table");
    tables.forEach(function (table) {
      if (!table.getAttribute("role")) {
        table.setAttribute("role", "table");
      }
    });

    // Mejorar la navegación por teclado
    const focusableElements = document.querySelectorAll(
      "a, button, input, select, textarea",
    );
    focusableElements.forEach(function (element) {
      element.addEventListener("focus", function () {
        this.style.outline = "2px solid #837896";
        this.style.outlineOffset = "2px";
      });

      element.addEventListener("blur", function () {
        this.style.outline = "none";
      });
    });
  }

  // Ejecutar mejoras adicionales
  improveUIExperience();
  improveAccessibility();
  initAdminDateTimeShortcutsPositioning();

  // ============================================
  // MEJORAS PARA LOGIN - Mostrar/Ocultar Contraseña
  // ============================================
  initLoginEnhancements();
});

/**
 * Mantiene los calendarios y relojes de Django junto a su icono.
 *
 * DateTimeShortcuts calcula posiciones absolutas recorriendo offsetParent. En
 * Jazzmin esas coordenadas dejan de coincidir con la ventana cuando hay
 * contenedores desplazables o cambia el zoom del navegador. Usamos las
 * coordenadas visibles del icono y position: fixed para evitar ese desfase.
 */
function initAdminDateTimeShortcutsPositioning() {
  if (
    typeof window.DateTimeShortcuts === 'undefined' ||
    window.DateTimeShortcuts.positioningPatched
  ) {
    return;
  }

  const shortcuts = window.DateTimeShortcuts;
  const VIEWPORT_GAP = 8;

  function clamp(value, minimum, maximum) {
    return Math.min(Math.max(value, minimum), Math.max(minimum, maximum));
  }

  function positionPopup(popup, anchor) {
    if (!popup || !anchor || popup.style.display === 'none') {
      return;
    }

    popup.style.setProperty('position', 'fixed', 'important');
    popup.style.setProperty('transform', 'none', 'important');
    popup.style.setProperty('margin', '0', 'important');
    popup.style.setProperty('z-index', '2050', 'important');

    const anchorRect = anchor.getBoundingClientRect();
    const popupRect = popup.getBoundingClientRect();
    const viewportWidth = document.documentElement.clientWidth;
    const viewportHeight = document.documentElement.clientHeight;

    let left = anchorRect.left;
    if (left + popupRect.width > viewportWidth - VIEWPORT_GAP) {
      left = anchorRect.right - popupRect.width;
    }
    left = clamp(
      left,
      VIEWPORT_GAP,
      viewportWidth - popupRect.width - VIEWPORT_GAP,
    );

    const below = anchorRect.bottom + VIEWPORT_GAP;
    const above = anchorRect.top - popupRect.height - VIEWPORT_GAP;
    let top = below;

    if (
      below + popupRect.height > viewportHeight - VIEWPORT_GAP &&
      above >= VIEWPORT_GAP
    ) {
      top = above;
    }
    top = clamp(
      top,
      VIEWPORT_GAP,
      viewportHeight - popupRect.height - VIEWPORT_GAP,
    );

    popup.style.setProperty('left', `${Math.round(left)}px`, 'important');
    popup.style.setProperty('top', `${Math.round(top)}px`, 'important');
  }

  function repositionOpenPopups() {
    document
      .querySelectorAll('.calendarbox[id^=calendarbox]')
      .forEach(function (popup) {
        const number = popup.id.replace('calendarbox', '');
        positionPopup(popup, document.getElementById(`calendarlink${number}`));
      });

    document
      .querySelectorAll('.clockbox[id^=clockbox]')
      .forEach(function (popup) {
        const number = popup.id.replace('clockbox', '');
        positionPopup(popup, document.getElementById(`clocklink${number}`));
      });
  }

  function wrapOpenMethod(methodName, popupPrefix, linkPrefix) {
    const originalMethod = shortcuts[methodName];
    if (typeof originalMethod !== 'function') {
      return;
    }

    shortcuts[methodName] = function (number) {
      originalMethod.call(shortcuts, number);
      positionPopup(
        document.getElementById(`${popupPrefix}${number}`),
        document.getElementById(`${linkPrefix}${number}`),
      );
    };
  }

  wrapOpenMethod('openCalendar', 'calendarbox', 'calendarlink');
  wrapOpenMethod('openClock', 'clockbox', 'clocklink');

  window.addEventListener('resize', repositionOpenPopups);
  window.addEventListener('scroll', repositionOpenPopups, true);
  shortcuts.positioningPatched = true;
}

/**
 * Inicializa mejoras para el formulario de login
 */
function initLoginEnhancements() {
  // Solo ejecutar en la página de login
  if (!document.body.classList.contains("jazzmin-login-page")) {
    return;
  }

  initPasswordToggle();
  initLoginFormValidation();
}

/**
 * Inicializa el botón para mostrar/ocultar contraseña
 */
function initPasswordToggle() {
  const passwordInput = document.querySelector(
    'input[type="password"][name="password"]',
  );

  if (!passwordInput) {
    return;
  }

  // Crear el botón de toggle
  const toggleButton = createPasswordToggleButton();

  // Obtener el contenedor del input
  const inputGroup =
    passwordInput.closest(".input-group") || passwordInput.parentElement;

  if (!inputGroup) {
    return;
  }

  // Asegurarse de que el contenedor tenga posición relativa
  if (!inputGroup.classList.contains("input-group")) {
    inputGroup.style.position = "relative";
  }

  // Agregar el botón al contenedor
  inputGroup.appendChild(toggleButton);

  // Agregar evento click al botón
  toggleButton.addEventListener("click", function (e) {
    e.preventDefault();
    e.stopPropagation();
    togglePasswordVisibility(passwordInput, toggleButton);
  });
}

/**
 * Crea el botón de toggle de contraseña
 */
function createPasswordToggleButton() {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "password-toggle-btn";
  button.setAttribute("aria-label", "Mostrar contraseña");
  button.setAttribute("title", "Mostrar contraseña");

  const icon = document.createElement("i");
  icon.className = "fas fa-eye";
  button.appendChild(icon);

  return button;
}

/**
 * Alterna la visibilidad de la contraseña
 */
function togglePasswordVisibility(input, button) {
  const icon = button.querySelector("i");
  const isPassword = input.type === "password";

  if (isPassword) {
    // Mostrar contraseña
    input.type = "text";
    icon.className = "fas fa-eye-slash";
    button.setAttribute("aria-label", "Ocultar contraseña");
    button.setAttribute("title", "Ocultar contraseña");
    button.classList.add("active");
  } else {
    // Ocultar contraseña
    input.type = "password";
    icon.className = "fas fa-eye";
    button.setAttribute("aria-label", "Mostrar contraseña");
    button.setAttribute("title", "Mostrar contraseña");
    button.classList.remove("active");
  }

  // Mantener el focus en el input
  input.focus();
}

/**
 * Validación del formulario de login
 */
function initLoginFormValidation() {
  const inputs = document.querySelectorAll(
    '.jazzmin-login-page input[type="text"], .jazzmin-login-page input[type="password"], .jazzmin-login-page input[type="email"]',
  );

  inputs.forEach(function (input) {
    // Limpiar validación al escribir
    input.addEventListener("input", function () {
      if (this.classList.contains("is-invalid")) {
        this.classList.remove("is-invalid");
      }
    });
  });

  // Validación al enviar formulario
  const form = document.querySelector(".jazzmin-login-page form");
  if (form) {
    form.addEventListener("submit", function (e) {
      let isValid = true;

      inputs.forEach(function (input) {
        if (input.hasAttribute("required") && !input.value.trim()) {
          input.classList.add("is-invalid");
          isValid = false;
        }
      });

      if (!isValid) {
        e.preventDefault();
        const firstInvalid = form.querySelector(".is-invalid");
        if (firstInvalid) {
          firstInvalid.focus();
        }
      }
    });
  }
}
