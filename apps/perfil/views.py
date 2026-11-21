"""Pantallas de configuración del perfil visual del estudiante (Jorge): HU-04-01.

Boceto: docs/iteracion-1/bocetos/despega_mockup_v3.html, pantalla B52 (Tutor · Perfil visual).
Revisión con la profesora (decisión 0005): el tutor entra por «Alumnos», elige uno y configura
su perfil por categorías, en tarjetas y sin desplazarse; nada se guarda hasta pulsar «Guardar».
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
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
    """«Alumnos»: los estudiantes del tutor; al pulsar uno se abre su perfil visual.

    Retrospectiva del 19/11: buscador por nombre, apellidos o código (se aplica al pulsar
    «Buscar», WCAG 3.2.2).
    """
    texto = (request.GET.get("q") or "").strip()[:80]
    estudiantes = _mis_estudiantes(request.user)
    total = estudiantes.count()
    if texto:
        estudiantes = estudiantes.filter(
            Q(usuario__first_name__icontains=texto)
            | Q(usuario__last_name__icontains=texto)
            | Q(codigo_estudiante__icontains=texto)
        )
    return render(
        request,
        "perfil/estudiantes.html",
        {"estudiantes": estudiantes, "texto": texto, "total": total},
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
            # «Guardar y salir» del aviso de cambios sin guardar: sigue a donde iba el tutor,
            # solo si es una dirección de esta misma web.
            siguiente = request.POST.get("siguiente", "")
            if siguiente and url_has_allowed_host_and_scheme(
                siguiente, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(siguiente)
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
