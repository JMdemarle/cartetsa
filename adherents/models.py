from django.conf import settings
from django.db import models


class Secteur(models.Model):
    nom = models.CharField("nom", max_length=100, unique=True)

    class Meta:
        ordering = ["nom"]
        verbose_name = "secteur"

    def __str__(self):
        return self.nom


class Adherent(models.Model):
    identifiant = models.CharField("identifiant", max_length=100, blank=True)
    civilite = models.CharField("civilité", max_length=30, blank=True)
    prenom = models.CharField("prénom", max_length=100, blank=True)
    nom = models.CharField("nom", max_length=150, blank=True)
    adresse = models.CharField("adresse", max_length=255)
    complement_adresse = models.CharField("complément d'adresse", max_length=255, blank=True)
    code_postal = models.CharField("code postal", max_length=10, blank=True)
    commune = models.CharField("commune", max_length=100, blank=True)
    telephone = models.CharField("téléphone", max_length=30, blank=True)
    email = models.EmailField("e-mail", blank=True)
    derniere_visite = models.DateField("dernière visite", null=True, blank=True)
    annees_cotisation = models.CharField("années de cotisation", max_length=255, blank=True)
    # Sert uniquement à limiter les droits d'accès des TSA ; n'est pas affiché.
    secteur = models.ForeignKey(
        Secteur, null=True, blank=True, on_delete=models.SET_NULL, related_name="adherents"
    )
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nom", "prenom"]
        verbose_name = "adhérent"

    def __str__(self):
        return self.nom_complet or self.identifiant or f"Adhérent {self.pk}"

    @property
    def nom_complet(self):
        return " ".join(p for p in (self.civilite, self.prenom, self.nom) if p)

    @property
    def adresse_geocodage(self):
        """Adresse envoyée au service de géocodage : sans le complément, sans nom ni téléphone."""
        return " ".join(p for p in (self.adresse, self.code_postal, self.commune) if p)


class ProfilTSA(models.Model):
    """Droits d'un compte : secteurs visibles et changement de mot de passe obligatoire."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profil"
    )
    secteurs = models.ManyToManyField(Secteur, blank=True, verbose_name="secteurs visibles")
    voit_tout = models.BooleanField("accès à tous les secteurs", default=False)
    doit_changer_mdp = models.BooleanField(
        "doit changer son mot de passe à la prochaine connexion", default=True
    )

    class Meta:
        verbose_name = "profil TSA"
        verbose_name_plural = "profils TSA"

    def __str__(self):
        return f"Profil de {self.user}"


class TSA(models.Model):
    """Technicien sanitaire apicole : affiché sur la carte par une croix rouge."""

    nom = models.CharField("nom", max_length=150)
    prenom = models.CharField("prénom", max_length=100, blank=True)
    telephone = models.CharField("téléphone", max_length=30, blank=True)
    email = models.EmailField("e-mail", blank=True)
    adresse = models.CharField("adresse", max_length=255)
    code_postal = models.CharField("code postal", max_length=10, blank=True)
    commune = models.CharField("commune", max_length=100, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nom", "prenom"]
        verbose_name = "TSA"
        verbose_name_plural = "TSA"

    def __str__(self):
        return self.nom_complet

    @property
    def nom_complet(self):
        return " ".join(p for p in (self.prenom, self.nom) if p)

    @property
    def adresse_geocodage(self):
        return " ".join(p for p in (self.adresse, self.code_postal, self.commune) if p)
