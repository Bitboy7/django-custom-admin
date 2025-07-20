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
});
