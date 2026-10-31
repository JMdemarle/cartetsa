"use strict";

// Service worker de l'application « Visites TSA ».
// Règle de sécurité : on ne met JAMAIS en cache de page HTML ni de réponse /api/.
// Seuls les fichiers statiques (styles, scripts, icônes) sont stockés sur l'appareil.

const VERSION = "{{ version }}";
const CACHE = "carte-apicole-" + VERSION;
const SHELL = {{ fichiers_json|safe }};
const HORS_LIGNE = "{{ url_hors_ligne }}";
const PREFIXE_STATIC = "{{ prefixe_static }}";

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(CACHE)
      .then(function (cache) {
        return Promise.all(
          SHELL.concat([HORS_LIGNE]).map(function (url) {
            return cache.add(url).catch(function () { return null; });
          })
        );
      })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys()
      .then(function (noms) {
        return Promise.all(
          noms
            .filter(function (nom) { return nom.indexOf("carte-apicole-") === 0 && nom !== CACHE; })
            .map(function (nom) { return caches.delete(nom); })
        );
      })
      .then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (event) {
  var requete = event.request;
  if (requete.method !== "GET") { return; }

  var url = new URL(requete.url);
  // Fonds de carte et autres sites : jamais interceptés.
  if (url.origin !== self.location.origin) { return; }
  // Données des adhérents : toujours directement depuis le serveur, jamais en cache.
  if (url.pathname.indexOf("/api/") === 0) { return; }

  // Pages : réseau uniquement ; page « hors ligne » neutre si le réseau est coupé.
  if (requete.mode === "navigate") {
    event.respondWith(
      fetch(requete).catch(function () { return caches.match(HORS_LIGNE); })
    );
    return;
  }

  // Fichiers statiques : cache d'abord, mis à jour en arrière-plan.
  if (url.pathname.indexOf(PREFIXE_STATIC) === 0) {
    event.respondWith(
      caches.open(CACHE).then(function (cache) {
        return cache.match(requete).then(function (enCache) {
          var depuisReseau = fetch(requete)
            .then(function (reponse) {
              if (reponse.ok) { cache.put(requete, reponse.clone()); }
              return reponse;
            })
            .catch(function () { return enCache; });
          return enCache || depuisReseau;
        });
      })
    );
  }
});
