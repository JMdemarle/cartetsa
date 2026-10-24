from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin  # importe aussi l'admin des utilisateurs

from .geocodage import geocoder
from .models import Adherent, ProfilTSA, Secteur

User = get_user_model()


@admin.register(Secteur)
class SecteurAdmin(admin.ModelAdmin):
    search_fields = ["nom"]


class LocaliseFilter(admin.SimpleListFilter):
    title = "géolocalisation"
    parameter_name = "localise"

    def lookups(self, request, model_admin):
        return (("oui", "Localisé"), ("non", "Non localisé"))

    def queryset(self, request, queryset):
        if self.value() == "oui":
            return queryset.filter(latitude__isnull=False)
        if self.value() == "non":
            return queryset.filter(latitude__isnull=True)
        return queryset


@admin.register(Adherent)
class AdherentAdmin(admin.ModelAdmin):
    list_display = ("nom_complet", "identifiant", "telephone", "commune", "derniere_visite", "secteur", "localise")
    list_filter = ("secteur", "derniere_visite", LocaliseFilter)
    search_fields = ("nom", "prenom", "identifiant", "adresse", "commune", "telephone", "email")
    actions = ["geocoder_selection"]

    @admin.display(boolean=True, description="Localisé")
    def localise(self, obj):
        return obj.latitude is not None and obj.longitude is not None

    def save_model(self, request, obj, form, change):
        adresse_modifiee = not change or {"adresse", "code_postal", "commune"} & set(form.changed_data)
        if adresse_modifiee:
            resultat = geocoder(obj.adresse_geocodage)
            if resultat:
                obj.latitude, obj.longitude = resultat[0], resultat[1]
            elif not {"latitude", "longitude"} & set(form.changed_data):
                obj.latitude = obj.longitude = None
        super().save_model(request, obj, form, change)

    @admin.action(description="Géocoder les adresses sélectionnées")
    def geocoder_selection(self, request, queryset):
        reussis = 0
        for adherent in queryset:
            resultat = geocoder(adherent.adresse_geocodage)
            if resultat:
                adherent.latitude, adherent.longitude = resultat[0], resultat[1]
                adherent.save(update_fields=["latitude", "longitude", "modifie_le"])
                reussis += 1
        self.message_user(
            request, f"{reussis} adresse(s) géocodée(s) sur {queryset.count()}.", messages.INFO
        )


class ProfilTSAInline(admin.StackedInline):
    model = ProfilTSA
    can_delete = False
    filter_horizontal = ("secteurs",)


class UtilisateurAdmin(UserAdmin):
    inlines = [ProfilTSAInline]


admin.site.unregister(User)
admin.site.register(User, UtilisateurAdmin)
