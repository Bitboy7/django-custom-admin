// Selector múltiple de meses
function initializeMultiMonthSelector() {
  const monthSelectorBtn = document.getElementById("month-selector-btn");
  const monthDropdown = document.getElementById("month-dropdown");
  const monthInput = document.getElementById("months");
  const monthSelectorText = document.getElementById("month-selector-text");
  const monthAllCheckbox = document.getElementById("month-all");
  const monthCheckboxes = document.querySelectorAll(".month-checkbox");
  const clearMonthsBtn = document.getElementById("clear-months");
  const applyMonthsBtn = document.getElementById("apply-months");

  // Retornar silenciosamente si los elementos no existen (normal en páginas sin selector de meses)
  if (!monthSelectorBtn || !monthDropdown || !monthInput) {
    return;
  }

  let selectedMonths = [];

  // Inicializar con valores existentes si los hay
  const initialValue = monthInput.value;

  if (initialValue && initialValue.trim() !== "") {
    selectedMonths = initialValue
      .split(",")
      .map((m) => parseInt(m.trim()))
      .filter((m) => !isNaN(m));
  }

  // Actualizar UI inicial
  updateDisplayText();
  updateCheckboxes();

  // Toggle dropdown al hacer click en el botón
  monthSelectorBtn.addEventListener("click", function (e) {
    e.preventDefault();
    e.stopPropagation();
    monthDropdown.classList.toggle("hidden");
  });

  // Cerrar dropdown al hacer click fuera
  document.addEventListener("click", function (e) {
    if (
      !monthSelectorBtn.contains(e.target) &&
      !monthDropdown.contains(e.target)
    ) {
      monthDropdown.classList.add("hidden");
    }
  });

  // Manejar "Todos los meses"
  if (monthAllCheckbox) {
    monthAllCheckbox.addEventListener("change", function () {
      if (this.checked) {
        selectedMonths = [];
        monthCheckboxes.forEach((checkbox) => {
          checkbox.checked = false;
        });
      }
      updateDisplayText();
    });
  }

  // Manejar checkboxes individuales
  monthCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener("change", function () {
      const monthValue = parseInt(this.value);

      if (this.checked) {
        if (!selectedMonths.includes(monthValue)) {
          selectedMonths.push(monthValue);
        }
        if (monthAllCheckbox) monthAllCheckbox.checked = false;
      } else {
        selectedMonths = selectedMonths.filter((m) => m !== monthValue);
      }

      selectedMonths.sort((a, b) => a - b);
      updateDisplayText();
    });
  });

  // Limpiar selección
  if (clearMonthsBtn) {
    clearMonthsBtn.addEventListener("click", function () {
      selectedMonths = [];
      if (monthAllCheckbox) monthAllCheckbox.checked = true;
      monthCheckboxes.forEach((checkbox) => {
        checkbox.checked = false;
      });
      updateDisplayText();

      // Actualizar el campo oculto y enviar formulario
      monthInput.value = "";
      const form = monthInput.closest("form");
      if (form) {
        form.submit();
      } else {
        console.error("No se encontró el formulario para enviar");
      }
    });
  }

  // Aplicar selección y cerrar dropdown
  if (applyMonthsBtn) {
    applyMonthsBtn.addEventListener("click", function () {
      monthInput.value = selectedMonths.join(",");
      monthDropdown.classList.add("hidden");
      updateDisplayText();

      // Enviar el formulario automáticamente
      const form = monthInput.closest("form");
      if (form) {
        form.submit();
      } else {
        console.error("No se encontró el formulario para enviar");
      }
    });
  }

  // Actualizar texto del selector
  function updateDisplayText() {
    let text = "";

    if (
      selectedMonths.length === 0 ||
      (monthAllCheckbox && monthAllCheckbox.checked)
    ) {
      text = "Todos los meses";
      monthInput.value = "";
    } else if (selectedMonths.length === 1) {
      const monthCheckbox = document.querySelector(
        `.month-checkbox[value="${selectedMonths[0]}"]`
      );
      const monthName = monthCheckbox
        ? monthCheckbox.dataset.name
        : `Mes ${selectedMonths[0]}`;
      text = monthName;
    } else if (selectedMonths.length <= 3) {
      const monthNames = selectedMonths.map((m) => {
        const monthCheckbox = document.querySelector(
          `.month-checkbox[value="${m}"]`
        );
        return monthCheckbox ? monthCheckbox.dataset.name : `Mes ${m}`;
      });
      text = monthNames.join(", ");
    } else {
      text = `${selectedMonths.length} meses seleccionados`;
    }

    if (monthSelectorText) {
      monthSelectorText.textContent = text;
    }
  }

  // Actualizar estado de checkboxes
  function updateCheckboxes() {
    if (selectedMonths.length === 0) {
      if (monthAllCheckbox) monthAllCheckbox.checked = true;
      monthCheckboxes.forEach((checkbox) => {
        checkbox.checked = false;
      });
    } else {
      if (monthAllCheckbox) monthAllCheckbox.checked = false;
      monthCheckboxes.forEach((checkbox) => {
        checkbox.checked = selectedMonths.includes(parseInt(checkbox.value));
      });
    }
  }
}

// Inicializar cuando el DOM esté listo
document.addEventListener("DOMContentLoaded", function () {
  // Esperar un poco para asegurar que todos los elementos estén cargados
  setTimeout(() => {
    initializeMultiMonthSelector();
  }, 100);
});
