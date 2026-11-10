"""HU-01-09. Agenda de un estudiante en modo consulta para el profesional que lo atiende.

Solo lectura: el profesional ve las tareas de un día (hora, imagen, pasos, estado y
quién la creó y la puso) y el horario de la clase de ese día. No puede cambiar ni
borrar lo que han creado otros (PA2); solo lo suyo, cuando existan las pantallas de
modificar (Iteración 2), y para eso está `puede_modificar`.
"""

from dataclasses import dataclass
from datetime import date

from django.db.models import Q

from apps.agenda.models import Ejecucion, EstadoEjecucion
from apps.agenda.servicios import DIAS
from apps.horario.models import HorarioClase
from apps.tareas.models import Asignacion


@dataclass
class TareaConsultada:
    asignacion: Asignacion
    ejecucion: Ejecucion | None
    modificable: bool

    @property
    def tarea(self):
        return self.asignacion.tarea

    @property
    def estado(self):
        if self.ejecucion:
            return self.ejecucion.get_estado_display()
        return EstadoEjecucion.PENDIENTE.label


# Nombres fijos en español: LocaleMiddleware usaría el idioma del navegador.
MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]  # fmt: skip


def fecha_en_texto(fecha: date):
    """«Martes 10 de noviembre»."""
    return f"{DIAS[fecha.weekday()].capitalize()} {fecha.day} de {MESES[fecha.month - 1]}"


def puede_modificar(usuario, asignacion):
    """PA2: solo quien creó la tarea y la puso en la agenda puede cambiarla o borrarla."""
    return asignacion.asignado_por_id == usuario.pk and asignacion.tarea.creador_id == usuario.pk


def tareas_del_dia(estudiante, fecha: date, usuario):
    """Las tareas que tiene el estudiante en `fecha`, por hora, con su estado de ese día."""
    asignaciones = list(
        Asignacion.objects.filter(
            estudiante=estudiante,
            vigencia_desde__lte=fecha,
            dias_semana__contains=[fecha.isoweekday()],
        )
        .filter(Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=fecha))
        .select_related("tarea", "tarea__creador", "asignado_por")
        .prefetch_related("tarea__pasos")
        .order_by("hora_inicio")
    )
    ejecuciones = {
        e.asignacion_id: e
        for e in Ejecucion.objects.filter(asignacion__in=asignaciones, fecha=fecha)
    }
    return [
        TareaConsultada(a, ejecuciones.get(a.pk), puede_modificar(usuario, a)) for a in asignaciones
    ]


def horario_del_dia(estudiante, fecha: date):
    """Las casillas del horario escolar de su clase ese día (vacío en fin de semana)."""
    return (
        HorarioClase.objects.filter(clase=estudiante.clase, dia_semana=fecha.isoweekday())
        .select_related("franja", "asignatura")
        .order_by("franja__orden")
    )
