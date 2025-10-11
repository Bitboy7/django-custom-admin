// JavaScript para mejorar la funcionalidad de los campos de dinero

document.addEventListener("DOMContentLoaded", function () {
  // Símbolos de moneda para mostrar
  const currencySymbols = {
    MXN: "$",
    USD: "US$",
    EUR: "€",
    GBP: "£",
    JPY: "¥",
    CAD: "C$",
    AUD: "A$",
    CHF: "CHF",
    CNY: "¥",
    INR: "₹",
  };

  // Tasas de cambio aproximadas con MXN como base (en una aplicación real, estas vendrían de una API)
  const exchangeRates = {
    MXN: 1.0,
    USD: 0.057,
    EUR: 0.048,
    GBP: 0.043,
    JPY: 6.28,
    CAD: 0.071,
    AUD: 0.077,
    CHF: 0.052,
    CNY: 0.37,
    INR: 4.28,
  };

  function initializeMoneyFields() {
    // Buscar todos los campos de dinero
    const moneyFields = document.querySelectorAll(
      'input[name*="_amount"], input[name*="monto_"], input[name*="precio_"]'
    );

    moneyFields.forEach(function (field) {
      const fieldContainer = field.closest(".form-row");
      if (!fieldContainer) return;

      // Buscar el select de moneda correspondiente
      const currencySelect = fieldContainer.querySelector(
        'select[name*="_currency"], select[name*="moneda_"]'
      );
      if (!currencySelect) return;

      // Crear wrapper personalizado
      createMoneyFieldWrapper(field, currencySelect);

      // Agregar validación en tiempo real
      addRealTimeValidation(field);

      // Agregar formateo automático
      addAutoFormatting(field);

      // Agregar conversión de moneda (opcional)
      addCurrencyConversion(field, currencySelect);
    });
  }

  function createMoneyFieldWrapper(amountField, currencySelect) {
    // Verificar si ya está envuelto
    if (amountField.closest(".money-field-wrapper")) return;

    const wrapper = document.createElement("div");
    wrapper.className = "money-field-wrapper";

    // Crear símbolo de moneda
    const symbolSpan = document.createElement("span");
    symbolSpan.className = "currency-symbol";
    symbolSpan.textContent = currencySymbols[currencySelect.value] || "$";

    // Reorganizar elementos
    const parent = amountField.parentNode;
    parent.insertBefore(wrapper, amountField);

    wrapper.appendChild(symbolSpan);
    wrapper.appendChild(amountField);
    wrapper.appendChild(currencySelect);

    // Actualizar símbolo cuando cambie la moneda
    currencySelect.addEventListener("change", function () {
      symbolSpan.textContent = currencySymbols[this.value] || "$";
    });

    // Agregar clases para styling
    amountField.classList.add("amount-input");
    currencySelect.classList.add("currency-select");
  }

  function addRealTimeValidation(field) {
    field.addEventListener("input", function () {
      const value = this.value;
      const wrapper = this.closest(".money-field-wrapper");

      // Validar que sea un número válido
      if (value && isNaN(parseFloat(value))) {
        wrapper.classList.add("error");
        this.setCustomValidity("Por favor ingresa un valor numérico válido");
      } else {
        wrapper.classList.remove("error");
        this.setCustomValidity("");
      }
    });
  }

  function addAutoFormatting(field) {
    field.addEventListener("blur", function () {
      const value = parseFloat(this.value);
      if (!isNaN(value)) {
        // Formatear a 2 decimales
        this.value = value.toFixed(2);
      }
    });

    // Agregar separadores de miles mientras se escribe
    field.addEventListener("input", function () {
      let value = this.value.replace(/,/g, "");
      if (!isNaN(value) && value !== "") {
        // Solo formatear si es un número válido
        const parts = value.split(".");
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
        this.value = parts.join(".");
      }
    });
  }

  function addCurrencyConversion(amountField, currencySelect) {
    function showConversion() {
      const amount = parseFloat(amountField.value.replace(/,/g, ""));
      const fromCurrency = currencySelect.value;

      if (isNaN(amount) || amount <= 0) return;

      // Convertir a MXN como base
      const mxnAmount = amount / exchangeRates[fromCurrency];

      // Crear tooltip con conversiones
      let tooltipText = `Equivalencias aproximadas:\n`;
      Object.keys(exchangeRates).forEach((currency) => {
        if (currency !== fromCurrency) {
          const convertedAmount = mxnAmount * exchangeRates[currency];
          tooltipText += `${currencySymbols[currency]}${convertedAmount.toFixed(
            2
          )} ${currency}\n`;
        }
      });
    }

    // Mostrar conversión cuando cambie el valor o la moneda
    amountField.addEventListener("blur", showConversion);
    currencySelect.addEventListener("change", showConversion);
  }

  function enhanceExistingMoneyWidgets() {
    // Mejorar widgets de django-money existentes
    const existingWidgets = document.querySelectorAll(
      ".vMoneyField, .money-widget"
    );

    existingWidgets.forEach(function (widget) {
      widget.style.display = "flex";
      widget.style.alignItems = "center";
      widget.style.gap = "8px";

      // Agregar estilos mejorados
      const inputs = widget.querySelectorAll("input, select");
      inputs.forEach(function (input) {
        input.style.borderRadius = "6px";
        input.style.padding = "8px 12px";
        input.style.border = "1px solid #d1d5db";
        input.style.transition = "all 0.2s ease";

        input.addEventListener("focus", function () {
          this.style.borderColor = "#4f46e5";
          this.style.boxShadow = "0 0 0 3px rgba(79, 70, 229, 0.1)";
        });

        input.addEventListener("blur", function () {
          this.style.borderColor = "#d1d5db";
          this.style.boxShadow = "none";
        });
      });
    });
  }

  // Inicializar todas las mejoras
  initializeMoneyFields();
  enhanceExistingMoneyWidgets();

  // Reinicializar cuando se agreguen nuevos campos dinámicamente
  const observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (mutation) {
      if (mutation.addedNodes.length > 0) {
        setTimeout(function () {
          initializeMoneyFields();
          enhanceExistingMoneyWidgets();
        }, 100);
      }
    });
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });
});
