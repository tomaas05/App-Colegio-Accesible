"""Lo que se comprueba en cada petición antes de llegar a la pantalla (Manu).

1. Cierra la sesión del estudiante cuando vuelve a las pantallas de entrada.

Antes lo hacía el context processor del perfil al pintar la plantilla; un context
processor no debe tener efectos secundarios (se ejecuta en cada plantilla, también en
las de error). Aquí ocurre una vez, antes de la vista, y solo con GET.

2. HU-01-02: el adulto que entra con una contraseña temporal solo puede cambiarla o salir.
"""

from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse

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


class CambiarContrasenaTemporal:
    """Con una contraseña temporal, cualquier pantalla lleva a «Cambia tu contraseña» (B15).

    Se dejan pasar la propia pantalla, «Salir» y los archivos estáticos y subidos (el
    logotipo, las hojas de estilo), que no enseñan datos de nadie.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = getattr(request, "user", None)
        if (
            getattr(usuario, "is_authenticated", False)
            and usuario.es_adulto
            and usuario.debe_cambiar_contrasena
            and not self._se_deja_pasar(request.path)
        ):
            return redirect("usuarios:cambiar_contrasena")
        return self.get_response(request)

    @staticmethod
    def _se_deja_pasar(ruta):
        if ruta in (reverse("usuarios:cambiar_contrasena"), reverse("usuarios:salir")):
            return True
        prefijos = ("/" + settings.STATIC_URL.lstrip("/"), "/" + settings.MEDIA_URL.lstrip("/"))
        return ruta.startswith(prefijos)
