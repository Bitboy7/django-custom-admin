(function () {
  "use strict";

  var root = document.getElementById("asistente-app");
  if (!root) return;

  var API_URL = root.dataset.apiUrl;
  var CONFIGURED = root.dataset.configurado === "true";
  var STORE_PREFIX = "ac:recent:v1";
  var STORE_KEY = STORE_PREFIX + ":" + (root.dataset.usuario || "anon");
  // En equipos compartidos (tablets de campo) no debe quedar a la vista la
  // cartera de otro usuario: se borra todo historial que no sea el propio.
  try {
    for (var k = localStorage.length - 1; k >= 0; k -= 1) {
      var storedKey = localStorage.key(k);
      if (storedKey && storedKey.indexOf(STORE_PREFIX) === 0 && storedKey !== STORE_KEY) {
        localStorage.removeItem(storedKey);
      }
    }
  } catch (error) {
    /* sin localStorage: no hay historial que purgar */
  }
  var MAX_RECENT = 8;
  var MAX_STORED_ROWS = 25;

  var el = {
    body: root.querySelector(".ac-body"),
    backdrop: root.querySelector("[data-close-drawers].ac-backdrop"),
    feed: root.querySelector("[data-feed]"),
    messages: root.querySelector("[data-messages]"),
    welcome: root.querySelector("[data-welcome]"),
    input: root.querySelector("[data-input]"),
    composer: root.querySelector("[data-composer]"),
    send: root.querySelector("[data-send]"),
    threadTitle: root.querySelector("[data-thread-title]"),
    threadMeta: root.querySelector("[data-thread-meta]"),
    suggestionsList: root.querySelector("[data-suggestions-list]"),
    filter: root.querySelector("[data-filter]"),
    filterEmpty: root.querySelector("[data-filter-empty]"),
    recentWrap: root.querySelector("[data-recent-wrap]"),
    recentList: root.querySelector("[data-recent-list]"),
    dataPanel: root.querySelector("[data-data-panel]"),
    dataEmpty: root.querySelector("[data-data-empty]"),
    dataContent: root.querySelector("[data-data-content]"),
    dataSub: root.querySelector("[data-data-sub]"),
    selectedHead: root.querySelector("[data-selected-head]"),
    tableSlot: root.querySelector("[data-table-slot]"),
    traceList: root.querySelector("[data-trace-list]"),
    argsSlot: root.querySelector("[data-args-slot]"),
    copyTable: root.querySelector("[data-copy-table]"),
    toast: root.parentElement.querySelector("[data-toast]") || document.querySelector("[data-toast]"),
    toastText: root.parentElement.querySelector("[data-toast-text]") || document.querySelector("[data-toast-text]"),
    status: root.querySelector("[data-status]"),
    header: root.querySelector(".ac-header"),
    thread: root.querySelector(".ac-col--thread"),
    leftPane: root.querySelector(".ac-col--left"),
    rightPane: root.querySelector(".ac-col--right"),
  };

  var state = {
    messages: [],
    conversationId: null,
    loading: false,
    active: { msgIndex: null, traces: [], selected: null },
    showAllRows: false,
    copyTableTsv: "",
  };

  var TOOL_LABELS = {
    listar_tablas: "Tablas disponibles",
    describir_tabla: "Esquema de tabla",
    resumen_financiero: "Resumen financiero",
    resumen_ventas: "Resumen de ventas",
    ventas_por_cliente: "Ventas por cliente",
    ventas_por_producto: "Ventas por producto",
    cartera_por_cliente: "Cartera por cliente",
    cartera_vencida: "Cartera vencida",
    pagos_recientes: "Pagos recientes",
    resumen_gastos: "Resumen de gastos",
    gastos_por_categoria: "Gastos por categoría",
    compras_por_producto: "Compras por producto",
    compras_por_productor: "Compras por productor",
    saldo_mensual: "Saldos por banco",
    consultar_sql: "Consulta SQL",
  };

  function csrfToken() {
    var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    if (match) return decodeURIComponent(match[1]);
    var input = root.querySelector("[name=csrfmiddlewaretoken]");
    return input ? input.value : "";
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatAnswer(text) {
    var safe = escapeHtml(text || "").trim();
    if (!safe) return "";
    var blocks = safe.split(/\n{2,}/);
    var html = blocks
      .map(function (block) {
        var lines = block.split("\n");
        var out = "";
        var inList = false;
        lines.forEach(function (line) {
          var bullet = line.match(/^\s*[-•]\s+(.*)$/);
          if (bullet) {
            if (!inList) {
              out += "<ul>";
              inList = true;
            }
            out += "<li>" + bullet[1] + "</li>";
          } else {
            if (inList) {
              out += "</ul>";
              inList = false;
            }
            if (line.trim() === "") return;
            out += (out && !/<\/ul>$/.test(out) ? "<br>" : "") + line;
          }
        });
        if (inList) out += "</ul>";
        return "<p>" + out + "</p>";
      })
      .join("")
      .replace(/<\/p><p>/g, "</p><p>");
    return html
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/<p><\/p>/g, "");
  }

  function toolLabel(name) {
    return TOOL_LABELS[name] || name || "Reporte";
  }

  function icon(id, className) {
    return (
      '<svg class="' +
      (className || "h-4 w-4") +
      '" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><use href="#' +
      id +
      '"/></svg>'
    );
  }

  function scrollFeed() {
    window.requestAnimationFrame(function () {
      if (el.feed) el.feed.scrollTop = el.feed.scrollHeight;
    });
  }

  function autoGrow() {
    if (!el.input) return;
    el.input.style.height = "auto";
    el.input.style.height = Math.min(el.input.scrollHeight, 132) + "px";
  }

  function setSending(sending) {
    state.loading = sending;
    if (el.send) {
      el.send.disabled = sending || !CONFIGURED;
      el.send.setAttribute("aria-busy", sending ? "true" : "false");
    }
    if (el.input) {
      el.input.readOnly = sending;
    }
  }

  // Única región viva: el feed ya no es aria-live, así que el lector de pantalla
  // oye solo lo que pasa ("Consultando…", "Respuesta lista…") y no relee el hilo.
  function announce(message) {
    if (!el.status) return;
    el.status.textContent = "";
    window.setTimeout(function () {
      el.status.textContent = message;
    }, 60);
  }

  function showTyping() {
    var node = document.createElement("div");
    node.className = "ac-bot ac-msg";
    node.setAttribute("data-typing", "");
    node.setAttribute("aria-hidden", "true");
    node.innerHTML =
      '<span class="ac-bot-avatar">' +
      icon("i-sun-wave", "h-4 w-4") +
      "</span>" +
      '<div class="ac-bot-body">' +
      '<div class="flex items-center gap-3">' +
      '<span class="ac-typing"><span></span><span></span><span></span></span>' +
      '<span class="text-[11.5px] text-[var(--as-muted)]">Consultando los registros…</span>' +
      "</div></div>";
    el.messages.appendChild(node);
    announce("Consultando los registros…");
    scrollFeed();
  }

  function removeTyping() {
    var node = el.messages.querySelector("[data-typing]");
    if (node) node.remove();
  }

  function messageTitle() {
    var firstUser = state.messages.filter(function (m) {
      return m.role === "user";
    })[0];
    if (!firstUser) return "Nueva conversación";
    return firstUser.content.length > 74
      ? firstUser.content.slice(0, 74).trim() + "…"
      : firstUser.content;
  }

  function updateThreadMeta() {
    var lastAssistant = null;
    for (var i = state.messages.length - 1; i >= 0; i -= 1) {
      if (state.messages[i].role === "assistant") {
        lastAssistant = state.messages[i];
        break;
      }
    }
    var meta = lastAssistant && lastAssistant.meta;
    if (!meta || !lastAssistant.traces || !lastAssistant.traces.length) {
      if (el.threadMeta) {
        el.threadMeta.textContent = "Elijo el reporte adecuado para tu pregunta.";
      }
      return;
    }
    var seconds = Math.max(0.1, (meta.duracion_ms || 0) / 1000);
    var cutoff = (lastAssistant.traces[0] && lastAssistant.traces[0].consultado_en) || meta.consultado_en;
    if (el.threadMeta) {
      el.threadMeta.textContent =
        (cutoff ? "Datos al " + shortDate(cutoff) + " · " : "") + "respondido en " + seconds.toFixed(1) + " s";
      // El modelo sigue disponible para quien administra, sin ocupar la vista.
      el.threadMeta.title = meta.modelo ? "Modelo: " + meta.modelo : "";
    }
  }

  function isSelectedTrace(msgIndex, traceIndex) {
    return Boolean(
      state.active && state.active.msgIndex === msgIndex && state.active.selected === traceIndex
    );
  }

  // Marca en el hilo cuál ficha corresponde a la tabla visible en Datos citados.
  function syncTraceChips() {
    if (!el.messages) return;
    el.messages.querySelectorAll("[data-trace-msg]").forEach(function (chip) {
      var selected = isSelectedTrace(Number(chip.dataset.traceMsg), Number(chip.dataset.traceIdx));
      chip.setAttribute("aria-pressed", String(selected));
    });
  }

  function renderTraceChip(trace, msgIndex, traceIndex) {
    var failed = Boolean(trace.error);
    return (
      '<button type="button" class="ac-trace-chip inline-flex items-center gap-1.5 rounded-full border px-2 py-[3px] text-[10px] font-[650] transition-colors ' +
      (failed
        ? "border-[color-mix(in_srgb,var(--as-danger)_45%,var(--as-border))] text-[var(--as-danger)] hover:bg-[color-mix(in_srgb,var(--as-danger)_8%,transparent)]"
        : "border-[var(--as-border)] text-[var(--as-text-2)] hover:border-[var(--as-mist)] hover:bg-[var(--as-mist-soft)]") +
      '" data-trace-msg="' +
      msgIndex +
      '" data-trace-idx="' +
      traceIndex +
      '" aria-pressed="' +
      String(isSelectedTrace(msgIndex, traceIndex)) +
      '" aria-label="Ver datos: ' +
      escapeHtml(toolLabel(trace.herramienta)) +
      (failed ? " (falló)" : "") +
      '">' +
      icon(failed ? "i-alert" : "i-table", "h-[11px] w-[11px]") +
      escapeHtml(toolLabel(trace.herramienta)) +
      "</button>"
    );
  }

  function renderMessage(message, index) {
    if (message.role === "user") {
      return (
        '<div class="ac-msg flex justify-end"><div class="ac-user-bubble">' +
        escapeHtml(message.content) +
        "</div></div>"
      );
    }

    var traces = message.traces || [];
    var partial = traces.some(function (t) {
      return t.tabla && t.tabla.truncado;
    });

    var body;
    if (message.error) {
      body = renderError(message, index);
    } else {
      body =
        (partial
          ? '<p class="ac-partial-lead">' +
            icon("i-alert", "h-3.5 w-3.5 shrink-0") +
            "<span><strong>Con datos parciales:</strong> el resultado llegó recortado. " +
            "Verifica en la tabla antes de usar estas cifras.</span></p>"
          : "") +
        '<div class="ac-prose">' +
        formatAnswer(message.content) +
        "</div>";
    }

    var foot = "";
    if (traces.length) {
      var chips = traces
        .map(function (trace, traceIndex) {
          return renderTraceChip(trace, index, traceIndex);
        })
        .join("");
      foot =
        '<div class="ac-answer-foot" role="group" aria-label="Fuentes de esta respuesta">' +
        '<span class="ac-foot-label">Fuentes</span>' +
        chips +
        "</div>";
    }

    return (
      '<div class="ac-bot ac-msg">' +
      '<span class="ac-bot-avatar">' +
      icon("i-sun-wave", "h-4 w-4") +
      "</span>" +
      '<div class="ac-bot-body">' +
      body +
      foot +
      "</div></div>"
    );
  }

  var LINK_CLASS =
    "text-[11px] font-[700] text-[var(--as-accent)] underline underline-offset-2 decoration-[color-mix(in_srgb,var(--as-accent)_40%,transparent)] hover:decoration-[var(--as-accent)]";

  function formatCountdown(seconds) {
    var s = Math.max(0, Math.ceil(seconds));
    var m = Math.floor(s / 60);
    return m + ":" + String(s % 60).padStart(2, "0");
  }

  // Cada error ofrece solo lo que puede resolverlo: reintentar (si sirve), una
  // cuenta regresiva (429), un enlace que corrige la causa (sesión, 2FA) y el
  // detalle técnico plegado para quien administra el servidor.
  function renderError(message, index) {
    var info = message.errorInfo || { reintentable: true };
    var actions = [];
    if (info.accion && info.accion.url) {
      var external = info.accion.nueva_pestana ? ' target="_blank" rel="noopener"' : "";
      actions.push(
        '<a class="' + LINK_CLASS + '" href="' + escapeHtml(info.accion.url) + '"' + external + ">" +
          escapeHtml(info.accion.etiqueta || "Resolver") +
          (info.accion.nueva_pestana ? '<span class="sr-only"> (se abre en otra pestaña)</span>' : "") +
          "</a>"
      );
    }
    if (info.reintentable) {
      var waiting = info.retryAt && info.retryAt > Date.now();
      actions.push(
        '<button type="button" class="ac-retry ' + LINK_CLASS + '" data-retry="' +
          index +
          '"' +
          (waiting ? ' disabled data-retry-at="' + info.retryAt + '"' : "") +
          ">" +
          (waiting
            ? "Reintentar en " + formatCountdown((info.retryAt - Date.now()) / 1000)
            : "Reintentar") +
          "</button>"
      );
    }
    var detail = info.detalle
      ? '<details class="mt-2"><summary class="cursor-pointer text-[11px] font-[650] text-[var(--as-muted)]">Detalle técnico</summary>' +
        '<p class="mt-1 text-[11.5px] leading-relaxed text-[var(--as-muted)]">' +
        escapeHtml(info.detalle) +
        "</p></details>"
      : "";
    return (
      '<div class="flex items-start gap-2.5" role="group" aria-label="No se pudo responder">' +
      icon("i-alert", "h-4 w-4 mt-0.5 shrink-0 text-[var(--as-danger)]") +
      '<div class="min-w-0"><p class="text-[13px] leading-relaxed text-[var(--as-text-2)]">' +
      escapeHtml(message.error) +
      "</p>" +
      (actions.length ? '<div class="mt-2 flex flex-wrap items-center gap-3">' + actions.join("") + "</div>" : "") +
      detail +
      "</div></div>"
    );
  }

  // Un solo temporizador actualiza los botones "Reintentar en m:ss" del 429.
  var countdownTimer = null;
  function syncCountdowns() {
    var pending = el.messages ? el.messages.querySelectorAll("[data-retry-at]") : [];
    if (!pending.length) {
      if (countdownTimer) window.clearInterval(countdownTimer);
      countdownTimer = null;
      return;
    }
    if (countdownTimer) return;
    countdownTimer = window.setInterval(function () {
      var buttons = el.messages.querySelectorAll("[data-retry-at]");
      buttons.forEach(function (button) {
        var left = (Number(button.dataset.retryAt) - Date.now()) / 1000;
        if (left <= 0) {
          button.disabled = false;
          button.removeAttribute("data-retry-at");
          button.textContent = "Reintentar";
          announce("Ya puedes volver a intentar la consulta.");
        } else {
          button.textContent = "Reintentar en " + formatCountdown(left);
        }
      });
      if (!buttons.length) {
        window.clearInterval(countdownTimer);
        countdownTimer = null;
      }
    }, 1000);
  }

  function afterMessagesChange() {
    if (el.welcome) el.welcome.hidden = state.messages.length > 0;
    if (el.threadTitle) el.threadTitle.textContent = messageTitle();
    updateThreadMeta();
    syncCountdowns();
    scrollFeed();
  }

  // Render completo: solo al abrir/crear conversación o al quitar un error.
  function renderMessages() {
    if (!el.messages) return;
    el.messages.innerHTML = state.messages
      .map(function (message, index) {
        return renderMessage(message, index);
      })
      .join("");
    afterMessagesChange();
  }

  // Render incremental: agrega el último mensaje sin reconstruir el hilo
  // (no se pierde el foco ni la posición de lectura).
  function appendLastMessage() {
    if (!el.messages) return;
    var index = state.messages.length - 1;
    var typing = el.messages.querySelector("[data-typing]");
    var html = renderMessage(state.messages[index], index);
    if (typing) typing.insertAdjacentHTML("beforebegin", html);
    else el.messages.insertAdjacentHTML("beforeend", html);
    afterMessagesChange();
  }

  function findPreviousUser(index) {
    for (var i = index; i >= 0; i -= 1) {
      if (state.messages[i] && state.messages[i].role === "user") {
        return state.messages[i].content;
      }
    }
    return "";
  }

  function isNumericColumn(column, rows) {
    var name = String(column || "").toLowerCase();
    if (
      /fecha|periodo|mes|anio|año|moneda|cliente|producto|variedad|nombre|metodo|referencia|carga|pedimento|^po$|banco|categoria|uuid|folio/.test(
        name
      )
    ) {
      return false;
    }
    if (
      /monto|saldo|total|pago|precio|ingreso|gasto|compra|balance|cartera|vencido|cantidad|num_|dias|días|inicial|final|limite|límite/.test(
        name
      )
    ) {
      return true;
    }
    var sample = rows.slice(0, 6);
    return (
      sample.length > 0 &&
      sample.every(function (row) {
        var value = row[column];
        if (value === null || value === undefined || value === "") return true;
        return typeof value === "number" || /^-?\d+(\.\d+)?$/.test(String(value).trim());
      })
    );
  }

  function isMoneyColumn(column) {
    return /monto|saldo|total|pago|precio|ingreso|gasto|compra|balance|cartera|vencido|inicial|final/i.test(
      String(column || "")
    );
  }

  function numberFormat(value) {
    var number = typeof value === "number" ? value : parseFloat(String(value).replace(/,/g, ""));
    if (!isFinite(number)) return escapeHtml(value);
    return new Intl.NumberFormat("es-MX", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(number);
  }

  // ---- Tabla citada: lenguaje contable ----
  var COLUMN_LABELS = {
    anio: "Año",
    mes: "Mes",
    periodo: "Periodo",
    moneda: "Moneda",
    monto: "Monto",
    monto_total: "Monto total",
    monto_pagado: "Pagado",
    pagado: "Pagado",
    saldo: "Saldo",
    saldo_pendiente: "Saldo pendiente",
    saldo_vencido: "Saldo vencido",
    saldo_inicial: "Saldo inicial",
    saldo_final: "Saldo final",
    num_ventas: "Núm. de ventas",
    num_pagos: "Núm. de pagos",
    num_gastos: "Núm. de gastos",
    num_compras: "Núm. de compras",
    dias_1_30: "Vencido 1–30 días",
    dias_31_60: "Vencido 31–60 días",
    dias_61_90: "Vencido 61–90 días",
    dias_mas_90: "Vencido +90 días",
    mas_90: "Vencido +90 días",
    metodo_pago: "Método de pago",
    categoria: "Categoría",
    fecha_vencimiento: "Vencimiento",
  };
  var WORD_FIXES = {
    anio: "año",
    dias: "días",
    num: "núm.",
    categoria: "categoría",
    metodo: "método",
    credito: "crédito",
    razon: "razón",
    numero: "número",
  };

  function columnLabel(column) {
    var key = String(column || "").toLowerCase();
    if (COLUMN_LABELS[key]) return COLUMN_LABELS[key];
    var text = key
      .split("_")
      .filter(Boolean)
      .map(function (word) {
        return WORD_FIXES[word] || word;
      })
      .join(" ");
    return text ? text.charAt(0).toUpperCase() + text.slice(1) : String(column || "");
  }

  function currencyColumn(columns) {
    for (var i = 0; i < columns.length; i += 1) {
      if (/^(moneda|currency|divisa)$/i.test(columns[i])) return columns[i];
    }
    return null;
  }

  function isOverdueColumn(column) {
    return /vencid|^dias_\d|mas_90|^mas_/i.test(String(column || ""));
  }

  function toNumber(value) {
    var number = typeof value === "number" ? value : parseFloat(String(value).replace(/,/g, ""));
    return isFinite(number) ? number : null;
  }

  // Sin columna de moneda no se antepone "$": mejor un número neutro que
  // insinuar MXN en un importe que podría ser USD.
  function formatCell(value, column, numeric, currency) {
    if (value === null || value === undefined || value === "") return '<span class="text-[var(--as-muted)]">—</span>';
    if (typeof value === "object") return escapeHtml(JSON.stringify(value));
    if (numeric) {
      var formatted = numberFormat(value);
      var suffix =
        currency && isMoneyColumn(column)
          ? ' <span class="ac-cur">' + escapeHtml(currency) + "</span>"
          : "";
      return '<span title="' + escapeHtml(value) + '">' + formatted + suffix + "</span>";
    }
    var text = escapeHtml(value);
    return '<span class="inline-block max-w-[190px] truncate align-bottom" title="' + text + '">' + text + "</span>";
  }

  // Totales por moneda de las columnas de importe y cantidad, sobre todas las
  // filas recibidas (no solo las visibles). Nunca suma monedas distintas.
  var NEVER_SUM = /precio|promedio|porcentaje|tasa|tipo_cambio|_pct$|^dias$|inicial|final|^limite|^anio$|^mes$|^id$|_id$/i;
  var FLOW_SUM = /^(monto|importe|total|pagado|ingreso|gasto|compra|cantidad|kilos|cajas)|^monto_|_total$|^num_|^dias_\d|^mas_90|_mas_90$/i;
  var BALANCE = /^saldo|vencido/i;
  var TIME_COLUMN = /^(periodo|mes|anio|año|fecha|semana|dia)$|^fecha_/i;

  // Un saldo (cartera, vencido) se puede sumar entre clientes o bancos de una
  // misma fecha, pero no a lo largo del tiempo: si la tabla tiene una columna
  // de periodo, los saldos no llevan total.
  function isSummableColumn(column, columns) {
    if (NEVER_SUM.test(column)) return false;
    if (FLOW_SUM.test(column)) return true;
    if (BALANCE.test(column)) {
      return !columns.some(function (other) {
        return TIME_COLUMN.test(other);
      });
    }
    return false;
  }

  function tableTotals(columns, rows, numeric, currencyCol) {
    var summable = columns.filter(function (column) {
      return numeric[column] && isSummableColumn(column, columns);
    });
    if (!summable.length || rows.length < 2) return [];
    var groups = {};
    var order = [];
    rows.forEach(function (row) {
      var key = currencyCol ? String(row[currencyCol] || "—") : "";
      if (!groups[key]) {
        groups[key] = {};
        order.push(key);
      }
      summable.forEach(function (column) {
        var number = toNumber(row[column]);
        if (number !== null) groups[key][column] = (groups[key][column] || 0) + number;
      });
    });
    return order.map(function (key) {
      return { currency: key, sums: groups[key] };
    });
  }

  function computeTotals(table) {
    var rows = table.filas || [];
    var columns = table.columnas || [];
    var numeric = {};
    columns.forEach(function (column) {
      numeric[column] = isNumericColumn(column, rows);
    });
    return tableTotals(columns, rows, numeric, currencyColumn(columns));
  }

  function renderTable(table, caption) {
    if (!table || !table.columnas || !table.columnas.length) {
      return '<p class="text-[11.5px] text-[var(--as-muted)]">Este reporte no devolvió una tabla.</p>';
    }
    var rows = table.filas || [];
    var columns = table.columnas;
    var visible = state.showAllRows ? rows : rows.slice(0, 8);
    var currencyCol = currencyColumn(columns);
    var numeric = {};
    columns.forEach(function (column) {
      numeric[column] = isNumericColumn(column, rows);
    });

    var head = columns
      .map(function (column) {
        return (
          '<th scope="col" class="' +
          (numeric[column] ? "is-num" : "") +
          '" title="' +
          escapeHtml(column) +
          '">' +
          escapeHtml(columnLabel(column)) +
          "</th>"
        );
      })
      .join("");

    var body = visible
      .map(function (row) {
        var currency = currencyCol ? row[currencyCol] : null;
        return (
          "<tr>" +
          columns
            .map(function (column) {
              var className = numeric[column] ? "is-num" : "";
              if (/fecha|periodo/i.test(column)) className += " is-date";
              if (isOverdueColumn(column) && (toNumber(row[column]) || 0) > 0) className += " is-overdue";
              return (
                '<td class="' +
                className.trim() +
                '">' +
                formatCell(row[column], column, numeric[column], currency) +
                "</td>"
              );
            })
            .join("") +
          "</tr>"
        );
      })
      .join("");

    if (!body) {
      body =
        '<tr><td colspan="' +
        columns.length +
        '" class="text-center text-[var(--as-muted)] py-5">Sin filas en el resultado.</td></tr>';
    }

    var totals = table.totales || tableTotals(columns, rows, numeric, currencyCol);
    var receivedRows = table.filas_originales || rows.length;
    var foot = totals
      .map(function (group) {
        var labelDone = false;
        return (
          "<tr>" +
          columns
            .map(function (column) {
              if (group.sums[column] !== undefined) {
                return (
                  '<td class="is-num">' +
                  formatCell(group.sums[column], column, true, group.currency || null) +
                  "</td>"
                );
              }
              if (!labelDone && !numeric[column]) {
                labelDone = true;
                return (
                  '<th scope="row">' +
                  (table.truncado ? "Suma parcial" : "Total") +
                  (group.currency ? " " + escapeHtml(group.currency) : "") +
                  "</th>"
                );
              }
              return "<td></td>";
            })
            .join("") +
          "</tr>"
        );
      })
      .join("");

    var more = "";
    if (rows.length > 8) {
      more =
        '<button type="button" class="mt-2 text-[10.5px] font-[700] text-[var(--as-accent)] underline underline-offset-2 decoration-[color-mix(in_srgb,var(--as-accent)_40%,transparent)] hover:decoration-[var(--as-accent)]" data-show-all>' +
        (state.showAllRows ? "Mostrar solo 8 filas" : "Ver las " + rows.length + " filas") +
        "</button>";
    }

    var totalsHelp = "";
    if (totals.length) {
      var summed = columns.filter(function (column) {
        return totals.some(function (group) {
          return group.sums[column] !== undefined;
        });
      });
      totalsHelp =
        '<details class="ac-totals-help"><summary>¿Cómo se calcula este total?</summary><p>' +
        "Suma " +
        escapeHtml(summed.map(columnLabel).join(", ")) +
        " de las " +
        receivedRows +
        " filas recibidas" +
        (currencyCol ? ", por separado para cada moneda" : "") +
        ". No se suman precios unitarios, porcentajes ni saldos de periodos distintos." +
        (table.truncado ? " Como el resultado viene recortado, es una suma parcial, no el total real." : "") +
        " Para conciliar, compara contra el reporte del módulo correspondiente.</p></details>";
    }

    var notes = [];
    if (table.filas_originales && table.filas_originales > rows.length) {
      notes.push(
        "Conversación guardada: se conservan " +
          rows.length +
          " de " +
          table.filas_originales +
          " filas; los totales son los de la consulta original."
      );
    } else if (totals.length && receivedRows > visible.length) {
      notes.push("Los totales suman las " + receivedRows + " filas, no solo las visibles.");
    }
    // El servidor corta en su límite y no informa cuántas filas existen en
    // total, así que se dice "llegaron N (el límite)" en vez de inventar "N de M".
    var warning = table.truncado
      ? '<p class="ac-table-warn" role="note">' +
        icon("i-alert", "h-3.5 w-3.5 shrink-0") +
        "<span><strong>Resultado parcial.</strong> Llegaron " +
        receivedRows +
        " filas, el límite por consulta; hay más en el ERP. Las sumas de abajo no son totales. " +
        '<button type="button" class="ac-narrow" data-narrow>Preguntar por un periodo más corto</button>' +
        "</span></p>"
      : "";

    return (
      warning +
      '<div class="ac-table-wrap" tabindex="0" role="region" aria-label="' +
      escapeHtml(caption || "Datos citados") +
      '"><table class="ac-table">' +
      '<caption class="sr-only">' +
      escapeHtml(caption || "Datos citados") +
      ", " +
      rows.length +
      (rows.length === 1 ? " fila" : " filas") +
      (table.truncado ? ", resultado parcial" : "") +
      "</caption><thead><tr>" +
      head +
      "</tr></thead><tbody>" +
      body +
      "</tbody>" +
      (foot
        ? '<tfoot class="ac-table-total' + (table.truncado ? " is-partial" : "") + '">' + foot + "</tfoot>"
        : "") +
      "</table></div>" +
      more +
      (notes.length ? '<p class="ac-table-note">' + notes.join(" ") + "</p>" : "") +
      totalsHelp
    );
  }

  function activeTrace() {
    if (!state.active || !state.active.traces) return null;
    var index = state.active.selected;
    if (index === null || index === undefined) return null;
    return state.active.traces[index] || null;
  }

  function renderTraceList() {
    var traces = state.active.traces || [];
    if (!traces.length) {
      el.traceList.innerHTML = "";
      return;
    }
    el.traceList.innerHTML = traces
      .map(function (trace, index) {
        var failed = Boolean(trace.error);
        var selected = index === state.active.selected ? ' aria-pressed="true"' : ' aria-pressed="false"';
        var meta = failed
          ? "falló"
          : (trace.filas || 0) + (trace.tabla && trace.tabla.truncado ? "+" : "") + " filas";
        return (
          '<button type="button" class="ac-tool' +
          (failed ? " ac-tool--error" : "") +
          '" data-select-trace="' +
          index +
          '"' +
          selected +
          ">" +
          icon(failed ? "i-alert" : "i-table", "h-4 w-4 text-[var(--as-muted)]") +
          '<span class="ac-tool__label min-w-0">' +
          escapeHtml(toolLabel(trace.herramienta)) +
          '</span><span class="ac-tool__meta">' +
          escapeHtml(meta) +
          "</span></button>"
        );
      })
      .join("");
  }

  function renderDataPanel() {
    var traces = (state.active && state.active.traces) || [];
    if (!traces.length) {
      syncTraceChips();
      if (typeof autoWidth !== "undefined" && autoWidth.right !== null) {
        autoWidth.right = null;
        applyWidth("right");
      }
      if (el.dataEmpty) el.dataEmpty.classList.remove("hidden");
      if (el.dataContent) el.dataContent.classList.add("hidden");
      if (el.copyTable) el.copyTable.disabled = true;
      if (el.dataSub) el.dataSub.textContent = "Tabla y traza de la última consulta.";
      return;
    }

    if (el.dataEmpty) el.dataEmpty.classList.add("hidden");
    if (el.dataContent) el.dataContent.classList.remove("hidden");
    if (el.dataSub) {
      var okTraces = traces.filter(function (t) {
        return !t.error;
      }).length;
      var failedTraces = traces.length - okTraces;
      el.dataSub.textContent =
        okTraces +
        (okTraces === 1 ? " reporte consultado" : " reportes consultados") +
        (failedTraces ? " · " + failedTraces + (failedTraces === 1 ? " falló." : " fallaron.") : ".");
    }

    var successful = traces.filter(function (trace) {
      return !trace.error;
    });
    var trace = activeTrace();
    if (!trace || trace.error) {
      if (trace && trace.error) {
        if (el.selectedHead) {
          el.selectedHead.innerHTML =
            '<div class="rounded-xl border border-[color-mix(in_srgb,var(--as-danger)_45%,var(--as-border))] bg-[color-mix(in_srgb,var(--as-danger)_8%,var(--as-panel))] px-3 py-2.5">' +
            '<p class="flex items-center gap-2 text-[11px] font-[750] uppercase tracking-[.04em] text-[var(--as-danger)]">' +
            icon("i-alert", "h-3.5 w-3.5") +
            "No se pudo obtener " +
            escapeHtml(toolLabel(trace.herramienta).toLowerCase()) +
            "</p>" +
            '<p class="mt-1.5 text-[11.5px] leading-relaxed text-[var(--as-text-2)]">' +
            escapeHtml(trace.error) +
            "</p></div>";
        }
        if (el.tableSlot) el.tableSlot.innerHTML = "";
        if (el.argsSlot) el.argsSlot.innerHTML = renderArgs(trace);
        state.copyTableTsv = "";
      } else {
        if (el.selectedHead) {
          el.selectedHead.innerHTML =
            '<p class="text-[11.5px] leading-relaxed text-[var(--as-muted)]">Esta conversación no dejó una tabla citada.</p>';
        }
        if (el.tableSlot) el.tableSlot.innerHTML = "";
        if (el.argsSlot) el.argsSlot.innerHTML = "";
      }
      if (el.copyTable) el.copyTable.disabled = true;
      renderTraceList();
      syncTraceChips();
      return;
    }

    // Encabezado en lenguaje contable: qué reporte y de qué periodo. El nombre
    // técnico de la tool y los ms quedan en "Cómo se obtuvo".
    if (el.selectedHead) {
      var period = periodText(trace.argumentos, trace.herramienta, trace.consultado_en);
      el.selectedHead.innerHTML =
        '<div class="flex items-start justify-between gap-2">' +
        '<h3 class="ac-data-title">' +
        escapeHtml(toolLabel(trace.herramienta)) +
        "</h3>" +
        '<span class="ac-chip shrink-0">' +
        (trace.filas || 0) +
        (trace.tabla && trace.tabla.truncado ? "+" : "") +
        ((trace.filas || 0) === 1 ? " fila" : " filas") +
        "</span></div>" +
        '<p class="ac-source">Fuente: registros del ERP' +
        (period ? " · " + escapeHtml(period) : "") +
        "</p>";
    }

    state.showAllRows = false;
    if (el.tableSlot) el.tableSlot.innerHTML = renderTable(trace.tabla, tableCaption(trace));
    if (el.argsSlot) el.argsSlot.innerHTML = renderArgs(trace);
    if (el.copyTable) el.copyTable.disabled = !trace.tabla;

    var table = trace.tabla;
    if (table && table.columnas) {
      var exportPeriod = periodText(trace.argumentos, trace.herramienta, trace.consultado_en);
      var preamble = [
        toolLabel(trace.herramienta),
        "Fuente: registros del ERP" + (exportPeriod ? " · " + exportPeriod : ""),
      ];
      if (trace.consultado_en) preamble.push("Consultado el " + shortDate(trace.consultado_en));
      if (table.truncado) {
        preamble.push("PARCIAL: resultado recortado al límite de filas; las sumas no son totales.");
      }
      var exportTotals = table.totales || computeTotals(table);
      var totalLines = exportTotals.map(function (group) {
        var label = (table.truncado ? "Suma parcial" : "Total") + (group.currency ? " " + group.currency : "");
        var labelUsed = false;
        return table.columnas
          .map(function (column) {
            if (group.sums[column] !== undefined) return String(Math.round(group.sums[column] * 100) / 100);
            if (!labelUsed) {
              labelUsed = true;
              return label;
            }
            return "";
          })
          .join("\t");
      });
      var tsv = preamble
        .concat([""])
        .concat([table.columnas.map(columnLabel).join("\t")])
        .concat(
          (table.filas || []).map(function (row) {
            return table.columnas
              .map(function (column) {
                var value = row[column];
                return value === null || value === undefined ? "" : String(value);
              })
              .join("\t");
          })
        )
        .concat(totalLines)
        .join("\n");
      state.copyTableTsv = tsv;
    } else {
      state.copyTableTsv = "";
    }

    renderTraceList();
    syncTraceChips();
    fitRightPaneToTable();
  }

  var MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

  function shortDate(value) {
    var match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(value || ""));
    if (!match) return String(value || "");
    return Number(match[3]) + " " + MONTHS[Number(match[2]) - 1] + " " + match[1];
  }

  // Periodo legible a partir de los argumentos de la tool (los mismos que el
  // servidor usó), p. ej. "del 1 ene 2026 al 31 ene 2026" o "corte al 23 nov 2026".
  function todayIso() {
    var d = new Date();
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }

  function periodText(args, tool, consultedOn) {
    args = args || {};
    if (args.fecha_inicio && args.fecha_fin) {
      return "del " + shortDate(args.fecha_inicio) + " al " + shortDate(args.fecha_fin);
    }
    if (args.fecha_corte) return "corte al " + shortDate(args.fecha_corte);
    if (args.anio && args.mes) return MONTHS[Number(args.mes) - 1] + " " + args.anio;
    if (args.anio) return "año " + args.anio;
    // La cartera sin fecha se calcula al día en que se consultó (no al de hoy:
    // una conversación reabierta conserva su fecha de corte real).
    if (/^cartera_/.test(String(tool || ""))) {
      return consultedOn ? "saldos al " + shortDate(consultedOn) : "saldos a la fecha de la consulta";
    }
    return "";
  }

  function tableCaption(trace) {
    var period = trace ? periodText(trace.argumentos, trace.herramienta, trace.consultado_en) : "";
    return toolLabel(trace && trace.herramienta) + (period ? ", " + period : "");
  }

  function renderArgs(trace) {
    if (!trace || !trace.herramienta) return "";
    var technical = {
      reporte: trace.herramienta,
      duracion_ms: trace.duracion_ms || 0,
      parametros: trace.argumentos || {},
    };
    return (
      '<details class="ac-totals-help">' +
      "<summary>Parámetros técnicos de la consulta</summary>" +
      '<pre class="ac-args">' +
      escapeHtml(JSON.stringify(technical, null, 2)) +
      "</pre></details>"
    );
  }

  function setActive(msgIndex, traces, selected) {
    state.active = {
      msgIndex: msgIndex,
      traces: traces || [],
      selected: selected === undefined ? null : selected,
    };
    state.showAllRows = false;
  }

  function lastSuccessfulIndex(traces) {
    for (var i = traces.length - 1; i >= 0; i -= 1) {
      if (!traces[i].error) return i;
    }
    return traces.length ? 0 : null;
  }

  function relativeTime(timestamp) {
    var diff = Date.now() - timestamp;
    if (diff < 60000) return "ahora";
    if (diff < 3600000) return "hace " + Math.floor(diff / 60000) + " min";
    if (diff < 86400000) return "hace " + Math.floor(diff / 3600000) + " h";
    if (diff < 172800000) return "ayer";
    return new Date(timestamp).toLocaleDateString("es-MX", { day: "2-digit", month: "short" });
  }

  function loadRecent() {
    try {
      var raw = localStorage.getItem(STORE_KEY);
      var parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  }

  function renderRecent() {
    var items = loadRecent();
    if (!el.recentWrap || !el.recentList) return;
    el.recentWrap.hidden = !items.length;
    el.recentList.innerHTML = items
      .map(function (item) {
        return (
          '<button type="button" class="ac-suggestion !px-2.5 !py-2" data-open-conversation="' +
          escapeHtml(item.id) +
          '">' +
          '<span class="flex items-center justify-between gap-2"><span class="ac-suggestion__title truncate">' +
          escapeHtml(item.title || "Consulta") +
          '</span><span class="ac-chip shrink-0">' +
          escapeHtml(relativeTime(item.updatedAt || Date.now())) +
          "</span></span></button>"
        );
      })
      .join("");
  }

  function saveConversation() {
    if (state.messages.length < 2) return;
    var id = state.conversationId || (window.crypto && crypto.randomUUID ? crypto.randomUUID() : "c" + Date.now());
    state.conversationId = id;
    var stored = state.messages.map(function (message) {
      var copy = {
        role: message.role,
        content: message.content,
        error: message.error || null,
      };
      if (message.errorInfo) copy.errorInfo = message.errorInfo;
      if (message.meta) copy.meta = message.meta;
      if (message.traces) {
        copy.traces = message.traces.map(function (trace) {
          var table = null;
          if (trace.tabla) {
            var allRows = trace.tabla.filas || [];
            table = {
              columnas: trace.tabla.columnas,
              filas: allRows.slice(0, MAX_STORED_ROWS),
              num_filas: trace.tabla.num_filas,
              truncado: trace.tabla.truncado,
            };
            // Al recortar para localStorage, los totales se congelan sobre todas
            // las filas recibidas: reabrir nunca debe sumar solo las guardadas.
            if (trace.tabla.totales) {
              table.totales = trace.tabla.totales;
              table.filas_originales = trace.tabla.filas_originales;
            } else if (allRows.length > MAX_STORED_ROWS) {
              table.totales = computeTotals(trace.tabla);
              table.filas_originales = allRows.length;
            }
          }
          return {
            consultado_en: trace.consultado_en || null,
            herramienta: trace.herramienta,
            argumentos: trace.argumentos || {},
            duracion_ms: trace.duracion_ms || 0,
            filas: trace.filas || 0,
            columnas: trace.columnas || [],
            tabla: table,
            error: trace.error || null,
          };
        });
      }
      return copy;
    });

    var items = loadRecent().filter(function (item) {
      return item.id !== id;
    });
    items.unshift({
      id: id,
      title: messageTitle(),
      updatedAt: Date.now(),
      messages: stored,
    });
    items = items.slice(0, MAX_RECENT);
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(items));
    } catch (error) {
      /* almacenamiento lleno o bloqueado: la conversación sigue en pantalla */
    }
    renderRecent();
  }

  function openConversation(id) {
    var item = loadRecent().filter(function (entry) {
      return entry.id === id;
    })[0];
    if (!item) return;
    state.messages = item.messages || [];
    state.conversationId = item.id;
    state.showAllRows = false;
    var lastIndex = null;
    var lastTraces = [];
    for (var i = state.messages.length - 1; i >= 0; i -= 1) {
      if (state.messages[i].role === "assistant" && state.messages[i].traces && state.messages[i].traces.length) {
        lastIndex = i;
        lastTraces = state.messages[i].traces;
        break;
      }
    }
    setActive(lastIndex, lastTraces, lastSuccessfulIndex(lastTraces));
    renderMessages();
    renderDataPanel();
    closeDrawers();
    focusInput();
  }

  function newConversation() {
    if (state.messages.length > 1) saveConversation();
    state.messages = [];
    state.conversationId = null;
    state.active = { msgIndex: null, traces: [], selected: null };
    state.showAllRows = false;
    renderMessages();
    renderDataPanel();
    closeDrawers();
    focusInput();
  }

  function pushError(text, info) {
    state.messages.push({ role: "assistant", content: "", error: text, errorInfo: info });
    appendLastMessage();
    announce("No se pudo responder. " + text);
  }

  // retry=true reenvía la pregunta que ya está en pantalla: no agrega otro
  // turno del usuario (el error previo lo quita quien llama).
  async function send(text, options) {
    var retry = Boolean(options && options.retry);
    text = String(text || "").trim();
    if (!text || state.loading) return;
    if (!CONFIGURED) {
      toast("El asistente no está disponible en este servidor.");
      return;
    }

    if (!retry) {
      state.messages.push({ role: "user", content: text });
      appendLastMessage();
      if (el.input) {
        el.input.value = "";
        autoGrow();
      }
    }
    setSending(true);
    showTyping();

    try {
      var response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken(),
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({
          mensaje: text,
          conversacion_id: state.conversationId,
        }),
      });
      var data = null;
      try {
        data = await response.json();
      } catch (error) {
        data = null;
      }
      removeTyping();

      if (!response.ok || !data) {
        data = data || {};
        var retryAfter = Number(data.reintentar_en || response.headers.get("Retry-After") || 0);
        pushError(data.error || "No pude completar la consulta.", {
          codigo: data.codigo || "http_" + response.status,
          // Sin el campo (respuesta antigua o proxy), reintentar solo ayuda en 5xx.
          reintentable:
            typeof data.reintentable === "boolean" ? data.reintentable : response.status >= 500,
          detalle: data.detalle || (data.error ? "" : "Respuesta HTTP " + response.status),
          accion: data.accion || null,
          retryAt: retryAfter > 0 ? Date.now() + retryAfter * 1000 : null,
        });
        return;
      }

      if (data.conversacion_id) {
        state.conversationId = data.conversacion_id;
      }

      var assistant = {
        role: "assistant",
        content: data.respuesta || "",
        traces: (Array.isArray(data.traza) ? data.traza : []).map(function (trace) {
          trace.consultado_en = (data.meta && data.meta.consultado_en) || todayIso();
          return trace;
        }),
        meta: data.meta || {},
      };
      state.messages.push(assistant);
      var msgIndex = state.messages.length - 1;
      setActive(msgIndex, assistant.traces, lastSuccessfulIndex(assistant.traces));
      appendLastMessage();
      renderDataPanel();
      saveConversation();
      var active = activeTrace();
      var partialAnswer = assistant.traces.some(function (t) {
        return t.tabla && t.tabla.truncado;
      });
      announce(
        "Respuesta lista." +
          (active && !active.error
            ? " " + toolLabel(active.herramienta) + ": " + (active.filas || 0) + " filas en Datos citados."
            : "") +
          (partialAnswer ? " Con datos parciales: verifica en la tabla." : "")
      );
    } catch (error) {
      removeTyping();
      pushError("No pude comunicarme con el asistente. Revisa tu conexión a internet.", {
        codigo: "sin_red",
        reintentable: true,
        detalle: error && error.message ? error.message : "",
      });
    } finally {
      setSending(false);
      focusInput();
    }
  }

  // Lleva el foco a la tabla citada (o al panel) sin importar el tamaño de
  // pantalla: en móvil abre el cajón; si el panel está oculto, lo muestra.
  function goToCitedData() {
    if (window.innerWidth <= 860) {
      openRight();
    } else if (layout.rightCollapsed) {
      setCollapsed("right", false);
    }
    var target =
      (el.tableSlot && el.tableSlot.querySelector(".ac-table-wrap")) ||
      (el.rightPane && el.rightPane.querySelector(".ac-pane-title"));
    if (target) {
      if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
      target.focus();
    }
    announce(
      el.tableSlot && el.tableSlot.querySelector(".ac-table-wrap")
        ? "Datos citados."
        : "Datos citados: aún no hay una tabla."
    );
  }

  function focusInput() {
    if (el.input && !el.input.readOnly) el.input.focus();
  }

  function toast(message) {
    if (!el.toast || !el.toastText) return;
    el.toastText.textContent = message;
    el.toast.classList.remove("hidden");
    announce(message);
    window.clearTimeout(toast._timer);
    toast._timer = window.setTimeout(function () {
      el.toast.classList.add("hidden");
    }, 2600);
  }

  function copyText(text, successMessage) {
    if (!text) return;
    var done = function () {
      toast(successMessage);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(function () {
        toast("No se pudo copiar.");
      });
      return;
    }
    var area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    try {
      document.execCommand("copy");
      done();
    } catch (error) {
      toast("No se pudo copiar.");
    }
    area.remove();
  }

  function threadAsText() {
    return state.messages
      .map(function (message) {
        if (message.role === "user") return "Pregunta: " + message.content;
        if (message.error) return "Asistente: (error) " + message.error;
        return "Asistente: " + message.content;
      })
      .join("\n\n");
  }

  // ---- Cajones (tablet/móvil): diálogo modal accesible ----
  // Al abrir: foco al primer control, fondo inert (no se tabula ni se lee) y
  // role=dialog. Al cerrar: se revierte y el foco vuelve al botón que lo abrió.
  var drawer = { pane: null, opener: null, inerted: [] };
  var FOCUSABLE =
    'button:not([disabled]):not([hidden]), [href], input:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

  function drawerBackground(pane) {
    var nodes = [el.header, el.thread, pane === el.leftPane ? el.rightPane : el.leftPane];
    // Cromo de Jazzmin/AdminLTE fuera del asistente.
    document.querySelectorAll(".main-header, .main-sidebar, .main-footer").forEach(function (node) {
      nodes.push(node);
    });
    root.querySelectorAll(".ac-resizer").forEach(function (node) {
      nodes.push(node);
    });
    return nodes.filter(function (node) {
      return node && node !== pane && !node.contains(pane);
    });
  }

  function setToggleState(open) {
    root.querySelectorAll("[data-toggle-left]").forEach(function (button) {
      button.setAttribute("aria-expanded", String(open === "left"));
    });
    root.querySelectorAll("[data-toggle-right]").forEach(function (button) {
      button.setAttribute("aria-expanded", String(open === "right"));
    });
  }

  function closeDrawers() {
    var pane = drawer.pane;
    if (el.body) {
      el.body.classList.remove("ac-left-open", "ac-right-open");
    }
    if (el.backdrop) el.backdrop.hidden = true;
    drawer.inerted.forEach(function (node) {
      node.inert = false;
    });
    drawer.inerted = [];
    if (pane) {
      pane.removeAttribute("role");
      pane.removeAttribute("aria-modal");
    }
    setToggleState(null);
    var opener = drawer.opener;
    drawer.pane = null;
    drawer.opener = null;
    if (pane && opener && document.contains(opener) && pane.contains(document.activeElement)) {
      opener.focus();
    }
  }

  function openDrawer(side) {
    if (!el.body) return;
    var pane = side === "left" ? el.leftPane : el.rightPane;
    if (drawer.pane) closeDrawers();
    drawer.opener = document.activeElement;
    el.body.classList.add(side === "left" ? "ac-left-open" : "ac-right-open");
    if (el.backdrop) el.backdrop.hidden = false;
    if (pane) {
      drawer.pane = pane;
      pane.setAttribute("role", "dialog");
      pane.setAttribute("aria-modal", "true");
      drawer.inerted = drawerBackground(pane).filter(function (node) {
        return !node.inert;
      });
      drawer.inerted.forEach(function (node) {
        node.inert = true;
      });
      var first = Array.prototype.filter.call(pane.querySelectorAll(FOCUSABLE), function (node) {
        return node.getClientRects().length > 0;
      })[0];
      if (first) first.focus();
    }
    setToggleState(side);
  }

  function openLeft() {
    openDrawer("left");
  }

  function openRight() {
    openDrawer("right");
  }

  function wireEvents() {
    document.addEventListener("click", function (event) {
      var suggestion = event.target.closest("[data-consulta]");
      if (suggestion) {
        event.preventDefault();
        closeDrawers();
        send(suggestion.dataset.consulta || suggestion.textContent);
        return;
      }

      var open = event.target.closest("[data-open-conversation]");
      if (open) {
        event.preventDefault();
        openConversation(open.dataset.openConversation);
        return;
      }

      var retry = event.target.closest("[data-retry]");
      if (retry) {
        event.preventDefault();
        if (retry.disabled || state.loading) return;
        var errorIndex = Number(retry.dataset.retry);
        var question = findPreviousUser(errorIndex);
        var isLast = errorIndex === state.messages.length - 1;
        if (question && isLast && state.messages[errorIndex].error) {
          // Reintento en su lugar: se quita el error y se reenvía la misma pregunta.
          state.messages.splice(errorIndex, 1);
          renderMessages();
          send(question, { retry: true });
        } else if (question) {
          // El hilo siguió después del error: se pregunta de nuevo al final.
          send(question);
        }
        return;
      }

      var traceChip = event.target.closest("[data-trace-msg]");
      if (traceChip) {
        event.preventDefault();
        var msgIndex = Number(traceChip.dataset.traceMsg);
        var traceIndex = Number(traceChip.dataset.traceIdx);
        var message = state.messages[msgIndex];
        if (message && message.traces) {
          setActive(msgIndex, message.traces, traceIndex);
          renderDataPanel();
          if (window.innerWidth <= 860) openRight();
          else announce("Datos citados: " + toolLabel(message.traces[traceIndex].herramienta) + ".");
        }
        return;
      }

      var selectTrace = event.target.closest("[data-select-trace]");
      if (selectTrace) {
        event.preventDefault();
        state.active.selected = Number(selectTrace.dataset.selectTrace);
        state.showAllRows = false;
        renderDataPanel();
        return;
      }

      if (event.target.closest("[data-show-all]")) {
        event.preventDefault();
        state.showAllRows = !state.showAllRows;
        var trace = activeTrace();
        if (trace && el.tableSlot) {
          el.tableSlot.innerHTML = renderTable(trace.tabla, tableCaption(trace));
          var toggle = el.tableSlot.querySelector("[data-show-all]");
          if (toggle) toggle.focus();
        }
        return;
      }

      if (event.target.closest("[data-narrow]")) {
        event.preventDefault();
        var lastQuestion = findPreviousUser(state.messages.length - 1);
        if (el.input && lastQuestion) {
          var asks = /\?\s*$/.test(lastQuestion);
          el.input.value =
            lastQuestion.replace(/\s*[.?]?\s*$/, "") + ", solo el mes actual" + (asks ? "?" : "");
          autoGrow();
          closeDrawers();
          el.input.focus();
          el.input.setSelectionRange(el.input.value.length, el.input.value.length);
          announce("Pregunta lista para editar con un periodo más corto.");
        }
        return;
      }

      if (event.target.closest("[data-new-chat]")) {
        event.preventDefault();
        newConversation();
        return;
      }

      if (event.target.closest("[data-toggle-left]")) {
        event.preventDefault();
        if (el.body.classList.contains("ac-left-open")) closeDrawers();
        else openLeft();
        return;
      }

      if (event.target.closest("[data-toggle-right]")) {
        event.preventDefault();
        if (el.body.classList.contains("ac-right-open")) closeDrawers();
        else openRight();
        return;
      }

      if (event.target.closest("[data-close-drawers]")) {
        event.preventDefault();
        closeDrawers();
        return;
      }

      if (event.target.closest("[data-copy-thread]")) {
        event.preventDefault();
        copyText(threadAsText(), "Conversación copiada.");
        return;
      }

      if (event.target.closest("[data-copy-table]")) {
        event.preventDefault();
        copyText(state.copyTableTsv, "Tabla copiada como TSV.");
        return;
      }
    });

    if (el.composer) {
      el.composer.addEventListener("submit", function (event) {
        event.preventDefault();
        send(el.input ? el.input.value : "");
      });
    }

    if (el.input) {
      el.input.addEventListener("input", autoGrow);
      el.input.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          send(el.input.value);
        }
      });
    }

    if (el.filter) {
      el.filter.addEventListener("input", function () {
        var query = el.filter.value.trim().toLowerCase();
        var visible = 0;
        el.suggestionsList.querySelectorAll("[data-consulta]").forEach(function (button) {
          var haystack = (
            (button.dataset.titulo || "") +
            " " +
            (button.dataset.tipo || "") +
            " " +
            (button.dataset.consulta || "")
          ).toLowerCase();
          var match = !query || haystack.indexOf(query) !== -1;
          button.hidden = !match;
          if (match) visible += 1;
        });
        if (el.filterEmpty) el.filterEmpty.hidden = visible > 0;
      });
    }

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && drawer.pane) {
        closeDrawers();
        return;
      }
      var target = event.target;
      var typing =
        target &&
        (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName || ""));
      if (event.key === "/" && !typing && !event.ctrlKey && !event.metaKey && !event.altKey) {
        event.preventDefault();
        focusInput();
        return;
      }
      if (!event.altKey || event.ctrlKey || event.metaKey) return;
      var key = String(event.key || "").toLowerCase();
      if (key === "d") {
        event.preventDefault();
        goToCitedData();
      } else if (key === "n") {
        event.preventDefault();
        newConversation();
        announce("Nueva conversación.");
      }
    });

    // Si la ventana crece y el cajón pasa a ser columna, se cierra el modo
    // diálogo por la vía normal (revierte inert/role).
    window.addEventListener("resize", function () {
      if (
        (drawer.pane === el.leftPane && window.innerWidth > 1099) ||
        (drawer.pane === el.rightPane && window.innerWidth > 860)
      ) {
        closeDrawers();
      }
    });
  }

  // ---- Paneles redimensionables / ocultables (solo escritorio) ----
  var LAYOUT_KEY = "ac:layout:v1";
  var THREAD_MIN = 360;
  var PANES = {
    left: {
      min: 220,
      max: 420,
      cssVar: "--ac-left-w",
      collapsedClass: "ac-left-collapsed",
      media: window.matchMedia("(min-width: 1100px)"),
      col: root.querySelector(".ac-col--left"),
      resizer: root.querySelector('[data-resizer="left"]'),
      collapseBtn: root.querySelector("[data-collapse-left]"),
      expandBtn: root.querySelector("[data-expand-left]"),
    },
    right: {
      min: 280,
      max: 520,
      cssVar: "--ac-right-w",
      collapsedClass: "ac-right-collapsed",
      media: window.matchMedia("(min-width: 861px)"),
      col: root.querySelector(".ac-col--right"),
      resizer: root.querySelector('[data-resizer="right"]'),
      collapseBtn: root.querySelector("[data-collapse-right]"),
      expandBtn: root.querySelector("[data-expand-right]"),
    },
  };
  var layout = { left: null, right: null, leftCollapsed: false, rightCollapsed: false };
  // Ancho sugerido por el contenido (tabla citada). Nunca se guarda y nunca
  // pisa un ancho que el usuario eligió arrastrando o con el teclado.
  var autoWidth = { left: null, right: null };

  function loadLayout() {
    try {
      var saved = JSON.parse(localStorage.getItem(LAYOUT_KEY) || "{}") || {};
      ["left", "right"].forEach(function (side) {
        var width = Number(saved[side]);
        layout[side] = Number.isFinite(width) && width > 0 ? width : null;
        layout[side + "Collapsed"] = saved[side + "Collapsed"] === true;
      });
    } catch (error) {
      /* localStorage no disponible o JSON inválido: se usan los defaults. */
    }
  }

  function saveLayout() {
    try {
      localStorage.setItem(LAYOUT_KEY, JSON.stringify(layout));
    } catch (error) {
      /* Sin persistencia; el layout funciona igual durante la sesión. */
    }
  }

  function paneActive(side) {
    return PANES[side].media.matches && !layout[side + "Collapsed"];
  }

  function paneWidth(side) {
    var pane = PANES[side];
    if (!paneActive(side) || !pane.col) return 0;
    return pane.col.getBoundingClientRect().width;
  }

  // Límite superior real: el del panel y el que deja al hilo central >= THREAD_MIN.
  function clampWidth(side, width) {
    var pane = PANES[side];
    var other = side === "left" ? "right" : "left";
    var available = el.body ? el.body.clientWidth - paneWidth(other) - THREAD_MIN : pane.max;
    var max = Math.max(pane.min, Math.min(pane.max, available));
    return Math.round(Math.min(max, Math.max(pane.min, width)));
  }

  // Sin ancho guardado se usa el default del breakpoint, pero también se recorta
  // si no deja 360 px al hilo (p. ej. 1100–1279 px con la barra lateral del admin).
  // El recorte no se guarda: al ensanchar la ventana vuelve el default.
  function applyWidth(side) {
    var pane = PANES[side];
    root.style.removeProperty(pane.cssVar);
    if (paneActive(side)) {
      var chosen = layout[side] !== null ? layout[side] : autoWidth[side];
      var desired = chosen !== null ? chosen : paneWidth(side);
      var width = clampWidth(side, desired);
      if (chosen !== null || width < Math.round(desired)) {
        root.style.setProperty(pane.cssVar, width + "px");
      }
    }
    if (pane.resizer) {
      var current = paneWidth(side);
      if (current) pane.resizer.setAttribute("aria-valuenow", String(Math.round(current)));
    }
  }

  function applyLayout() {
    ["left", "right"].forEach(function (side) {
      var pane = PANES[side];
      var collapsed = layout[side + "Collapsed"];
      root.classList.toggle(pane.collapsedClass, collapsed);
      if (pane.collapseBtn) pane.collapseBtn.setAttribute("aria-expanded", String(!collapsed));
      if (pane.expandBtn) pane.expandBtn.setAttribute("aria-expanded", String(!collapsed));
    });
    // El izquierdo primero: el límite del derecho depende del ancho del izquierdo.
    applyWidth("left");
    applyWidth("right");
  }

  function setCollapsed(side, collapsed) {
    var pane = PANES[side];
    var hadFocusInside = pane.col && pane.col.contains(document.activeElement);
    layout[side + "Collapsed"] = collapsed;
    applyLayout();
    saveLayout();
    if (collapsed && hadFocusInside && pane.expandBtn) {
      pane.expandBtn.focus();
    } else if (!collapsed && pane.collapseBtn && document.activeElement === pane.expandBtn) {
      pane.collapseBtn.focus();
    }
  }

  function setWidth(side, width, persist) {
    layout[side] = width === null ? null : clampWidth(side, width);
    applyWidth(side);
    if (persist) saveLayout();
  }

  function wireResizer(side) {
    var pane = PANES[side];
    var handle = pane.resizer;
    if (!handle) return;
    var drag = null;

    handle.addEventListener("pointerdown", function (event) {
      if (event.button !== 0 || !paneActive(side)) return;
      event.preventDefault();
      drag = { startX: event.clientX, startWidth: paneWidth(side), pointerId: event.pointerId };
      handle.setPointerCapture(event.pointerId);
      handle.classList.add("is-dragging");
      root.classList.add("ac-resizing");
    });

    handle.addEventListener("pointermove", function (event) {
      if (!drag || event.pointerId !== drag.pointerId) return;
      var delta = event.clientX - drag.startX;
      setWidth(side, drag.startWidth + (side === "left" ? delta : -delta), false);
    });

    function endDrag(event) {
      if (!drag || event.pointerId !== drag.pointerId) return;
      if (handle.hasPointerCapture(event.pointerId)) handle.releasePointerCapture(event.pointerId);
      drag = null;
      handle.classList.remove("is-dragging");
      root.classList.remove("ac-resizing");
      saveLayout();
    }
    handle.addEventListener("pointerup", endDrag);
    handle.addEventListener("pointercancel", endDrag);

    handle.addEventListener("dblclick", function () {
      setWidth(side, null, true);
    });

    // Las flechas mueven el separador: en el panel derecho, izquierda = más ancho.
    handle.addEventListener("keydown", function (event) {
      var step = event.shiftKey ? 48 : 16;
      var grow = side === "left" ? 1 : -1;
      var current = paneWidth(side);
      var next = null;
      if (event.key === "ArrowLeft") next = current - step * grow;
      else if (event.key === "ArrowRight") next = current + step * grow;
      else if (event.key === "Home") next = pane.min;
      else if (event.key === "End") next = pane.max;
      if (next === null) return;
      event.preventDefault();
      setWidth(side, next, true);
    });
  }

  // Ensancha Datos citados lo justo para que la tabla no necesite scroll
  // horizontal (hasta 520 px y sin bajar el hilo de 360 px).
  function fitRightPaneToTable() {
    if (!PANES.right.media.matches || layout.rightCollapsed || layout.right !== null) return;
    autoWidth.right = null;
    applyWidth("right");
    var wrap = el.tableSlot && el.tableSlot.querySelector(".ac-table-wrap");
    if (!wrap) return;
    var overflow = wrap.scrollWidth - wrap.clientWidth;
    if (overflow <= 0) return;
    autoWidth.right = paneWidth("right") + overflow + 2;
    applyWidth("right");
  }

  function initLayout() {
    loadLayout();
    applyLayout();
    ["left", "right"].forEach(function (side) {
      var pane = PANES[side];
      wireResizer(side);
      if (pane.collapseBtn) {
        pane.collapseBtn.addEventListener("click", function () {
          setCollapsed(side, true);
        });
      }
      if (pane.expandBtn) {
        pane.expandBtn.addEventListener("click", function () {
          setCollapsed(side, false);
        });
      }
      var onMediaChange = function () {
        applyLayout();
      };
      if (pane.media.addEventListener) pane.media.addEventListener("change", onMediaChange);
      else if (pane.media.addListener) pane.media.addListener(onMediaChange);
    });

    var resizeFrame = null;
    window.addEventListener("resize", function () {
      if (resizeFrame) return;
      resizeFrame = window.requestAnimationFrame(function () {
        resizeFrame = null;
        applyLayout();
      });
    });
  }

  renderRecent();
  renderMessages();
  renderDataPanel();
  wireEvents();
  initLayout();
  autoGrow();
})();
