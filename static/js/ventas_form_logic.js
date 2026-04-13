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
      input.style.color = "#475569";
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
    color = color || "#d1fae5";
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
      s.style.cssText = "color:#dc2626;font-weight:700;margin-left:2px;";
      s.textContent = " *";
      label.appendChild(s);
    } else if (!show && marker) {
      marker.remove();
    }
  }

  /* ══════════════════════════════════════════════════════════════════
     DATE CALCULATION
   ══════════════════════════════════════════════════════════════════ */

  function recalcVencimiento() {
    var modalEl = el(ID.modalidad);
    var depEl = el(ID.fechaDep);
    var venEl = el(ID.fechaVen);
    if (!modalEl || modalEl.value !== "Credito") return;
    if (!terminoDias || !depEl || !depEl.value) return;

    var parts = depEl.value.split("-");
    if (parts.length !== 3) return;

    var d = new Date(+parts[0], +parts[1] - 1, +parts[2]);
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
      "#0d8fa2",
    );
  }

  function fetchDiasAndRecalc(termId) {
    removeBadge("vf-badge-vencimiento");
    if (!termId) {
      terminoDias = 0;
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

    /* ─ termino_credito: required marker & attribute ─ */
    setRequired(ID.termino, isCredito);
    var termEl = el(ID.termino);
    if (termEl) {
      if (isCredito) termEl.setAttribute("required", "required");
      else termEl.removeAttribute("required");
    }

    /* ─ fecha_vencimiento: locked/calculated when credit ─ */
    setDateReadonly(ID.fechaVen, isCredito);

    if (isCredito) {
      fetchDiasAndRecalc(termEl ? termEl.value : "");

      /* Auto estado_cobranza = Pendiente when switching to Crédito */
      var estEl = el(ID.estadoCob);
      if (estEl && (estEl.value === "Pagado" || estEl.value === "")) {
        s2set(ID.estadoCob, "Pendiente");
      }

      tabBadge("Modalidad", "vf-tb-modal", "CRÉDITO", "#0d8fa2");
    } else {
      /* Contado: clear due date, remove badges */
      var fvEl = el(ID.fechaVen);
      if (fvEl) fvEl.value = "";
      terminoDias = 0;
      removeBadge("vf-badge-vencimiento");
      removeTabBadge("vf-tb-modal");

      /* Auto estado_cobranza = Pagado when switching to Contado */
      var estEl2 = el(ID.estadoCob);
      if (estEl2) s2set(ID.estadoCob, "Pagado");
    }
  }

  /* ══════════════════════════════════════════════════════════════════
     CLIENTE CHANGE  →  FOREIGN CLIENT DETECTION
   ══════════════════════════════════════════════════════════════════ */

  function applyClienteData(data) {
    console.log("applyClienteData called with:", data);
    var tipoEl = el(ID.tipoVenta);
    var mercadoEl = el(ID.mercado);

    if (data.es_extranjero) {
      console.log("Cliente extranjero detectado:", data.pais_nombre);
      /* 1. Set tipo_venta = "Exportación" via Select2 */
      s2set(
        ID.tipoVenta,
        "Exportación",
      ); /* "Exportación" — exact option value */

      /* 2. Lock the Select2 container so user cannot change it */
      tipoVentaLocked = true;
      s2lock(
        ID.tipoVenta,
        true,
        "Bloqueado: cliente de " + (data.pais_nombre || "país extranjero"),
      );

      /* 3. Inline badge next to tipo_venta */
      placeBadge(
        ID.tipoVenta,
        "vf-badge-tipoventa",
        "🌍 " + (data.pais_nombre || "Extranjero"),
        "#1e3a5f",
      );
      flash(ID.tipoVenta, "#dbeafe");

      /* 4. Tab badge on "Mercado y Exportación" */
      tabBadge("Mercado", "vf-tb-mercado", "AUTO", "#1e3a5f");

      /* 5. Fill mercado_destino if available */
      if (data.mercado_destino_id) {
        s2set(ID.mercado, String(data.mercado_destino_id));
        flash(ID.mercado, "#d1fae5");
        console.log("Cliente nacional detectado:", data.pais_nombre);
        /* Domestic client: set Nacional and unlock tipo_venta */
        s2set(ID.tipoVenta, "Nacional");
      } else {
        /* Domestic client: unlock tipo_venta */
        tipoVentaLocked = false;
        s2lock(ID.tipoVenta, false);
        removeBadge("vf-badge-tipoventa");
        removeTabBadge("vf-tb-mercado");
      }

      /* 6. Pre-fill termino_credito from client's default (only if Crédito & empty) */
      if (data.termino_credito_id) {
        var modalEl = el(ID.modalidad);
        var termEl = el(ID.termino);
        if (modalEl && modalEl.value === "Credito" && termEl && !termEl.value) {
          s2set(ID.termino, String(data.termino_credito_id));
          flash(ID.termino, "#d1fae5");
          fetchDiasAndRecalc(data.termino_credito_id);
        }
      }
    }
    {
      console.log("onClienteChange: no cliente selected");
      return;
    }
    console.log("onClienteChange: fetching data for cliente", clienteId);
    var apiUrl = apiBase() + "api/cliente-info/" + clienteId + "/";
    console.log("API URL:", apiUrl);

    fetch(apiUrl)
      .then(function (r) {
        if (!r.ok) {
          throw new Error("HTTP " + r.status);
        }
        return r.json();
      })
      .then(function (data) {
        console.log("API response:", data);
        applyClienteData(data);
      })
      .catch(function (err) {
        console.error("Error fetching cliente info:", err);
      });
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
