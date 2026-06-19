(function () {
  "use strict";

  if (window.jQuery) {
    window.$ = window.jQuery;
    return;
  }

  if (window.django && window.django.jQuery) {
    window.$ = window.jQuery = window.django.jQuery;
  }
})();
