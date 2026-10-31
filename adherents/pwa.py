"""Vues PWA : manifeste, service worker et page hors ligne.

Aucune donnée personnelle ici : ces trois réponses sont publiques (le navigateur doit
pouvoir les lire même avant la connexion).
"""
import json
import os

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse

# Fichiers de l'« enveloppe » de l'application, mis en cache pour un démarrage rapide.
# Jamais de page HTML ni de réponse /api/ : les données d'adhérents ne sont pas stockées.
FICHIERS_SHELL = (
    "css/app.css",
    "js/carte.js",
    "js/pwa.js",
    "vendor/leaflet/leaflet.css",
    "vendor/leaflet/leaflet.js",
    "icons/icone-192.png",
)


def manifest(request):
    donnees = {
        "name": "Carte des visites – Plan sanitaire apicole",
        "short_name": "Visites TSA",
        "description": "Carte des adhérents à visiter pour les techniciens sanitaires apicoles.",
        "lang": "fr",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#f6f6f3",
        "theme_color": "#7a5c00",
        "icons": [
            {"src": static("icons/icone-192.png"), "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": static("icons/icone-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {
                "src": static("icons/icone-maskable-512.png"),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
    }
    reponse = JsonResponse(donnees, content_type="application/manifest+json")
    reponse["Cache-Control"] = "public, max-age=3600"
    return reponse


def service_worker(request):
    contexte = {
        "version": os.environ.get("PWA_VERSION") or getattr(settings, "PWA_VERSION", "1"),
        "fichiers_json": json.dumps([static(f) for f in FICHIERS_SHELL]),
        "url_hors_ligne": reverse("hors_ligne"),
        "prefixe_static": settings.STATIC_URL,
    }
    reponse = render(request, "adherents/sw.js", contexte, content_type="application/javascript")
    reponse["Cache-Control"] = "no-cache"  # le navigateur doit pouvoir détecter une nouvelle version
    return reponse


def hors_ligne(request):
    return render(request, "adherents/hors_ligne.html")
