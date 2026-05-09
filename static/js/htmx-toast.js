/**
 * HTMX Toast Notifications
 * Sistema de notificaciones toast impulsado por eventos HTMX.
 * Escucha eventos personalizados disparados via HX-Trigger header.
 */
(function () {
  'use strict';

  var container = null;

  function ensureContainer() {
    if (container) return container;
    container = document.createElement('div');
    container.id = 'htmx-toast-container';
    container.setAttribute('aria-live', 'polite');
    container.setAttribute('aria-atomic', 'true');
    container.style.cssText =
      'position:fixed;top:1rem;right:1rem;z-index:9999;' +
      'display:flex;flex-direction:column;gap:0.5rem;' +
      'max-width:320px;width:100%;pointer-events:none;';
    document.body.appendChild(container);
    return container;
  }

  function createToast(data) {
    var type = data.type || 'info';
    var title = data.title || '';
    var message = data.message || '';
    var duration = data.duration || 4000;

    var colors = {
      success: { border: '#5a7d6b', bg: '#f0fdf4', icon: '#5a7d6b', iconClass: 'fa-check-circle' },
      error:   { border: '#b85450', bg: '#fef2f2', icon: '#b85450', iconClass: 'fa-times-circle' },
      warning: { border: '#c9a227', bg: '#fffbeb', icon: '#c9a227', iconClass: 'fa-exclamation-triangle' },
      info:    { border: '#586f7c', bg: 'rgba(184,219,217,.1)', icon: '#586f7c', iconClass: 'fa-info-circle' },
    };
    var c = colors[type] || colors.info;

    var toast = document.createElement('div');
    toast.style.cssText =
      'pointer-events:auto;background:#fff;border-left:4px solid ' + c.border + ';' +
      'border-radius:0.375rem;box-shadow:0 10px 15px -3px rgba(0,0,0,0.1),0 4px 6px -2px rgba(0,0,0,0.05);' +
      'padding:0.75rem 1rem;display:flex;align-items:flex-start;gap:0.75rem;' +
      'transform:translateX(120%);opacity:0;transition:transform 0.3s cubic-bezier(0.25,1,0.5,1),opacity 0.3s ease;';

    toast.innerHTML =
      '<div style="flex-shrink:0;width:1.5rem;height:1.5rem;border-radius:9999px;background:' + c.bg + ';' +
      'display:flex;align-items:center;justify-content:center;">' +
      '<i class="fas ' + c.iconClass + '" style="color:' + c.icon + ';font-size:0.75rem;"></i></div>' +
      '<div style="flex:1;min-width:0;">' +
      (title ? '<p style="margin:0;font-size:0.8125rem;font-weight:700;color:#2f4550;line-height:1.25;">' + escapeHtml(title) + '</p>' : '') +
      (message ? '<p style="margin:0.25rem 0 0;font-size:0.75rem;color:#586f7c;line-height:1.4;">' + escapeHtml(message) + '</p>' : '') +
      '</div>' +
      '<button style="flex-shrink:0;background:none;border:none;padding:0.125rem;cursor:pointer;color:#586f7c;' +
      'line-height:1;" aria-label="Cerrar notificaci&oacute;n"><i class="fas fa-times" style="font-size:0.625rem;"></i></button>';

    ensureContainer().appendChild(toast);

    // Trigger reflow
    void toast.offsetWidth;
    toast.style.transform = 'translateX(0)';
    toast.style.opacity = '1';

    var closeBtn = toast.querySelector('button');
    closeBtn.addEventListener('click', function () { dismiss(toast); });

    if (duration > 0) {
      setTimeout(function () { dismiss(toast); }, duration);
    }
  }

  function dismiss(toast) {
    if (!toast.parentNode) return;
    toast.style.transform = 'translateX(120%)';
    toast.style.opacity = '0';
    setTimeout(function () {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 300);
  }

  function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Listen for custom toast events fired by HX-Trigger header
  document.addEventListener('showToast', function (evt) {
    var detail = evt.detail || {};
    createToast(detail);
  });

  // Also listen for htmx events to show generic error toasts
  document.addEventListener('htmx:responseError', function (evt) {
    createToast({
      type: 'error',
      title: 'Error del servidor',
      message: 'Ocurri&oacute; un problema al procesar la solicitud. Intente de nuevo.'
    });
  });

  document.addEventListener('htmx:sendError', function (evt) {
    createToast({
      type: 'error',
      title: 'Error de conexi&oacute;n',
      message: 'No se pudo conectar con el servidor. Verifique su conexi&oacute;n.'
    });
  });

  // Global helper for manual toast invocation
  window.showHtmxToast = createToast;
})();
