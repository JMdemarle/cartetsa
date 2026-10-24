import time

from django.core.management.base import BaseCommand

from adherents.geocodage import geocoder
from adherents.models import Adherent


class Command(BaseCommand):
    help = "Géocode les adhérents qui n'ont pas encore de coordonnées."

    def handle(self, *args, **options):
        reussis = 0
        a_traiter = Adherent.objects.filter(latitude__isnull=True)
        total = a_traiter.count()
        for adherent in a_traiter:
            resultat = geocoder(adherent.adresse_geocodage)
            if resultat:
                adherent.latitude, adherent.longitude = resultat[0], resultat[1]
                adherent.save(update_fields=["latitude", "longitude", "modifie_le"])
                reussis += 1
            time.sleep(0.05)
        self.stdout.write(f"{reussis} adresse(s) localisée(s) sur {total}.")
