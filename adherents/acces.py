from .models import Adherent


def adherents_visibles(user):
    """Adhérents que cet utilisateur a le droit de voir (principe du moindre privilège)."""
    qs = Adherent.objects.all()
    if user.is_superuser:
        return qs
    profil = getattr(user, "profil", None)
    if profil is None:
        return qs.none()
    if profil.voit_tout:
        return qs
    return qs.filter(secteur__in=profil.secteurs.all())


def tsa_public():
    """Vrai si l'annuaire des TSA est consultable sans connexion (variable TSA_PUBLIC=1)."""
    import os

    return os.environ.get("TSA_PUBLIC", "0").strip().lower() in {"1", "true", "yes", "oui"}
