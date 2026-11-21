(function () {
  "use strict";

  var root = document.getElementById("asistente-app");
  if (!root) return;

  var API_URL = root.dataset.apiUrl;
  var CONFIGURED = root.dataset.configurado === "true";
  var STORE_KEY = "ac:recent:v1";
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
    return TOOL_LABELS[name] || name;
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

  function showTyping() {
    var node = document.createElement("div");
    node.className = "ac-bot ac-msg";
    node.setAttribute("data-typing", "");
    node.innerHTML =
      '<span class="ac-bot-avatar">' +
      icon("i-sun-wave", "h-4 w-4") +
      "</span>" +
      '<div class="ac-bot-body">' +
      '<div class="flex items-center gap-3">' +
      '<span class="ac-typing" aria-hidden="true"><span></span><span></span><span></span></span>' +
      '<span class="text-[11.5px] text-[var(--as-muted)]">Consultando el servidor MCP…</span>' +
      "</div></div>";
    el.messages.appendChild(node);
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
    if (!firstUser) return "Nueva consulta";
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
        el.threadMeta.textContent = "El asistente elige la herramienta de solo lectura adecuada.";
      }
      return;
    }
    var seconds = Math.max(0.1, (meta.duracion_ms || 0) / 1000);
    var tools = (lastAssistant.traces || []).length;
    if (el.threadMeta) {
      el.threadMeta.textContent =
        tools +
        (tools === 1 ? " consulta MCP" : " consultas MCP") +
        " · " +
        seconds.toFixed(1) +
        " s" +
        (meta.modelo ? " · " + meta.modelo : "");
    }
  }

  function renderTraceChip(trace, msgIndex, traceIndex) {
    var failed = Boolean(trace.error);
    return (
      '<button type="button" class="inline-flex items-center gap-1.5 rounded-full border px-2 py-[3px] text-[10px] font-[650] transition-colors ' +
      (failed
        ? "border-[color-mix(in_srgb,var(--as-danger)_45%,var(--as-border))] text-[var(--as-danger)] hover:bg-[color-mix(in_srgb,var(--as-danger)_8%,transparent)]"
        : "border-[var(--as-border)] text-[var(--as-text-2)] hover:border-[var(--as-mist)] hover:bg-[var(--as-mist-soft)]") +
      '" data-trace-msg="' +
      msgIndex +
      '" data-trace-idx="' +
      traceIndex +
      '" title="Ver ' +
      escapeHtml(trace.herramienta) +
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

    var body;
    if (message.error) {
      body =
        '<div class="flex items-start gap-2.5">' +
        icon("i-alert", "h-4 w-4 mt-0.5 shrink-0 text-[var(--as-danger)]") +
        '<div class="min-w-0"><p class="text-[13px] leading-relaxed text-[var(--as-text-2)]">' +
        escapeHtml(message.error) +
        '</p><button type="button" class="mt-2 text-[11px] font-[700] text-[var(--as-accent)] underline underline-offset-2 decoration-[color-mix(in_srgb,var(--as-accent)_40%,transparent)] hover:decoration-[var(--as-accent)]" data-retry="' +
        index +
        '">Reintentar</button></div></div>';
    } else {
      body = '<div class="ac-prose">' + formatAnswer(message.content) + "</div>";
    }

    var traces = message.traces || [];
    var foot = "";
    if (traces.length) {
      var okCount = traces.filter(function (t) {
        return !t.error;
      }).length;
      var chips = traces
        .slice(0, 5)
        .map(function (trace, traceIndex) {
          return renderTraceChip(trace, index, traceIndex);
        })
        .join("");
      var duration = message.meta && message.meta.duracion_ms
        ? (message.meta.duracion_ms / 1000).toFixed(1) + " s"
        : "";
      foot =
        '<div class="ac-answer-foot">' +
        '<span class="ac-chip">' +
        okCount +
        (okCount === 1 ? " consulta" : " consultas") +
        "</span>" +
        chips +
        (duration
          ? '<span class="ml-auto inline-flex items-center gap-1">' +
            icon("i-clock", "h-3 w-3") +
            duration +
            "</span>"
          : "") +
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

  function renderMessages() {
    if (!el.messages) return;
    el.messages.innerHTML = state.messages
      .map(function (message, index) {
        return renderMessage(message, index);
      })
      .join("");
    if (el.welcome) el.welcome.hidden = state.messages.length > 0;
    if (el.threadTitle) el.threadTitle.textContent = messageTitle();
    updateThreadMeta();
    scrollFeed();
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

  function formatCell(value, column, numeric) {
    if (value === null || value === undefined || value === "") return '<span class="text-[var(--as-muted)]">—</span>';
    if (typeof value === "object") return escapeHtml(JSON.stringify(value));
    if (numeric) {
      var formatted = numberFormat(value);
      var prefix = isMoneyColumn(column) ? "$" : "";
      return '<span title="' + escapeHtml(value) + '">' + prefix + formatted + "</span>";
    }
    var text = escapeHtml(value);
    return '<span class="inline-block max-w-[190px] truncate align-bottom" title="' + text + '">' + text + "</span>";
  }

  function renderTable(table) {
    if (!table || !table.columnas || !table.columnas.length) {
      return '<p class="text-[11.5px] text-[var(--as-muted)]">La herramienta no devolvió una tabla.</p>';
    }
    var rows = table.filas || [];
    var columns = table.columnas;
    var visible = state.showAllRows ? rows : rows.slice(0, 8);
    var numeric = {};
    columns.forEach(function (column) {
      numeric[column] = isNumericColumn(column, rows);
    });

    var head = columns
      .map(function (column) {
        return (
          '<th class="' +
          (numeric[column] ? "is-num" : "") +
          '">' +
          escapeHtml(column) +
          "</th>"
        );
      })
      .join("");

    var body = visible
      .map(function (row) {
        return (
          "<tr>" +
          columns
            .map(function (column) {
              var className = numeric[column] ? "is-num" : "";
              if (/fecha|periodo/i.test(column)) className += " is-date";
              return (
                '<td class="' +
                className.trim() +
                '">' +
                formatCell(row[column], column, numeric[column]) +
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

    var more = "";
    if (rows.length > 8) {
      more =
        '<button type="button" class="mt-2 text-[10.5px] font-[700] text-[var(--as-accent)] underline underline-offset-2 decoration-[color-mix(in_srgb,var(--as-accent)_40%,transparent)] hover:decoration-[var(--as-accent)]" data-show-all>' +
        (state.showAllRows ? "Mostrar solo 8 filas" : "Ver las " + rows.length + " filas") +
        "</button>";
    }

    var note = table.truncado
      ? '<p class="mt-1.5 text-[10px] text-[var(--as-muted)]">El servidor truncó el resultado al límite permitido.</p>'
      : "";

    return (
      '<div class="ac-table-wrap"><table class="ac-table"><thead><tr>' +
      head +
      "</tr></thead><tbody>" +
      body +
      "</tbody></table></div>" +
      more +
      note
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
          ? "error"
          : (trace.filas || 0) + " filas · " + (trace.duracion_ms || 0) + " ms";
        return (
          '<button type="button" class="ac-tool' +
          (failed ? " ac-tool--error" : "") +
          '" data-select-trace="' +
          index +
          '"' +
          selected +
          ">" +
          icon(failed ? "i-alert" : "i-table", "h-4 w-4 text-[var(--as-muted)]") +
          '<span class="ac-tool__name">' +
          escapeHtml(trace.herramienta) +
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
      if (el.dataEmpty) el.dataEmpty.classList.remove("hidden");
      if (el.dataContent) el.dataContent.classList.add("hidden");
      if (el.copyTable) el.copyTable.disabled = true;
      if (el.dataSub) el.dataSub.textContent = "Tabla y traza de la última consulta.";
      return;
    }

    if (el.dataEmpty) el.dataEmpty.classList.add("hidden");
    if (el.dataContent) el.dataContent.classList.remove("hidden");
    if (el.dataSub) {
      el.dataSub.textContent =
        traces.length + (traces.length === 1 ? " herramienta consultada." : " herramientas consultadas.");
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
            "Error de herramienta</p>" +
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
      return;
    }

    if (el.selectedHead) {
      el.selectedHead.innerHTML =
        '<div class="flex items-center justify-between gap-2">' +
        '<span class="font-mono text-[10.5px] font-[500] text-[var(--as-text-2)] truncate" title="' +
        escapeHtml(trace.herramienta) +
        '">' +
        escapeHtml(trace.herramienta) +
        "</span>" +
        '<span class="ac-chip">' +
        (trace.filas || 0) +
        " filas</span></div>" +
        '<p class="mt-1 text-[10.5px] text-[var(--as-muted)]">' +
        toolLabel(trace.herramienta) +
        " · " +
        (trace.duracion_ms || 0) +
        " ms</p>";
    }

    state.showAllRows = false;
    if (el.tableSlot) el.tableSlot.innerHTML = renderTable(trace.tabla);
    if (el.argsSlot) el.argsSlot.innerHTML = renderArgs(trace);
    if (el.copyTable) el.copyTable.disabled = !trace.tabla;

    var table = trace.tabla;
    if (table && table.columnas) {
      var tsv = [table.columnas.join("\t")]
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
        .join("\n");
      state.copyTableTsv = tsv;
    } else {
      state.copyTableTsv = "";
    }

    renderTraceList();
  }

  function renderArgs(trace) {
    var args = trace && trace.argumentos;
    if (!args || !Object.keys(args).length) return "";
    return (
      '<details class="rounded-xl border border-[var(--as-border)] bg-[var(--as-panel)] px-3 py-2">' +
      '<summary class="cursor-pointer text-[10.5px] font-[700] text-[var(--as-muted)]">Parámetros de la consulta</summary>' +
      '<pre class="mt-2 overflow-x-auto whitespace-pre-wrap break-words font-mono text-[10.5px] leading-relaxed text-[var(--as-text-2)]">' +
      escapeHtml(JSON.stringify(args, null, 2)) +
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
      if (message.meta) copy.meta = message.meta;
      if (message.traces) {
        copy.traces = message.traces.map(function (trace) {
          var table = trace.tabla
            ? {
                columnas: trace.tabla.columnas,
                filas: (trace.tabla.filas || []).slice(0, MAX_STORED_ROWS),
                num_filas: trace.tabla.num_filas,
                truncado: trace.tabla.truncado,
              }
            : null;
          return {
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

  async function send(text) {
    text = String(text || "").trim();
    if (!text || state.loading) return;
    if (!CONFIGURED) {
      toast("El servidor MCP no está configurado.");
      return;
    }

    var history = state.messages
      .filter(function (message) {
        return (message.role === "user" || message.role === "assistant") && !message.error;
      })
      .map(function (message) {
        return { role: message.role, content: message.content };
      });

    state.messages.push({ role: "user", content: text });
    renderMessages();
    if (el.input) {
      el.input.value = "";
      autoGrow();
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
        body: JSON.stringify({ mensaje: text, historial: history.slice(-12) }),
      });
      var data = null;
      try {
        data = await response.json();
      } catch (error) {
        data = { error: "El servidor devolvió una respuesta no válida." };
      }
      removeTyping();

      if (!response.ok) {
        state.messages.push({
          role: "assistant",
          content: "",
          error: data && data.error ? data.error : "No pude completar la consulta.",
        });
        renderMessages();
        return;
      }

      var assistant = {
        role: "assistant",
        content: data.respuesta || "",
        traces: Array.isArray(data.traza) ? data.traza : [],
        meta: data.meta || {},
      };
      state.messages.push(assistant);
      var msgIndex = state.messages.length - 1;
      setActive(msgIndex, assistant.traces, lastSuccessfulIndex(assistant.traces));
      renderMessages();
      renderDataPanel();
      saveConversation();
    } catch (error) {
      removeTyping();
      state.messages.push({
        role: "assistant",
        content: "",
        error:
          "No pude comunicarme con el asistente. Revisa tu conexión y que el servidor MCP esté activo.",
      });
      renderMessages();
    } finally {
      setSending(false);
      focusInput();
    }
  }

  function focusInput() {
    if (el.input && !el.input.readOnly) el.input.focus();
  }

  function toast(message) {
    if (!el.toast || !el.toastText) return;
    el.toastText.textContent = message;
    el.toast.classList.remove("hidden");
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

  function closeDrawers() {
    if (el.body) {
      el.body.classList.remove("ac-left-open", "ac-right-open");
    }
    if (el.backdrop) el.backdrop.hidden = true;
  }

  function openLeft() {
    if (!el.body) return;
    el.body.classList.remove("ac-right-open");
    el.body.classList.add("ac-left-open");
    if (el.backdrop) el.backdrop.hidden = false;
  }

  function openRight() {
    if (!el.body) return;
    el.body.classList.remove("ac-left-open");
    el.body.classList.add("ac-right-open");
    if (el.backdrop) el.backdrop.hidden = false;
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
        var question = findPreviousUser(Number(retry.dataset.retry));
        if (question) send(question);
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
          el.tableSlot.innerHTML = renderTable(trace.tabla);
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
      if (event.key === "Escape") closeDrawers();
    });

    window.addEventListener("resize", function () {
      if (window.innerWidth > 1099) {
        if (el.body) el.body.classList.remove("ac-left-open");
      }
      if (window.innerWidth > 860) {
        if (el.body) el.body.classList.remove("ac-right-open");
      }
      if (!el.body || (!el.body.classList.contains("ac-left-open") && !el.body.classList.contains("ac-right-open"))) {
        if (el.backdrop) el.backdrop.hidden = true;
      }
    });
  }

  renderRecent();
  renderMessages();
  renderDataPanel();
  wireEvents();
  autoGrow();
})();
