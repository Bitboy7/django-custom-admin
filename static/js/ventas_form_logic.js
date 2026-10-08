/**
 * ventas_form_logic.js  — Ventas admin smart form logic
 *
 * Features
 * ─────────
 *  1. Modalidad = Crédito  → termino_credito required (visual + server).
 *  2. termino_credito / fecha_deposito change → fecha_vencimiento recalculated
 *     in real-time and locked (readonly) — cannot be edited manually.
 *  3. Cliente extranjero → tipo_venta auto-set to "Exportación" and LOCKED
 *     (cannot be overridden).  mercado_destino pre-filled from client data.
 *  4. Tab badges & inline info chips keep the user informed of auto-managed
 *     fields without switching tabs.
 *  5. Modalidad = Contado → estado_cobranza auto-set to "Pagado".
 *     Modalidad = Crédito → estado_cobranza auto-set to "Pendiente".
 *
 * Select2 compatibility
 * ─────────────────────
 * Jazzmin/AdminLTE applies Select2 to *all* <select> elements.
 * Plain `.value = x` updates the hidden <select> but NOT the Select2 rendered
 * widget.  Every programmatic value change must go through:
 *     jQ(el).val(x).trigger('change')
 * Similarly, blocking user interaction requires targeting the .select2-container
 * sibling, not the hidden <select>.
 */
