"""Lecture de l'export CSV du logiciel FNOSAD (aucune dépendance à Django).

Seules les colonnes utiles sont lues ; toutes les autres (date de naissance, SIRET,
TVA, description, etc.) sont ignorées et ne sont jamais enregistrées.
"""
import csv
import io
import re
import unicodedata
from datetime import date

# clé interne -> nom de colonne normalisé (sans accents, en minuscules)
COLONNES_UTILISEES = {
    "identifiant": "identifiant",
    "prenom": "prenom",
    "nom": "nom",
    "civilite": "civilite",
    "adresse": "adresse",
    "complement": "complement d'adresse",
    "code_postal": "code postal",
    "commune": "commune",
    "telephone": "telephone",
    "email": "email",
    "derniere_visite": "derniere visite",
    "annees_cotisation": "annees de cotisation",
    "secteur": "secteur",
}
OBLIGATOIRES = ("nom", "adresse", "code_postal", "commune", "derniere_visite", "annees_cotisation")


def normaliser(texte):
    texte = unicodedata.normalize("NFKD", texte or "")
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = texte.replace("\u2019", "'").replace("\u00a0", " ")
    return " ".join(texte.lower().split())


def decoder(octets):
    """UTF-8 (avec ou sans BOM), sinon Windows-1252 (export Excel français)."""
    try:
        return octets.decode("utf-8-sig")
    except UnicodeDecodeError:
        return octets.decode("cp1252", errors="replace")


def lire_export(texte):
    """Retourne (lignes, colonnes_manquantes).

    Chaque ligne est un dict des colonnes utilisées, plus "_numero" (ligne du fichier).
    Si une colonne apparaît plusieurs fois, la première est retenue.
    """
    premiere = texte.split("\n", 1)[0]
    delimiteur = ";" if premiere.count(";") >= premiere.count(",") else ","
    lecteur = csv.reader(io.StringIO(texte, newline=""), delimiter=delimiteur)
    try:
        entetes = next(lecteur)
    except StopIteration:
        return [], list(OBLIGATOIRES)

    index = {}
    for position, nom in enumerate(entetes):
        index.setdefault(normaliser(nom), position)

    positions = {}
    for cle, colonne in COLONNES_UTILISEES.items():
        if colonne in index:
            positions[cle] = index[colonne]
        elif cle == "annees_cotisation":
            # tolérance : en-tête collé à la colonne suivante (copier-coller)
            for nom, position in index.items():
                if nom.startswith(colonne):
                    positions[cle] = position
                    break

    manquantes = [c for c in OBLIGATOIRES if c not in positions]
    if manquantes:
        return [], manquantes

    lignes = []
    for champs in lecteur:
        if not any(c.strip() for c in champs):
            continue
        ligne = {
            cle: (champs[pos].strip() if pos < len(champs) else "")
            for cle, pos in positions.items()
        }
        ligne["_numero"] = lecteur.line_num
        lignes.append(ligne)
    return lignes, []


def lire_date(texte):
    """« 14/01/2023 à 01h00:00 » -> date(2023, 1, 14). Vide -> None."""
    texte = (texte or "").strip()
    if not texte:
        return None
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", texte)
    if m:
        jour, mois, annee = (int(x) for x in m.groups())
    else:
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", texte)
        if not m:
            raise ValueError(f"date invalide : {texte!r}")
        annee, mois, jour = (int(x) for x in m.groups())
    try:
        return date(annee, mois, jour)
    except ValueError:
        raise ValueError(f"date invalide : {texte!r}")


def annees_depuis(texte):
    """« 2026, 2025, 2019 » -> [2026, 2025, 2019] (ordre décroissant, sans doublon)."""
    trouvees = re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", texte or "")
    return sorted({int(a) for a in trouvees}, reverse=True)
