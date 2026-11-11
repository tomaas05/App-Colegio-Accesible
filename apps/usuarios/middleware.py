"""Cierra la sesión del estudiante cuando vuelve a las pantallas de entrada.

Antes lo hacía el context processor del perfil al pintar la plantilla; un context
processor no debe tener efectos secundarios (se ejecuta en cada plantilla, también en
las de error). Aquí ocurre una vez, antes de la vista, y solo con GET.
"""

from django.contrib.auth import logout

# La portada «¿Quién eres?», elegir clase y avatar, y la entrada de adultos.
RUTAS_ENTRADA = ("/estudiante/", "/entrar/")


def es_ruta_de_entrada(ruta):
    return ruta == "/" or ruta.startswith(RUTAS_ENTRADA)


class EstudianteSaleAlVolverALaEntrada:
    """Si un estudiante con sesión abre la portada, el siguiente empieza sin su sesión."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = getattr(request, "user", None)
        if (
            request.method == "GET"
            and es_ruta_de_entrada(request.path)
            and getattr(usuario, "is_authenticated", False)
            and getattr(usuario, "es_estudiante", False)
        ):
            logout(request)
        return self.get_response(request)
