from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.carte, name="carte"),
    path("api/points/", views.api_points, name="api_points"),

    path("api/tsa/", views.api_tsa, name="api_tsa"),
    path("tsa/", views.tsa_publique, name="tsa_publique"),
    path("api/tsa-public/", views.api_tsa_publique, name="api_tsa_publique"),
   
    path("confidentialite/", views.confidentialite, name="confidentialite"),
    path(
        "connexion/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html", redirect_authenticated_user=True
        ),
        name="login",
    ),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="logout"),
    path("compte/mot-de-passe/", views.ChangerMotDePasse.as_view(), name="password_change"),
    path(
        "compte/mot-de-passe/ok/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="registration/password_change_done.html"
        ),
        name="password_change_done",
    ),
]
