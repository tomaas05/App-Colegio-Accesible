"""Comparar textos sin tildes ni mayúsculas (Manu).

Lo usan la carga de estudiantes (cabeceras e imágenes del CSV) y los buscadores de
Usuarios (B20) y Vínculos (B25): «lucia» encuentra a Lucía. PostgreSQL distingue
las tildes en icontains, así que con unos cientos de cuentas se filtra en Python.
"""

import unicodedata


def normalizar(texto):
    """«Lucía Pérez» → «lucia perez»."""
    sin_tildes = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn").strip().lower()


def coincide(busqueda, *textos):
    """True si `busqueda` aparece en alguno de los textos, sin mirar tildes ni mayúsculas."""
    buscado = normalizar(busqueda)
    return any(buscado in normalizar(texto) for texto in textos)
