const tours = require("../balance-tours.js");

function memoryStorage() {
  const values = {};
  return {
    getItem(key) {
      return Object.prototype.hasOwnProperty.call(values, key) ? values[key] : null;
    },
    setItem(key, value) {
      values[key] = String(value);
    },
  };
}

describe("balance tours state", () => {
  test("uses a versioned and page-specific storage key", () => {
    expect(tours.getStorageKey("gastos")).toBe("balance-tour:v1:gastos:completed");
    expect(tours.getStorageKey("ventas")).not.toBe(tours.getStorageKey("gastos"));
  });

  test("marks a tour as completed without storing filter data", () => {
    const storage = memoryStorage();

    expect(tours.isCompleted("ventas", storage)).toBe(false);
    expect(tours.markCompleted("ventas", storage)).toBe(true);
    expect(tours.isCompleted("ventas", storage)).toBe(true);
  });

  test("defines complete tours with stable data-tour selectors", () => {
    const gastosSteps = tours.getSteps("gastos");
    const ventasSteps = tours.getSteps("ventas");

    expect(gastosSteps.length).toBeGreaterThanOrEqual(8);
    expect(ventasSteps.length).toBeGreaterThanOrEqual(8);
    gastosSteps.concat(ventasSteps).forEach((tourStep) => {
      expect(tourStep.element).toMatch(/^\[data-balance-tour=/);
      expect(tourStep.popover.title).toBeTruthy();
      expect(tourStep.popover.description).toBeTruthy();
    });
  });
});
