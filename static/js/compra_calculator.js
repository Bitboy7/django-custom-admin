/**
 * Calculadora automática para formularios de compra
 * Calcula automáticamente el monto total basado en cantidad × precio unitario
 */

(function () {
  "use strict";

  // Configuración
  const CONFIG = {
    selectors: {
      cantidad: [
        'input[name="cantidad"]',
        'input[id*="cantidad"]',
        ".field-cantidad input",
        "#id_cantidad_compra",
        ".form-group.field-cantidad input",
      ],
      precioUnitario: [
        'input[name="precio_unitario"]',
        'input[id*="precio_unitario"]',
        ".field-precio_unitario input",
        "#id_precio_unitario_compra",
        ".form-group.field-precio_unitario input",
      ],
      montoTotal: [
        'input[name="monto_total"]',
        'input[id*="monto_total"]',
        ".field-monto_total input",
        "#id_monto_total_compra",
        ".form-group.field-monto_total input",
      ],
    },
    animationDuration: 1000,
    highlightColor: "#e8f5e8",
    readonlyColor: "#f8f9fa",
  };

  /**
   * Busca un elemento usando múltiples selectores
   */
  function findElement(selectors) {
    for (const selector of selectors) {
      const element = document.querySelector(selector);
      if (element) {
        console.log(`✅ Elemento encontrado con selector: ${selector}`);
        return element;
      }
    }
    return null;
  }

  /**
   * Valida y formatea un número
   */
  function parseNumber(value) {
    const num = parseFloat(value) || 0;
    return Math.max(0, num); // No permitir números negativos
  }

  /**
   * Formatea un número a 2 decimales
   */
  function formatCurrency(value) {
    return parseNumber(value).toFixed(2);
  }

  /**
   * Agrega efecto visual de cálculo
   */
  function highlightCalculation(element) {
    if (!element) return;

    const originalColor = element.style.backgroundColor;
    element.style.backgroundColor = CONFIG.highlightColor;
    element.style.transition = "background-color 0.3s ease";

    setTimeout(() => {
      element.style.backgroundColor = originalColor;
    }, CONFIG.animationDuration);
  }

  /**
   * Configura un campo como solo lectura
   */
  function makeReadonly(element, placeholder = "") {
    if (!element) return;

    element.setAttribute("readonly", true);
    element.style.backgroundColor = CONFIG.readonlyColor;
    element.title =
      "Este campo se calcula automáticamente (Cantidad × Precio Unitario)";

    if (placeholder) {
      element.placeholder = placeholder;
    }
  }

  /**
   * Calcula el monto total
   */
  function calculateTotal(cantidadInput, precioInput, totalInput) {
    const cantidad = parseNumber(cantidadInput.value);
    const precio = parseNumber(precioInput.value);
    const total = cantidad * precio;

    totalInput.value = formatCurrency(total);
    highlightCalculation(totalInput);

    console.log(
      `💰 Cálculo: ${cantidad} × ${precio} = ${formatCurrency(total)}`
    );

    // Dispatch custom event for other scripts
    totalInput.dispatchEvent(
      new CustomEvent("compra:calculated", {
        detail: { cantidad, precio, total },
      })
    );

    return total;
  }

  /**
   * Inicializa la calculadora para un conjunto de campos
   */
  function initializeCalculator() {
    console.log("🔢 Inicializando calculadora de compras...");

    // Buscar elementos
    const cantidadInput = findElement(CONFIG.selectors.cantidad);
    const precioInput = findElement(CONFIG.selectors.precioUnitario);
    const totalInput = findElement(CONFIG.selectors.montoTotal);

    // Verificar que todos los elementos existan
    if (!cantidadInput || !precioInput || !totalInput) {
      console.log("⚠️ No se encontraron todos los campos necesarios:", {
        cantidad: !!cantidadInput,
        precio: !!precioInput,
        total: !!totalInput,
      });
      return false;
    }

    console.log("✅ Todos los campos encontrados, configurando calculadora...");

    // Hacer el campo total de solo lectura
    makeReadonly(totalInput, "Se calculará automáticamente");

    // Función de cálculo
    const updateTotal = () =>
      calculateTotal(cantidadInput, precioInput, totalInput);

    // Agregar event listeners
    cantidadInput.addEventListener("input", updateTotal);
    cantidadInput.addEventListener("change", updateTotal);
    cantidadInput.addEventListener("blur", updateTotal);

    precioInput.addEventListener("input", updateTotal);
    precioInput.addEventListener("change", updateTotal);
    precioInput.addEventListener("blur", updateTotal);

    // Validación de entrada para cantidad (solo números enteros positivos)
    cantidadInput.addEventListener("input", function () {
      let value = this.value.replace(/[^\d]/g, ""); // Solo números
      if (value !== this.value) {
        this.value = value;
      }
    });

    // Validación de entrada para precio (números decimales positivos)
    precioInput.addEventListener("input", function () {
      let value = this.value.replace(/[^\d.]/g, ""); // Solo números y punto decimal

      // Asegurar solo un punto decimal
      const parts = value.split(".");
      if (parts.length > 2) {
        value = parts[0] + "." + parts.slice(1).join("");
      }

      if (value !== this.value) {
        this.value = value;
      }
    });

    // Cálculo inicial si ya hay valores
    updateTotal();

    console.log("🎉 Calculadora configurada exitosamente");
    return true;
  }

  /**
   * Reinicia la calculadora (útil para formularios dinámicos)
   */
  function reinitializeCalculator() {
    console.log("🔄 Reinicializando calculadora...");
    return initializeCalculator();
  }

  /**
   * Observador de mutaciones para detectar nuevos formularios
   */
  function setupMutationObserver() {
    const observer = new MutationObserver(function (mutations) {
      let shouldReinitialize = false;

      mutations.forEach(function (mutation) {
        if (mutation.addedNodes.length > 0) {
          mutation.addedNodes.forEach(function (node) {
            if (node.nodeType === Node.ELEMENT_NODE) {
              // Verificar si se agregaron campos de formulario relevantes
              const hasRelevantFields =
                node.querySelector &&
                (node.querySelector('input[name*="cantidad"]') ||
                  node.querySelector('input[name*="precio_unitario"]') ||
                  node.querySelector('input[name*="monto_total"]'));

              if (hasRelevantFields) {
                shouldReinitialize = true;
              }
            }
          });
        }
      });

      if (shouldReinitialize) {
        setTimeout(reinitializeCalculator, 100);
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });

    console.log("👀 Observador de mutaciones configurado");
  }

  // API pública
  window.CompraCalculator = {
    init: initializeCalculator,
    reinit: reinitializeCalculator,
    calculate: calculateTotal,
  };

  // Inicialización automática
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      initializeCalculator();
      setupMutationObserver();
    });
  } else {
    initializeCalculator();
    setupMutationObserver();
  }

  console.log("💼 Módulo CompraCalculator cargado");
})();
