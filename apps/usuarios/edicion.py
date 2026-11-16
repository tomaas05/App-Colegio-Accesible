"""Cambios sobre una cuenta que ya existe (HU-01-02, Manu).

Lo usa la pantalla «Editar cuenta» (B23): restablecer la contraseña de un adulto con una
temporal y saber si una cuenta se puede desactivar. Los datos (nombre, clase, avatar…)
los guarda el formulario `EditarCuentaForm`.
"""

import secrets

from axes.utils import reset as quitar_bloqueo
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

# Sin letras ni cifras que se confunden al leerlas o dictarlas: l, i, o, 0 y 1.
LETRAS_TEMPORAL = "abcdefghjkmnpqrstuvwxyz23456789"
GRUPOS_TEMPORAL = 3
LARGO_GRUPO = 4


def contrasena_temporal():
    """Una contraseña al azar, fácil de dictar: «kq7m-x3pd-9wtr»."""
    while True:
        grupos = [
            "".join(secrets.choice(LETRAS_TEMPORAL) for _ in range(LARGO_GRUPO))
            for _ in range(GRUPOS_TEMPORAL)
        ]
        contrasena = "-".join(grupos)
        try:
            validate_password(contrasena)
        except ValidationError:
            continue  # por ejemplo, si salieran solo cifras
        return contrasena


def puede_restablecer(cuenta, quien):
    """Solo a los adultos y nunca a uno mismo (quien administra ya sabe su contraseña).

    Los estudiantes no entran con usuario y contraseña de adulto: su forma de entrar
    (3 imágenes o una contraseña corta) se elige al crear la cuenta.
    """
    return cuenta.es_adulto and cuenta.pk != quien.pk


def restablecer_contrasena(cuenta):
    """Pone una contraseña temporal y obliga a cambiarla al entrar. La devuelve en claro.

    Es la única vez que se ve: en la base de datos solo queda su hash. También se quita
    el bloqueo por intentos fallidos, para que pueda entrar con la nueva sin esperar.
    """
    temporal = contrasena_temporal()
    cuenta.set_password(temporal)
    cuenta.debe_cambiar_contrasena = True
    cuenta.save(update_fields=["password", "debe_cambiar_contrasena"])
    quitar_bloqueo(username=cuenta.username)
    return temporal


def motivo_para_no_desactivar(cuenta, quien):
    """Por qué no se puede desactivar esta cuenta, o "" si se puede.

    Nadie se desactiva a sí mismo. Con eso basta para que siempre quede un administrador
    activo: quien desactiva a otro administrador es, a su vez, un administrador activo.
    """
    if cuenta.pk == quien.pk:
        return "No puedes desactivar tu propia cuenta: te quedarías sin poder entrar."
    return ""
