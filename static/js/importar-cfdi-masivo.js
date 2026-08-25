(function () {
  "use strict";

  function ready(callback) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback);
    } else {
      callback();
    }
  }

  function formatBytes(bytes) {
    if (!bytes) return "0 KB";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  function renderSelectedFiles(input) {
    var summary = document.querySelector("[data-file-summary]");
    var count = document.querySelector("[data-file-count]");
    var size = document.querySelector("[data-file-size]");
    var list = document.querySelector("[data-file-list]");
    var defaultState = document.querySelector("[data-drop-default]");
    var selectedState = document.querySelector("[data-drop-selected]");
    var files = input && input.files ? Array.prototype.slice.call(input.files) : [];

    if (!summary || !count || !size || !list) return;

    summary.hidden = files.length === 0;
    if (defaultState) defaultState.hidden = files.length > 0;
    if (selectedState) selectedState.hidden = files.length === 0;
    if (!files.length) return;

    var totalSize = files.reduce(function (total, file) {
      return total + file.size;
    }, 0);

    count.textContent = files.length === 1 ? "1 archivo seleccionado" : files.length + " archivos seleccionados";
    size.textContent = formatBytes(totalSize);
    list.replaceChildren();

    files.slice(0, 6).forEach(function (file) {
      var item = document.createElement("li");
      var icon = document.createElement("i");
      var name = document.createElement("span");
      item.className = "file-summary__item";
      icon.className = file.name.toLowerCase().endsWith(".zip") ? "fas fa-file-zipper" : "fas fa-file-code";
      icon.setAttribute("aria-hidden", "true");
      name.textContent = file.name;
      item.appendChild(icon);
      item.appendChild(name);
      list.appendChild(item);
    });

    if (files.length > 6) {
      var remaining = document.createElement("li");
      remaining.className = "file-summary__item";
      remaining.textContent = "+ " + (files.length - 6) + " archivos más";
      list.appendChild(remaining);
    }
  }

  function initDropzone() {
    var dropzone = document.querySelector("[data-upload-dropzone]");
    var input = document.getElementById("id_archivos_cfdi");
    if (!dropzone || !input) return;

    input.addEventListener("change", function () {
      renderSelectedFiles(input);
    });

    ["dragenter", "dragover"].forEach(function (eventName) {
      dropzone.addEventListener(eventName, function (event) {
        event.preventDefault();
        dropzone.classList.add("is-dragging");
      });
    });

    ["dragleave", "drop"].forEach(function (eventName) {
      dropzone.addEventListener(eventName, function (event) {
        event.preventDefault();
        dropzone.classList.remove("is-dragging");
      });
    });

    dropzone.addEventListener("drop", function (event) {
      if (!event.dataTransfer || !event.dataTransfer.files.length) return;
      input.files = event.dataTransfer.files;
      renderSelectedFiles(input);
    });

    dropzone.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        input.click();
      }
    });
  }

  function initSubmitState() {
    document.querySelectorAll("[data-loading-form]").forEach(function (form) {
      form.addEventListener("submit", function () {
        var button = form.querySelector("[data-submit-button]");
        if (!button) return;
        button.classList.add("is-loading");
        button.disabled = true;
        var label = button.querySelector("[data-submit-label]");
        if (label) label.textContent = button.dataset.loadingLabel || "Procesando…";
      });
    });
  }

  function updateSelectionCount() {
    var checkboxes = Array.prototype.slice.call(document.querySelectorAll("[data-include-row]:not(:disabled)"));
    var selected = checkboxes.filter(function (checkbox) { return checkbox.checked; }).length;
    var count = document.querySelector("[data-selection-count]");
    var selectAll = document.querySelector("[data-select-all]");

    if (count) count.textContent = selected + " de " + checkboxes.length + " seleccionados";
    if (selectAll) {
      selectAll.checked = checkboxes.length > 0 && selected === checkboxes.length;
      selectAll.indeterminate = selected > 0 && selected < checkboxes.length;
    }
  }

  function initSelectionControls() {
    var selectAll = document.querySelector("[data-select-all]");
    var checkboxes = document.querySelectorAll("[data-include-row]:not(:disabled)");

    if (selectAll) {
      selectAll.addEventListener("change", function () {
        checkboxes.forEach(function (checkbox) {
          checkbox.checked = selectAll.checked;
        });
        updateSelectionCount();
      });
    }

    checkboxes.forEach(function (checkbox) {
      checkbox.addEventListener("change", updateSelectionCount);
    });
    updateSelectionCount();
  }

  function setCreateMode(index, enabled) {
    var select = document.querySelector('[data-cliente-select="' + index + '"]');
    var fields = document.querySelector('[data-create-fields="' + index + '"]');
    if (select && enabled) select.value = "";
    if (fields) fields.hidden = !enabled;
  }

  function initClientCreation() {
    document.querySelectorAll("[data-crear-cliente]").forEach(function (toggle) {
      var index = toggle.dataset.crearCliente;
      var select = document.querySelector('[data-cliente-select="' + index + '"]');

      toggle.addEventListener("change", function () {
        setCreateMode(index, toggle.checked);
      });

      if (select) {
        select.addEventListener("change", function () {
          if (select.value && toggle.checked) {
            toggle.checked = false;
            setCreateMode(index, false);
          }
        });
      }
      setCreateMode(index, toggle.checked);
    });
  }

  ready(function () {
    initDropzone();
    initSubmitState();
    initSelectionControls();
    initClientCreation();
  });
})();
