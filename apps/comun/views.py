"""Buscador de pictogramas de ARASAAC en el servidor (decisión 0004).

Solo lectura y solo para adultos. El navegador pide aquí la búsqueda y las imágenes;
a ARASAAC solo habla el servidor (apps/comun/pictogramas.py).
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from . import pictogramas

BUSQUEDAS_POR_MINUTO = 30
IMAGENES_POR_MINUTO = 240  # cada búsqueda enseña hasta 12 vistas previas
UN_ANO = 365 * 24 * 60 * 60
# El nombre del campo del formulario al que irá el pictograma elegido.
CAMPOS = ("arasaac_id_tarea", "arasaac_id_paso")


def solo_adultos(vista):
    """Con sesión y sin ser estudiante. Sin sesión, a la portada; un estudiante, 403."""

    @login_required
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if request.user.es_estudiante:
            raise PermissionDenied
        return vista(request, *args, **kwargs)

    return envoltura


def _campo(nombre):
    """Solo se aceptan los campos del formulario de tareas: arasaac_id_tarea o pasos-N-…"""
    if nombre == "arasaac_id_tarea":
        return nombre
    partes = nombre.split("-")
    if len(partes) == 3 and partes[0] == "pasos" and partes[1].isdigit() and partes[2] == CAMPOS[1]:
        return nombre
    return "arasaac_id_tarea"


@solo_adultos
@require_GET
def buscar(request):
    """GET /pictogramas/buscar/?q=perro&campo=arasaac_id_tarea → parcial para HTMX."""
    campo = _campo(request.GET.get("campo", ""))
    texto = pictogramas.texto_valido(request.GET.get("q", ""))
    contexto = {"campo": campo, "texto": texto, "resultados": [], "aviso": ""}
    if not texto:
        contexto["aviso"] = "Escribe una palabra de 2 a 40 letras para buscar."
    else:
        try:
            pictogramas.contar_peticion(request.user, "buscar", BUSQUEDAS_POR_MINUTO)
            contexto["resultados"] = pictogramas.buscar(texto)
        except pictogramas.DemasiadasPeticiones:
            contexto["aviso"] = "Has buscado muchas veces seguidas. Espera un minuto."
        except pictogramas.ErrorArasaac:
            contexto["aviso"] = (
                "Ahora no se puede buscar en ARASAAC. "
                "Puedes subir una imagen de tu equipo con «Imagen»."
            )
    return render(request, "comun/_pictogramas_resultados.html", contexto)


@solo_adultos
@require_GET
def vista_previa(request, identificador):
    """GET /pictogramas/<id>.png: la copia local del pictograma (se descarga una vez)."""
    try:
        pictogramas.contar_peticion(request.user, "imagen", IMAGENES_POR_MINUTO)
        ruta = pictogramas.obtener(identificador)
    except pictogramas.DemasiadasPeticiones:
        return HttpResponse(status=429)
    except pictogramas.ErrorArasaac:
        raise Http404("No se ha podido traer el pictograma.") from None
    respuesta = FileResponse(default_storage.open(ruta), content_type="image/png")
    # El pictograma de un número no cambia: el navegador no vuelve a pedirlo.
    respuesta["Cache-Control"] = f"private, max-age={UN_ANO}, immutable"
    respuesta["X-Content-Type-Options"] = "nosniff"
    return respuesta
