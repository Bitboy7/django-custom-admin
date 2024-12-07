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
const brandText = document.querySelector('.brand-text');
if (brandText) {
  brandText.textContent = "";
}

// Cambia la imagen del elemento con la clase "image img"
const imgElement = document.querySelector('.image img');
if (imgElement) {
  imgElement.src = "/static/img/avatar.jpg";
}

// Agrega una imagen al menú desplegable con el id "jazzy-usermenu"
const dropdownMenu = document.getElementById('jazzy-usermenu');
if (dropdownMenu) {
  const imgElement = document.createElement("img");
  imgElement.src =
    "https://cdn-icons-png.freepik.com/256/9691/9691478.png?semt=ais_hybrid";
  imgElement.classList.add("dropdown-image");
  imgElement.style.height = "36px";
  imgElement.style.width = "36px";
  dropdownMenu.insertBefore(imgElement, dropdownMenu.firstChild);
}

// Cambia el texto del elemento con la clase "login-box-msg"
const loginBoxMsg = document.querySelector('.login-box-msg');
if (loginBoxMsg) {
  loginBoxMsg.textContent = "Bienvenido";
}

// Remueve el elemento del footer
const footerElement = document.querySelector('footer');
if (footerElement) {
  footerElement.remove();
}

// Cambia la opacidad del elemento con el id "jazzy-sidebar"
const jazzySidebar = document.getElementById('jazzy-sidebar');
if (jazzySidebar) {
  jazzySidebar.style.opacity = "0.85";
}

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
const cardBodyInputs = document.querySelectorAll(".card-body input");
cardBodyInputs.forEach((input) => {
  input.placeholder = "Ingresa un valor";
});


// Seleccionamos todos los elementos con la clase "field-fecha" en el documento HTML
const cantidadInput = document.querySelector(".form-group.field-cantidad input");
const precioUnitarioInput = document.querySelector(".form-group.field-precio_unitario input");
const montoTotalInput = document.querySelector(".form-group.field-monto_total input");

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

// Añade un botón dentro del elemento con el id "jazzy-navbar"
const jazzyNavbar = document.getElementById('jazzy-navbar');
if (jazzyNavbar) {
  const button = document.createElement("button");
  button.textContent = "Nuevo Botón";
  button.classList.add("btn", "btn-primary");
  jazzyNavbar.appendChild(button);
}