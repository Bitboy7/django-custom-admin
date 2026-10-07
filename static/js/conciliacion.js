/*
 * Conciliación de CFDI — desglose de documentos "sin vincular".
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
