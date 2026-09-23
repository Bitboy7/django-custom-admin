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
      if (form.dataset.ajaxUpload === "true") return;
      form.addEventListener("submit", function () {
        var progress = form.querySelector("[data-processing-progress]");
        form.setAttribute("aria-busy", "true");
        if (progress) progress.hidden = false;
        var button = form.querySelector("[data-submit-button]");
        if (!button) return;
        button.classList.add("is-loading");
        button.disabled = true;
        var label = button.querySelector("[data-submit-label]");
        if (label) label.textContent = button.dataset.loadingLabel || "Procesando…";
      });
    });
  }

  function initUploadProgress() {
    var form = document.querySelector("[data-upload-form]");
    if (!form || !window.FormData || !window.XMLHttpRequest) return;

    form.dataset.ajaxUpload = "true";

    var input = document.getElementById("id_archivos_cfdi");
    var dropzone = form.querySelector("[data-upload-dropzone]");
    var progress = form.querySelector("[data-upload-progress]");
    var track = form.querySelector("[data-upload-track]");
    var bar = form.querySelector("[data-upload-bar]");
    var value = form.querySelector("[data-upload-value]");
    var title = form.querySelector("[data-upload-title]");
    var status = form.querySelector("[data-upload-status]");
    var note = form.querySelector("[data-upload-note]");
    var button = form.querySelector("[data-submit-button]");
    var buttonLabel = button ? button.querySelector("[data-submit-label]") : null;
    var originalButtonLabel = buttonLabel ? buttonLabel.textContent : "Procesar archivos";

    function setProgress(percent) {
      var safePercent = Math.max(0, Math.min(100, Math.round(percent)));
      if (bar) bar.style.width = safePercent + "%";
      if (value) value.textContent = safePercent + "%";
      if (track) {
        track.setAttribute("aria-valuenow", String(safePercent));
        track.removeAttribute("aria-valuetext");
      }
    }

    function setLoading(active) {
      form.setAttribute("aria-busy", active ? "true" : "false");
      if (input) input.disabled = active;
      if (dropzone) {
        dropzone.classList.toggle("is-uploading", active);
        dropzone.setAttribute("aria-disabled", active ? "true" : "false");
        dropzone.tabIndex = active ? -1 : 0;
      }
      if (button) {
        button.disabled = active;
        button.classList.toggle("is-loading", active);
      }
    }

    function showError(message) {
      setLoading(false);
      if (progress) {
        progress.hidden = false;
        progress.classList.remove("is-processing");
        progress.classList.add("is-error");
      }
      if (title) title.textContent = "No se pudieron subir los archivos";
      if (status) status.textContent = message;
      if (note) note.textContent = "Revisa tu conexión y vuelve a intentarlo.";
      if (value) value.textContent = "Error";
      if (track) {
        track.removeAttribute("aria-valuenow");
        track.setAttribute("aria-valuetext", "Error durante la carga");
      }
      if (buttonLabel) buttonLabel.textContent = "Intentar de nuevo";
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      if (form.dataset.uploading === "true") return;

      var files = input && input.files ? input.files.length : 0;
      if (!files) return;

      var body = new FormData(form);
      var request = new XMLHttpRequest();
      form.dataset.uploading = "true";
      setLoading(true);
      setProgress(0);

      if (progress) {
        progress.hidden = false;
        progress.classList.remove("is-error", "is-processing");
      }
      if (title) title.textContent = files === 1 ? "Subiendo comprobante…" : "Subiendo comprobantes…";
      if (status) status.textContent = files === 1 ? "Enviando 1 archivo" : "Enviando " + files + " archivos";
      if (note) note.textContent = "No cierres esta ventana mientras termina la carga.";
      if (buttonLabel) buttonLabel.textContent = "Subiendo archivos…";

      request.open((form.method || "POST").toUpperCase(), form.action || window.location.href, true);
      request.setRequestHeader("X-Requested-With", "XMLHttpRequest");

      request.upload.addEventListener("progress", function (uploadEvent) {
        if (!uploadEvent.lengthComputable) {
          if (progress) progress.classList.add("is-processing");
          if (value) value.textContent = "Subiendo";
          if (track) {
            track.removeAttribute("aria-valuenow");
            track.setAttribute("aria-valuetext", "Subiendo archivos");
          }
          return;
        }
        if (progress) progress.classList.remove("is-processing");
        setProgress((uploadEvent.loaded / uploadEvent.total) * 100);
        if (status) status.textContent = formatBytes(uploadEvent.loaded) + " de " + formatBytes(uploadEvent.total);
      });

      request.upload.addEventListener("load", function () {
        setProgress(100);
        if (progress) progress.classList.add("is-processing");
        if (title) title.textContent = "Carga completada";
        if (status) status.textContent = "Analizando y validando los comprobantes…";
        if (note) note.textContent = "Este paso puede tardar unos segundos.";
        if (value) value.textContent = "Procesando";
        if (track) {
          track.removeAttribute("aria-valuenow");
          track.setAttribute("aria-valuetext", "Analizando archivos");
        }
        if (buttonLabel) buttonLabel.textContent = "Analizando archivos…";
      });

      request.addEventListener("load", function () {
        form.dataset.uploading = "false";
        if (request.status >= 200 && request.status < 400) {
          if (request.responseURL && new URL(request.responseURL).pathname !== window.location.pathname) {
            window.location.assign(request.responseURL);
            return;
          }
          document.open();
          document.write(request.responseText);
          document.close();
          return;
        }
        showError("El servidor respondió con el código " + request.status + ".");
      });

      request.addEventListener("error", function () {
        form.dataset.uploading = "false";
        showError("Se interrumpió la conexión durante la carga.");
      });

      request.addEventListener("abort", function () {
        form.dataset.uploading = "false";
        showError("La carga fue cancelada antes de completarse.");
      });

      request.send(body);
    });

    window.addEventListener("pageshow", function (event) {
      if (!event.persisted) return;
      form.dataset.uploading = "false";
      setLoading(false);
      if (buttonLabel) buttonLabel.textContent = originalButtonLabel;
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

  function syncProductRequirement(row) {
    var include = row.querySelector("[data-include-row]");
    var product = row.querySelector("[data-product-select]");
    var createProduct = row.querySelector("[data-crear-producto]");
    var help = row.querySelector("[data-product-help]");
    if (!product) return;

    var requiredForType = product.dataset.productRequired === "true";
    var rowIncluded = !include || include.checked;
    var creatingProduct = Boolean(createProduct && createProduct.checked);
    product.required = requiredForType && rowIncluded && !product.disabled && !creatingProduct;
    product.setAttribute("aria-required", product.required ? "true" : "false");
    if (help) help.hidden = !product.required || Boolean(product.value) || creatingProduct;
  }

  function initSelectionControls() {
    var selectAll = document.querySelector("[data-select-all]");
    var checkboxes = document.querySelectorAll("[data-include-row]:not(:disabled)");

    if (selectAll) {
      selectAll.addEventListener("change", function () {
        checkboxes.forEach(function (checkbox) {
          checkbox.checked = selectAll.checked;
          syncProductRequirement(checkbox.closest("[data-import-row]"));
        });
        updateSelectionCount();
      });
    }

    checkboxes.forEach(function (checkbox) {
      checkbox.addEventListener("change", function () {
        syncProductRequirement(checkbox.closest("[data-import-row]"));
        updateSelectionCount();
      });
    });
    document.querySelectorAll("[data-import-row]").forEach(syncProductRequirement);
    document.querySelectorAll("[data-product-select]").forEach(function (product) {
      product.addEventListener("change", function () {
        syncProductRequirement(product.closest("[data-import-row]"));
      });
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

  function initProductCreation() {
    document.querySelectorAll("[data-crear-producto]").forEach(function (toggle) {
      var index = toggle.dataset.crearProducto;
      var select = document.querySelector('[data-product-select="' + index + '"]');
      var row = toggle.closest("[data-import-row]");

      toggle.addEventListener("change", function () {
        var suggestion = toggle.dataset.productSuggestion;
        document.querySelectorAll("[data-crear-producto]").forEach(function (candidate) {
          if (candidate.dataset.productSuggestion !== suggestion) return;
          candidate.checked = toggle.checked;
          var candidateIndex = candidate.dataset.crearProducto;
          var candidateSelect = document.querySelector('[data-product-select="' + candidateIndex + '"]');
          if (candidateSelect && candidate.checked) candidateSelect.value = "";
          syncProductRequirement(candidate.closest("[data-import-row]"));
        });
      });

      if (select) {
        select.addEventListener("change", function () {
          if (select.value && toggle.checked) toggle.checked = false;
          syncProductRequirement(row);
        });
      }
      syncProductRequirement(row);
    });
  }

  ready(function () {
    initDropzone();
    initUploadProgress();
    initSubmitState();
    initSelectionControls();
    initClientCreation();
    initProductCreation();
  });
})();
