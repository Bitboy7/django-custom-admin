(function () {
  "use strict";

  function toggleTerminoCredito() {
    var modalidad = document.getElementById("id_modalidad_pago");
    var group = document.getElementById("termino-credito-group");

    if (!modalidad || !group) {
      return;
    }

    var isCredito = modalidad.value === "Credito";
    var select = group.querySelector("select");

    group.style.display = isCredito ? "" : "none";
    if (select) {
      select.required = isCredito;
    }
  }

  function toggleExportFields() {
    var tipoVenta = document.getElementById("id_tipo_venta");
    var isNacional = tipoVenta && tipoVenta.value === "Nacional";

    document.querySelectorAll(".cfdi-export-only").forEach(function (group) {
      group.classList.toggle("cfdi-hidden", Boolean(isNacional));
      group.querySelectorAll("input, select, textarea").forEach(function (field) {
        field.required = false;
        if (isNacional) {
          field.value = "";
        }
      });
    });
  }

  function updateFileName(input) {
    var display = document.getElementById("file-name-display");

    if (!display || !input.files || !input.files[0]) {
      return;
    }

    display.textContent = input.files[0].name;
    display.classList.add("is-selected");
  }

  function initUploadDropzone() {
    var uploadLabel = document.getElementById("upload-label");
    var fileInput = document.getElementById("id_xml_file");

    if (!uploadLabel || !fileInput) {
      return;
    }

    fileInput.addEventListener("change", function () {
      updateFileName(fileInput);
    });

    ["dragover", "dragenter"].forEach(function (eventName) {
      uploadLabel.addEventListener(eventName, function (event) {
        event.preventDefault();
        uploadLabel.classList.add("is-dragging");
      });
    });

    ["dragleave", "drop"].forEach(function (eventName) {
      uploadLabel.addEventListener(eventName, function (event) {
        event.preventDefault();
        uploadLabel.classList.remove("is-dragging");
      });
    });

    uploadLabel.addEventListener("drop", function (event) {
      if (!event.dataTransfer || !event.dataTransfer.files.length) {
        return;
      }

      fileInput.files = event.dataTransfer.files;
      updateFileName(fileInput);
    });
  }

  function parseAccountLabel(option) {
    var text = option.textContent.trim();
    var parts = text.split(" - ");

    if (!option.value) {
      return {
        number: "Sin cuenta contable",
        detail: "Opcional para esta venta",
        search: text.toLowerCase()
      };
    }

    if (parts.length >= 4) {
      return {
        number: parts[parts.length - 1],
        detail: parts[1] + " · " + parts[2],
        search: text.toLowerCase()
      };
    }

    return {
      number: text,
      detail: "Cuenta bancaria",
      search: text.toLowerCase()
    };
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function createAccountLabel(option) {
    var account = parseAccountLabel(option);
    var selectedClass = option.selected ? " is-selected" : "";
    var value = escapeHtml(option.value);
    var search = escapeHtml(account.search);
    var number = escapeHtml(account.number);
    var detail = escapeHtml(account.detail);

    return (
      '<button type="button" class="bank-account-option' + selectedClass + '" data-bank-account-option data-value="' + value + '" data-search="' + search + '">' +
        '<span class="bank-account-option-content" data-bank-account-label>' +
          '<span class="bank-account-placeholder"><i class="fas fa-building-columns text-xs"></i></span>' +
          '<span class="min-w-0">' +
            '<span class="bank-account-number">' + number + '</span>' +
            '<span class="bank-account-bank">' + detail + '</span>' +
          '</span>' +
        '</span>' +
      '</button>'
    );
  }

  function initAccountSearch(wrapper) {
    var input = wrapper.querySelector("[data-bank-account-search]");
    var empty = wrapper.querySelector("[data-bank-account-empty]");
    var options = wrapper.querySelectorAll("[data-bank-account-option]");

    if (!input) {
      return;
    }

    input.addEventListener("input", function () {
      var query = input.value.trim().toLowerCase();
      var visibleCount = 0;

      options.forEach(function (option) {
        var isVisible = !query || (option.getAttribute("data-search") || "").indexOf(query) !== -1;
        option.hidden = !isVisible;
        if (isVisible) {
          visibleCount += 1;
        }
      });

      if (empty) {
        empty.classList.toggle("is-visible", visibleCount === 0);
      }
    });
  }

  function closeCuentaDropdown(wrapper) {
    var trigger = wrapper.querySelector("[data-cfdi-account-button]");

    wrapper.classList.remove("is-open");
    if (trigger) {
      trigger.setAttribute("aria-expanded", "false");
    }
  }

  function openCuentaDropdown(wrapper) {
    var trigger = wrapper.querySelector("[data-cfdi-account-button]");
    var search = wrapper.querySelector("[data-bank-account-search]");

    wrapper.classList.add("is-open");
    if (trigger) {
      trigger.setAttribute("aria-expanded", "true");
    }
    if (search) {
      search.focus();
    }
  }

  function updateCuentaCurrent(wrapper, option) {
    var current = wrapper.querySelector("[data-cfdi-account-current]");
    var label = option.querySelector("[data-bank-account-label]");

    if (current && label) {
      current.innerHTML = label.innerHTML;
    }
  }

  function bindCuentaDropdown(wrapper, select) {
    var trigger = wrapper.querySelector("[data-cfdi-account-button]");
    var options = wrapper.querySelectorAll("[data-bank-account-option]");

    if (!trigger) {
      return;
    }

    trigger.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();

      if (wrapper.classList.contains("is-open")) {
        closeCuentaDropdown(wrapper);
      } else {
        openCuentaDropdown(wrapper);
      }
    });

    options.forEach(function (option) {
      option.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();

        select.value = option.getAttribute("data-value") || "";
        select.dispatchEvent(new Event("change", { bubbles: true }));

        options.forEach(function (item) {
          item.classList.remove("is-selected");
        });
        option.classList.add("is-selected");

        updateCuentaCurrent(wrapper, option);
        closeCuentaDropdown(wrapper);
        trigger.focus();
      });
    });

    document.addEventListener("click", function (event) {
      if (!wrapper.contains(event.target)) {
        closeCuentaDropdown(wrapper);
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        closeCuentaDropdown(wrapper);
      }
    });
  }

  function initCuentaDropdown() {
    var select = document.getElementById("id_cuenta");

    if (!select || select.dataset.cfdiAccountReady === "true") {
      return;
    }

    var selectedOption = select.options[select.selectedIndex] || select.options[0];
    var menuId = "id_cuenta_menu";
    var wrapper = document.createElement("div");
    var labels = Array.prototype.map.call(select.options, createAccountLabel).join("");

    wrapper.className = "bank-account-select cfdi-account-select";
    wrapper.innerHTML =
      '<button type="button" class="bank-account-trigger" data-cfdi-account-button aria-expanded="false" aria-controls="' + menuId + '">' +
        '<span class="bank-account-current" data-cfdi-account-current>' +
          createAccountLabel(selectedOption).replace(/^<button[^>]*>|<\/button>$/g, "") +
        '</span>' +
        '<i class="fas fa-chevron-down bank-account-chevron"></i>' +
      '</button>' +
      '<div class="bank-account-menu" id="' + menuId + '" role="listbox">' +
        '<div class="cfdi-account-search"><input type="search" data-bank-account-search placeholder="Buscar cuenta, banco o sucursal"></div>' +
        '<div class="cfdi-account-options">' + labels + '</div>' +
        '<div class="cfdi-account-empty" data-bank-account-empty>No hay cuentas con esa búsqueda.</div>' +
      '</div>';

    select.classList.add("cfdi-native-select");
    select.setAttribute("data-bank-account-native", "");
    select.dataset.cfdiAccountReady = "true";
    select.insertAdjacentElement("afterend", wrapper);
    wrapper.insertBefore(select, wrapper.firstChild);

    initAccountSearch(wrapper);
    bindCuentaDropdown(wrapper, select);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var modalidad = document.getElementById("id_modalidad_pago");
    var tipoVenta = document.getElementById("id_tipo_venta");

    if (modalidad) {
      modalidad.addEventListener("change", toggleTerminoCredito);
      toggleTerminoCredito();
    }

    if (tipoVenta) {
      tipoVenta.addEventListener("change", toggleExportFields);
      toggleExportFields();
    }

    initUploadDropzone();
    initCuentaDropdown();
  });
})();
