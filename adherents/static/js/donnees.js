(function () {
  "use strict";

  var form = document.getElementById("form-import");
  var etat = document.getElementById("etat-geocodage");
  var bouton = document.getElementById("lancer-geocodage");

  if (form) {
    form.addEventListener("submit", function (e) {
      var mode = form.querySelector("input[name=mode]:checked");
      if (mode && mode.value === "remplacer" && !window.confirm(
        "Remplacer toute la liste des adhérents par le contenu de ce fichier ?\n" +
        "Les adhérents absents du fichier seront supprimés.")) {
        e.preventDefault();
      }
    });
  }

  if (!etat || !bouton || !form) { return; }
  var jeton = form.querySelector("input[name=csrfmiddlewaretoken]").value;

  function lancer() {
    var apres = 0;
    var traites = 0;
    var reussis = 0;
    var echecsDeSuite = 0;

    function lot() {
      return fetch(etat.dataset.url, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": jeton,
          "Content-Type": "application/x-www-form-urlencoded",
          Accept: "application/json"
        },
        body: "apres_id=" + apres
      })
        .then(function (r) {
          if (!r.ok) { throw new Error("HTTP " + r.status); }
          return r.json();
        })
        .then(function (d) {
          apres = d.dernier_id;
          traites += d.traites;
          reussis += d.reussis;
          echecsDeSuite = (d.traites > 0 && d.reussis === 0) ? echecsDeSuite + 1 : 0;
          etat.textContent = reussis + " adresse(s) localisée(s), " + d.restants + " restante(s)…";
          if (d.restants > 0 && d.traites > 0 && echecsDeSuite < 3) { return lot(); }
          if (echecsDeSuite >= 3) {
            etat.textContent = "Le service de localisation ne répond pas ou refuse ces adresses. Réessayez plus tard.";
            return null;
          }
          etat.textContent = "Terminé : " + reussis + " adresse(s) localisée(s) sur " + traites + " traitée(s)." +
            (traites > reussis ? " " + (traites - reussis) + " non localisée(s) : corrigez-les dans l'administration." : "");
          return null;
        });
    }

    return lot();
  }

  bouton.addEventListener("click", function () {
    bouton.disabled = true;
    etat.textContent = "Localisation en cours…";
    lancer()
      .catch(function () {
        etat.textContent = "Interruption : vérifiez la connexion puis relancez.";
      })
      .then(function () { bouton.disabled = false; });
  });
})();
