"""Context processor del perfil visual del estudiante (HU-04-01)."""

from django.contrib.auth import logout

from .models import Perfil

RUTAS_ENTRADA = ("/estudiante/", "/entrar/")


def perfil_estudiante(request):
    """Añade `perfil_activo` al contexto si hay un estudiante dentro de su agenda."""
    usuario = getattr(request, "user", None)
    if not usuario or not usuario.is_authenticated or not getattr(usuario, "es_estudiante", False):
        return {"perfil_activo": None}

    # Si vuelve a la portada «¿Quién eres?» o a elegir clase/avatar, se cierra
    # la sesión del estudiante anterior para que el siguiente empiece limpio.
    if request.path == "/" or request.path.startswith(RUTAS_ENTRADA):
        if request.method == "GET":
            logout(request)
        return {"perfil_activo": None}

    return {"perfil_activo": Perfil.objects.filter(estudiante_id=usuario.pk).first()}
