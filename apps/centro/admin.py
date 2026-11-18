from django.contrib import admin

from .models import (
    AsistenciaComedor,
    ClaseComedorTerminada,
    ComedorDelDia,
    RepartoMenu,
    TareaDelCentro,
    TrabajoReprografia,
)


@admin.register(TareaDelCentro)
class TareaDelCentroAdmin(admin.ModelAdmin):
    list_display = ("tipo", "tarea")


@admin.register(ComedorDelDia)
class ComedorDelDiaAdmin(admin.ModelAdmin):
    list_display = ("fecha", "asignacion")
    date_hierarchy = "fecha"


@admin.register(RepartoMenu)
class RepartoMenuAdmin(admin.ModelAdmin):
    list_display = ("mes", "asignacion", "menu")


@admin.register(AsistenciaComedor)
class AsistenciaComedorAdmin(admin.ModelAdmin):
    list_display = ("fecha", "estudiante", "come", "anotada_por")
    list_filter = ("come", "estudiante__clase")
    date_hierarchy = "fecha"


@admin.register(ClaseComedorTerminada)
class ClaseComedorTerminadaAdmin(admin.ModelAdmin):
    list_display = ("fecha", "clase", "terminada_por", "terminada_en")
    date_hierarchy = "fecha"


@admin.register(TrabajoReprografia)
class TrabajoReprografiaAdmin(admin.ModelAdmin):
    list_display = ("asignacion", "copias", "imprimir", "fotocopiar", "plastificar", "aula")
