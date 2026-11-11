"""Pictogramas de la propia interfaz, guardados en static/img/pictogramas/ (decisión 0004).

Se descargan una vez con `python manage.py descargar_pictogramas`. Mientras un pictograma
no esté descargado, la interfaz enseña su dibujo de reserva (un emoji o un marcador).
"""

import re

from django.conf import settings

from apps.usuarios.texto import normalizar

CARPETA = settings.BASE_DIR / "static" / "img" / "pictogramas"


def nombre_de_archivo(palabra):
    """«Educación física» → «educacion-fisica»."""
    return re.sub(r"[^a-z0-9]+", "-", normalizar(palabra)).strip("-")


def archivo(palabra):
    """La ruta del PNG de una palabra, o None si todavía no se ha descargado."""
    nombre = nombre_de_archivo(palabra)
    ruta = CARPETA / f"{nombre}.png"
    return ruta if nombre and ruta.is_file() else None
