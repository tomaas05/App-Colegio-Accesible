"""Vínculos de cada estudiante con su tutor y su familiar (HU-01-04, Manu).

`estudiantes_de(usuario)` es la regla de quién ve a qué estudiante para toda la
aplicación: un tutor solo ve a los suyos (PA3), un familiar solo a los suyos (PA4)
y un profesional a los que atiende (tabla Atencion, HU-01-08). Cualquier pantalla
que enseñe estudiantes a un adulto debe sacar la lista de aquí.
"""

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Estudiante, Rol

# Qué estudiantes ve cada rol. El administrador los ve todos.
FILTRO_POR_ROL = {
    Rol.ADMINISTRADOR: lambda usuario: Q(),
    Rol.TUTOR: lambda usuario: Q(tutor=usuario),
    Rol.FAMILIAR: lambda usuario: Q(familiar=usuario),
    Rol.PROFESIONAL: lambda usuario: Q(atenciones__profesional=usuario),
    Rol.ESTUDIANTE: lambda usuario: Q(usuario=usuario),
}


def estudiantes_de(usuario):
    """Los estudiantes activos que puede ver `usuario`, con su usuario y su clase."""
    activos = Estudiante.objects.filter(usuario__is_active=True).select_related("usuario", "clase")
    filtro = FILTRO_POR_ROL.get(getattr(usuario, "rol", None))
    if not getattr(usuario, "is_authenticated", False) or filtro is None:
        return activos.none()
    return activos.filter(filtro(usuario))


@transaction.atomic
def guardar_vinculos(estudiante, *, tutor, familiar):
    """Pone el tutor y el familiar del estudiante. Devuelve si ha cambiado el tutor.

    La fecha de alta de cada vínculo es la de hoy si el vínculo cambia, y se borra si
    se quita (las restricciones del modelo piden fecha cuando hay tutor o familiar).
    Como mucho un familiar: el modelo solo tiene un campo para él.
    """
    hoy = timezone.localdate()
    cambia_tutor = estudiante.tutor_id != (tutor.pk if tutor else None)
    if cambia_tutor:
        estudiante.tutor = tutor
        estudiante.fecha_alta_tutor = hoy if tutor else None
    if estudiante.familiar_id != (familiar.pk if familiar else None):
        estudiante.familiar = familiar
        estudiante.fecha_alta_familiar = hoy if familiar else None
    estudiante.clean()  # comprueba que el tutor es tutor y el familiar es familiar
    estudiante.save(update_fields=["tutor", "fecha_alta_tutor", "familiar", "fecha_alta_familiar"])
    return cambia_tutor
