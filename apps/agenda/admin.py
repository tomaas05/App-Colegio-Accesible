from django.contrib import admin

from .models import Ejecucion, EjecucionPaso


class EjecucionPasoInline(admin.TabularInline):
    model = EjecucionPaso
    extra = 0


@admin.register(Ejecucion)
class EjecucionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "fecha", "estado", "inicio_real", "fin_real")
    list_filter = ("estado", "fecha")
    inlines = [EjecucionPasoInline]
