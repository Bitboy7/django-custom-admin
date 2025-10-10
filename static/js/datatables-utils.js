/**
 * DataTables Utils - Utilidades reutilizables para configuración de DataTables
 *
 * Este archivo contiene funciones genéricas para trabajar con DataTables
 * que pueden ser reutilizadas en diferentes módulos (gastos, compras, ventas, etc.)
 *
 * @author Sistema de Gestión
 * @version 1.0.0
 */

// ============================================================================
// FUNCIONES DE EXTRACCIÓN Y FORMATEO DE DATOS
// ============================================================================

/**
 * Extrae texto limpio de contenido HTML
 * Útil para extraer valores de celdas que contienen HTML
 *
 * @param {string} htmlContent - Contenido HTML a limpiar
 * @returns {string} Texto limpio sin etiquetas HTML
 */
function getCleanTextFromHTML(htmlContent) {
  if (!htmlContent) return "";

  // Si ya es texto plano, devolverlo
  if (typeof htmlContent === "string" && !htmlContent.includes("<")) {
    return htmlContent.trim();
  }

  var tempDiv = document.createElement("div");
  tempDiv.innerHTML = htmlContent;

  // Extraer solo el texto de elementos específicos o todo el texto
  var text = tempDiv.textContent || tempDiv.innerText || "";

  // Limpiar caracteres especiales de formato
  text = text
    .replace(/[\n\r\t]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  return text;
}

/**
 * Obtiene un valor numérico desde un nodo (TD) soportando múltiples formatos
 * Formatos soportados: "1,234.56", "1.234,56", "$ 1,234.56", "MXN 1.234,56", "720 749.86", etc.
 *
 * @param {HTMLElement} node - Nodo del DOM (típicamente una celda TD)
 * @returns {number} Valor numérico extraído o NaN si no se puede convertir
 */
function getNumericValueFromNode(node) {
  if (!node) return NaN;
  var dataOrder = node.getAttribute && node.getAttribute("data-order");
  if (dataOrder != null && dataOrder !== "") {
    var parsed = parseFloat(dataOrder);
    if (!isNaN(parsed)) return parsed;
  }

  var text = getCleanTextFromHTML(node.innerHTML || node.innerText || "");
  return parseNumericString(text);
}

/**
 * Parsea una cadena numérica con diferentes formatos
 *
 * @param {string} text - Texto a parsear
 * @returns {number} Valor numérico o NaN
 */
function parseNumericString(text) {
  if (!text || text === "") return NaN;

  // Quitar símbolos de moneda y espacios
  text = text.replace(/[$€£¥₹₽MXN USD EUR GBP\s]/gi, "").trim();

  // Detectar formato: si tiene punto antes de la última coma => formato europeo (1.234,56)
  var lastComma = text.lastIndexOf(",");
  var lastDot = text.lastIndexOf(".");

  var cleaned;
  if (lastComma > lastDot) {
    // Formato europeo: 1.234,56 -> quitar puntos, reemplazar coma por punto
    cleaned = text.replace(/\./g, "").replace(/,/g, ".");
  } else {
    // Formato americano: 1,234.56 -> quitar comas
    cleaned = text.replace(/,/g, "");
  }

  var parsed = parseFloat(cleaned);
  return isNaN(parsed) ? NaN : parsed;
}

/**
 * Formatea un valor numérico con separadores de miles y decimales
 *
 * @param {number} value - Valor numérico a formatear
 * @param {number} decimals - Número de decimales (por defecto 2)
 * @param {string} decimalSep - Separador decimal (por defecto '.')
 * @param {string} thousandsSep - Separador de miles (por defecto ',')
 * @returns {string} Valor formateado
 */
function formatNumericValue(value, decimals, decimalSep, thousandsSep) {
  decimals = typeof decimals !== "undefined" ? decimals : 2;
  decimalSep = typeof decimalSep !== "undefined" ? decimalSep : ".";
  thousandsSep = typeof thousandsSep !== "undefined" ? thousandsSep : ",";

  if (isNaN(value) || value === null) return "0.00";

  var fixedValue = parseFloat(value).toFixed(decimals);
  var parts = fixedValue.split(".");
  var integerPart = parts[0];
  var decimalPart = parts.length > 1 ? parts[1] : "";

  // Agregar separadores de miles
  integerPart = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, thousandsSep);

  return integerPart + (decimalPart ? decimalSep + decimalPart : "");
}

// ============================================================================
// FUNCIONES DE FECHA Y HORA
// ============================================================================

/**
 * Obtiene la fecha y hora actual en formato legible
 *
 * @param {string} format - Formato deseado: 'datetime' (por defecto), 'date', 'time'
 * @returns {string} Fecha formateada
 */
