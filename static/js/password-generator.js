(function () {
  'use strict';

  var LOWER = 'abcdefghijkmnopqrstuvwxyz';
  var UPPER = 'ABCDEFGHJKLMNPQRSTUVWXYZ';
  var DIGITS = '23456789';
  var SYMBOLS = '!@#$%^&*()-_=+[]{};:,.?/|~';
  var MIN_ENTROPY = { weak: 64, strong: 96 };

  function hasSecureRandom() {
    return !!(window.crypto && typeof window.crypto.getRandomValues === 'function');
  }

  function randomIndex(max) {
    if (max <= 0) return 0;
    var buffer = new Uint32Array(1);
    var limit = Math.floor(4294967296 / max) * max;
    var value;
    do {
      window.crypto.getRandomValues(buffer);
      value = buffer[0];
    } while (value >= limit);
    return value % max;
  }

  function pick(chars) {
    return chars.charAt(randomIndex(chars.length));
  }

  function shuffle(items) {
    for (var i = items.length - 1; i > 0; i -= 1) {
      var j = randomIndex(i + 1);
      var tmp = items[i];
      items[i] = items[j];
      items[j] = tmp;
    }
    return items;
  }

  function generate(length, useSymbols) {
    var required = [pick(LOWER), pick(UPPER), pick(DIGITS)];
    var pool = LOWER + UPPER + DIGITS;
    if (useSymbols) {
      required.push(pick(SYMBOLS));
      pool += SYMBOLS;
    }

    var chars = required.slice();
    while (chars.length < length) {
      chars.push(pick(pool));
    }
    return shuffle(chars).slice(0, length).join('');
  }

  function entropyBits(length, poolSize) {
    return length * (Math.log(poolSize) / Math.LN2);
  }

  function init() {
    var root = document.querySelector('[data-password-generator]');
    if (!root) return;

    var lengthInput = root.querySelector('#pw-gen-length');
    var symbolsInput = root.querySelector('#pw-gen-symbols');
    var generateBtn = root.querySelector('#pw-gen-generate');
    var output = root.querySelector('#pw-gen-output');
    var valueInput = root.querySelector('#pw-gen-value');
    var copyBtn = root.querySelector('#pw-gen-copy');
    var meterBar = root.querySelector('#pw-gen-meter-bar');
    var feedback = root.querySelector('#pw-gen-feedback');
    var password1 = document.getElementById('id_password1');
    var password2 = document.getElementById('id_password2');

    var messages = {
      generated: root.getAttribute('data-msg-generated') || '',
      copied: root.getAttribute('data-msg-copied') || '',
      copyError: root.getAttribute('data-msg-copyerror') || '',
      unsupported: root.getAttribute('data-msg-unsupported') || '',
      weak: root.getAttribute('data-msg-weak') || '',
      good: root.getAttribute('data-msg-good') || '',
      strong: root.getAttribute('data-msg-strong') || ''
    };

    function setFeedback(text) {
      if (feedback) feedback.textContent = text;
    }

    function strengthLabel(bits) {
      if (bits < MIN_ENTROPY.weak) return messages.weak;
      if (bits < MIN_ENTROPY.strong) return messages.good;
      return messages.strong;
    }

    function updateMeter(value, useSymbols) {
      if (!meterBar || !value) return '';
      var poolSize = LOWER.length + UPPER.length + DIGITS.length + (useSymbols ? SYMBOLS.length : 0);
      var bits = entropyBits(value.length, poolSize);
      var label = strengthLabel(bits);
      var percent = Math.max(8, Math.min(100, Math.round((bits / 128) * 100)));

      meterBar.style.width = percent + '%';
      meterBar.setAttribute('data-level', label === messages.weak ? 'weak' : (label === messages.good ? 'good' : 'strong'));
      return label;
    }

    function fillFields(value) {
      [password1, password2].forEach(function (field) {
        if (!field) return;
        field.value = value;
        field.dispatchEvent(new Event('input', { bubbles: true }));
        field.dispatchEvent(new Event('change', { bubbles: true }));
      });
    }

    function copyValue() {
      var value = valueInput ? valueInput.value : '';
      if (!value) return;

      function done() {
        setFeedback(messages.copied);
      }

      function fallback() {
        if (!valueInput) return;
        valueInput.focus();
        valueInput.select();
        try {
          document.execCommand('copy');
          done();
        } catch (error) {
          setFeedback(messages.copyError);
        }
      }

      if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
        navigator.clipboard.writeText(value).then(done, fallback);
      } else {
        fallback();
      }
    }

    if (!hasSecureRandom()) {
      if (generateBtn) {
        generateBtn.disabled = true;
        generateBtn.setAttribute('aria-disabled', 'true');
      }
      setFeedback(messages.unsupported);
      return;
    }

    if (generateBtn) {
      generateBtn.addEventListener('click', function () {
        var length = parseInt(lengthInput ? lengthInput.value : '20', 10) || 20;
        var useSymbols = !!(symbolsInput && symbolsInput.checked);
        var value = generate(length, useSymbols);

        if (valueInput) valueInput.value = value;
        if (output) output.hidden = false;

        fillFields(value);
        var label = updateMeter(value, useSymbols);
        setFeedback(messages.generated + (label ? ' ' + label : ''));
      });
    }

    if (copyBtn) {
      copyBtn.addEventListener('click', copyValue);
    }

    if (password1) {
      password1.addEventListener('input', function () {
        var useSymbols = /[^A-Za-z0-9]/.test(password1.value);
        updateMeter(password1.value, useSymbols);
      });
    }

    Array.prototype.forEach.call(document.querySelectorAll('.pw-field__toggle'), function (button) {
      button.addEventListener('click', function () {
        var target = document.getElementById(button.getAttribute('data-pw-target'));
        if (!target) return;

        var show = target.type === 'password';
        target.type = show ? 'text' : 'password';
        button.setAttribute('aria-pressed', show ? 'true' : 'false');

        var label = show ? button.getAttribute('data-label-hide') : button.getAttribute('data-label-show');
        if (label) button.setAttribute('aria-label', label);

        var icon = button.querySelector('i');
        if (icon) icon.className = show ? 'fas fa-eye-slash' : 'fas fa-eye';
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
