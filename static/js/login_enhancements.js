/**
 * Mejoras para el formulario de login
 * - Mostrar/ocultar contraseña
 * - Validación visual
 */

(function () {
  "use strict";

  // Esperar a que el DOM esté listo
  document.addEventListener("DOMContentLoaded", function () {
    initPasswordToggle();
    initFormEnhancements();
  });

  /**
   * Inicializa el botón para mostrar/ocultar contraseña
   */
  function initPasswordToggle() {
    // Buscar el campo de contraseña
    const passwordInput = document.querySelector(
      'input[type="password"][name="password"]'
    );

    if (!passwordInput) {
      return;
    }

    // Crear el botón de toggle
    const toggleButton = createToggleButton();

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

    // Ajustar el padding del input para dar espacio al botón
    adjustInputPadding(passwordInput);
  }

  /**
   * Crea el botón de toggle
   */
  function createToggleButton() {
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
   * Ajusta el padding del input para dar espacio al botón
   */
  function adjustInputPadding(input) {
    const currentPaddingRight = window.getComputedStyle(input).paddingRight;
    const additionalPadding = 45; // Espacio para el botón

    // Si ya tiene padding considerable, usarlo, sino agregar
    const currentPadding = parseFloat(currentPaddingRight) || 0;
    const newPadding = Math.max(currentPadding, additionalPadding);

    input.style.paddingRight = newPadding + "px";
  }

  /**
   * Mejoras adicionales del formulario
   */
  function initFormEnhancements() {
    // Agregar validación visual en tiempo real
    const inputs = document.querySelectorAll(
      'input[type="text"], input[type="password"], input[type="email"]'
    );

    inputs.forEach(function (input) {
      // Validación al perder el foco
      input.addEventListener("blur", function () {
        validateInput(this);
      });

      // Limpiar validación al escribir
      input.addEventListener("input", function () {
        if (this.classList.contains("is-invalid")) {
          this.classList.remove("is-invalid");
        }
      });
    });

    // Prevenir envío de formulario vacío
    const form = document.querySelector("form");
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
          // Focus en el primer campo inválido
          const firstInvalid = form.querySelector(".is-invalid");
          if (firstInvalid) {
            firstInvalid.focus();
          }
        }
      });
    }
  }

  /**
   * Valida un input individual
   */
  function validateInput(input) {
    if (input.hasAttribute("required") && !input.value.trim()) {
      input.classList.add("is-invalid");
      return false;
    }

    // Validación de email si es un campo de email
    if (input.type === "email" && input.value.trim()) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(input.value)) {
        input.classList.add("is-invalid");
        return false;
      }
    }

    input.classList.remove("is-invalid");
    return true;
  }

  /**
   * Animación de entrada para el formulario
   */
  function animateFormEntry() {
    const formGroups = document.querySelectorAll(".form-group, .input-group");
    formGroups.forEach(function (group, index) {
      group.style.opacity = "0";
      group.style.transform = "translateY(20px)";

      setTimeout(function () {
        group.style.transition = "all 0.4s ease-out";
        group.style.opacity = "1";
        group.style.transform = "translateY(0)";
      }, index * 100);
    });
  }

  // Ejecutar animación si el navegador lo soporta
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", animateFormEntry);
  } else {
    animateFormEntry();
  }
})();
