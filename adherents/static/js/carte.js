(function () {
  "use strict";

  var el = document.getElementById("map");
  var champRecherche = document.getElementById("recherche");  // absent sur la page publique des TSA
  var compteur = document.getElementById("compteur");
  var caseTsa = document.getElementById("afficher-tsa");
  var boutonAutour = document.getElementById("autour");
  var blocProches = document.getElementById("proches");
  var listeProches = document.getElementById("liste-proches");
  var positionMarqueur = null;
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

  // « Itinéraire » : ouvre Waze ou Google Maps (et Plans sur iPhone/iPad) vers l'adhérent.
  // Seules les coordonnées sont transmises, uniquement au clic sur le lien choisi.
  function liensItineraire(lat, lon) {
    var la = Number(lat).toFixed(6);
    var lo = Number(lon).toFixed(6);
    var ua = navigator.userAgent || "";
    var ios = /iPad|iPhone|iPod/.test(ua) ||
      (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    var liens = [
      { libelle: "Waze", url: "https://waze.com/ul?ll=" + la + "," + lo + "&navigate=yes" },
      { libelle: "Google Maps", url: "https://www.google.com/maps/dir/?api=1&destination=" + la + "," + lo + "&travelmode=driving" }
    ];
    if (ios) {
      liens.push({ libelle: "Plans", url: "https://maps.apple.com/?daddr=" + la + "," + lo + "&dirflg=d" });
    }
    return liens;
  }

  function boutonItineraire(pt) {
    var p = document.createElement("p");
    p.className = "itineraire-liens";
    var etiquette = document.createElement("span");
    etiquette.textContent = "Itinéraire :";
    p.appendChild(etiquette);
    liensItineraire(pt.lat, pt.lon).forEach(function (l) {
      var a = document.createElement("a");
      a.className = "itineraire";
      a.href = l.url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = l.libelle;
      p.appendChild(a);
    });
    return p;
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
    boite.appendChild(boutonItineraire(pt));
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
          pt: pt,
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

  // --- « Autour de moi » : la position est utilisée uniquement dans le navigateur ---
  function distanceKm(lat1, lon1, lat2, lon2) {
    var rad = Math.PI / 180;
    var dLat = (lat2 - lat1) * rad;
    var dLon = (lon2 - lon1) * rad;
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  function afficherProches(proches) {
    listeProches.textContent = "";
    proches.forEach(function (p) {
      var li = document.createElement("li");
      var bouton = document.createElement("button");
      bouton.type = "button";
      bouton.className = "proche";
      var pastille = document.createElement("span");
      pastille.className = "pastille";
      pastille.style.background = p.m.pt.couleur;
      var texte = document.createElement("span");
      texte.textContent = titre(p.m.pt) + " – " + p.m.pt.commune + " – " +
        p.d.toFixed(1).replace(".", ",") + " km";
      bouton.appendChild(pastille);
      bouton.appendChild(texte);
      bouton.addEventListener("click", function () {
        groupe.addLayer(p.m.marqueur);
        carte.setView([p.m.pt.lat, p.m.pt.lon], 16);
        p.m.marqueur.openPopup();
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      });
      li.appendChild(bouton);
      listeProches.appendChild(li);
    });
    blocProches.hidden = false;
  }

  if (boutonAutour) {
    boutonAutour.addEventListener("click", function () {
      if (!navigator.geolocation) {
        compteur.textContent = "Géolocalisation indisponible sur cet appareil.";
        return;
      }
      compteur.textContent = "Recherche de votre position…";
      navigator.geolocation.getCurrentPosition(function (pos) {
        var lat = pos.coords.latitude;
        var lon = pos.coords.longitude;
        if (positionMarqueur) { carte.removeLayer(positionMarqueur); }
        positionMarqueur = L.circleMarker([lat, lon], {
          radius: 7, color: "#ffffff", weight: 2, fillColor: "#1976d2", fillOpacity: 1
        }).addTo(carte).bindTooltip("Vous êtes ici");
        var proches = marqueurs
          .map(function (m) { return { m: m, d: distanceKm(lat, lon, m.pt.lat, m.pt.lon) }; })
          .sort(function (a, b) { return a.d - b.d; })
          .slice(0, 10);
        afficherProches(proches);
        var bornes = [[lat, lon]].concat(proches.slice(0, 5).map(function (p) {
          return [p.m.pt.lat, p.m.pt.lon];
        }));
        carte.fitBounds(bornes, { padding: [30, 30], maxZoom: 14 });
        afficher(champRecherche ? champRecherche.value.trim().toLowerCase() : "");
      }, function () {
        compteur.textContent = "Position indisponible (autorisation refusée ?).";
      }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 });
    });
  }

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
