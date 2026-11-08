"""Control de acceso de las pantallas del estudiante.

Los permisos se comprueban siempre en el servidor. Cuando Manu fusione la entrada del
estudiante (HU-01-06) solo hay que comprobar que `settings.LOGIN_URL` apunta a ella.
"""

import os
from functools import wraps

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import Http404

from apps.usuarios.models import Estudiante


def atajo_activo():
    """El atajo ?como= solo funciona con DEBUG y con AGENDA_ENTRAR_COMO=1 en el .env.

    No basta con DEBUG: el .env.example deja DEBUG=True y la demo se monta con él,
    así que en la demo cualquiera podría entrar como cualquier estudiante.
    """
    return settings.DEBUG and os.environ.get("AGENDA_ENTRAR_COMO") == "1"


def _entrar_como(request, codigo):
    """SOLO DESARROLLO: /agenda/?como=A01 entra como ese estudiante.

    Existe mientras no está la entrada real (HU-01-06). Se borra después.
    """
    try:
        estudiante = Estudiante.objects.select_related("usuario").get(
            codigo_estudiante=codigo.upper()
        )
    except Estudiante.DoesNotExist:
        raise Http404 from None
    login(request, estudiante.usuario, backend="django.contrib.auth.backends.ModelBackend")


def estudiante_requerido(vista):
    """Solo entra un estudiante con sesión. Deja el Estudiante en `request.estudiante`."""

    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if request.GET.get("como") and atajo_activo():
            _entrar_como(request, request.GET["como"])
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        estudiante = getattr(request.user, "estudiante", None)
        if estudiante is None:
            raise PermissionDenied  # un adulto no abre la agenda de un estudiante por aquí
        request.estudiante = estudiante
        return vista(request, *args, **kwargs)

    return envoltura
