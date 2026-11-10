"""Pantallas de configuración del perfil visual del estudiante (Jorge): HU-04-01.

Boceto: docs/iteracion-1/bocetos/despega_mockup_v3.html, pantalla B52 (Tutor · Perfil visual).
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from apps.usuarios.models import Estudiante, Rol

from .forms import PerfilVisualForm
from .models import Perfil


def tutor_requerido(vista):
    """Solo un usuario con rol de tutor puede configurar perfiles (HU-04-01)."""

    @wraps(vista)
    @login_required
    def envoltura(request, *args, **kwargs):
        if request.user.rol != Rol.TUTOR:
            raise PermissionDenied
        return vista(request, *args, **kwargs)

    return envoltura


def _mis_estudiantes(tutor):
    return (
        Estudiante.objects.filter(tutor=tutor, usuario__is_active=True)
        .select_related("usuario", "clase", "perfil")
        .order_by("usuario__first_name", "usuario__last_name")
    )


@tutor_requerido
@require_GET
def elegir_estudiante(request):
    """Lista de estudiantes del tutor para elegir cuál personalizar."""
    estudiantes = _mis_estudiantes(request.user)
    return render(
        request,
        "perfil/estudiantes.html",
        {"estudiantes": estudiantes},
    )


@tutor_requerido
@require_http_methods(["GET", "POST"])
def editar_perfil(request, codigo):
    """B52 · Tutor · Perfil visual de un estudiante (HU-04-01)."""
    estudiante = get_object_or_404(
        _mis_estudiantes(request.user),
        codigo_estudiante=codigo.upper(),
    )
    perfil, _ = Perfil.objects.get_or_create(estudiante=estudiante)

    if request.method == "POST":
        form = PerfilVisualForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"Perfil visual de {estudiante.usuario.first_name} guardado correctamente.",
            )
            return redirect("perfil:editar", codigo=estudiante.codigo_estudiante)
    else:
        form = PerfilVisualForm(instance=perfil)

    return render(
        request,
        "perfil/editar.html",
        {
            "estudiante": estudiante,
            "perfil": perfil,
            "form": form,
            "estudiantes": _mis_estudiantes(request.user),
        },
    )
