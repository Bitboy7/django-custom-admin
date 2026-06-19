/**
 * Theme Toggle — Dark/Light/Auto Mode Switcher
 *
 * Características:
 * - 3 modos: Claro → Oscuro → Auto (sistema) → Claro...
 * - Persistencia en localStorage
 * - Detecta preferencia del sistema en tiempo real
 * - Iconos SVG animados (sol / luna / auto)
 * - Transición suave entre temas (CSS transition)
 * - Accesible: aria-label, keyboard, focus-visible
 * - Toast notification integrado
 *
 * Skills: ui-ux-pro-max, frontend-design
 */
(function () {
  'use strict';

  var THEME_KEY = 'agricola-theme';
  var DARK  = 'dark';
  var LIGHT = 'light';
  var AUTO  = 'auto';

  /* ── SVG Icons ────────────────────────────────────────────────── */
  var ICONS = {
    sun: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1"  x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>',
    moon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>',
    auto: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>'
  };

  /* ── Helpers ──────────────────────────────────────────────────── */
  function getSystemPreference() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? DARK : LIGHT;
  }

  function getStoredTheme() {
    var stored = localStorage.getItem(THEME_KEY);
    return stored === LIGHT || stored === DARK || stored === AUTO ? stored : AUTO;
  }

  function setStoredTheme(theme) {
    localStorage.setItem(THEME_KEY, theme);
  }

  function getResolvedTheme(theme) {
    var t = theme || getStoredTheme();
    return t === AUTO ? getSystemPreference() : t;
  }

  function isDark() {
    return getResolvedTheme() === DARK;
  }

  /* ── Apply theme to DOM ───────────────────────────────────────── */
  function applyTheme(theme) {
    var resolved = getResolvedTheme(theme);
    var mode = theme || getStoredTheme();
    document.documentElement.setAttribute('data-theme', resolved);
    document.documentElement.setAttribute('data-theme-mode', mode);
    document.documentElement.classList.toggle('dark', resolved === DARK);
    document.documentElement.style.colorScheme = resolved;
  }

  /* ── Smooth transition (one-time on toggle) ──────────────────── */
  function enableTransition() {
    var style = document.createElement('style');
    style.id = 'theme-transition';
    style.textContent =
      '*, *::before, *::after { transition: background-color .35s cubic-bezier(0.4,0,0.2,1), color .3s cubic-bezier(0.4,0,0.2,1), border-color .25s cubic-bezier(0.4,0,0.2,1), box-shadow .3s cubic-bezier(0.4,0,0.2,1) !important; }';
    document.head.appendChild(style);

    setTimeout(function () {
      var el = document.getElementById('theme-transition');
      if (el) el.remove();
    }, 500);
  }

  /* ── Toggle logic ─────────────────────────────────────────────── */
  function cycleTheme() {
    var current = getStoredTheme();
    var next = current === LIGHT ? DARK : current === DARK ? AUTO : LIGHT;

    enableTransition();
    setStoredTheme(next);
    applyTheme(next);
    updateToggleButton();
    showToast(next);

    return next;
  }

  /* ── Update toggle button state ───────────────────────────────── */
  function updateToggleButton() {
    var btn = document.getElementById('theme-toggle-btn');
    if (!btn) return;

    var stored  = getStoredTheme();
    var resolved = getResolvedTheme();

    btn.innerHTML = ICONS[resolved === DARK ? 'moon' : 'sun'];

    /* Add auto indicator dot */
    if (stored === AUTO) {
      var dot = document.createElement('span');
      dot.className = 'theme-toggle-auto-dot';
      btn.appendChild(dot);
    }

    /* Tooltip label */
    var label = stored === AUTO
      ? 'Auto — ' + (resolved === DARK ? 'oscuro' : 'claro') + ' (click para cambiar)'
      : resolved === DARK
        ? 'Modo oscuro — click para modo auto'
        : 'Modo claro — click para modo oscuro';

    btn.setAttribute('aria-label', label);
    btn.setAttribute('title', label);
  }

  /* ── Create toggle button in navbar ───────────────────────────── */
  function createToggleButton() {
    if (document.getElementById('theme-toggle-btn')) return;

    var nav = document.querySelector('.navbar-nav.ml-auto, .navbar-nav.ms-auto');
    if (!nav) { return; }

    var li = document.createElement('li');
    li.className = 'nav-item d-flex align-items-center';

    var btn = document.createElement('button');
    btn.id = 'theme-toggle-btn';
    btn.className = 'theme-toggle';
    btn.setAttribute('aria-label', 'Cambiar tema de color');
    btn.setAttribute('type', 'button');

    btn.addEventListener('click', function (e) {
      e.preventDefault();
      cycleTheme();
    });

    /* Keyboard support */
    btn.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        cycleTheme();
      }
    });

    li.appendChild(btn);
    nav.prepend(li);
    updateToggleButton();
  }

  /* ── Toast notification ───────────────────────────────────────── */
  function showToast(mode) {
    var colors = { dark: '#0db892', light: '#f0a520', auto: '#5b9bd5' };
    var labels = { dark: 'Modo oscuro activado', light: 'Modo claro activado', auto: 'Auto (sistema)' };
    var emoji = { dark: '\uD83C\uDF19', light: '\u2600\uFE0F', auto: '\uD83D\uDCBB' };

    var container = document.getElementById('theme-toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'theme-toast-container';
      container.style.cssText =
        'position:fixed;top:20px;right:20px;z-index:10000;display:flex;flex-direction:column;gap:8px;pointer-events:none;';
      document.body.appendChild(container);
    }

    var toast = document.createElement('div');
    toast.style.cssText =
      'pointer-events:auto;background:' + (isDark() ? '#1e2220' : '#fefdfb') +
      ';color:' + (isDark() ? '#f5f2eb' : '#1c1814') +
      ';border:1px solid ' + (isDark() ? '#333835' : '#e0dcd3') +
      ';border-radius:12px;box-shadow:0 8px 32px rgba(12,25,41,0.18);' +
      'padding:12px 16px;min-width:240px;max-width:300px;' +
      'display:flex;align-items:center;gap:10px;font-family:"Plus Jakarta Sans",sans-serif;font-size:13px;font-weight:600;' +
      'transform:translateX(120%);opacity:0;transition:transform .4s cubic-bezier(0.34,1.56,0.64,1),opacity .3s ease;';

    toast.innerHTML =
      '<span style="font-size:18px;flex-shrink:0">' + emoji[mode] + '</span>' +
      '<span>' + labels[mode] + '</span>';

    container.appendChild(toast);

    /* Animate in */
    requestAnimationFrame(function () {
      toast.style.transform = 'translateX(0)';
      toast.style.opacity = '1';
    });

    /* Animate out */
    setTimeout(function () {
      toast.style.transform = 'translateX(120%)';
      toast.style.opacity = '0';
      setTimeout(function () {
        if (toast.parentNode) toast.remove();
      }, 450);
    }, 2200);
  }

  /* ── Init ──────────────────────────────────────────────────────── */
  function init() {
    applyTheme(getStoredTheme());
    createToggleButton();

    /* Listen for system theme changes when in auto mode */
    var systemThemeQuery = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)');
    var handleSystemThemeChange = function () {
      if (getStoredTheme() === AUTO) {
        enableTransition();
        applyTheme(AUTO);
        updateToggleButton();
      }
    };

    if (systemThemeQuery) {
      if (systemThemeQuery.addEventListener) {
        systemThemeQuery.addEventListener('change', handleSystemThemeChange);
      } else if (systemThemeQuery.addListener) {
        systemThemeQuery.addListener(handleSystemThemeChange);
      }
    }

    /* Log the resolved mode for debugging */
    var resolved = getResolvedTheme();
    var stored = getStoredTheme();
    console.log(
      '%c\uD83C\uDF3E Tema%c ' + (stored === AUTO ? 'Auto → ' + resolved : resolved === DARK ? 'Oscuro' : 'Claro') +
      '%c | Agricola de la Costa ERP',
      'color:#089b7a;font-weight:700;', 'color:inherit;', 'color:#9c9385;'
    );
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
