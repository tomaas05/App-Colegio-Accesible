"""Datos de la estructura común de todas las pantallas (templates/base.html). Decisión 0003.

Sin efectos secundarios y sin consultas a la base de datos: solo lee `request.user`
(ya cargado por la sesión) y resuelve direcciones.
"""

from .navegacion import inicio_de, navegacion_de


def navegacion(request):
    """`inicio_url` (a dónde lleva el logotipo) y `nav_principal` (panel lateral del adulto).

    El estudiante no tiene panel lateral: su pantalla tiene pocos elementos.
    """
    usuario = getattr(request, "user", None)
    contexto = {"inicio_url": inicio_de(usuario), "nav_principal": None}
    if getattr(usuario, "is_authenticated", False) and not usuario.es_estudiante:
        contexto["nav_principal"] = navegacion_de(usuario, request.path)
    return contexto
