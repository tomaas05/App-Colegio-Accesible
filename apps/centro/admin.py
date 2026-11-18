from django.contrib import admin

from .models import ComedorDelDia, RepartoMenu, TareaDelCentro


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
