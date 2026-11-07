from django.contrib import admin

from .models import Asignatura, Franja, HorarioClase


@admin.register(Franja)
class FranjaAdmin(admin.ModelAdmin):
    list_display = ("orden", "hora_inicio", "hora_fin")


@admin.register(Asignatura)
class AsignaturaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo")
    list_filter = ("tipo",)
    search_fields = ("nombre",)


@admin.register(HorarioClase)
class HorarioClaseAdmin(admin.ModelAdmin):
    list_display = ("clase", "dia_semana", "franja", "asignatura")
    list_filter = ("clase", "dia_semana")
