import csv
import os
import secrets

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from adherents.models import ProfilTSA, Secteur

ALPHABET = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class Command(BaseCommand):
    help = (
        "Crée les comptes depuis un CSV (identifiant;email;prenom;nom;secteurs;voit_tout). "
        "Secteurs séparés par |. Les mots de passe initiaux sont écrits dans un fichier à "
        "transmettre de façon sécurisée puis à supprimer."
    )

    def add_arguments(self, parser):
        parser.add_argument("fichier")
        parser.add_argument("--sortie", default="mots_de_passe_initiaux.csv")

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            f = open(options["fichier"], newline="", encoding="utf-8-sig")
        except OSError as erreur:
            raise CommandError(str(erreur))
        resultats = []
        with f:
            echantillon = f.readline()
            f.seek(0)
            for ligne in csv.DictReader(f, delimiter=";" if ";" in echantillon else ","):
                ligne = {k.strip().lower(): (v or "").strip() for k, v in ligne.items() if k}
                identifiant = ligne.get("identifiant", "")
                if not identifiant:
                    continue
                if User.objects.filter(username=identifiant).exists():
                    self.stderr.write(f"{identifiant} existe déjà : ignoré.")
                    continue
                mot_de_passe = "".join(secrets.choice(ALPHABET) for _ in range(16))
                utilisateur = User.objects.create_user(
                    username=identifiant,
                    email=ligne.get("email", ""),
                    password=mot_de_passe,
                    first_name=ligne.get("prenom", ""),
                    last_name=ligne.get("nom", ""),
                )
                profil = ProfilTSA.objects.create(
                    user=utilisateur,
                    doit_changer_mdp=True,
                    voit_tout=ligne.get("voit_tout", "").lower() in {"oui", "1", "true", "x"},
                )
                for nom in (n.strip() for n in ligne.get("secteurs", "").split("|")):
                    if nom:
                        secteur, _ = Secteur.objects.get_or_create(nom=nom)
                        profil.secteurs.add(secteur)
                resultats.append((identifiant, mot_de_passe))

        descripteur = os.open(options["sortie"], os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descripteur, "w", newline="", encoding="utf-8") as sortie:
            ecrivain = csv.writer(sortie, delimiter=";")
            ecrivain.writerow(["identifiant", "mot_de_passe_initial"])
            ecrivain.writerows(resultats)
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(resultats)} compte(s) créé(s). Mots de passe dans {options['sortie']} "
                "(à transmettre puis supprimer ; changement obligatoire à la 1re connexion)."
            )
        )
