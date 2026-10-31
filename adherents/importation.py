"""Import de l'export FNOSAD depuis l'interface web (mêmes règles que la commande importer_adherents).

Différences utiles pour le web : aucun appel réseau pendant l'import (le géocodage se fait ensuite par
petits lots) et réutilisation des coordonnées déjà connues quand l'adresse n'a pas changé.
"""
from dataclasses import dataclass, field

from django.db import transaction

from .export_fnosad import annees_depuis, decoder, lire_date, lire_export, normaliser
from .models import Adherent, Secteur

CHAMPS = (
    "identifiant", "civilite", "prenom", "nom", "adresse", "complement_adresse",
    "code_postal", "commune", "telephone", "email", "derniere_visite",
    "annees_cotisation", "secteur",
)
MAX_AVERTISSEMENTS = 30


class ErreurImport(Exception):
    pass


@dataclass
class Bilan:
    crees: int = 0
    mis_a_jour: int = 0
    supprimes: int = 0
    exclus: int = 0
    ignores: int = 0
    a_localiser: int = 0
    avertissements: list = field(default_factory=list)

    def resume(self):
        morceaux = [f"{self.crees} adhérent(s) créé(s)"]
        if self.mis_a_jour:
            morceaux.append(f"{self.mis_a_jour} mis à jour")
        if self.supprimes:
            morceaux.append(f"{self.supprimes} ancienne(s) fiche(s) supprimée(s)")
        morceaux.append(f"{self.exclus} exclu(s) (cotisation hors période)")
        if self.ignores:
            morceaux.append(f"{self.ignores} ligne(s) ignorée(s)")
        texte = "Import terminé : " + ", ".join(morceaux) + "."
        if self.a_localiser:
            texte += f" {self.a_localiser} adresse(s) restent à localiser (bouton ci-dessous)."
        return texte


def _cle(adherent):
    return normaliser(adherent.adresse_geocodage)


def _avertir(bilan, message):
    if len(bilan.avertissements) < MAX_AVERTISSEMENTS:
        bilan.avertissements.append(message)


def importer(octets, annees, remplacer):
    """Importe l'export (octets). annees : liste d'entiers à conserver. Retourne un Bilan."""
    lignes, manquantes = lire_export(decoder(octets))
    if manquantes:
        raise ErreurImport("Colonnes absentes de l'export : " + ", ".join(manquantes))

    voulues = set(annees)
    bilan = Bilan()
    nouveaux = []
    for ligne in lignes:
        numero = ligne["_numero"]
        if not ligne.get("adresse", "") or not (ligne.get("nom", "") or ligne.get("prenom", "")):
            bilan.ignores += 1
            _avertir(bilan, f"Ligne {numero} ignorée (adresse ou nom vide).")
            continue
        annees_ligne = annees_depuis(ligne.get("annees_cotisation", ""))
        if not voulues & set(annees_ligne):
            bilan.exclus += 1
            continue
        try:
            derniere_visite = lire_date(ligne.get("derniere_visite", ""))
        except ValueError as erreur:
            derniere_visite = None
            _avertir(bilan, f"Ligne {numero} : {erreur} (importée sans date de visite).")
        adherent = Adherent(
            identifiant=ligne.get("identifiant", ""),
            civilite=ligne.get("civilite", ""),
            prenom=ligne.get("prenom", ""),
            nom=ligne.get("nom", ""),
            adresse=ligne.get("adresse", ""),
            complement_adresse=ligne.get("complement", ""),
            code_postal=ligne.get("code_postal", ""),
            commune=ligne.get("commune", ""),
            telephone=ligne.get("telephone", ""),
            email=ligne.get("email", ""),
            derniere_visite=derniere_visite,
            annees_cotisation=", ".join(str(a) for a in annees_ligne),
        )
        nouveaux.append((adherent, ligne.get("secteur", "")))

    if not nouveaux:
        raise ErreurImport("Aucun adhérent retenu (vérifiez l'année) : la base n'a pas été modifiée.")

    anciennes = {}
    for a in Adherent.objects.filter(latitude__isnull=False, longitude__isnull=False):
        anciennes.setdefault(_cle(a), (a.latitude, a.longitude))

    secteurs = {}

    def secteur(nom):
        if not nom:
            return None
        if nom not in secteurs:
            secteurs[nom], _ = Secteur.objects.get_or_create(nom=nom)
        return secteurs[nom]

    with transaction.atomic():
        if remplacer:
            bilan.supprimes = Adherent.objects.count()
            Adherent.objects.all().delete()
            for adherent, nom_secteur in nouveaux:
                adherent.secteur = secteur(nom_secteur)
                coordonnees = anciennes.get(_cle(adherent))
                if coordonnees:
                    adherent.latitude, adherent.longitude = coordonnees
            Adherent.objects.bulk_create([a for a, _ in nouveaux], batch_size=200)
            bilan.crees = len(nouveaux)
        else:
            existants = {a.identifiant: a for a in Adherent.objects.exclude(identifiant="")}
            a_creer = []
            for adherent, nom_secteur in nouveaux:
                adherent.secteur = secteur(nom_secteur)
                coordonnees = anciennes.get(_cle(adherent))
                actuel = existants.get(adherent.identifiant) if adherent.identifiant else None
                if actuel is None:
                    if coordonnees:
                        adherent.latitude, adherent.longitude = coordonnees
                    a_creer.append(adherent)
                    continue
                adresse_changee = _cle(actuel) != _cle(adherent)
                for champ in CHAMPS:
                    setattr(actuel, champ, getattr(adherent, champ))
                if adresse_changee:
                    actuel.latitude, actuel.longitude = coordonnees if coordonnees else (None, None)
                actuel.save()
                bilan.mis_a_jour += 1
            Adherent.objects.bulk_create(a_creer, batch_size=200)
            bilan.crees = len(a_creer)

    bilan.a_localiser = Adherent.objects.filter(latitude__isnull=True).count()
    return bilan
