"""Quién crea y asigna tareas (HU-03-01, Úrsula).

Que haya sesión no basta (docs/contribuir.md): el diccionario de datos dice que una
tarea la asigna un tutor, un profesional o un familiar. Un estudiante no.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from apps.usuarios.models import Rol

ROLES_QUE_GESTIONAN_TAREAS = (Rol.TUTOR, Rol.PROFESIONAL, Rol.FAMILIAR)


def gestiona_tareas(vista):
    """Solo tutor, profesional o familiar. Sin sesión, a la portada; otro rol, 403."""

    @login_required
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if request.user.rol not in ROLES_QUE_GESTIONAN_TAREAS:
            raise PermissionDenied
        return vista(request, *args, **kwargs)

    return envoltura
