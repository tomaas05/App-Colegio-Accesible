"""Pictogramas de ARASAAC servidos siempre desde nuestro servidor (decisión 0004).

RNF1.1.2: el navegador nunca habla con ARASAAC. Es el servidor quien busca y quien
descarga, una sola vez, cada pictograma elegido; la copia queda en
`media/pictogramas/<id>.png` y la comparten todas las tareas y pasos que lo usan.
Hacia ARASAAC solo sale la palabra buscada o el número del pictograma: ningún dato
de personas.

Pictogramas: Sergio Palao. Origen: ARASAAC (arasaac.org). Licencia: CC BY-NC-SA.
Propiedad: Gobierno de Aragón.
"""

import hashlib
import io
import re
import time
from urllib.parse import quote

import requests
from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image

from apps.usuarios.texto import normalizar

ATRIBUCION = (
    "Pictogramas: Sergio Palao. Origen: ARASAAC (arasaac.org). "
    "Licencia: CC BY-NC-SA. Propiedad: Gobierno de Aragón."
)

# Direcciones de ARASAAC. Se pueden cambiar en los ajustes si ARASAAC cambia su API.
URL_BUSQUEDA = getattr(
    settings, "ARASAAC_URL_BUSQUEDA", "https://api.arasaac.org/v1/pictograms/es/search/{texto}"
)
URL_IMAGEN = getattr(
    settings, "ARASAAC_URL_IMAGEN", "https://static.arasaac.org/pictograms/{id}/{id}_300.png"
)
# (conexión, lectura) en segundos: una ARASAAC lenta no deja colgada la pantalla.
TIEMPO_MAXIMO = (3, 5)
TAMANO_MAXIMO = 512 * 1024  # bytes; un pictograma de 300 px pesa entre 10 y 60 kB
LADO_MAXIMO = 1024  # píxeles
MAX_RESULTADOS = 12
CACHE_BUSQUEDA = 24 * 60 * 60  # un día
CARPETA = "pictogramas"

# Un identificador de ARASAAC es un número; con esto no se puede pedir otra dirección.
_ID = re.compile(r"[1-9][0-9]{0,6}")
# Lo que se puede buscar: de 2 a 40 letras, números, espacios o guiones.
_TEXTO = re.compile(r"[^\W_][\w \-']{1,39}", re.UNICODE)


class ErrorArasaac(Exception):
    """ARASAAC no responde, tarda demasiado o devuelve algo que no vale."""


class IdentificadorNoValido(ValueError):
    """El identificador no es un número de pictograma."""


class DemasiadasPeticiones(Exception):
    """El usuario ha superado el límite de peticiones por minuto."""


def id_valido(valor):
    """El identificador como entero, o IdentificadorNoValido."""
    texto = str(valor).strip()
    if not _ID.fullmatch(texto):
        raise IdentificadorNoValido(texto)
    return int(texto)


def texto_valido(texto):
    """La búsqueda limpia (sin espacios de más), o "" si no se puede buscar."""
    limpio = " ".join(str(texto or "").split())
    return limpio if _TEXTO.fullmatch(limpio) else ""


def contar_peticion(usuario, clase, maximo):
    """Límite de peticiones por usuario y minuto. Lanza DemasiadasPeticiones al pasarse."""
    clave = f"picto:limite:{clase}:{usuario.pk}:{int(time.time() // 60)}"
    cache.add(clave, 0, 120)
    try:
        veces = cache.incr(clave)
    except ValueError:  # la clave ha caducado entre add e incr
        cache.set(clave, 1, 120)
        veces = 1
    if veces > maximo:
        raise DemasiadasPeticiones


def _pedir(url, **opciones):
    try:
        respuesta = requests.get(
            url,
            timeout=TIEMPO_MAXIMO,
            headers={"User-Agent": "Despega (agenda escolar)"},
            **opciones,
        )
    except requests.RequestException as error:
        raise ErrorArasaac("ARASAAC no responde.") from error
    return respuesta