function getCurrentDateFormatted(format) {
  format = format || "datetime";
  var now = new Date();
  var day = String(now.getDate()).padStart(2, "0");
  var month = String(now.getMonth() + 1).padStart(2, "0");
  var year = now.getFullYear();
  var hours = String(now.getHours()).padStart(2, "0");
  var minutes = String(now.getMinutes()).padStart(2, "0");
  var seconds = String(now.getSeconds()).padStart(2, "0");

  switch (format) {
    case "date":
      return day + "/" + month + "/" + year;
    case "time":
      return hours + ":" + minutes;
    case "datetime":
      return day + "/" + month + "/" + year + " " + hours + ":" + minutes;
    case "filename":
      return (
        year +
        "-" +
        month +
        "-" +
        day +
        "-" +
        hours +
        "-" +
        minutes +
        "-" +
        seconds
      );
    default:
      return day + "/" + month + "/" + year + " " + hours + ":" + minutes;
  }
}

/**
 * Obtiene el nombre del mes según su índice
 *
 * @param {number} monthIndex - Índice del mes (1-12)
 * @param {string} lang - Idioma ('es', 'en')
 * @returns {string} Nombre del mes
 */
function getMonthName(monthIndex, lang) {
  lang = lang || "es";
  var monthNames = {
    es: [
      "Enero",
      "Febrero",
      "Marzo",
      "Abril",
      "Mayo",
      "Junio",
      "Julio",
      "Agosto",
      "Septiembre",
      "Octubre",
      "Noviembre",
      "Diciembre",
    ],
    en: [
      "January",
      "February",
      "March",
      "April",
      "May",
      "June",
      "July",
      "August",
      "September",
      "October",
      "November",
      "December",
    ],
  };

  var index = parseInt(monthIndex) - 1;
  if (index >= 0 && index < 12) {
    return monthNames[lang][index];
  }
  return "";
}

// ============================================================================
// FUNCIONES PARA GENERAR TÍTULOS DE REPORTES
// ============================================================================

/**
 * Genera el título de un reporte basado en los filtros de la URL
 * Esta es una función genérica que puede ser personalizada por módulo
 *
 * @param {object} config - Configuración del reporte
 * @param {string} config.moduleName - Nombre del módulo (ej: "Gastos", "Compras", "Ventas")
 * @param {array} config.filterFields - Array de campos a incluir en el título
 * @returns {string} Título del reporte
 */
function generateReportTitle(config) {
  var urlParams = new URLSearchParams(window.location.search);
  var titleParts = [];
  var moduleName = config.moduleName || "Reporte";

  // Filtros comunes
  var filters = {
    cuenta_id: { label: "Cuenta", elementId: "cuenta_id" },
    sucursal_id: { label: "Sucursal", elementId: "sucursal_id" },
    proveedor_id: { label: "Proveedor", elementId: "proveedor_id" },
    cliente_id: { label: "Cliente", elementId: "cliente_id" },
    year: { label: "Año", elementId: null },
    month: { label: "Mes", elementId: "month", isMonth: true },
    periodo: {
      label: "Período",
      elementId: null,
      mapping: { diario: "Diario", semanal: "Semanal", mensual: "Mensual" },
    },
  };

  // Procesar filtros según configuración
  var filterFields = config.filterFields || Object.keys(filters);

  filterFields.forEach(function (fieldName) {
    var filterConfig = filters[fieldName];
    if (!filterConfig) return;

    var value = urlParams.get(fieldName);
    if (!value || value.trim() === "") return;

    // Caso especial: mes
    if (filterConfig.isMonth) {
      var monthName = getMonthName(value);
      if (monthName) {
        titleParts.push(filterConfig.label + ": " + monthName);
      }
      return;
    }

    // Caso especial: mapeo de valores
    if (filterConfig.mapping) {
      var mappedValue = filterConfig.mapping[value] || value;
      titleParts.push(filterConfig.label + ": " + mappedValue);
      return;
    }

    // Caso general: obtener valor de select
    if (filterConfig.elementId) {
      var element = document.getElementById(filterConfig.elementId);
      if (
        element &&
        element.tagName === "SELECT" &&
        element.selectedIndex >= 0
      ) {
        var selectedOption = element.options[element.selectedIndex];
        if (
          selectedOption &&
          selectedOption.text !== "Todas" &&
          selectedOption.text !== "Todos"
        ) {
          titleParts.push(filterConfig.label + ": " + selectedOption.text);
        }
      }
    } else {
      // Si no hay elemento, usar el valor directamente
      titleParts.push(filterConfig.label + ": " + value);
    }
  });

  // Agregar indicador de "todos los meses" si aplica
  var year = urlParams.get("year");
  var month = urlParams.get("month");
  if (
    year &&
    year.trim() !== "" &&
    (!month || month.trim() === "") &&
    filterFields.includes("month")
  ) {
    titleParts.push("Período: Todos los meses");
  }

  // Construir título completo
  if (titleParts.length > 0) {
    return moduleName + " - " + titleParts.join(" | ");
  } else {
    return moduleName + " - General";
  }
}

// ============================================================================
// FUNCIONES PARA PERSONALIZACIÓN DE PDF
// ============================================================================

/**
 * Configura el encabezado estándar para PDFs
 *
 * @param {string} reportTitle - Título del reporte
 * @param {string} currentDate - Fecha actual formateada
 * @returns {object} Configuración del encabezado para pdfMake
 */
