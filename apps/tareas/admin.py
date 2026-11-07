from django.contrib import admin

from .models import Asignacion, Paso, Tarea


class PasoInline(admin.TabularInline):
    model = Paso
    extra = 0


@admin.register(Tarea)
class TareaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "ambito", "creador")
    list_filter = ("ambito",)
    search_fields = ("nombre",)
    inlines = [PasoInline]


@admin.register(Asignacion)
class AsignacionAdmin(admin.ModelAdmin):
    list_display = (
        "tarea",
        "estudiante",
        "hora_inicio",
        "hora_fin",
        "dias_semana",
        "vigencia_desde",
        "vigencia_hasta",
    )
    list_filter = ("estudiante__clase", "tarea__ambito")
    search_fields = ("tarea__nombre", "estudiante__usuario__first_name")
