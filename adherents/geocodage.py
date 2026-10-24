"""Géocodage via le service public (Géoplateforme IGN).

Seule l'adresse est envoyée : jamais le nom ni le téléphone.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings


def geocoder(adresse_complete):
    """Retourne (latitude, longitude, score) ou None si l'adresse n'est pas trouvée."""
    if not adresse_complete:
        return None
    params = urllib.parse.urlencode({"q": adresse_complete, "limit": 1})
    requete = urllib.request.Request(
        f"{settings.GEOCODAGE_URL}?{params}", headers={"User-Agent": "carte-apicole/1.0"}
    )
    try:
        with urllib.request.urlopen(requete, timeout=10) as reponse:
            donnees = json.load(reponse)
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None
    resultats = donnees.get("features") or []
    if not resultats:
        return None
    resultat = resultats[0]
    score = resultat.get("properties", {}).get("score", 0)
    if score < settings.GEOCODAGE_SCORE_MIN:
        return None
    longitude, latitude = resultat["geometry"]["coordinates"][:2]
    return latitude, longitude, score
