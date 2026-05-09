/**
 * Vista previa de comprobantes de pago con modal accesible
 * Soporta imágenes y PDFs con navegación por teclado
 */

(function () {
  "use strict";

  // Crear modal al cargar la página
  function createModal() {
    if (document.getElementById("comprobante-modal")) {
      return; // Ya existe
    }

    const modal = document.createElement("div");
    modal.id = "comprobante-modal";
    modal.className = "comprobante-modal";
    modal.setAttribute("role", "dialog");
    modal.setAttribute("aria-modal", "true");
    modal.setAttribute("aria-labelledby", "modal-title");
    modal.innerHTML = `
            <div class="comprobante-modal-backdrop" aria-hidden="true"></div>
            <div class="comprobante-modal-content">
                <div class="comprobante-modal-header">
                    <h2 id="modal-title">Comprobante de Pago</h2>
                    <button type="button" class="comprobante-modal-close" 
                            aria-label="Cerrar vista previa" title="Cerrar (Esc)">
                        <span aria-hidden="true">×</span>
                    </button>
                </div>
                <div class="comprobante-modal-body">
                    <div class="comprobante-loading">
                        <div class="spinner"></div>
                        <p>Cargando comprobante...</p>
                    </div>
                    <div class="comprobante-content"></div>
                </div>
                <div class="comprobante-modal-footer">
                    <a href="#" target="_blank" class="btn-download" download>
                        📥 Descargar
                    </a>
                    <a href="#" target="_blank" class="btn-open-new">
                        🔗 Abrir en nueva pestaña
                    </a>
                </div>
            </div>
        `;

    document.body.appendChild(modal);

    // Event listeners
    const closeBtn = modal.querySelector(".comprobante-modal-close");
    const backdrop = modal.querySelector(".comprobante-modal-backdrop");

    closeBtn.addEventListener("click", closeModal);
    backdrop.addEventListener("click", closeModal);

    // ESC key para cerrar
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && modal.classList.contains("active")) {
        closeModal();
      }
    });
  }

  // Abrir modal con comprobante
  window.previewComprobante = function (event, element) {
    event.preventDefault();

    const fileUrl = element.dataset.fileUrl;
    const fileType = element.dataset.fileType;

    if (!fileUrl) {
      console.error("No se encontró URL del archivo");
      return false;
    }

    const modal = document.getElementById("comprobante-modal");
    const content = modal.querySelector(".comprobante-content");
    const loading = modal.querySelector(".comprobante-loading");
    const downloadBtn = modal.querySelector(".btn-download");
    const openBtn = modal.querySelector(".btn-open-new");

    // Configurar botones
    downloadBtn.href = fileUrl;
    openBtn.href = fileUrl;

    // Limpiar contenido previo
    content.innerHTML = "";
    loading.style.display = "block";

    // Mostrar modal
    modal.classList.add("active");
    document.body.style.overflow = "hidden";

    // Focus en el botón de cerrar para accesibilidad
    setTimeout(() => {
      modal.querySelector(".comprobante-modal-close").focus();
    }, 100);

    // Cargar contenido según tipo
    if (fileType === "imagen") {
      const img = new Image();

      img.onload = function () {
        loading.style.display = "none";
        content.innerHTML = `
                    <img src="${fileUrl}" 
                         alt="Comprobante de pago" 
                         class="comprobante-image"
                         tabindex="0" />
                `;
      };

      img.onerror = function () {
        loading.style.display = "none";
        content.innerHTML = `
                    <div class="comprobante-error">
                        <p>❌ Error al cargar la imagen</p>
                        <a href="${fileUrl}" target="_blank" class="btn-fallback">
                            Abrir en nueva pestaña
                        </a>
                    </div>
                `;
      };

      img.src = fileUrl;
    } else if (fileType === "pdf") {
      // Para PDFs, mostrar directamente el fallback con iframe opcional
      loading.style.display = "none";
      content.innerHTML = `
                <div class="comprobante-pdf">
                    <div class="pdf-notice">
                        <p style="text-align:center; margin-bottom:16px; color:#586f7c; font-weight:500;">
                            📄 Comprobante PDF disponible
                        </p>
                        <div style="display:flex; gap:12px; justify-content:center; margin-bottom:16px; flex-wrap:wrap;">
                            <a href="${fileUrl}" target="_blank" class="btn-pdf-primary">
                                📄 Abrir en nueva pestaña
                            </a>
                            <button onclick="loadPDFInline(this, '${fileUrl}')" class="btn-pdf-secondary">
                                👁️ Ver aquí (vista previa)
                            </button>
                        </div>
                    </div>
                    <div id="pdf-inline-container" style="display:none; width:100%; height:550px;">
                        <iframe src="${fileUrl}#view=FitH" 
                               class="pdf-viewer"
                               style="width:100%; height:100%; border:2px solid #d8dce6; border-radius:8px;"
                               frameborder="0"
                               aria-label="Visor de PDF del comprobante">
                        </iframe>
                    </div>
                </div>
            `;
    } else {
      loading.style.display = "none";
      content.innerHTML = `
                <div class="comprobante-generic">
                    <div class="file-icon">📎</div>
                    <p>Este tipo de archivo no se puede previsualizar</p>
                    <a href="${fileUrl}" target="_blank" class="btn-fallback">
                        Descargar archivo
                    </a>
                </div>
            `;
    }

    return false;
  };

  // Cerrar modal
  function closeModal() {
    const modal = document.getElementById("comprobante-modal");
    modal.classList.remove("active");
    document.body.style.overflow = "";
  }

  // Cargar PDF inline (función global para onclick)
  window.loadPDFInline = function (button, url) {
    const container = document.getElementById("pdf-inline-container");
    const notice = button.closest(".pdf-notice");

    if (container) {
      container.style.display = "block";
      notice.style.display = "none";

      // Opcional: recargar iframe para asegurar que se cargue
      const iframe = container.querySelector("iframe");
      if (iframe) {
        iframe.src = iframe.src; // Force reload
      }
    }
  };

  // Inicializar cuando el DOM esté listo
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", createModal);
  } else {
    createModal();
  }
})();
