"""HU-06-03 · Consultar el día del estudiante (Manu). Solo el familiar."""

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from apps.usuarios import consulta
from apps.usuarios.models import Rol
from apps.usuarios.views import _fecha_pedida
from apps.usuarios.vinculos import estudiantes_de

from . import dia


def _solo_familiar(request):
    if request.user.rol != Rol.FAMILIAR:
        raise PermissionDenied("Esta pantalla es del familiar.")


@login_required
@require_GET
def elegir(request):
    """«Día en el colegio» del menú: con un solo estudiante, directamente su día; con
    varios (hermanos), primero se elige cuál."""
    _solo_familiar(request)
    estudiantes = list(estudiantes_de(request.user).order_by("usuario__first_name"))
    if len(estudiantes) == 1:
        return redirect("seguimiento:dia", codigo=estudiantes[0].codigo_estudiante)
    return render(request, "seguimiento/elegir_estudiante.html", {"estudiantes": estudiantes})


@login_required
@require_GET
def dia_del_estudiante(request, codigo):
    """B34 + B35 · El día del estudiante: tareas (solo consulta), comedor y menú.

    Se pasa de un día a otro con ?dia=AAAA-MM-DD, como en la agenda del profesional. Si no
    es su estudiante, 404: no se dice si existe (PA5).
    """
    _solo_familiar(request)
    suyos = estudiantes_de(request.user)
    estudiante = suyos.filter(codigo_estudiante=codigo.upper()).first()
    if estudiante is None:
        raise Http404("No es tu estudiante.")
    fecha, hoy = _fecha_pedida(request)
    return render(
        request,
        "seguimiento/dia_familiar.html",
        {
            "estudiante": estudiante,
            "fecha": fecha,
            "fecha_texto": consulta.fecha_en_texto(fecha),
            "es_hoy": fecha == hoy,
            "anterior": fecha - timedelta(days=1),
            "siguiente": fecha + timedelta(days=1),
            "tareas": consulta.tareas_del_dia(estudiante, fecha, request.user),
            "comedor": dia.comedor(estudiante, fecha, hoy),
            "menu": dia.menu(fecha),
            "varios": suyos.count() > 1,
        },
    )
