/**
 * Mejoras para el formulario de login
 * - Mostrar/ocultar contraseña
 * - Validación visual en tiempo real
 * - Animaciones de entrada
 */

(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    initLoginPlaceholders();
    initPasswordToggle();
    initFormEnhancements();
  });

  function initLoginPlaceholders() {
    const inputs = document.querySelectorAll(
      '.field-wrap input[type="text"], .field-wrap input[type="password"], .field-wrap input[type="email"], .field-wrap input[type="number"]',
    );

    inputs.forEach(function (input) {
      const name = (input.getAttribute("name") || "").toLowerCase();
      const id = (input.getAttribute("id") || "").toLowerCase();
      const label = getFieldLabel(input).toLowerCase();
      const key = name + " " + id + " " + label;

      if (key.includes("password") || key.includes("contraseña")) {
        input.setAttribute("placeholder", "Ingresa tu contraseña");
        input.setAttribute("autocomplete", "current-password");
      } else if (
        key.includes("token") ||
        key.includes("otp") ||
        key.includes("código") ||
        key.includes("codigo")
      ) {
        input.setAttribute("placeholder", "000000");
        input.setAttribute("autocomplete", "one-time-code");
        input.setAttribute("inputmode", "numeric");
      } else if (
        key.includes("username") ||
        key.includes("usuario") ||
        key.includes("email")
      ) {
        input.setAttribute("placeholder", "tu.usuario");
        input.setAttribute("autocomplete", "username");
      }
    });
  }

  function getFieldLabel(input) {
    if (!input.id) return "";
    const label = document.querySelector('label[for="' + input.id + '"]');
    return label ? label.textContent.trim() : "";
  }

  /**
   * Inicializa el botón para mostrar/ocultar contraseña
   */
  function initPasswordToggle() {
    const passwordInput = document.querySelector(
      '.field-wrap input[type="password"]',
    );

    if (!passwordInput) return;

    const fieldWrap = passwordInput.closest(".field-wrap");
    if (!fieldWrap) return;

    fieldWrap.style.position = "relative";

    const toggleButton = createToggleButton();
    fieldWrap.appendChild(toggleButton);
    passwordInput.setAttribute("data-password-visible", "false");

    toggleButton.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      togglePasswordVisibility(passwordInput, toggleButton);
    });

    // Ajustar padding del input
    const currentPadding =
      parseFloat(window.getComputedStyle(passwordInput).paddingRight) || 0;
    passwordInput.style.paddingRight = Math.max(currentPadding, 48) + "px";
  }

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

  function togglePasswordVisibility(input, button) {
    const icon = button.querySelector("i");
    const isPassword = input.type === "password";

    if (isPassword) {
      input.type = "text";
      icon.className = "fas fa-eye-slash";
      button.setAttribute("aria-label", "Ocultar contraseña");
      button.setAttribute("title", "Ocultar contraseña");
      button.classList.add("active");
      input.setAttribute("data-password-visible", "true");
    } else {
      input.type = "password";
      icon.className = "fas fa-eye";
      button.setAttribute("aria-label", "Mostrar contraseña");
      button.setAttribute("title", "Mostrar contraseña");
      button.classList.remove("active");
      input.setAttribute("data-password-visible", "false");
    }

    input.focus();
  }

  /**
   * Mejoras adicionales del formulario
   */
  function initFormEnhancements() {
    const inputs = document.querySelectorAll(
      'input[type="text"], input[type="password"], input[type="email"], input[type="number"]',
    );

    inputs.forEach(function (input) {
      input.addEventListener("blur", function () {
        validateInput(this);
      });

      input.addEventListener("input", function () {
        if (this.classList.contains("is-invalid")) {
          this.classList.remove("is-invalid");
        }
      });
    });

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
          const firstInvalid = form.querySelector(".is-invalid");
          if (firstInvalid) firstInvalid.focus();
        } else {
          // Deshabilitar botón y mostrar spinner durante envío
          const btn = form.querySelector(".btn-submit");
          if (btn) {
            btn.disabled = true;
            btn.style.opacity = "0.7";
            const originalHTML = btn.innerHTML;
            btn.innerHTML =
              '<i class="fas fa-circle-notch fa-spin"></i> ' +
              (btn.textContent.trim().split(" ")[0] || "Procesando...");
            // Restaurar después de 10s por si hay error de red
            setTimeout(function () {
              btn.disabled = false;
              btn.style.opacity = "";
              btn.innerHTML = originalHTML;
            }, 10000);
          }
        }
      });
    }
  }

  function validateInput(input) {
    if (input.hasAttribute("required") && !input.value.trim()) {
      input.classList.add("is-invalid");
      return false;
    }

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
})();