(function () {
  "use strict";

  /* ── jQuery / Select2 handle ─────────────────────────────────────
   * Django admin exposes its bundled jQuery as django.jQuery.
   * Jazzmin also sets window.jQuery. Prefer django.jQuery.           */
  var jQ = (typeof django !== "undefined" && django.jQuery) || window.jQuery;

  /* ── Field IDs ──────────────────────────────────────────────────── */
  var ID = {
    modalidad: "id_modalidad_pago",
    termino: "id_termino_credito",
    fechaDep: "id_fecha_deposito",
    fechaVen: "id_fecha_vencimiento",
    tipoVenta: "id_tipo_venta",
    mercado: "id_mercado_destino",
    cliente: "id_cliente",
    estadoCob: "id_estado_cobranza",
  };
  function sel(id) {
    return "#" + id;
  }
  function el(id) {
    return document.getElementById(id);
  }

  /* ── Admin API base URL ─────────────────────────────────────────── */
  function apiBase() {
    var m = window.location.pathname.match(/^(.*\/ventas\/ventas\/)/);
    return m ? m[1] : "/admin/ventas/ventas/";
  }

  /* ── State ──────────────────────────────────────────────────────── */
  var terminoDias = 0;
  var tipoVentaLocked = false;
  var clienteTerminoDefault = null;

  /* ══════════════════════════════════════════════════════════════════
     SELECT 2 HELPERS
   ══════════════════════════════════════════════════════════════════ */

  /**
   * Set a <select> value and update the Select2 widget.
   * Falls back to plain .value if jQuery/Select2 not present.
   */
  function s2set(id, value) {
    var input = el(id);
    if (!input) {
      console.warn("s2set: element not found:", id);
      return;
    }

    // Debug: log available options
    var options = Array.from(input.options).map(function (opt) {
      return opt.value;
    });
    console.log("s2set:", id, "→", value, "| Available:", options);

    // Verify the value exists in options
    if (!options.includes(value)) {
      console.error(
        "s2set: value not found in options:",
        value,
        "| Try:",
        options,
      );
      return;
    }

    if (jQ) {
      jQ(input).val(value).trigger("change");
      // Force Select2 refresh
      setTimeout(function () {
        jQ(input).trigger("change.select2");
      }, 100);
    } else {
      input.value = value;
    }
  }

  /**
   * Lock the Select2 rendered container so the user cannot interact with it.
   * The underlying <select> stays enabled so its value submits with the form.
   */
  function s2lock(id, locked, title) {
    var input = el(id);
    if (!input) return;

    if (jQ) {
      var $container = jQ(input).next(".select2-container");
      if (locked) {
        $container.css({
          "pointer-events": "none",
          opacity: "0.72",
          background: "#f1f5f9",
          cursor: "not-allowed",
          "border-radius": "4px",
        });
        $container.attr("title", title || "Gestionado automáticamente");
      } else {
        $container.css({
          "pointer-events": "",
          opacity: "",
          background: "",
          cursor: "",
        });
        $container.removeAttr("title");
      }
    }

    /* Also update a data attribute so the change guard below can check */
    if (locked) {
      input.dataset.vfLocked = "1";
      input.dataset.vfLockedValue = input.value;
    } else {
      input.dataset.vfLocked = "";
      input.dataset.vfLockedValue = "";
    }
  }

  /* ══════════════════════════════════════════════════════════════════
     DATE INPUT HELPERS
   ══════════════════════════════════════════════════════════════════ */

  /**
   * Make the fecha_vencimiento input readonly (or editable).
   * readonly still submits the value, unlike disabled.
   */
  function setDateReadonly(id, locked) {
    var input = el(id);
    if (!input) return;
    if (locked) {
      input.setAttribute("readonly", "readonly");
      input.style.background = "#f1f5f9";
      input.style.cursor = "not-allowed";
      input.style.color = "#586f7c";
      /* Also hide the calendar icon/button if present */
      var wrapper = input.closest(".related-widget-wrapper, .input-group");
      if (wrapper) {
        wrapper
          .querySelectorAll("a, button, .datetimeshortcuts")
          .forEach(function (btn) {
            btn.style.pointerEvents = "none";
            btn.style.opacity = "0.4";
          });
      }
    } else {
      input.removeAttribute("readonly");
      input.style.background = "";
      input.style.cursor = "";
      input.style.color = "";
      var wrapper2 = input.closest(".related-widget-wrapper, .input-group");
      if (wrapper2) {
        wrapper2
          .querySelectorAll("a, button, .datetimeshortcuts")
          .forEach(function (btn) {
            btn.style.pointerEvents = "";
            btn.style.opacity = "";
          });
      }
    }
  }

  /* ══════════════════════════════════════════════════════════════════
     BADGE / CHIP HELPERS
   ══════════════════════════════════════════════════════════════════ */

  var BADGE_CSS =
    "display:inline-flex;align-items:center;gap:3px;" +
    "margin-left:8px;padding:2px 9px;border-radius:20px;" +
    "font-size:0.68rem;font-weight:700;line-height:1.6;" +
    "vertical-align:middle;white-space:nowrap;";

  function upsertBadge(badgeId, text, bg, fg) {
    fg = fg || "#fff";
    var b = document.getElementById(badgeId);
    if (!b) {
      b = document.createElement("span");
      b.id = badgeId;
      b.style.cssText = BADGE_CSS + "background:" + bg + ";color:" + fg + ";";
    } else {
      b.style.background = bg;
    }
    b.textContent = text;
    return b;
  }

  /** Insert badge immediately after an element if not already in DOM. */
  function placeBadge(afterId, badgeId, text, bg, fg) {
    var anchor = el(afterId);
    if (!anchor) return;
    var badge = upsertBadge(badgeId, text, bg, fg);
    if (!document.getElementById(badgeId)) {
      /* Find the Select2 container (it sits right after the hidden <select>) */
      var insertAfter =
        (jQ && jQ(anchor).next(".select2-container").get(0)) || anchor;
      insertAfter.parentNode.insertBefore(badge, insertAfter.nextSibling);
    }
  }

  function removeBadge(badgeId) {
    var b = document.getElementById(badgeId);
    if (b) b.remove();
  }

  /* ── Tab badge: add a small chip to a tab whose text matches ────── */
  function tabBadge(textFragment, badgeId, label, bg) {
    var tabs = document.querySelectorAll(
      "#jazzy-tabs .nav-link, .change-form .nav-tabs .nav-link",
    );
    for (var i = 0; i < tabs.length; i++) {
      var tab = tabs[i];
      if (
        tab.textContent
          .trim()
          .toLowerCase()
          .indexOf(textFragment.toLowerCase()) !== -1
      ) {
        var existing = document.getElementById(badgeId);
        if (!existing) {
          var b = document.createElement("span");
          b.id = badgeId;
          b.textContent = label;
          b.style.cssText =
            "margin-left:5px;padding:1px 6px;border-radius:8px;" +
            "font-size:0.6rem;font-weight:800;background:" +
            bg +
            ";color:#fff;" +
            "vertical-align:middle;line-height:1.5;";
          tab.appendChild(b);
        } else {
          existing.textContent = label;
          existing.style.background = bg;
        }
        return;
      }
    }
  }

  function removeTabBadge(badgeId) {
    var b = document.getElementById(badgeId);
    if (b) b.remove();
  }

  /* ── Flash highlight ───────────────────────────────────────────── */
  function flash(id, color) {
    var input = el(id);
    if (!input) return;
    color = color || "rgba(184,219,217,.1)";
    input.style.transition = "background-color 0.3s";
    input.style.backgroundColor = color;
    setTimeout(function () {
      input.style.backgroundColor = "";
    }, 2200);
  }

  /* ── Required marker on label ────────────────────────────────────── */
  function setRequired(id, show) {
    var label = document.querySelector('label[for="' + id + '"]');
    if (!label) return;
    var marker = label.querySelector(".vf-req");
    if (show && !marker) {
      var s = document.createElement("span");
      s.className = "vf-req";
      s.setAttribute("aria-hidden", "true");
      s.style.cssText = "color:#b85450;font-weight:700;margin-left:2px;";
      s.textContent = " *";
      label.appendChild(s);
    } else if (!show && marker) {
      marker.remove();
    }
  }

  /* ══════════════════════════════════════════════════════════════════
     DATE CALCULATION
   ══════════════════════════════════════════════════════════════════ */

  function parseFecha(value) {
    if (!value) return null;
    if (value.indexOf("-") !== -1) {
      var iso = value.split("-");
      if (iso.length === 3) return new Date(+iso[0], +iso[1] - 1, +iso[2]);
    }
    if (value.indexOf("/") !== -1) {
      var dmy = value.split("/");
      if (dmy.length === 3) return new Date(+dmy[2], +dmy[1] - 1, +dmy[0]);
    }
    return null;
  }

  function recalcVencimiento() {
    var modalEl = el(ID.modalidad);
    var depEl = el(ID.fechaDep);
    var venEl = el(ID.fechaVen);
    if (!modalEl || modalEl.value !== "Credito") return;
    if (!terminoDias || !depEl || !depEl.value) return;

    var d = parseFecha(depEl.value);
    if (!d) return;
    d.setDate(d.getDate() + terminoDias);

    var y = d.getFullYear();
    var mo = String(d.getMonth() + 1).padStart(2, "0");
    var dy = String(d.getDate()).padStart(2, "0");

    if (venEl) {
      venEl.value = y + "-" + mo + "-" + dy;
      flash(ID.fechaVen);
    }

    /* Inline info chip showing the auto-calculated date + term length */
    placeBadge(
      ID.fechaVen,
      "vf-badge-vencimiento",
      "🗓 " + dy + "/" + mo + "/" + y + " (" + terminoDias + " días)",
      "#b8dbd9",
    );
  }

  function diasDesdeSelect(selectEl) {
    if (!selectEl) return 0;
    var option = selectEl.options[selectEl.selectedIndex];
    if (!option) return 0;
    var dias = option.getAttribute("data-dias");
    return dias ? parseInt(dias, 10) || 0 : 0;
  }

  function fetchDiasAndRecalc(termId) {
    removeBadge("vf-badge-vencimiento");
    if (!termId) {
      terminoDias = 0;
      return;
    }
    /* Preferir data-dias del <option> seleccionado (evita el fetch). */
    var local = diasDesdeSelect(el(ID.termino));
    if (local) {
      terminoDias = local;
      recalcVencimiento();
      return;
    }
    fetch(apiBase() + "api/termino-credito-info/" + termId + "/")
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        terminoDias = d.dias_credito || 0;
        recalcVencimiento();
      })
      .catch(function () {
        terminoDias = 0;
      });
  }

  /* ══════════════════════════════════════════════════════════════════
     MODALIDAD SYNC
   ══════════════════════════════════════════════════════════════════ */

  function syncModalidad() {
    var modalEl = el(ID.modalidad);
    if (!modalEl) return;
    var isCredito = modalEl.value === "Credito";
    /* Dejar término/estado como selects nativos (Select2 no respeta cambios
       dinámicos de disabled). */
    stripSelect2On([ID.termino, ID.estadoCob]);
    var termEl = el(ID.termino);
    var venEl = el(ID.fechaVen);
    var estEl = el(ID.estadoCob);

    /* ─ termino_credito: habilitado solo a crédito ─ */
    setRequired(ID.termino, isCredito);
    if (termEl) {
      termEl.disabled = !isCredito;
      if (isCredito) termEl.setAttribute("required", "required");
      else termEl.removeAttribute("required");
    }
    if (jQ && termEl) jQ(termEl).prop("disabled", !isCredito);
    s2lock(ID.termino, !isCredito, "Solo para ventas a crédito");

    /* ─ fecha_vencimiento: calculada a crédito, bloqueada a contado ─ */
    if (venEl) venEl.disabled = !isCredito;
    setDateReadonly(ID.fechaVen, isCredito);

    /* ─ estado_cobranza: siempre derivado (no editable) ─ */
    if (estEl) estEl.disabled = true;

    if (isCredito) {
      /* Término por defecto del cliente si aún no se eligió uno. */
      if (termEl && !termEl.value && clienteTerminoDefault) {
        s2set(ID.termino, String(clienteTerminoDefault));
        flash(ID.termino, "rgba(184,219,217,.1)");
      }
      fetchDiasAndRecalc(termEl ? termEl.value : "");
      if (estEl && (estEl.value === "Pagado" || estEl.value === "")) {
        s2set(ID.estadoCob, "Pendiente");
      }
      tabBadge("Modalidad", "vf-tb-modal", "CRÉDITO", "#b8dbd9");
    } else {
      if (venEl) venEl.value = "";
      terminoDias = 0;
      removeBadge("vf-badge-vencimiento");
      removeTabBadge("vf-tb-modal");
      if (estEl) s2set(ID.estadoCob, "Pagado");
    }
  }

  /* ══════════════════════════════════════════════════════════════════
     MONEDA DE VENTA + TIPO DE CAMBIO (derivados del campo Monto)
   ══════════════════════════════════════════════════════════════════ */

  /**
   * Quita Select2 de un <select> para dejarlo nativo.
   * Necesario en campos que se bloquean/desbloquean dinámicamente: Select2 no
   * reacciona a cambios de `disabled`, pero un select nativo sí.
   */
  function stripSelect2On(ids) {
    if (!jQ || !jQ.fn || !jQ.fn.select2) return;
    ids.forEach(function (id) {
      var node = el(id);
      if (node && jQ(node).hasClass("select2-hidden-accessible")) {
        try {
          jQ(node).select2("destroy");
        } catch (e) {
          /* noop */
        }
      }
    });
  }

  function syncMoneda(focus) {
    /* django-money renderiza Monto como monto_0 (importe) + monto_1 (moneda). */
    var curEl = el("id_monto_1");
    var monEl = el("id_moneda_venta");
    var tcEl = el("id_tipo_cambio");
    if (!curEl) return;

    var moneda = (curEl.value || "MXN").toUpperCase();
    if (monEl) monEl.value = moneda;
    if (!tcEl) {
      if (monEl) flash("id_moneda_venta", "rgba(184,219,217,.12)");
      return;
    }

    if (moneda === "MXN") {
      tcEl.value = "1.0";
      tcEl.disabled = true;
      tcEl.style.background = "#f1f5f9";
    } else {
      tcEl.disabled = false;
      tcEl.style.background = "";
      if (!tcEl.value || parseFloat(tcEl.value) === 1) tcEl.value = "";
      if (focus) tcEl.focus();
    }
    if (jQ) jQ(tcEl).prop("disabled", tcEl.disabled);
    if (monEl) flash("id_moneda_venta", "rgba(184,219,217,.12)");
  }

  /* ══════════════════════════════════════════════════════════════════
     CLIENTE CHANGE  →  FOREIGN CLIENT DETECTION
   ══════════════════════════════════════════════════════════════════ */

  function onClienteChange(clienteId) {
    if (!clienteId) return;
    var apiUrl = apiBase() + "api/cliente-info/" + clienteId + "/";
    fetch(apiUrl)
      .then(function (r) {
        if (!r.ok) {
          throw new Error("HTTP " + r.status);
        }
        return r.json();
      })
      .then(function (data) {
        applyClienteData(data);
      })
      .catch(function (err) {
        console.error("Error fetching cliente info:", err);
      });
  }

  function applyClienteData(data) {
    if (!data) return;

    if (data.es_extranjero) {
      /* Cliente extranjero → Exportación SIEMPRE (aunque tenga mercado). */
      s2set(ID.tipoVenta, "Exportación");
      tipoVentaLocked = true;
      s2lock(
        ID.tipoVenta,
        true,
        "Bloqueado: cliente de " + (data.pais_nombre || "país extranjero"),
      );
      placeBadge(
        ID.tipoVenta,
        "vf-badge-tipoventa",
        "🌍 " + (data.pais_nombre || "Extranjero"),
        "#2f4550",
      );
      flash(ID.tipoVenta, "rgba(184,219,217,.15)");
      tabBadge("Mercado", "vf-tb-mercado", "AUTO", "#2f4550");
    } else {
      /* Cliente nacional → Nacional, editable. */
      s2set(ID.tipoVenta, "Nacional");
      tipoVentaLocked = false;
      s2lock(ID.tipoVenta, false);
      removeBadge("vf-badge-tipoventa");
      removeTabBadge("vf-tb-mercado");
    }

    /* mercado_destino: autocompletar el del cliente (aplica a ambos casos). */
    if (data.mercado_destino_id) {
      s2set(ID.mercado, String(data.mercado_destino_id));
      flash(ID.mercado, "rgba(184,219,217,.1)");
    }

    /* Guardar término por defecto del cliente (se aplica ahora si es a
       crédito, o al cambiar a crédito desde syncModalidad). */
    clienteTerminoDefault = data.termino_credito_id || null;
    if (clienteTerminoDefault) {
      var modalEl = el(ID.modalidad);
      var termEl = el(ID.termino);
      if (modalEl && modalEl.value === "Credito" && termEl && !termEl.value) {
        s2set(ID.termino, String(clienteTerminoDefault));
        flash(ID.termino, "rgba(184,219,217,.1)");
        fetchDiasAndRecalc(clienteTerminoDefault);
      }
    }
  }

  /* ══════════════════════════════════════════════════════════════════
     BOOTSTRAP
   ══════════════════════════════════════════════════════════════════ */

  document.addEventListener("DOMContentLoaded", function () {
    console.log("ventas_form_logic.js loaded");
    /* Guard: only run on the Ventas add/change page */
    if (!el(ID.modalidad)) {
      console.log("Not on ventas form, exiting");
      return;
    }

    /* ── Initial state ── */
    syncModalidad();
    syncMoneda(false);

    /* Termino/estado se bloquean y desbloquean; usar selects nativos.
       Jazzmin aplica Select2 al final, por eso esperamos (timeout + load). */
    function quitarSelect2Dinamicos() {
      stripSelect2On([ID.termino, ID.estadoCob]);
      syncModalidad();
    }
    setTimeout(quitarSelect2Dinamicos, 0);
    window.addEventListener("load", quitarSelect2Dinamicos);

    /* ── Guard: prevent user from changing locked selects ──
       Runs in capture phase to intercept before Select2 processes.      */
    document.addEventListener(
      "change",
      function (e) {
        var target = e.target;
        if (target && target.dataset && target.dataset.vfLocked === "1") {
          /* Restore the formerly-locked value via Select2 */
          if (jQ) {
            jQ(target).val(target.dataset.vfLockedValue).trigger("change");
          } else {
            target.value = target.dataset.vfLockedValue;
          }
          e.stopImmediatePropagation();
        }
      },
      true /* capture phase */,
    );

    /* ── modalidad_pago ── */
    var modalEl = el(ID.modalidad);
    if (modalEl) modalEl.addEventListener("change", syncModalidad);
    if (jQ && el(ID.modalidad)) {
      jQ(el(ID.modalidad)).on("select2:select", syncModalidad);
    }

    /* ── moneda del Monto → moneda_venta + tipo_cambio ── */
    var curEl = el("id_monto_1");
    if (curEl) {
      curEl.addEventListener("change", function () {
        syncMoneda(true);
      });
      if (jQ) {
        jQ(curEl).on("select2:select", function () {
          syncMoneda(true);
        });
      }
    }

    /* ── termino_credito ── */
    var termEl = el(ID.termino);
    if (termEl) {
      termEl.addEventListener("change", function () {
        fetchDiasAndRecalc(this.value);
      });
      if (jQ) {
        jQ(termEl).on("select2:select", function () {
          fetchDiasAndRecalc(jQ(termEl).val());
        });
      }
    }

    /* ── fecha_deposito: recalc on any change/input ── */
    var depEl = el(ID.fechaDep);
    if (depEl) {
      depEl.addEventListener("change", recalcVencimiento);
      depEl.addEventListener("input", recalcVencimiento);
    }

    /* ── cliente: native + Select2 event ── */
    var cliEl = el(ID.cliente);
    if (cliEl) {
      cliEl.addEventListener("change", function () {
        onClienteChange(this.value);
      });
      if (jQ) {
        jQ(cliEl).on("select2:select", function (e) {
          var id =
            e.params && e.params.data ? e.params.data.id : jQ(cliEl).val();
          onClienteChange(id);
        });
      }
    }

    /* ── On edit forms: re-apply client logic for pre-filled value ── */
    var initialCliente = cliEl && cliEl.value;
    if (initialCliente) {
      console.log("Initial cliente detected on page load:", initialCliente);
      // Wait for Select2 to fully initialize
      setTimeout(function () {
        onClienteChange(initialCliente);
      }, 300);
    }
  });
})();
