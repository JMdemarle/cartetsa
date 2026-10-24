import time

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from adherents.export_fnosad import annees_depuis, decoder, lire_date, lire_export
from adherents.geocodage import geocoder
from adherents.models import Adherent, Secteur


class Command(BaseCommand):
    help = (
        "Importe l'export CSV du logiciel FNOSAD. Ne conserve que les adhérents dont les "
        "« Années de cotisation » contiennent au moins une des années passées avec --annee. "
        "Seules les colonnes utiles sont lues ; les autres ne sont jamais enregistrées."
    )

    def add_arguments(self, parser):
        parser.add_argument("fichier")
        parser.add_argument(
            "--annee",
            type=int,
            action="append",
            required=True,
            help="Année de cotisation à conserver (répétable : --annee 2025 --annee 2026).",
        )
        parser.add_argument(
            "--remplacer",
            action="store_true",
            help="Remplace toute la base (les adhérents absents de l'export disparaissent).",
        )
        parser.add_argument("--sans-geocodage", action="store_true")

    def handle(self, *args, **options):
        try:
            with open(options["fichier"], "rb") as f:
                octets = f.read()
        except OSError as erreur:
            raise CommandError(str(erreur))

        lignes, manquantes = lire_export(decoder(octets))
        if manquantes:
            raise CommandError(f"Colonnes absentes de l'export : {', '.join(manquantes)}")
        if lignes and "secteur" not in lignes[0]:
            self.stderr.write(
                "Colonne « Secteur » absente : seuls les superutilisateurs et les comptes "
                "« accès à tous les secteurs » verront les adhérents."
            )

        annees_voulues = set(options["annee"])
        a_enregistrer = []
        exclus = 0
        non_localises = 0

        for ligne in lignes:
            numero = ligne["_numero"]
            if not ligne["adresse"] or not (ligne["nom"] or ligne["prenom"]):
                self.stderr.write(f"Ligne {numero} ignorée (adresse ou nom vide).")
                continue
            annees = annees_depuis(ligne["annees_cotisation"])
            if not annees_voulues & set(annees):
                exclus += 1
                continue
            try:
                derniere_visite = lire_date(ligne["derniere_visite"])
            except ValueError as erreur:
                self.stderr.write(f"Ligne {numero} : {erreur} (importée sans date de visite).")
                derniere_visite = None

            adherent = Adherent(
                identifiant=ligne["identifiant"],
                civilite=ligne["civilite"],
                prenom=ligne["prenom"],
                nom=ligne["nom"],
                adresse=ligne["adresse"],
                complement_adresse=ligne["complement"],
                code_postal=ligne["code_postal"],
                commune=ligne["commune"],
                telephone=ligne["telephone"],
                email=ligne["email"],
                derniere_visite=derniere_visite,
                annees_cotisation=", ".join(str(a) for a in annees),
            )
            if not options["sans_geocodage"]:
                resultat = geocoder(adherent.adresse_geocodage)  # adresse seule, sans complément
                if resultat:
                    adherent.latitude, adherent.longitude = resultat[0], resultat[1]
                else:
                    non_localises += 1
                    self.stderr.write(f"Ligne {numero} : adresse non localisée.")
                time.sleep(0.05)
            a_enregistrer.append((adherent, ligne.get("secteur", "")))

        if not a_enregistrer:
            raise CommandError("Aucun adhérent retenu (vérifiez --annee) : base inchangée.")

        with transaction.atomic():
            if options["remplacer"]:
                Adherent.objects.all().delete()
            for adherent, nom_secteur in a_enregistrer:
                if nom_secteur:
                    adherent.secteur, _ = Secteur.objects.get_or_create(nom=nom_secteur)
                adherent.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"{len(a_enregistrer)} adhérent(s) importé(s), {exclus} exclu(s) "
                f"(cotisation hors {sorted(annees_voulues)}), {non_localises} non localisé(s)."
            )
        )
