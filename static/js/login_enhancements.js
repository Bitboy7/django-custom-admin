/**
 * Mejoras para el formulario de login
 * - Mostrar/ocultar contraseña
 * - Validación visual en tiempo real
 * - Animaciones de entrada
 */

(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    initPasswordToggle();
    initFormEnhancements();
  });

  /**
   * Inicializa el botón para mostrar/ocultar contraseña
   */
  function initPasswordToggle() {
    const passwordInput = document.querySelector(
      'input[type="password"][name="password"]'
    );

    if (!passwordInput) return;

    const fieldWrap = passwordInput.closest(".field-wrap");
    if (!fieldWrap) return;

    fieldWrap.style.position = "relative";

    const toggleButton = createToggleButton();
    fieldWrap.appendChild(toggleButton);

    toggleButton.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      togglePasswordVisibility(passwordInput, toggleButton);
    });

    // Ajustar padding del input
    const currentPadding = parseFloat(window.getComputedStyle(passwordInput).paddingRight) || 0;
    passwordInput.style.paddingRight = Math.max(currentPadding, 48) + "px";
  }

  function createToggleButton() {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "password-toggle-btn";
    button.setAttribute("aria-label", "Mostrar contraseña");
    button.setAttribute("title", "Mostrar contraseña");
    button.style.cssText =
      "position:absolute;right:12px;top:50%;transform:translateY(-50%);" +
      "background:none;border:none;padding:6px;cursor:pointer;" +
      "color:#586f7c;font-size:14px;line-height:1;border-radius:6px;" +
      "transition:color .2s,background .2s;";

    const icon = document.createElement("i");
    icon.className = "fas fa-eye";
    button.appendChild(icon);

    button.addEventListener("mouseenter", function () {
      this.style.color = "#586f7c";
      this.style.background = "#f4f4f9";
    });
    button.addEventListener("mouseleave", function () {
      this.style.color = this.classList.contains("active") ? "#2f4550" : "#586f7c";
      this.style.background = "transparent";
    });

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
      button.style.color = "#2f4550";
    } else {
      input.type = "password";
      icon.className = "fas fa-eye";
      button.setAttribute("aria-label", "Mostrar contraseña");
      button.setAttribute("title", "Mostrar contraseña");
      button.classList.remove("active");
      button.style.color = "#586f7c";
    }

    input.focus();
  }

  /**
   * Mejoras adicionales del formulario
   */
  function initFormEnhancements() {
    const inputs = document.querySelectorAll(
      'input[type="text"], input[type="password"], input[type="email"]'
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
          const btn = form.querySelector('.btn-submit');
          if (btn) {
            btn.disabled = true;
            btn.style.opacity = '0.7';
            const originalHTML = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> ' + (btn.textContent.trim().split(' ')[0] || 'Procesando...');
            // Restaurar después de 10s por si hay error de red
            setTimeout(function() {
              btn.disabled = false;
              btn.style.opacity = '';
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
