from django.contrib import admin

from .models import Asignacion, ExcepcionAsignacion, Paso, PlanB, Tarea


class PasoInline(admin.TabularInline):
    model = Paso
    extra = 0


class PlanBInline(admin.TabularInline):
    model = PlanB
    fk_name = "tarea"
    extra = 0
    autocomplete_fields = ("alternativa",)


class ExcepcionInline(admin.TabularInline):
    model = ExcepcionAsignacion
    extra = 0


@admin.register(Tarea)
class TareaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "ambito", "creador")
    list_filter = ("ambito",)
    search_fields = ("nombre",)
    inlines = [PasoInline, PlanBInline]


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
        "cancelada",
    )
    list_filter = ("estudiante__clase", "tarea__ambito", "cancelada")
    search_fields = ("tarea__nombre", "estudiante__usuario__first_name")
    inlines = [ExcepcionInline]
