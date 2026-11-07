from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Atencion, Clase, Estudiante, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "rol", "is_active")
    list_filter = ("rol", "is_active")
    search_fields = ("username", "first_name", "last_name")
    ordering = ("rol", "first_name")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Datos personales", {"fields": ("first_name", "last_name", "email", "rol")}),
        ("Estado", {"fields": ("is_active", "is_staff", "is_superuser", "groups")}),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "first_name", "last_name", "rol", "password1", "password2"),
            },
        ),
    )


@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    list_display = ("nombre", "curso_escolar")
    list_filter = ("curso_escolar",)


class AtencionInline(admin.TabularInline):
    model = Atencion
    extra = 0
    autocomplete_fields = ("profesional",)


@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display = ("__str__", "codigo_estudiante", "clase", "tutor", "familiar")
    list_filter = ("clase",)
    search_fields = ("codigo_estudiante", "usuario__first_name", "usuario__last_name")
    autocomplete_fields = ("usuario", "tutor", "familiar")
    inlines = [AtencionInline]


@admin.register(Atencion)
class AtencionAdmin(admin.ModelAdmin):
    list_display = ("profesional", "estudiante", "fecha_alta")
    list_filter = ("profesional",)
