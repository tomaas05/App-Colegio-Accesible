"""Eliminar una cuenta (HU-01-03, Manu).

Lo usan la ventana «¿Eliminar la cuenta?» (B24, en «Editar cuenta») y su página sin
JavaScript. Aquí está qué se borra con cada cuenta y qué impide borrarla.

Qué se borra con un estudiante (PA3): su perfil, su agenda (las tareas que tiene
puestas), lo que ha hecho cada día (ejecuciones y pasos marcados) y los profesionales
que lo atendían. Todo cuelga de él en cascada en la base de datos. Las comprobaciones del
tutor y las emociones (área 6, iteración 2) se borrarán igual si sus modelos apuntan al
estudiante con on_delete=CASCADE, como pide el diccionario de datos.

Qué impide borrar a un adulto: que tenga estudiantes vinculados (PA4) o tareas creadas o
puestas en agendas. La base de datos lo protege (on_delete=PROTECT) para que ningún
estudiante se quede sin tareas sin que nadie lo decida. En esos casos se explica qué
hacer y se ofrece desactivar la cuenta, que conserva todo.
"""

from dataclasses import dataclass, field

from django.db import transaction

from apps.agenda.models import Ejecucion

from .models import Estudiante


@dataclass
class Baja:
    """Lo que hay que saber antes de eliminar una cuenta."""

    motivos: list[str] = field(default_factory=list)  # por qué no se puede (vacío = se puede)
    se_borra: list[str] = field(default_factory=list)  # qué desaparece con ella

    @property
    def se_puede(self):
        return not self.motivos


def _plural(n, uno, varios):
    return f"{n} {uno if n == 1 else varios}"


def baja_de(cuenta, quien):
    """Si `quien` puede eliminar `cuenta` y, si puede, qué se borrará con ella."""
    baja = Baja()
    if cuenta.pk == quien.pk:
        baja.motivos.append("No puedes eliminar tu propia cuenta: te quedarías sin poder entrar.")
        return baja

    if cuenta.es_estudiante:
        estudiante = cuenta.estudiante
        asignaciones = estudiante.asignaciones.count()
        dias = Ejecucion.objects.filter(asignacion__estudiante=estudiante).count()
        baja.se_borra.append("su perfil visual y su forma de entrar")
        baja.se_borra.append(
            f"su agenda: {_plural(asignaciones, 'tarea puesta', 'tareas puestas')}"
        )
        if dias:
            hecho = _plural(dias, "tarea empezada o terminada", "tareas empezadas o terminadas")
            baja.se_borra.append(f"lo que ha hecho: {hecho}")
        atendido = estudiante.atenciones.count()
        if atendido:
            baja.se_borra.append(
                f"{_plural(atendido, 'profesional deja', 'profesionales dejan')} de atenderle"
            )
        return baja

    tutorizados = cuenta.estudiantes_tutorizados.count()
    if tutorizados:
        baja.motivos.append(
            f"Tiene {_plural(tutorizados, 'estudiante', 'estudiantes')} a su cargo como tutor. "
            "Antes, ponles otro tutor en «Vínculos»."
        )
    familiares = cuenta.estudiantes_familiares.count()
    if familiares:
        baja.motivos.append(
            f"Figura como familiar de {_plural(familiares, 'estudiante', 'estudiantes')}. "
            "Antes, quítale el vínculo en «Vínculos»."
        )
    creadas = cuenta.tareas_creadas.count()
    puestas = cuenta.asignaciones_hechas.count()
    if creadas or puestas:
        partes = []
        if creadas:
            partes.append(f"ha creado {_plural(creadas, 'tarea', 'tareas')}")
        if puestas:
            partes.append(f"ha puesto {_plural(puestas, 'tarea', 'tareas')} en agendas")
        baja.motivos.append(
            " y ".join(partes).capitalize()
            + ". Si se eliminara, desaparecerían de las agendas de los estudiantes."
        )
    if not baja.motivos:
        atiende = cuenta.atenciones.count()
        if atiende:
            baja.se_borra.append(
                f"deja de atender a {_plural(atiende, 'estudiante', 'estudiantes')}"
            )
        baja.se_borra.append("su usuario y su contraseña")
    return baja


@transaction.atomic
def eliminar(cuenta):
    """Borra la cuenta y lo que cuelga de ella. El avatar se borra del disco al terminar."""
    avatar = ""
    if cuenta.es_estudiante:
        avatar = cuenta.estudiante.avatar.name
        almacen = cuenta.estudiante.avatar.storage
    cuenta.delete()
    # El archivo solo si ningún otro estudiante usa la misma imagen, y solo si el borrado
    # en la base de datos se ha completado.
    if avatar and not Estudiante.objects.filter(avatar=avatar).exists():
        transaction.on_commit(lambda: almacen.delete(avatar))
