(function () {
  "use strict";

  var el = document.getElementById("map");
  var champRecherche = document.getElementById("recherche");  // absent sur la page publique
  var compteur = document.getElementById("compteur");
  var caseTsa = document.getElementById("afficher-tsa");
  var nonLocalises = 0;
  var nbTsa = 0;

  var carte = L.map("map").setView([46.6, 2.5], 6);
  L.tileLayer(el.dataset.tileUrl, {
    attribution: el.dataset.attribution,
    maxZoom: 19
  }).addTo(carte);

  var groupe = L.layerGroup().addTo(carte);      // adhérents (ronds colorés)
  var groupeTsa = L.layerGroup().addTo(carte);   // TSA (croix rouges)
  var marqueurs = [];
  var bornesAdherents = [];
  var bornesTsa = [];

  var iconeTsa = L.divIcon({
    className: "croix-tsa",
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -12]
  });

  // Les popups sont construites avec textContent (jamais innerHTML) :
  // aucune donnée n'est interprétée comme du HTML.
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

  function ajouter(boite, texte, gras) {
    if (texte) { boite.appendChild(ligne(texte, gras)); }
  }

  function lien(prefixe, valeur, texte) {
    var p = document.createElement("p");
    var a = document.createElement("a");
    a.href = prefixe + valeur;
    a.textContent = texte;
    p.appendChild(a);
    return p;
  }

  function contacts(boite, pt) {
    if (pt.telephone) {
      boite.appendChild(lien("tel:", pt.telephone.replace(/[^0-9+]/g, ""), pt.telephone));
    }
    if (pt.email) {
      boite.appendChild(lien("mailto:", pt.email.split(/[?&\s]/)[0], pt.email));
    }
  }

  function titre(pt) {
    return [pt.civilite, pt.prenom, pt.nom].filter(Boolean).join(" ");
  }

  function contenuPopup(pt) {
    var boite = document.createElement("div");
    boite.className = "popup";
    ajouter(boite, titre(pt), true);
    if (pt.identifiant) { ajouter(boite, "Identifiant : " + pt.identifiant, false); }
    ajouter(boite, pt.adresse, false);
    ajouter(boite, pt.complement, false);
    ajouter(boite, [pt.code_postal, pt.commune].filter(Boolean).join(" "), false);
    contacts(boite, pt);
    ajouter(boite, "Dernière visite : " + (pt.derniere_visite || "aucune"), false);
    if (pt.annees_cotisation) { ajouter(boite, "Cotisations : " + pt.annees_cotisation, false); }
    return boite;
  }

  function contenuPopupTsa(pt) {
    var boite = document.createElement("div");
    boite.className = "popup";
    ajouter(boite, "Technicien sanitaire apicole", false);
    ajouter(boite, titre(pt), true);
    ajouter(boite, pt.adresse, false);
    ajouter(boite, [pt.code_postal, pt.commune].filter(Boolean).join(" "), false);
    contacts(boite, pt);
    return boite;
  }

  function majCompteur(n) {
    if (!compteur) { return; }
    if (el.dataset.api) {
      compteur.textContent = n + " adhérent(s) affiché(s)" +
        (nonLocalises ? " – " + nonLocalises + " non localisé(s)" : "");
    } else {
      compteur.textContent = nbTsa + " TSA";
    }
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
    majCompteur(n);
  }

  function charger(url) {
    return fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } })
      .then(function (r) {
        if (!r.ok) { throw new Error("HTTP " + r.status); }
        return r.json();
      });
  }

  function erreur() {
    if (compteur) { compteur.textContent = "Impossible de charger les données."; }
  }

  function chargerAdherents() {
    return charger(el.dataset.api).then(function (donnees) {
      nonLocalises = donnees.non_localises || 0;
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
        bornesAdherents.push([pt.lat, pt.lon]);
      });
      afficher("");
    }).catch(erreur);
  }

  function chargerTsa() {
    return charger(el.dataset.apiTsa).then(function (donnees) {
      donnees.points.forEach(function (pt) {
        L.marker([pt.lat, pt.lon], {
          icon: iconeTsa,
          title: "TSA " + titre(pt),
          alt: "TSA " + titre(pt)
        }).bindPopup(contenuPopupTsa(pt)).addTo(groupeTsa);
        bornesTsa.push([pt.lat, pt.lon]);
      });
      nbTsa = bornesTsa.length;
      if (!el.dataset.api) { majCompteur(0); }
    }).catch(erreur);
  }

  var requetes = [];
  if (el.dataset.api) { requetes.push(chargerAdherents()); }
  if (el.dataset.apiTsa) { requetes.push(chargerTsa()); }
  Promise.all(requetes).then(function () {
    var bornes = bornesAdherents.length ? bornesAdherents : bornesTsa;
    if (bornes.length) {
      carte.fitBounds(bornes, { padding: [30, 30], maxZoom: 14 });
    }
  });

  if (champRecherche) {
    champRecherche.addEventListener("input", function () {
      afficher(champRecherche.value.trim().toLowerCase());
    });
  }
  if (caseTsa) {
    caseTsa.addEventListener("change", function () {
      if (caseTsa.checked) { groupeTsa.addTo(carte); } else { carte.removeLayer(groupeTsa); }
    });
  }
})();
