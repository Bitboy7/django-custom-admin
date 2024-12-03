<<<<<<< HEAD
/*!
 * Start Bootstrap - SB Admin v7.0.5 (https://startbootstrap.com/template/sb-admin)
 * Copyright 2013-2022 Start Bootstrap
 * Licensed under MIT (https://github.com/StartBootstrap/startbootstrap-sb-admin/blob/master/LICENSE)
 */
//
=======
     /*!
    * Start Bootstrap - SB Admin v7.0.5 (https://startbootstrap.com/template/sb-admin)
    * Copyright 2013-2022 Start Bootstrap
    * Licensed under MIT (https://github.com/StartBootstrap/startbootstrap-sb-admin/blob/master/LICENSE)
    */
    // 
>>>>>>> e36d22bf634f764dffac4100fb5b4d24b0dd40b7
// Scripts
//

window.addEventListener("DOMContentLoaded", (event) => {
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

window.addEventListener("DOMContentLoaded", (event) => {
  // Simple-DataTables
  // https://github.com/fiduswriter/Simple-DataTables/wiki

  const datatablesSimple = document.getElementById("datatablesSimple");
  if (datatablesSimple) {
    new simpleDatatables.DataTable(datatablesSimple);
  }
});

<<<<<<< HEAD
// Remove the text from the element with class "brand-text"
const brandText = document.querySelector(".brand-text");
=======
// Remueve el texto del elemento con la clase "brand-text"
const brandText = document.querySelector('.brand-text');
>>>>>>> e36d22bf634f764dffac4100fb5b4d24b0dd40b7
if (brandText) {
  brandText.textContent = "";
}

<<<<<<< HEAD
const imgElement = document.querySelector(".image img");
=======
// Cambia la imagen del elemento con la clase "image img"
const imgElement = document.querySelector('.image img');
>>>>>>> e36d22bf634f764dffac4100fb5b4d24b0dd40b7
if (imgElement) {
  imgElement.src = "/static/img/avatar.jpg";
}

<<<<<<< HEAD
const dropdownMenu = document.getElementById("jazzy-usermenu");
=======
// Agrega una imagen al menú desplegable con el id "jazzy-usermenu"
const dropdownMenu = document.getElementById('jazzy-usermenu');
>>>>>>> e36d22bf634f764dffac4100fb5b4d24b0dd40b7
if (dropdownMenu) {
  const imgElement = document.createElement("img");
  imgElement.src =
    "https://cdn-icons-png.freepik.com/256/9691/9691478.png?semt=ais_hybrid";
  imgElement.classList.add("dropdown-image");
  imgElement.style.height = "36px";
  imgElement.style.width = "36px";
  dropdownMenu.insertBefore(imgElement, dropdownMenu.firstChild);
}

<<<<<<< HEAD
const loginBoxMsg = document.querySelector(".login-box-msg");
=======
// Cambia el texto del elemento con la clase "login-box-msg"
const loginBoxMsg = document.querySelector('.login-box-msg');
>>>>>>> e36d22bf634f764dffac4100fb5b4d24b0dd40b7
if (loginBoxMsg) {
  loginBoxMsg.textContent = "Bienvenido";
}

<<<<<<< HEAD
const footerElement = document.querySelector("footer");
=======
// Remueve el elemento del footer
const footerElement = document.querySelector('footer');
>>>>>>> e36d22bf634f764dffac4100fb5b4d24b0dd40b7
if (footerElement) {
  footerElement.remove();
}

<<<<<<< HEAD
const jazzySidebar = document.getElementById("jazzy-sidebar");
=======
// Cambia la opacidad del elemento con el id "jazzy-sidebar"
const jazzySidebar = document.getElementById('jazzy-sidebar');
>>>>>>> e36d22bf634f764dffac4100fb5b4d24b0dd40b7
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

const cardBodyInputs = document.querySelectorAll(".card-body input");
cardBodyInputs.forEach((input) => {
  input.placeholder = "placeholder";
});
