const fs = require("node:fs");
const vm = require("node:vm");

function element({ dataset = {}, hidden = false } = {}) {
  return {
    dataset,
    hidden,
    style: {},
    listeners: {},
    attributes: {},
    addEventListener(name, callback) {
      this.listeners[name] = callback;
    },
    getAttribute(name) {
      return this.attributes[name] || null;
    },
    setAttribute(name, value) {
      this.attributes[name] = value;
    },
    getBoundingClientRect() {
      return { top: 100, bottom: 130, right: 400 };
    },
    focus() {},
    matches() {
      return false;
    },
  };
}

function startConciliacionScript() {
  const trigger = element();
  trigger.attributes["aria-controls"] = "origin-panel";

  const summary = element({
    dataset: { total: "600.00", moneda: "MXN", count: "2" },
  });
  const emptyState = element({ hidden: true });
  const items = [
    element({ dataset: { concOriginItem: "venta_contado", concOriginAmount: "300.00" } }),
    element({ dataset: { concOriginItem: "pago_sin_rep", concOriginAmount: "300.00" } }),
  ];
  const panel = element({ hidden: true });
  panel.offsetWidth = 320;
  panel.offsetHeight = 280;
  panel.querySelectorAll = (selector) =>
    selector === "[data-conc-origin-item]" ? items : [];
  panel.querySelector = (selector) => {
    if (selector === "[data-conc-origin-summary]") return summary;
    if (selector === "[data-conc-origin-empty]") return emptyState;
    return null;
  };

  const select = element();
  select.value = "";
  select.closest = () => panel;

  const document = {
    readyState: "complete",
    activeElement: null,
    querySelectorAll(selector) {
      if (selector === "[data-conc-trigger]") return [trigger];
      if (selector === "[data-conc-origin-filter]") return [select];
      return [];
    },
    getElementById(id) {
      return id === "origin-panel" ? panel : null;
    },
    addEventListener() {},
  };
  const window = {
    innerWidth: 1000,
    innerHeight: 700,
    addEventListener() {},
    clearTimeout() {},
    setTimeout() {},
  };

  const script = fs.readFileSync(require.resolve("../conciliacion.js"), "utf8");
  vm.runInNewContext(script, { document, window });
  return { select, items, summary, emptyState };
}

describe("filtro de origen del desglose de conciliación", () => {
  test("filtra el origen sin ocultar el total completo y muestra su subtotal", () => {
    const { select, items, summary, emptyState } = startConciliacionScript();

    select.value = "pago_sin_rep";
    select.listeners.change();

    expect(items.map((item) => item.hidden)).toEqual([true, false]);
    expect(summary.textContent).toContain("Mostrando 1 de 2 movimientos");
    expect(summary.textContent).toContain("Subtotal seleccionado: 300.00 MXN");
    expect(summary.textContent).toContain("Total completo: 600.00 MXN");
    expect(emptyState.hidden).toBe(true);
  });

  test("muestra un estado vacío si no existen movimientos del origen elegido", () => {
    const { select, items, summary, emptyState } = startConciliacionScript();

    select.value = "otro_origen";
    select.listeners.change();

    expect(items.every((item) => item.hidden)).toBe(true);
    expect(summary.textContent).toContain("Mostrando 0 de 2 movimientos");
    expect(emptyState.hidden).toBe(false);
  });
});
