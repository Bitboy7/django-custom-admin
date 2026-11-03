/*
 * Conciliación de CFDI — popovers de documentos sin vincular y origen de cobros.
 *
 * Popover accesible (ratón + teclado) con posicionamiento fijo para que
 * el scroll horizontal/vertical de la tabla nunca lo recorte. El panel vive
 * junto a su disparador en el DOM, pero se posiciona respecto al viewport.
 */
(function () {
  'use strict';

  function init() {
    var triggers = document.querySelectorAll('[data-conc-trigger]');
    if (!triggers.length) {
      return;
    }

    var active = null;
    var hideTimer = null;

    function panelFor(trigger) {
      var id = trigger.getAttribute('aria-controls');
      return id ? document.getElementById(id) : null;
    }

    function position(trigger, panel) {
      var gap = 8;
      var rect = trigger.getBoundingClientRect();
      var width = panel.offsetWidth;
      var height = panel.offsetHeight;

      var top = rect.bottom + gap;
      if (top + height > window.innerHeight - gap) {
        top = Math.max(gap, rect.top - gap - height);
      }

      var left = rect.right - width;
      left = Math.min(Math.max(gap, left), window.innerWidth - width - gap);

      panel.style.top = top + 'px';
      panel.style.left = left + 'px';
    }

    function open(trigger) {
      var panel = panelFor(trigger);
      if (!panel) {
        return;
      }
      window.clearTimeout(hideTimer);
      if (active && active !== trigger) {
        close(active);
      }
      active = trigger;
      trigger.setAttribute('aria-expanded', 'true');
      panel.hidden = false;
      position(trigger, panel);
    }

    function close(trigger) {
      var panel = panelFor(trigger);
      if (!panel) {
        return;
      }
      trigger.setAttribute('aria-expanded', 'false');
      panel.hidden = true;
      if (active === trigger) {
        active = null;
      }
    }

    function scheduleClose(trigger) {
      var panel = panelFor(trigger);
      window.clearTimeout(hideTimer);
      hideTimer = window.setTimeout(function () {
        var overPanel = panel && panel.matches(':hover');
        var focused = document.activeElement === trigger || (panel && panel.contains(document.activeElement));
        if (!overPanel && !focused) {
          close(trigger);
        }
      }, 140);
    }

    triggers.forEach(function (trigger) {
      var panel = panelFor(trigger);
      if (!panel) {
        return;
      }

      trigger.addEventListener('mouseenter', function () { open(trigger); });
      trigger.addEventListener('mouseleave', function () { scheduleClose(trigger); });
      trigger.addEventListener('focus', function () { open(trigger); });
      trigger.addEventListener('blur', function () { scheduleClose(trigger); });
      trigger.addEventListener('click', function (event) {
        event.preventDefault();
        if (active === trigger) {
          close(trigger);
        } else {
          open(trigger);
        }
      });

      panel.addEventListener('mouseenter', function () { window.clearTimeout(hideTimer); });
      panel.addEventListener('mouseleave', function () { scheduleClose(trigger); });
      panel.addEventListener('focusout', function () { scheduleClose(trigger); });

      // Mantener el panel alineado mientras el viewport cambia.
      panel.addEventListener('scroll', function () {
        if (active === trigger) {
          position(trigger, panel);
        }
      });
    });

    document.querySelectorAll('[data-conc-origin-filter]').forEach(function (select) {
      var panel = select.closest('.conc-pop');
      if (!panel) {
        return;
      }

      var items = Array.prototype.slice.call(
        panel.querySelectorAll('[data-conc-origin-item]')
      );
      var summary = panel.querySelector('[data-conc-origin-summary]');
      var emptyState = panel.querySelector('[data-conc-origin-empty]');
      var total = summary ? Number(summary.dataset.total || 0) : 0;
      var currency = summary ? summary.dataset.moneda || '' : '';

      function formatAmount(amount) {
        return Number(amount).toLocaleString('es-MX', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2
        });
      }

      function applyOriginFilter() {
        var selectedType = select.value;
        var visibleCount = 0;
        var visibleTotal = 0;

        items.forEach(function (item) {
          var visible = !selectedType || item.dataset.concOriginItem === selectedType;
          item.hidden = !visible;
          if (visible) {
            visibleCount += 1;
            visibleTotal += Number(item.dataset.concOriginAmount || 0);
          }
        });

        if (summary) {
          var totalCount = Number(summary.dataset.count || items.length);
          summary.textContent = selectedType
            ? 'Mostrando ' + visibleCount + ' de ' + totalCount +
              ' movimientos · Subtotal seleccionado: ' + formatAmount(visibleTotal) +
              ' ' + currency + ' · Total completo: ' + formatAmount(total) + ' ' + currency
            : 'Mostrando ' + visibleCount + ' movimientos · Total completo: ' +
              formatAmount(total) + ' ' + currency;
        }
        if (emptyState) {
          emptyState.hidden = visibleCount > 0;
        }
        if (active && panelFor(active) === panel) {
          position(active, panel);
        }
      }

      select.addEventListener('change', applyOriginFilter);
      applyOriginFilter();
    });

    window.addEventListener('resize', function () {
      if (active) {
        position(active, panelFor(active));
      }
    });

    document.addEventListener('scroll', function () {
      if (active) {
        close(active);
      }
    }, true);

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && active) {
        var trigger = active;
        close(trigger);
        trigger.focus();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
