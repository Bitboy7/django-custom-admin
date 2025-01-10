/*!
 * Start Bootstrap - SB Admin v7.0.5 (https://startbootstrap.com/template/sb-admin)
 * Copyright 2013-2022 Start Bootstrap
 * Licensed under MIT (https://github.com/StartBootstrap/startbootstrap-sb-admin/blob/master/LICENSE)
 */
//
// Scripts
//

window.addEventListener("DOMContentLoaded", () => {
  // Toggle the side navigation
  const sidebarToggle = document.body.querySelector("#sidebarToggle");
  if (sidebarToggle) {
    // Uncomment Below to persist sidebar toggle between refreshes
    // if (localStorage.getItem('sb|sidebar-toggle') === 'true') {
    //     document.body.classList.toggle('sb-sidenav-toggled');
    // }
    sidebarToggle.addEventListener("click", (event) => {
      event.preventDefault();
      document.body.classList.toggle("sb-sidenav-toggled");
      localStorage.setItem(
        "sb|sidebar-toggle",
        document.body.classList.contains("sb-sidenav-toggled")
      );
    });
  }
});

window.addEventListener("DOMContentLoaded", () => {
  // Simple-DataTables
  // https://github.com/fiduswriter/Simple-DataTables/wiki

  const datatablesSimple = document.getElementById("datatablesSimple");
  if (datatablesSimple) {
    new simpleDatatables.DataTable(datatablesSimple);
  }
});

// Remove the text from the element with class "brand-text"
const brandText = document.querySelector(".brand-text");
if (brandText) {
  brandText.textContent = "";
}

// Cambia la imagen del elemento con la clase "image img"
const imgElement = document.querySelector(".image img");
if (imgElement) {
  imgElement.src = "/static/img/avatar-female.png";
}

// Agrega una imagen al menú desplegable con el id "jazzy-usermenu"
const dropdownMenu = document.getElementById("jazzy-usermenu");
if (dropdownMenu) {
  const imgElement = document.createElement("img");
  imgElement.src =
    "https://cdn-icons-png.freepik.com/256/9691/9691478.png?semt=ais_hybrid";
  imgElement.classList.add("dropdown-image");
  imgElement.style.height = "72px"; // Aumenta el tamaño de la imagen
  imgElement.style.width = "72px"; // Aumenta el tamaño de la imagen
  imgElement.style.display = "block";
  imgElement.style.margin = "0 auto"; // Centra la imagen
  dropdownMenu.insertBefore(imgElement, dropdownMenu.firstChild);
}

// Cambia el texto del elemento con la clase "login-box-msg"
const loginBoxMsg = document.querySelector(".login-box-msg");
if (loginBoxMsg) {
  loginBoxMsg.textContent = "Bienvenido";
}

// Remueve el elemento del footer
const footerElement = document.querySelector("footer");
if (footerElement) {
  footerElement.remove();
}

// Cambia la opacidad del elemento con el id "jazzy-sidebar"
const jazzySidebar = document.getElementById("jazzy-sidebar");
if (jazzySidebar) {
  jazzySidebar.style.opacity = "0.85";
}

// Add placeholders to vTextField inputs
const vTextFields = document.querySelectorAll(".vTextField");
vTextFields.forEach((input) => {
  const label = input.closest(".form-group").querySelector("label");
  if (label) {
    input.placeholder = label.textContent.trim();
  }
});

// Seleccionamos todas las tablas en el documento HTML
const tablas = document.getElementsByTagName("table");

// Recorremos cada tabla
for (let i = 0; i < tablas.length; i++) {
  // Obtenemos los elementos con la clase "field-monto" dentro de cada tabla
  const camposMonto = tablas[i].querySelectorAll(".field-monto");

  // Recorremos cada elemento y le agregamos el formato de moneda
  camposMonto.forEach((campo) => {
    // Obtenemos el valor actual del campo como un número flotante
    let valor = parseFloat(campo.textContent);

    // Formateamos el valor con el símbolo de moneda y sin redondeo
    let valorConFormato = new Intl.NumberFormat("es-ES", {
      style: "currency",
      currency: "MXN",
      maximumFractionDigits: 16,
    }).format(valor);

    // Actualizamos el contenido del campo con el valor formateado
    campo.textContent = valorConFormato;
  });
}

// Seleccionamos todos los elementos con la clase "field-fecha" en el documento HTML
const cantidadInput = document.querySelector(
  ".form-group.field-cantidad input"
);
const precioUnitarioInput = document.querySelector(
  ".form-group.field-precio_unitario input"
);
const montoTotalInput = document.querySelector(
  ".form-group.field-monto_total input"
);

if (cantidadInput && precioUnitarioInput && montoTotalInput) {
  const updateMontoTotal = () => {
    const cantidad = parseFloat(cantidadInput.value) || 0;
    const precioUnitario = parseFloat(precioUnitarioInput.value) || 0;
    const montoTotal = cantidad * precioUnitario;
    montoTotalInput.value = montoTotal.toFixed(2);
  };

  cantidadInput.addEventListener("input", updateMontoTotal);
  precioUnitarioInput.addEventListener("input", updateMontoTotal);
}

updateMontoTotal();

if (tablas.length > 0) {
  // Obtener todos los elementos con la clase field-monto de esta tabla
  const montos = tablas[0].querySelectorAll(".field-monto");
  let sumaTotal = 0;

  // Sumar los montos
  montos.forEach((monto) => {
    // Limpiar el texto de símbolos de moneda y comas
    const valor = parseFloat(monto.textContent.replace(/[^0-9.-]+/g, ""));
    if (!isNaN(valor)) {
      sumaTotal += valor;
    }
  });

  // Crear una nueva fila para el total
  const nuevaFila = tabla_monto_suma[0].insertRow(-1);
  const celdaTotal = nuevaFila.insertCell(0);
  celdaTotal.colSpan = tabla_monto_suma[0].rows[0].cells.length;
  celdaTotal.style.textAlign = "right";
  celdaTotal.style.fontWeight = "bold";

  // Formatear y mostrar el total
  const totalFormateado = new Intl.NumberFormat("es-ES", {
    style: "currency",
    currency: "MXN",
  }).format(sumaTotal);

  celdaTotal.textContent = `Total: ${totalFormateado}`;
}

// Resalta el cursor sobre los elementos tipo <a/> y cambia el color del texto
const anchorElements = document.querySelectorAll("a");
anchorElements.forEach((anchor) => {
  anchor.addEventListener("mouseover", () => {
    anchor.style.cursor = "pointer";
    anchor.style.color = "red"; // Cambia el color del texto a rojo
  });
  anchor.addEventListener("mouseout", () => {
    anchor.style.color = ""; // Restaura el color original del texto
  });
});

// Elimina todos los elementos <li> con la clase "nav-header" y el texto "Gastos"
const navHeaders = document.querySelectorAll("li.nav-header");
navHeaders.forEach((header) => {
  if (header.textContent.trim() === "Gastos") {
    header.remove();
  }
});
