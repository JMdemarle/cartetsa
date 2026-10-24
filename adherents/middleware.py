from urllib.parse import urlparse

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class ChangementMotDePasseMiddleware:
    """Oblige les comptes nouvellement créés à choisir leur mot de passe."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            profil = getattr(user, "profil", None)
            if profil is not None and profil.doit_changer_mdp:
                autorises = {
                    reverse("password_change"),
                    reverse("password_change_done"),
                    reverse("logout"),
                }
                static = "/" + settings.STATIC_URL.strip("/") + "/"
                if request.path not in autorises and not request.path.startswith(static):
                    return redirect("password_change")
        return self.get_response(request)


class EnTetesSecuriteMiddleware:
    """En-têtes de sécurité (CSP restrictive : seul le fond de carte vient d'ailleurs)."""

    def __init__(self, get_response):
        self.get_response = get_response
        tuiles = urlparse(settings.TILE_URL)
        origine = f"{tuiles.scheme}://{tuiles.netloc}" if tuiles.netloc and "{" not in tuiles.netloc else "https:"
        self.csp = "; ".join(
            [
                "default-src 'self'",
                f"img-src 'self' data: {origine}",
                "style-src 'self' 'unsafe-inline'",
                "script-src 'self'",
                "connect-src 'self'",
                "object-src 'none'",
                "base-uri 'self'",
                "form-action 'self'",
                "frame-ancestors 'none'",
            ]
        )
        self.prefixe_admin = "/" + settings.ADMIN_URL

    def __call__(self, request):
        reponse = self.get_response(request)
        if not request.path.startswith(self.prefixe_admin):
            reponse.headers.setdefault("Content-Security-Policy", self.csp)
        reponse.headers.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
        return reponse
