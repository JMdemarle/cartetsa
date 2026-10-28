import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from . import visites
from .acces import adherents_visibles, tsa_public
from .models import TSA, ProfilTSA

journal = logging.getLogger("adherents.acces")


@login_required
@never_cache
@require_GET
def carte(request):
    annee = timezone.localdate().year
    return render(
        request,
        "adherents/carte.html",
        {
            "tile_url": settings.TILE_URL,
            "tile_attribution": settings.TILE_ATTRIBUTION,
            "legende": visites.legende(annee),
        },
    )


@login_required
@never_cache
@require_GET
def api_points(request):
    annee = timezone.localdate().year
    visibles = adherents_visibles(request.user)
    localises = visibles.filter(latitude__isnull=False, longitude__isnull=False)
    points = [
        {
            "identifiant": a.identifiant,
            "civilite": a.civilite,
            "prenom": a.prenom,
            "nom": a.nom,
            "adresse": a.adresse,
            "complement": a.complement_adresse,
            "code_postal": a.code_postal,
            "commune": a.commune,
            "telephone": a.telephone,
            "email": a.email,
            "derniere_visite": a.derniere_visite.strftime("%d/%m/%Y") if a.derniere_visite else "",
            "annees_cotisation": a.annees_cotisation,
            "couleur": visites.COULEURS[visites.couleur_pour(a.derniere_visite, annee)],
            "lat": a.latitude,
            "lon": a.longitude,
        }
        for a in localises
    ]
    non_localises = visibles.filter(latitude__isnull=True).count()
    journal.info("consultation utilisateur=%s points=%d", request.user.get_username(), len(points))
    return JsonResponse({"points": points, "non_localises": non_localises})


def confidentialite(request):
    return render(
        request,
        "adherents/confidentialite.html",
        {
            "organisme_nom": settings.ORGANISME_NOM,
            "organisme_contact": settings.ORGANISME_CONTACT,
            "tsa_public": tsa_public(),
        },
    )


class ChangerMotDePasse(PasswordChangeView):
    template_name = "registration/password_change_form.html"
    success_url = reverse_lazy("password_change_done")

    def form_valid(self, form):
        reponse = super().form_valid(form)
        ProfilTSA.objects.filter(user=self.request.user).update(doit_changer_mdp=False)
        return reponse


def _points_tsa():
    return [
        {
            "prenom": t.prenom,
            "nom": t.nom,
            "adresse": t.adresse,
            "code_postal": t.code_postal,
            "commune": t.commune,
            "telephone": t.telephone,
            "email": t.email,
            "lat": t.latitude,
            "lon": t.longitude,
        }
        for t in TSA.objects.filter(latitude__isnull=False, longitude__isnull=False)
    ]


@login_required
@never_cache
@require_GET
def api_tsa(request):
    """Annuaire des TSA, mode protégé (utilisateurs connectés)."""
    return JsonResponse({"points": _points_tsa()})


@never_cache
@require_GET
def tsa_publique(request):
    """Page publique de l'annuaire des TSA (désactivée sauf TSA_PUBLIC=1)."""
    if not tsa_public():
        raise Http404
    return render(
        request,
        "adherents/tsa_publique.html",
        {"tile_url": settings.TILE_URL, "tile_attribution": settings.TILE_ATTRIBUTION},
    )


@never_cache
@require_GET
def api_tsa_publique(request):
    if not tsa_public():
        raise Http404
    return JsonResponse({"points": _points_tsa()})
