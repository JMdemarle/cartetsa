import time

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from adherents.export_fnosad import decoder, lire_csv
from adherents.geocodage import geocoder
from adherents.models import TSA

COLONNES = {
    "nom": ("nom",),
    "prenom": ("prenom",),
    "telephone": ("telephone", "tel", "portable", "mobile"),
    "email": ("email", "mail", "e-mail", "courriel"),
    "adresse": ("adresse",),
    "code_postal": ("code postal", "cp"),
    "commune": ("commune", "ville"),
}


class Command(BaseCommand):
    help = (
        "Importe la liste des TSA depuis un CSV "
        "(nom;prenom;telephone;email;adresse;code_postal;commune). "
        "Avec --remplacer, la liste existante est entièrement remplacée."
    )

    def add_arguments(self, parser):
        parser.add_argument("fichier")
        parser.add_argument("--remplacer", action="store_true")
        parser.add_argument("--sans-geocodage", action="store_true")

    def handle(self, *args, **options):
        try:
            with open(options["fichier"], "rb") as f:
                octets = f.read()
        except OSError as erreur:
            raise CommandError(str(erreur))

        lignes, manquantes = lire_csv(decoder(octets), COLONNES, ("nom", "adresse"))
        if manquantes:
            raise CommandError(f"Colonnes absentes : {', '.join(manquantes)}")

        a_enregistrer = []
        non_localises = 0
        for ligne in lignes:
            numero = ligne["_numero"]
            if not ligne["nom"] or not ligne["adresse"]:
                self.stderr.write(f"Ligne {numero} ignorée (nom ou adresse vide).")
                continue
            tsa = TSA(
                nom=ligne["nom"],
                prenom=ligne.get("prenom", ""),
                telephone=ligne.get("telephone", ""),
                email=ligne.get("email", ""),
                adresse=ligne["adresse"],
                code_postal=ligne.get("code_postal", ""),
                commune=ligne.get("commune", ""),
            )
            if not options["sans_geocodage"]:
                resultat = geocoder(tsa.adresse_geocodage)
                if resultat:
                    tsa.latitude, tsa.longitude = resultat[0], resultat[1]
                else:
                    non_localises += 1
                    self.stderr.write(f"Ligne {numero} : adresse non localisée.")
                time.sleep(0.05)
            a_enregistrer.append(tsa)

        if not a_enregistrer:
            raise CommandError("Aucun TSA à importer : base inchangée.")

        with transaction.atomic():
            if options["remplacer"]:
                TSA.objects.all().delete()
            for tsa in a_enregistrer:
                tsa.save()

        self.stdout.write(
            self.style.SUCCESS(f"{len(a_enregistrer)} TSA importé(s), {non_localises} non localisé(s).")
        )
