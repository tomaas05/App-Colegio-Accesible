"""Galería de avatares del estudiante (retrospectiva del 19/11).

Los avatares no pueden ser los mismos dibujos que la contraseña de imágenes (perro, gato, sol…):
el estudiante confundía «quién soy» con «mi contraseña». Por eso tienen su propia categoría,
caras sencillas y alegres de un color cada una, en `static/img/avatares/` (licencia en su
LEEME.md). Se guardan en el repositorio: la aplicación no sale a Internet (decisión 0004).

`listado.csv` tiene una línea por avatar: `nombre;palabra` (archivo y nombre que se lee).
"""

import csv
import re
from functools import cache
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.templatetags.static import static

CARPETA = Path(settings.BASE_DIR) / "static" / "img" / "avatares"


@cache
def galeria():
    """[(clave, nombre)] en el orden del listado: («miel», «Miel»), («fresa», «Fresa»)…"""
    with open(CARPETA / "listado.csv", encoding="utf-8") as f:
        return [(fila["nombre"], fila["palabra"]) for fila in csv.DictReader(f, delimiter=";")]


def claves():
    return [clave for clave, _ in galeria()]


def url(clave):
    return static(f"img/avatares/{clave}.png")


def opciones():
    """Para un campo de formulario: [(clave, nombre)]."""
    return list(galeria())


def archivo(clave, codigo):
    """El PNG del avatar `clave`, listo para `estudiante.avatar.save(...)`."""
    if clave not in claves():
        raise ValueError(f"No hay ningún avatar «{clave}» en la galería.")
    datos = (CARPETA / f"{clave}.png").read_bytes()
    return ContentFile(datos, name=f"{codigo.lower()}-{clave}.png")


def de_codigo(codigo):
    """El avatar que le toca por defecto a un código (A01 → el primero, A02 → el segundo…).

    Así, en una clase de hasta 18 estudiantes con códigos seguidos no se repite ninguno.
    """
    numero = int(re.sub(r"\D", "", codigo) or 1)
    lista = claves()
    return lista[(numero - 1) % len(lista)]


def clave_de(estudiante):
    """La clave del avatar de galería que tiene guardado un estudiante, o None si es subido."""
    nombre = Path(estudiante.avatar.name or "").stem
    for clave in claves():
        if nombre.endswith(f"-{clave}") or nombre == clave:
            return clave
    return None
