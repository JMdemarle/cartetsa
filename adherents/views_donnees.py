"""Export / mise à jour des adhérents depuis le site (réservé au statut « équipe »)."""
import csv
import logging
from functools import wraps

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .export_fnosad import annees_depuis, securiser_csv
from .geocodage import geocoder
from .importation import ErreurImport, importer
from .models import Adherent

journal = logging.getLogger("adherents.acces")

TAILLE_MAX = 10 * 1024 * 1024  # 10 Mo
LOT_GEOCODAGE = 8
ENTETES_EXPORT = [
    "Identifiant", "Civilité", "Prénom", "Nom", "Adresse", "Complément d'adresse",
    "Code postal", "Commune", "Téléphone", "Email", "Dernière visite",
    "Années de cotisation", "Secteur",
]


def staff_requis(vue):
    """Réservé aux comptes actifs ayant le statut « équipe » (accès à l'administration)."""

    @wraps(vue)
    @login_required
    def enveloppe(request, *args, **kwargs):
        if not (request.user.is_active and request.user.is_staff):
            raise PermissionDenied
        return vue(request, *args, **kwargs)

    return enveloppe


class ImportForm(forms.Form):
    fichier = forms.FileField(label="Export CSV du logiciel FNOSAD")
    annees = forms.CharField(
        label="Année(s) de cotisation à conserver",
        max_length=60,
        help_text="Exemples : 2026 ou 2025, 2026. Seuls les adhérents cotisants sont importés.",
    )
    mode = forms.ChoiceField(
        label="Mode de mise à jour",
        choices=[
            ("remplacer", "Remplacer toute la liste (recommandé : les adhérents absents du fichier disparaissent)"),
            ("ajouter", "Ajouter les nouveaux et mettre à jour les existants (même identifiant), sans rien supprimer"),
        ],
        widget=forms.RadioSelect,
        initial="remplacer",
    )

    def clean_fichier(self):
        fichier = self.cleaned_data["fichier"]
        if fichier.size > TAILLE_MAX:
            raise ValidationError("Fichier trop volumineux (10 Mo maximum).")
        if not fichier.name.lower().endswith((".csv", ".txt")):
            raise ValidationError("Choisissez un fichier .csv.")
        return fichier

    def clean_annees(self):
        annees = annees_depuis(self.cleaned_data["annees"])
        if not annees:
            raise ValidationError("Indiquez au moins une année (exemple : 2026).")
        return annees


@staff_requis
@never_cache
@require_http_methods(["GET", "POST"])
def donnees(request):
    if request.method == "POST":
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                bilan = importer(
                    form.cleaned_data["fichier"].read(),
                    form.cleaned_data["annees"],
                    form.cleaned_data["mode"] == "remplacer",
                )
            except ErreurImport as erreur:
                form.add_error(None, str(erreur))
            else:
                journal.info(
                    "import adherents utilisateur=%s mode=%s crees=%d mis_a_jour=%d supprimes=%d",
                    request.user.get_username(), form.cleaned_data["mode"],
                    bilan.crees, bilan.mis_a_jour, bilan.supprimes,
                )
                messages.success(request, bilan.resume())
                for avertissement in bilan.avertissements:
                    messages.warning(request, avertissement)
                return redirect("donnees")
    else:
        form = ImportForm(initial={"annees": str(timezone.localdate().year)})
    return render(
        request,
        "adherents/donnees.html",
        {
            "form": form,
            "total": Adherent.objects.count(),
            "a_localiser": Adherent.objects.filter(latitude__isnull=True).count(),
        },
    )


@staff_requis
@never_cache
@require_GET
def export_csv(request):
    reponse = HttpResponse(content_type="text/csv; charset=utf-8")
    reponse["Content-Disposition"] = (
        f'attachment; filename="adherents_{timezone.localdate():%Y-%m-%d}.csv"'
    )
    reponse.write("\ufeff")  # BOM : Excel reconnaît l'UTF-8
    ecrivain = csv.writer(reponse, delimiter=";")
    ecrivain.writerow(ENTETES_EXPORT)
    lignes = 0
    for a in Adherent.objects.select_related("secteur").order_by("nom", "prenom").iterator():
        ecrivain.writerow(
            [
                securiser_csv(valeur)
                for valeur in (
                    a.identifiant, a.civilite, a.prenom, a.nom, a.adresse, a.complement_adresse,
                    a.code_postal, a.commune, a.telephone, a.email,
                    a.derniere_visite.strftime("%d/%m/%Y") if a.derniere_visite else "",
                    a.annees_cotisation, a.secteur.nom if a.secteur else "",
                )
            ]
        )
        lignes += 1
    journal.info("export adherents utilisateur=%s lignes=%d", request.user.get_username(), lignes)
    return reponse


@staff_requis
@never_cache
@require_POST
def geocoder_lot(request):
    """Localise un petit lot d'adresses (appelé en boucle par la page pour éviter les délais d'attente)."""
    try:
        apres = int(request.POST.get("apres_id", 0))
    except ValueError:
        apres = 0
    lot = list(
        Adherent.objects.filter(latitude__isnull=True, id__gt=apres).order_by("id")[:LOT_GEOCODAGE]
    )
    reussis = 0
    for adherent in lot:
        resultat = geocoder(adherent.adresse_geocodage)  # adresse seule
        if resultat:
            adherent.latitude, adherent.longitude = resultat[0], resultat[1]
            adherent.save(update_fields=["latitude", "longitude", "modifie_le"])
            reussis += 1
    dernier = lot[-1].id if lot else apres
    restants = Adherent.objects.filter(latitude__isnull=True, id__gt=dernier).count()
    return JsonResponse(
        {"traites": len(lot), "reussis": reussis, "dernier_id": dernier, "restants": restants}
    )