def buscar(texto):
    """Pictogramas de una palabra: [{"id": 2349, "nombre": "perro"}], como mucho 12.

    El resultado se guarda un día en la caché de Django: la misma palabra no vuelve a
    salir hacia ARASAAC. Una búsqueda sin resultados devuelve [].
    """
    texto = texto_valido(texto)
    if not texto:
        return []
    clave = "picto:buscar:" + hashlib.sha256(normalizar(texto).encode()).hexdigest()
    guardado = cache.get(clave)
    if guardado is not None:
        return guardado

    respuesta = _pedir(URL_BUSQUEDA.format(texto=quote(texto, safe="")))
    if respuesta.status_code == 404:  # ARASAAC responde 404 cuando no encuentra nada
        resultados = []
    elif respuesta.status_code != 200:
        raise ErrorArasaac(f"ARASAAC ha respondido {respuesta.status_code}.")
    else:
        try:
            datos = respuesta.json()
        except ValueError as error:
            raise ErrorArasaac("ARASAAC no ha devuelto una lista.") from error
        resultados = _leer_resultados(datos, texto)
    cache.set(clave, resultados, CACHE_BUSQUEDA)
    return resultados


def _leer_resultados(datos, texto):
    """De la respuesta de ARASAAC solo se toma el número y la primera palabra clave."""
    resultados = []
    for uno in datos if isinstance(datos, list) else []:
        if not isinstance(uno, dict):
            continue
        try:
            identificador = id_valido(uno.get("_id"))
        except IdentificadorNoValido:
            continue
        palabras = uno.get("keywords") or []
        primera = palabras[0] if palabras and isinstance(palabras[0], dict) else {}
        nombre = str(primera.get("keyword") or texto)[:60]
        resultados.append({"id": identificador, "nombre": nombre})
        if len(resultados) == MAX_RESULTADOS:
            break
    return resultados


def ruta(identificador):
    """Dónde se guarda la copia local, dentro de MEDIA_ROOT."""
    return f"{CARPETA}/{id_valido(identificador)}.png"


def _comprobar_png(contenido):
    """Pillow confirma que es un PNG de tamaño razonable (no se fía del Content-Type)."""
    try:
        with Image.open(io.BytesIO(contenido)) as imagen:
            formato, (ancho, alto) = imagen.format, imagen.size
            imagen.verify()
    except Exception as error:  # Pillow lanza varios tipos según el fallo
        raise ErrorArasaac("Lo que ha devuelto ARASAAC no es una imagen.") from error
    if formato != "PNG":
        raise ErrorArasaac("Lo que ha devuelto ARASAAC no es una imagen PNG.")
    if max(ancho, alto) > LADO_MAXIMO:
        raise ErrorArasaac("La imagen de ARASAAC es demasiado grande.")


def descargar(identificador):
    """Los bytes del PNG de un pictograma, comprobados. No guarda nada."""
    identificador = id_valido(identificador)
    respuesta = _pedir(URL_IMAGEN.format(id=identificador), stream=True)
    try:
        if respuesta.status_code != 200:
            raise ErrorArasaac(f"ARASAAC ha respondido {respuesta.status_code}.")
        if int(respuesta.headers.get("Content-Length") or 0) > TAMANO_MAXIMO:
            raise ErrorArasaac("La imagen de ARASAAC pesa demasiado.")
        trozos, total = [], 0
        try:
            for trozo in respuesta.iter_content(64 * 1024):
                total += len(trozo)
                if total > TAMANO_MAXIMO:
                    raise ErrorArasaac("La imagen de ARASAAC pesa demasiado.")
                trozos.append(trozo)
        except requests.RequestException as error:
            raise ErrorArasaac("ARASAAC ha tardado demasiado.") from error
    finally:
        respuesta.close()
    contenido = b"".join(trozos)
    _comprobar_png(contenido)
    return contenido


def obtener(identificador):
    """La ruta de la copia local de un pictograma; lo descarga solo la primera vez."""
    destino = ruta(identificador)
    if not default_storage.exists(destino):
        contenido = descargar(identificador)
        guardado = default_storage.save(destino, ContentFile(contenido))
        if guardado != destino:  # otra petición lo ha guardado a la vez: sobra esta copia
            default_storage.delete(guardado)
    return destino
