from django.contrib import admin

from .models import Perfil


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = (
        "estudiante",
        "tema",
        "paleta",
        "tamano_letra",
        "tamano_botones",
        "tipo_temporizador",
        "metodo_acceso",
        "usa_lector_pantalla",
    )
    list_filter = ("tema", "paleta", "tipo_temporizador", "metodo_acceso", "usa_lector_pantalla")
