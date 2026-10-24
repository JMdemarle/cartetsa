(function () {
  "use strict";

  var el = document.getElementById("map");
  var champRecherche = document.getElementById("recherche");
  var compteur = document.getElementById("compteur");
  var nonLocalises = 0;

  var carte = L.map("map").setView([46.6, 2.5], 6);
  L.tileLayer(el.dataset.tileUrl, {
    attribution: el.dataset.attribution,
    maxZoom: 19
  }).addTo(carte);

  var groupe = L.layerGroup().addTo(carte);
  var marqueurs = [];

  // Le contenu des popups est construit avec textContent (jamais innerHTML) :
  // aucune donnée d'adhérent n'est interprétée comme du HTML.
  function ligne(texte, gras) {
    var p = document.createElement("p");
    if (gras) {
      var s = document.createElement("strong");
      s.textContent = texte;
      p.appendChild(s);
    } else {
      p.textContent = texte;
    }
    return p;
  }

  function lien(prefixe, valeur, texte) {
    var p = document.createElement("p");
    var a = document.createElement("a");
    a.href = prefixe + valeur;
    a.textContent = texte;
    p.appendChild(a);
    return p;
  }

  function titre(pt) {
    return [pt.civilite, pt.prenom, pt.nom].filter(Boolean).join(" ");
  }

  function contenuPopup(pt) {
    var boite = document.createElement("div");
    boite.className = "popup";
    boite.appendChild(ligne(titre(pt), true));
    if (pt.identifiant) {
      boite.appendChild(ligne("Identifiant : " + pt.identifiant, false));
    }
    boite.appendChild(ligne(pt.adresse, false));
    if (pt.complement) {
      boite.appendChild(ligne(pt.complement, false));
    }
    boite.appendChild(ligne([pt.code_postal, pt.commune].filter(Boolean).join(" "), false));
    if (pt.telephone) {
      boite.appendChild(lien("tel:", pt.telephone.replace(/[^0-9+]/g, ""), pt.telephone));
    }
    if (pt.email) {
      boite.appendChild(lien("mailto:", pt.email.split(/[?&\s]/)[0], pt.email));
    }
    boite.appendChild(ligne("Dernière visite : " + (pt.derniere_visite || "aucune"), false));
    if (pt.annees_cotisation) {
      boite.appendChild(ligne("Cotisations : " + pt.annees_cotisation, false));
    }
    return boite;
  }

  function afficher(filtre) {
    groupe.clearLayers();
    var n = 0;
    marqueurs.forEach(function (m) {
      if (!filtre || m.texte.indexOf(filtre) !== -1) {
        groupe.addLayer(m.marqueur);
        n += 1;
      }
    });
    compteur.textContent = n + " adhérent(s) affiché(s)" +
      (nonLocalises ? " – " + nonLocalises + " non localisé(s)" : "");
  }

  fetch(el.dataset.api, { credentials: "same-origin", headers: { Accept: "application/json" } })
    .then(function (r) {
      if (!r.ok) { throw new Error("HTTP " + r.status); }
      return r.json();
    })
    .then(function (donnees) {
      nonLocalises = donnees.non_localises || 0;
      var bornes = [];
      donnees.points.forEach(function (pt) {
        var marqueur = L.circleMarker([pt.lat, pt.lon], {
          radius: 9,
          color: "#ffffff",
          weight: 2,
          fillColor: pt.couleur,
          fillOpacity: 0.95
        }).bindPopup(contenuPopup(pt));
        marqueurs.push({
          marqueur: marqueur,
          texte: [titre(pt), pt.identifiant, pt.adresse, pt.commune].join(" ").toLowerCase()
        });
        bornes.push([pt.lat, pt.lon]);
      });
      afficher("");
      if (bornes.length) {
        carte.fitBounds(bornes, { padding: [30, 30], maxZoom: 14 });
      }
    })
    .catch(function () {
      compteur.textContent = "Impossible de charger les données.";
    });

  champRecherche.addEventListener("input", function () {
    afficher(champRecherche.value.trim().toLowerCase());
  });
})();
