/*
 * Pagos de Ventas — edición en modal sobre el formset inline.
 *
 * El formset real permanece oculto (.pv-forms); la tabla .pv-summary es una
 * vista compacta. Abrir/editar mueve los .pv-field al modal y, al aceptar,
 * los devuelve. Agregar clona la plantilla __prefix__, la reindexa y sube
 * TOTAL_FORMS. El guardado lo hace el formset de Django normalmente.
 */
(function () {
  "use strict";

  function onReady(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  function forEach(nodes, fn) {
    Array.prototype.forEach.call(nodes, fn);
  }

  function reindex(root, from, to) {
    var nodes = root.querySelectorAll("[name],[id],[for]");
    function fix(el) {
      ["name", "id", "for"].forEach(function (attr) {
        var value = el.getAttribute(attr);
        if (value && value.indexOf(from) !== -1) {
          el.setAttribute(attr, value.split(from).join(to));
        }
      });
    }
    fix(root);
    forEach(nodes, fix);
  }

  function selectedText(select) {
    if (!select || select.selectedIndex < 0) return "";
    var option = select.options[select.selectedIndex];
    return option ? option.textContent.trim() : "";
  }

  function jQueryRef() {
    return window.jQuery || (window.django && window.django.jQuery);
  }

  // Jazzmin inicializa Select2 sobre TODOS los <select> mientras el formset
  // está oculto; al inicializarse sin tamaño visible el dropdown no abre dentro
  // del modal. Lo desactivamos para dejar selects nativos (que siempre abren).
  function stripSelect2(root) {
    var $ = jQueryRef();
    if (!$ || !$.fn || !$.fn.select2 || !root) return;
    forEach(root.querySelectorAll("select.select2-hidden-accessible"), function (sel) {
      try {
        $(sel).select2("destroy");
      } catch (err) {
        /* noop */
      }
    });
  }

  function initGroup(group) {
    if (group.dataset.pvReady === "1") return;
    group.dataset.pvReady = "1";

    var prefix = group.dataset.prefix;
    var hasChange = group.dataset.hasChange === "1";
    var hasDelete = group.dataset.hasDelete === "1";

    var formsWrap = group.querySelector(".pv-forms");
    var summaryBody = group.querySelector(".pv-summary-body");
    var emptyMsg = group.querySelector(".pv-empty-msg");
    var addBtn = group.querySelector(".pv-add");
    var totalInput = group.querySelector('input[name="' + prefix + '-TOTAL_FORMS"]');
    var modal = document.getElementById("pv-modal-" + prefix);

    if (!formsWrap || !summaryBody || !totalInput || !modal) return;

    var modalBody = modal.querySelector(".pv-modal-body");
    var acceptBtn = modal.querySelector(".pv-modal-accept");

    var currentForm = null;
    var currentRow = null;
    var isNew = false;

    function formByIndex(index) {
      return formsWrap.querySelector('.pv-form[data-index="' + index + '"]');
    }

    function readValues(form) {
      var fecha = form.querySelector(".field-fecha_pago input");
      var monto = form.querySelector(".field-monto_pago input");
      var cuenta = form.querySelector(".field-cuenta_destino select");
      var metodo = form.querySelector(".field-metodo_pago select");
      return {
        fecha: fecha ? fecha.value : "",
        monto: monto ? monto.value : "",
        cuenta: selectedText(cuenta),
        metodo: selectedText(metodo)
      };
    }

    function refreshRow(row, form) {
      if (!row || !form) return;
      var values = readValues(form);
      row.children[0].textContent = values.fecha;
      row.children[1].textContent = values.monto;
      row.children[2].textContent = values.cuenta;
      row.children[3].textContent = values.metodo;
    }

    function visibleRows() {
      return summaryBody.querySelectorAll(".pv-summary-row:not(.pv-row-removed)");
    }

    function updateEmptyMsg() {
      if (!emptyMsg) return;
      emptyMsg.hidden = visibleRows().length > 0;
    }

    function openModal(form, row, newFlag) {
      currentForm = form;
      currentRow = row;
      isNew = !!newFlag;
      forEach(form.querySelectorAll(".pv-field"), function (field) {
        modalBody.appendChild(field);
      });
      stripSelect2(modalBody);
      modal.hidden = false;
      document.body.classList.add("pv-modal-open");
      var focusable = modalBody.querySelector("input, select, textarea");
      if (focusable) focusable.focus();
    }

    function closeModal() {
      if (currentForm) {
        forEach(modalBody.querySelectorAll(".pv-field"), function (field) {
          currentForm.appendChild(field);
        });
      }
      modal.hidden = true;
      document.body.classList.remove("pv-modal-open");
      currentForm = null;
      currentRow = null;
      isNew = false;
    }

    function markDeleted(row, form) {
      var deleteInput = form.querySelector('input[type="checkbox"][name$="-DELETE"]');
      if (deleteInput) deleteInput.checked = true;
      if (row) {
        row.hidden = true;
        row.classList.add("pv-row-removed");
      }
      form.hidden = true;
    }

    function createRow(index) {
      var row = document.createElement("tr");
      row.className = "pv-summary-row";
      row.dataset.index = index;
      var actions = '<td class="pv-actions">';
      if (hasChange) {
        actions += '<button type="button" class="pv-edit" title="Editar" aria-label="Editar pago">✏️</button>';
      }
      if (hasDelete) {
        actions += '<button type="button" class="pv-delete" title="Eliminar" aria-label="Eliminar pago">✕</button>';
      }
      actions += "</td>";
      row.innerHTML = "<td></td><td class=\"pv-monto\"></td><td></td><td></td>" + actions;
      return row;
    }

    function addPayment() {
      var template = formByIndex("__prefix__");
      if (!template) return;
      var index = parseInt(totalInput.value, 10) || 0;
      var clone = template.cloneNode(true);
      reindex(clone, "__prefix__", String(index));
      clone.dataset.index = String(index);
      clone.dataset.original = "0";
      formsWrap.appendChild(clone);
      totalInput.value = index + 1;
      var row = createRow(index);
      summaryBody.appendChild(row);
      updateEmptyMsg();
      openModal(clone, row, true);
    }

    function accept() {
      if (currentForm) refreshRow(currentRow, currentForm);
      closeModal();
    }

    function cancel() {
      var wasNew = isNew;
      var form = currentForm;
      var row = currentRow;
      if (wasNew && form && row) markDeleted(row, form);
      closeModal();
      updateEmptyMsg();
    }

    if (addBtn) addBtn.addEventListener("click", addPayment);
    if (acceptBtn) acceptBtn.addEventListener("click", accept);
    forEach(modal.querySelectorAll("[data-pv-close]"), function (el) {
      el.addEventListener("click", cancel);
    });

    group.addEventListener("click", function (event) {
      var editBtn = event.target.closest(".pv-edit");
      var deleteBtn = event.target.closest(".pv-delete");
      if (editBtn) {
        var row = editBtn.closest(".pv-summary-row");
        var form = formByIndex(row.dataset.index);
        if (form) openModal(form, row, false);
      } else if (deleteBtn) {
        var delRow = deleteBtn.closest(".pv-summary-row");
        var delForm = formByIndex(delRow.dataset.index);
        if (delForm) {
          markDeleted(delRow, delForm);
          updateEmptyMsg();
        }
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !modal.hidden) cancel();
    });

    // Si la validación del servidor falló, abrir el primer form con errores.
    var errorForm = null;
    forEach(formsWrap.querySelectorAll(".pv-form"), function (form) {
      if (!errorForm && form.dataset.index !== "__prefix__" && form.querySelector(".pv-errors .errorlist")) {
        errorForm = form;
      }
    });
    if (errorForm) {
      var errorRow = summaryBody.querySelector('.pv-summary-row[data-index="' + errorForm.dataset.index + '"]');
      openModal(errorForm, errorRow, false);
    }

    updateEmptyMsg();
  }

  onReady(function () {
    forEach(document.querySelectorAll(".pagoventa-modal-group"), initGroup);
  });

  // Tras `load`, Jazzmin ya aplicó Select2 (su handler corre en document.ready).
  window.addEventListener("load", function () {
    forEach(document.querySelectorAll(".pagoventa-modal-group .pv-forms"), stripSelect2);
  });
})();
