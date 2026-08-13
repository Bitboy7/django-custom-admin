(function () {
  "use strict";

  function closeSelect(select) {
    var trigger = select.querySelector("[data-bank-account-button]");
    select.classList.remove("is-open");
    if (trigger) {
      trigger.setAttribute("aria-expanded", "false");
    }
  }

  function openSelect(select) {
    document.querySelectorAll("[data-bank-account-select].is-open").forEach(function (item) {
      if (item !== select) {
        closeSelect(item);
      }
    });

    var trigger = select.querySelector("[data-bank-account-button]");
    select.classList.add("is-open");
    if (trigger) {
      trigger.setAttribute("aria-expanded", "true");
    }
  }

  function initBankAccountSelect(select) {
    var trigger = select.querySelector("[data-bank-account-button]");
    var hiddenInput = select.querySelector('input[type="hidden"]');
    var current = select.querySelector("[data-bank-account-current]");
    var options = select.querySelectorAll("[data-bank-account-option]");

    if (!trigger || !hiddenInput || !current) {
      return;
    }

    trigger.addEventListener("click", function () {
      if (select.classList.contains("is-open")) {
        closeSelect(select);
      } else {
        openSelect(select);
      }
    });

    options.forEach(function (option) {
      option.addEventListener("click", function () {
        hiddenInput.value = option.getAttribute("data-value") || "";
        current.innerHTML = option.querySelector("[data-bank-account-label]").innerHTML;

        options.forEach(function (item) {
          item.classList.remove("is-selected");
        });
        option.classList.add("is-selected");
        closeSelect(select);
        trigger.focus();
      });
    });
  }

  document.addEventListener("click", function (event) {
    document.querySelectorAll("[data-bank-account-select].is-open").forEach(function (select) {
      if (!select.contains(event.target)) {
        closeSelect(select);
      }
    });
  });

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") {
      return;
    }

    document.querySelectorAll("[data-bank-account-select].is-open").forEach(closeSelect);
  });

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-bank-account-select]").forEach(initBankAccountSelect);
  });
})();