function createPdfHeader(reportTitle, currentDate) {
  return function (currentPage, pageCount) {
    return {
      stack: [
        {
          text: reportTitle,
          style: "header",
          alignment: "center",
          margin: [0, 30, 0, 5],
        },
        {
          text: "Fecha de generación: " + currentDate,
          style: "subheader",
          alignment: "center",
        },
      ],
      margin: [40, 20, 40, 0],
    };
  };
}

/**
 * Configura el pie de página estándar para PDFs
 *
 * @param {string} systemName - Nombre del sistema (ej: "Sistema de Gestión de Gastos")
 * @returns {object} Configuración del pie de página para pdfMake
 */
function createPdfFooter(systemName) {
  systemName = systemName || "Sistema de Gestión";

  return function (currentPage, pageCount) {
    return {
      columns: [
        {
          text: systemName,
          alignment: "left",
          style: "footer",
          margin: [40, 0, 0, 0],
        },
        {
          text: "Página " + currentPage.toString() + " de " + pageCount,
          alignment: "right",
          style: "footer",
          margin: [0, 0, 40, 0],
        },
      ],
      margin: [0, 10, 0, 0],
    };
  };
}

/**
 * Obtiene los estilos estándar para PDFs
 *
 * @returns {object} Objeto con estilos para pdfMake
 */
function getPdfStyles() {
  return {
    header: {
      fontSize: 18,
      bold: true,
      color: "#2c3e50",
    },
    subheader: {
      fontSize: 11,
      color: "#7f8c8d",
      italics: true,
    },
    tableHeader: {
      bold: true,
      fontSize: 11,
      color: "white",
      fillColor: "#34495e",
      alignment: "center",
    },
    footer: {
      fontSize: 9,
      color: "#95a5a6",
    },
  };
}

/**
 * Configura un documento PDF con opciones estándar
 *
 * @param {object} doc - Documento pdfMake a configurar
 * @param {object} options - Opciones de configuración
 * @param {string} options.reportTitle - Título del reporte
 * @param {string} options.systemName - Nombre del sistema
 * @param {string} options.orientation - Orientación ('landscape' o 'portrait')
 * @param {array} options.pageMargins - Márgenes [left, top, right, bottom]
 */
function configurePdfDocument(doc, options) {
  options = options || {};

  var reportTitle = options.reportTitle || "Reporte";
  var systemName = options.systemName || "Sistema de Gestión";
  var orientation = options.orientation || "landscape";
  var pageMargins = options.pageMargins || [40, 80, 40, 60];

  var currentDate = getCurrentDateFormatted("datetime");

  // Configurar documento
  doc.pageOrientation = orientation;
  doc.pageMargins = pageMargins;

  // Configurar encabezado
  doc.header = createPdfHeader(reportTitle, currentDate);

  // Configurar pie de página
  doc.footer = createPdfFooter(systemName);

  // Configurar estilos
  doc.styles = getPdfStyles();

  return doc;
}

// ============================================================================
// FUNCIONES PARA EXPORTACIÓN CSV
// ============================================================================

/**
 * Genera y descarga un archivo CSV desde datos de DataTable
 *
 * @param {object} config - Configuración para la exportación
 * @param {string} config.filename - Nombre base del archivo (sin extensión)
 * @param {array} config.headers - Array de encabezados
 * @param {array} config.data - Array de arrays con los datos
 * @param {string} config.separator - Separador (por defecto ',')
 */
function exportToCSV(config) {
  var separator = config.separator || ",";
  var csvData = "";

  // Agregar encabezados
  if (config.headers && config.headers.length > 0) {
    csvData +=
      config.headers
        .map(function (h) {
          return '"' + h + '"';
        })
        .join(separator) + "\n";
  }

  // Agregar datos
  if (config.data && config.data.length > 0) {
    config.data.forEach(function (row) {
      csvData +=
        row
          .map(function (cell) {
            // Manejar valores numéricos y texto
            if (typeof cell === "number") {
              return cell.toFixed(2);
            }
            return '"' + (cell || "").toString().replace(/"/g, '""') + '"';
          })
          .join(separator) + "\n";
    });
  }

  // Crear y descargar el archivo
  var filename = config.filename || "export";
  var timestamp = getCurrentDateFormatted("filename");
  var fullFilename = filename + "-" + timestamp + ".csv";

  var blob = new Blob([csvData], { type: "text/csv;charset=utf-8;" });
  var link = document.createElement("a");
  var url = URL.createObjectURL(blob);
  link.setAttribute("href", url);
  link.setAttribute("download", fullFilename);
  link.style.visibility = "hidden";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// ============================================================================
// EXPORT (para uso en módulos ES6 si es necesario)
// ============================================================================

// Si estás usando módulos ES6, puedes descomentar esto:
// export {
//   getCleanTextFromHTML,
//   getNumericValueFromNode,
//   parseNumericString,
//   formatNumericValue,
//   getCurrentDateFormatted,
//   getMonthName,
//   generateReportTitle,
//   createPdfHeader,
//   createPdfFooter,
//   getPdfStyles,
//   configurePdfDocument,
//   exportToCSV
// };
