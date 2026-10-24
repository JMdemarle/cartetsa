"""Couleur des symboles selon la date de dernière visite (sans dépendance à Django).

Seuil = 1er janvier de (année en cours - N), comparaison stricte (« postérieure à ») :
  vert   : dernière visite postérieure au 01/01 de (année - 1)
  jaune  : postérieure au 01/01 de (année - 2)
  orange : postérieure au 01/01 de (année - 3)
  rouge  : postérieure au 01/01 de (année - 4)
  noir   : sinon (visite plus ancienne ou date inconnue)
"""
from datetime import date

COULEURS = {
    "vert": "#2e7d32",
    "jaune": "#f9a825",
    "orange": "#ef6c00",
    "rouge": "#c62828",
    "noir": "#000000",
}
_ORDRE = (("vert", 1), ("jaune", 2), ("orange", 3), ("rouge", 4))


def couleur_pour(derniere_visite, annee_courante):
    """Retourne le nom de la couleur ("vert", "jaune", "orange", "rouge" ou "noir")."""
    if derniere_visite:
        for nom, decalage in _ORDRE:
            if derniere_visite > date(annee_courante - decalage, 1, 1):
                return nom
    return "noir"


def legende(annee_courante):
    """Liste de dicts {hex, libelle} pour afficher la légende de la carte."""
    elements = [
        {
            "hex": COULEURS[nom],
            "libelle": f"Visite après le 01/01/{annee_courante - decalage}",
        }
        for nom, decalage in _ORDRE
    ]
    elements.append({"hex": COULEURS["noir"], "libelle": "Visite plus ancienne ou inconnue"})
    return elements
