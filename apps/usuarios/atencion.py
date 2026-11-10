"""HU-01-08. Los estudiantes que atiende un profesional (tabla Atencion, RI1.2.2).

Aquí está la regla de quién puede abrir la agenda de quién: la usan la pantalla
«Mis estudiantes» (HU-01-08) y la agenda en modo consulta (HU-01-09).
"""

from django.db import transaction
from django.db.models import Q

from .models import Atencion, Estudiante, Rol


def estudiantes_del_centro(texto="", clase_id=None):
    """Estudiantes activos del centro, con filtro opcional por nombre/apellidos y clase."""
    estudiantes = Estudiante.objects.filter(usuario__is_active=True).select_related(
        "usuario", "clase"
    )
    for palabra in texto.split():
        estudiantes = estudiantes.filter(
            Q(usuario__first_name__icontains=palabra) | Q(usuario__last_name__icontains=palabra)
        )
    if clase_id:
        estudiantes = estudiantes.filter(clase_id=clase_id)
    return estudiantes.order_by("usuario__first_name", "usuario__last_name")


def mis_estudiantes(profesional):
    """Los estudiantes activos que atiende el profesional (PA2)."""
    return (
        Estudiante.objects.filter(atenciones__profesional=profesional, usuario__is_active=True)
        .select_related("usuario", "clase")
        .order_by("usuario__first_name", "usuario__last_name")
    )


@transaction.atomic
def guardar_mis_estudiantes(profesional, codigos):
    """Deja como atendidos justo los estudiantes de `codigos` (PA2 y PA4).

    Los que ya estaban y siguen elegidos conservan su fecha de alta.
    Devuelve (añadidos, quitados).
    """
    elegidos = set(
        Estudiante.objects.filter(
            codigo_estudiante__in=codigos, usuario__is_active=True
        ).values_list("pk", flat=True)
    )
    actuales = set(profesional.atenciones.values_list("estudiante_id", flat=True))
    quitar = actuales - elegidos
    anadir = elegidos - actuales
    profesional.atenciones.filter(estudiante_id__in=quitar).delete()
    Atencion.objects.bulk_create(
        Atencion(profesional=profesional, estudiante_id=pk) for pk in anadir
    )
    return len(anadir), len(quitar)


def atiende(usuario, estudiante):
    """¿Es `usuario` un profesional que atiende a `estudiante`? (PA3 y PA4)."""
    return (
        usuario.is_authenticated
        and usuario.rol == Rol.PROFESIONAL
        and Atencion.objects.filter(profesional=usuario, estudiante=estudiante).exists()
    )
