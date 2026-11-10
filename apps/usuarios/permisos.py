"""Permisos por rol de las pantallas de usuarios (Manu).

Que haya sesión no basta: cada pantalla comprueba el rol en el servidor
(docs/contribuir.md, decisión 0002).
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import Rol


def admin_requerido(vista):
    """Solo el administrador del centro. Sin sesión, a la portada; con otro rol, 403."""

    @login_required
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if request.user.rol != Rol.ADMINISTRADOR:
            raise PermissionDenied
        return vista(request, *args, **kwargs)

    return envoltura
