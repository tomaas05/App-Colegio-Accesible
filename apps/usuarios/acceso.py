"""Cómo se guarda la contraseña de imágenes de un estudiante.

Solo define el formato de almacenamiento, que es parte del diseño de la base
de datos. Las pantallas de entrada (HU-01-06) y de configuración las hace Manu.

La combinación son 3 imágenes de la rejilla común (ImagenAcceso), sin orden.
Se ordenan sus identificadores y se guarda el hash de esa cadena en
usuario.password, con el mismo algoritmo que las contraseñas normales (Argon2).
Así la base de datos no revela qué imágenes ha elegido nadie.

Un estudiante tiene en usuario.password o su contraseña de texto o su
combinación de imágenes, según perfil.metodo_acceso.
"""

from django.contrib.auth.hashers import check_password, make_password

IMAGENES_POR_CONTRASENA = 3


def _clave(ids_imagenes):
    ids = sorted({int(i) for i in ids_imagenes})
    if len(ids) != IMAGENES_POR_CONTRASENA:
        raise ValueError(f"Hay que elegir {IMAGENES_POR_CONTRASENA} imágenes distintas.")
    return "imagenes:" + "-".join(str(i) for i in ids)


def establecer_contrasena_imagenes(usuario, ids_imagenes, guardar=True):
    """Guarda la combinación de 3 imágenes (en cualquier orden) del estudiante."""
    usuario.password = make_password(_clave(ids_imagenes))
    if guardar:
        usuario.save(update_fields=["password"])


def comprobar_contrasena_imagenes(usuario, ids_imagenes):
    """True si las 3 imágenes elegidas (en cualquier orden) son las del estudiante."""
    try:
        clave = _clave(ids_imagenes)
    except (ValueError, TypeError):
        return False
    return check_password(clave, usuario.password)
