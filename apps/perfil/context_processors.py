"""Context processor del perfil visual del estudiante (HU-04-01)."""

from .models import Perfil


def perfil_estudiante(request):
    """Añade `perfil_activo` al contexto si hay un estudiante con sesión.

    Sin efectos secundarios: cerrar la sesión al volver a la portada lo hace
    apps/usuarios/middleware.py, antes de llegar aquí.
    """
    usuario = getattr(request, "user", None)
    if not usuario or not usuario.is_authenticated or not getattr(usuario, "es_estudiante", False):
        return {"perfil_activo": None}
    return {"perfil_activo": Perfil.objects.filter(estudiante_id=usuario.pk).first()}
