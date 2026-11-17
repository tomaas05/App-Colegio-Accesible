"""Pantallas del área 6 · Seguimiento (HU-06-02, Manu)."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.agenda import servicios as agenda
from apps.usuarios.consulta import fecha_en_texto
from apps.usuarios.models import Rol

from . import servicios

# PA3 y PA4: el tutor ve a sus estudiantes y el profesional, a los que atiende.
ROLES = (Rol.TUTOR, Rol.PROFESIONAL)


@login_required
@require_GET
def hoy(request):
    """B50 · Seguimiento de hoy: cómo van las tareas de cada estudiante y los avisos de
    plan B. Solo consulta: no hay nada que cambiar en esta pantalla (PA4)."""
    if request.user.rol not in ROLES:
        raise PermissionDenied("Solo el tutor y el profesional ven el seguimiento.")
    ahora = agenda.ahora()
    estados = servicios.seguimiento(request.user, ahora)
    return render(
        request,
        "seguimiento/hoy.html",
        {
            "estados": estados,
            "con_avisos": sum(1 for e in estados if e.avisos),
            "fecha_texto": fecha_en_texto(ahora.date()),
            "ahora": ahora,
            "es_tutor": request.user.rol == Rol.TUTOR,
        },
    )
