(function () {
  'use strict';

  function initializePdfPreview() {
    var modal = document.getElementById('cfdi-pdf-modal');
    if (!modal) return;

    var dialog = modal.querySelector('.cfdi-pdf-modal__dialog');
    var closeButton = modal.querySelector('.cfdi-pdf-modal__close');
    var description = document.getElementById('cfdi-pdf-modal-description');
    var frame = document.getElementById('cfdi-pdf-frame');
    var loader = document.getElementById('cfdi-pdf-loader');
    var fallback = document.getElementById('cfdi-pdf-fallback');
    var openTab = document.getElementById('cfdi-pdf-open-tab');
    var fallbackLink = document.getElementById('cfdi-pdf-fallback-link');
    var previousFocus = null;
    var loadTimer = null;

    function focusableElements() {
      return Array.prototype.slice.call(
        dialog.querySelectorAll(
          'a[href]:not([hidden]), button:not([disabled]):not([hidden]), iframe:not([hidden]), [tabindex]:not([tabindex="-1"]):not([hidden])'
        )
      );
    }

    function showFallback() {
      loader.hidden = true;
      frame.hidden = true;
      fallback.hidden = false;
    }

    function openPreview(trigger) {
      var url = trigger.getAttribute('data-pdf-url');
      var title = trigger.getAttribute('data-pdf-title') || 'PDF del CFDI';
      if (!url) return;

      previousFocus = document.activeElement;
      description.textContent = title;
      openTab.href = url;
      fallbackLink.href = url;
      fallback.hidden = true;
      frame.hidden = true;
      loader.hidden = false;
      modal.hidden = false;
      modal.setAttribute('aria-hidden', 'false');
      document.body.classList.add('cfdi-pdf-modal-open');

      window.clearTimeout(loadTimer);
      loadTimer = window.setTimeout(showFallback, 15000);
      frame.onload = function () {
        window.clearTimeout(loadTimer);
        loader.hidden = true;
        fallback.hidden = true;
        frame.hidden = false;
      };
      frame.src = url;
      closeButton.focus();
    }

    function closePreview() {
      if (modal.hidden) return;

      window.clearTimeout(loadTimer);
      frame.onload = null;
      frame.src = 'about:blank';
      modal.hidden = true;
      modal.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('cfdi-pdf-modal-open');
      if (previousFocus && typeof previousFocus.focus === 'function') {
        previousFocus.focus();
      }
    }

    document.addEventListener('click', function (event) {
      var trigger = event.target.closest('.js-cfdi-pdf-preview');
      if (trigger) {
        event.preventDefault();
        openPreview(trigger);
        return;
      }

      if (event.target.closest('[data-pdf-close]')) {
        event.preventDefault();
        closePreview();
      }
    });

    document.addEventListener('keydown', function (event) {
      if (modal.hidden) return;

      if (event.key === 'Escape') {
        event.preventDefault();
        closePreview();
        return;
      }

      if (event.key !== 'Tab') return;
      var items = focusableElements();
      if (!items.length) {
        event.preventDefault();
        dialog.focus();
        return;
      }

      var first = items[0];
      var last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializePdfPreview);
  } else {
    initializePdfPreview();
  }
})();
