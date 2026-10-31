(function () {
  "use strict";
  if (!("serviceWorker" in navigator)) { return; }
  var balise = document.querySelector("script[data-sw]");
  if (!balise) { return; }
  window.addEventListener("load", function () {
    navigator.serviceWorker.register(balise.dataset.sw, { scope: "/" }).catch(function () {
      /* pas bloquant : le site fonctionne sans service worker */
    });
  });
})();
