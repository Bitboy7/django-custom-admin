/**
 * Pruebas unitarias para las funciones de paleta y construcción de filas de categorías
 * en balances-charts.js.
 *
 * Verifica la invariante clave:
 *   el color del swatch en la tabla PDF de cada categoría debe coincidir
 *   con el color que Chart.js le asignó según su posición ORIGINAL en el array,
 *   independientemente del orden de clasificación de la tabla.
 */

// balances-charts.js usa APIs de navegador; las shimamos antes de requerir el módulo.
global.window = {
  addEventListener: function () {},
  balancesCategoriasLabels: undefined,
  balancesCategoriasData: undefined,
};
global.document = {
  addEventListener: function () {},
  getElementById: function () {
    return null;
  },
  querySelectorAll: function () {
    return [];
  },
  querySelector: function () {
    return null;
  },
};

const {
  _curatedPalette,
  generateColor,
  buildColorArrays,
  hslToHex,
  paletteHex,
  buildCategoryRows,
} = require("../balances-charts.js");

// ─────────────────────────────────────────────
// paletteHex
// ─────────────────────────────────────────────
describe("paletteHex", () => {
  test("devuelve un string hex de 7 caracteres (#rrggbb)", () => {
    for (let i = 0; i < _curatedPalette.length + 5; i++) {
      const hex = paletteHex(i);
      expect(hex).toMatch(/^#[0-9a-f]{6}$/i);
    }
  });

  test("los primeros N índices usan la paleta curada exacta", () => {
    _curatedPalette.forEach(([r, g, b], i) => {
      const expected =
        "#" +
        r.toString(16).padStart(2, "0") +
        g.toString(16).padStart(2, "0") +
        b.toString(16).padStart(2, "0");
      expect(paletteHex(i)).toBe(expected);
    });
  });

  test("índices fuera de la paleta curada devuelven un hex válido (golden-angle)", () => {
    const beyond = _curatedPalette.length;
    expect(paletteHex(beyond)).toMatch(/^#[0-9a-f]{6}$/i);
    expect(paletteHex(beyond + 10)).toMatch(/^#[0-9a-f]{6}$/i);
  });

  test("dos índices distintos producen colores distintos", () => {
    expect(paletteHex(0)).not.toBe(paletteHex(1));
    expect(paletteHex(3)).not.toBe(paletteHex(7));
  });
});

// ─────────────────────────────────────────────
// buildColorArrays
// ─────────────────────────────────────────────
describe("buildColorArrays", () => {
  test("devuelve arrays bg y border de la longitud solicitada", () => {
    const { bg, border } = buildColorArrays(6);
    expect(bg).toHaveLength(6);
    expect(border).toHaveLength(6);
  });

  test("bg usa alpha 0.75; border usa alpha 1", () => {
    const { bg, border } = buildColorArrays(3);
    // Los primeros 20 índices son rgba(r,g,b,alpha); más allá son hsla
    expect(bg[0]).toMatch(/,0\.75\)$/);
    expect(border[0]).toMatch(/,1\)$/);
  });
});

// ─────────────────────────────────────────────
// buildCategoryRows — invariante central de color
// ─────────────────────────────────────────────
describe("buildCategoryRows", () => {
  // Datos de prueba: 6 categorías en orden de servidor (NO por valor)
  const labels = [
    "GASTOS ADMINISTRACION GRO", // origIdx 0 — valor más alto
    "EQUIPO COMPUTO", // origIdx 1
    "AGUINALDO", // origIdx 2
    "FLETES Y ACARREOS", // origIdx 3
    "GASOLINA / DIESEL", // origIdx 4
    "INTERNET - CAMARAS", // origIdx 5 — valor más bajo
  ];
  const data = [69, 12, 8, 2, 1, 1];

  const rows = buildCategoryRows(labels, data);

  test("incluye fila de encabezado más una fila por categoría", () => {
    expect(rows).toHaveLength(labels.length + 1);
  });

  test("cada fila de datos tiene 5 celdas (swatch, #, categoría, total, %)", () => {
    rows.slice(1).forEach((row) => {
      expect(row).toHaveLength(5);
    });
  });

  test("la tabla está ordenada de mayor a menor valor", () => {
    const totals = rows.slice(1).map((row) => {
      // El texto tiene formato "$69.00" → extraer número
      const raw = row[3].text.replace(/[$,]/g, "");
      return parseFloat(raw);
    });
    for (let i = 0; i < totals.length - 1; i++) {
      expect(totals[i]).toBeGreaterThanOrEqual(totals[i + 1]);
    }
  });

  /**
   * INVARIANTE PRINCIPAL:
   * El color del swatch (fillColor) en cada fila debe ser idéntico al color
   * que Chart.js asignaría a esa categoría según su índice ORIGINAL en el array
   * (es decir, paletteHex(origIdx)), NO según su posición en la tabla ordenada.
   *
   * Esto garantiza que el color de la celda en el PDF coincida con el color
   * del segmento en el gráfico de dona.
   */
  test("el swatch de cada fila coincide con paletteHex(origIdx) — no con el índice de la tabla", () => {
    // Construir el orden esperado: sorted desc por valor
    const sorted = labels
      .map((l, i) => ({ l, d: data[i], origIdx: i }))
      .sort((a, b) => b.d - a.d);

    sorted.forEach((item, tableIdx) => {
      const dataRow = rows[tableIdx + 1]; // +1 por encabezado
      const swatchCell = dataRow[0];
      const expectedHex = paletteHex(item.origIdx);
      expect(swatchCell.fillColor).toBe(expectedHex);
    });
  });

  test("el swatch NO usa el índice de la tabla ordenada (detecta la regresión original)", () => {
    // Si el bug original existiera (paletteHex(tableIdx) en lugar de paletteHex(origIdx)),
    // la primera fila (mayor valor = origIdx 0) coincidiría por casualidad,
    // pero la segunda fila fallaría porque EQUIPO COMPUTO (origIdx 1) está en
    // posición de tabla 1 → lo mismo; para detectar diferencia real usamos
    // una categoría cuyos origIdx y tableIdx nunca coincidan.
    //
    // Con los datos de prueba, FLETES Y ACARREOS (origIdx 3) ocupa tableIdx 3
    // en la tabla ordenada — pero con datos diferentes se movería.
    // Usamos un conjunto donde INTERNET - CAMARAS (origIdx 5) quede en tableIdx 2.
    const l2 = ["A", "B", "C", "D", "E", "F"];
    const d2 = [10, 1, 1, 1, 1, 100]; // F (origIdx 5) debe quedar en tableIdx 0
    const r2 = buildCategoryRows(l2, d2);
    // Primera fila de datos: F (origIdx 5)
    const firstDataRow = r2[1];
    expect(firstDataRow[0].fillColor).toBe(paletteHex(5)); // correcto: origIdx
    expect(firstDataRow[0].fillColor).not.toBe(paletteHex(0)); // bug: tableIdx 0
  });

  test("los porcentajes suman ~100%", () => {
    const pcts = rows.slice(1).map((row) => parseFloat(row[4].text));
    const sum = pcts.reduce((a, b) => a + b, 0);
    expect(sum).toBeCloseTo(100, 0);
  });

  test("el porcentaje de la categoría más grande es correcto", () => {
    // GASTOS ADMINISTRACION GRO = 69 de 93 total ≈ 74.2%
    const total = data.reduce((a, b) => a + b, 0);
    const expected = ((69 / total) * 100).toFixed(1) + "%";
    const firstRow = rows[1]; // mayor valor → primera fila
    expect(firstRow[4].text).toBe(expected);
  });

  test("maneja array vacío sin lanzar excepción", () => {
    const emptyRows = buildCategoryRows([], []);
    expect(emptyRows).toHaveLength(1); // solo encabezado
  });
});

// ─────────────────────────────────────────────
// hslToHex
// ─────────────────────────────────────────────
describe("hslToHex", () => {
  test("hsl(0,100,50) = rojo puro #ff0000", () => {
    expect(hslToHex(0, 100, 50)).toBe("#ff0000");
  });

  test("hsl(120,100,50) = verde puro #00ff00", () => {
    expect(hslToHex(120, 100, 50)).toBe("#00ff00");
  });

  test("hsl(240,100,50) = azul puro #0000ff", () => {
    expect(hslToHex(240, 100, 50)).toBe("#0000ff");
  });

  test("siempre devuelve un string hex de 7 caracteres", () => {
    for (let h = 0; h < 360; h += 30) {
      expect(hslToHex(h, 60, 50)).toMatch(/^#[0-9a-f]{6}$/i);
    }
  });
});
