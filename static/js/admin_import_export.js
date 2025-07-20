// Script para reposicionar los botones de import/export en Django Unfold
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
              node.querySelector?.(".import_export_menu"))
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
    const messages = document.querySelectorAll('.messagelist li');
    messages.forEach(function(message) {
      message.style.borderRadius = '6px';
      message.style.padding = '12px 16px';
      message.style.margin = '8px 0';
    });

    // Mejorar las tablas de resultados
    const resultTables = document.querySelectorAll('.results table');
    resultTables.forEach(function(table) {
      table.style.borderRadius = '8px';
      table.style.overflow = 'hidden';
    });

    // Agregar animaciones sutiles a los botones
    const buttons = document.querySelectorAll('.button, .submit-row input[type="submit"]');
    buttons.forEach(function(button) {
      button.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-1px)';
        this.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.15)';
        this.style.transition = 'all 0.2s ease';
      });
      
      button.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
        this.style.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.1)';
      });
    });

    // Mejorar los campos de formulario
    const fieldBoxes = document.querySelectorAll('.form-row');
    fieldBoxes.forEach(function(fieldBox) {
      if (!fieldBox.classList.contains('field-box')) {
        fieldBox.classList.add('field-box');
      }
    });
  }

  // Función para mejorar la accesibilidad
  function improveAccessibility() {
    // Agregar roles ARIA apropiados
    const tables = document.querySelectorAll('table');
    tables.forEach(function(table) {
      if (!table.getAttribute('role')) {
        table.setAttribute('role', 'table');
      }
    });

    // Mejorar la navegación por teclado
    const focusableElements = document.querySelectorAll('a, button, input, select, textarea');
    focusableElements.forEach(function(element) {
      element.addEventListener('focus', function() {
        this.style.outline = '2px solid #4f46e5';
        this.style.outlineOffset = '2px';
      });
      
      element.addEventListener('blur', function() {
        this.style.outline = 'none';
      });
    });
  }

  // Ejecutar mejoras adicionales
  improveUIExperience();
  improveAccessibility();

  console.log('🎉 JavaScript personalizado del admin cargado correctamente');
});
