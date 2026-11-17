"""HU-01-09. Agenda de un estudiante en modo consulta para el profesional que lo atiende.

Solo lectura: el profesional ve las tareas de un día (hora, imagen, pasos, estado y
quién la creó y la puso) y el horario de la clase de ese día. No puede cambiar ni
borrar lo que han creado otros (PA2); solo lo suyo, cuando existan las pantallas de
modificar (Iteración 2), y para eso está `puede_modificar`.
"""

from dataclasses import dataclass
from datetime import date

from django.db.models import prefetch_related_objects

from apps.agenda import servicios
from apps.agenda.models import Ejecucion, EstadoEjecucion
from apps.agenda.servicios import DIAS
from apps.horario.models import HorarioClase
from apps.tareas import planificacion
from apps.tareas.models import Asignacion


@dataclass
class TareaConsultada:
    asignacion: Asignacion
    ejecucion: Ejecucion | None
    modificable: bool
    vencida: bool = False
    # Cómo queda ese día (HU-03-04 y HU-03-05): sus horas y si se ha cancelado.
    ocurrencia: planificacion.Ocurrencia | None = None

    @property
    def tarea(self):
        return self.asignacion.tarea

    @property
    def hora_inicio(self):
        return self.ocurrencia.hora_inicio if self.ocurrencia else self.asignacion.hora_inicio

    @property
    def hora_fin(self):
        return self.ocurrencia.hora_fin if self.ocurrencia else self.asignacion.hora_fin

    @property
    def estado(self):
        # Igual que en la agenda del estudiante: «vencida» y «cancelada» no se guardan.
        pendiente = not self.ejecucion or self.ejecucion.estado == EstadoEjecucion.PENDIENTE
        if pendiente and self.ocurrencia and self.ocurrencia.cancelada:
            return EstadoEjecucion.CANCELADA.label
        if pendiente and self.vencida:
            return EstadoEjecucion.VENCIDA.label
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
    """Las tareas que tiene el estudiante en `fecha`, por la hora de ese día, con su estado.

    Como la agenda del estudiante (apps/tareas/planificacion.py): con las horas cambiadas
    solo para ese día y con las canceladas, que se ven como «Cancelada».
    """
    ocurrencias = planificacion.ocurrencias_del_dia(estudiante, fecha)
    asignaciones = [o.asignacion for o in ocurrencias]
    prefetch_related_objects(asignaciones, "tarea__pasos")
    ejecuciones = {
        e.asignacion_id: e
        for e in Ejecucion.objects.filter(asignacion__in=asignaciones, fecha=fecha)
    }
    ahora = servicios.ahora()
    hoy, hora = ahora.date(), ahora.time()

    def vencida(o):
        """Ya ha pasado su hora de fin: un día anterior, o hoy más tarde de esa hora."""
        return fecha < hoy or (fecha == hoy and o.hora_fin <= hora)

    return [
        TareaConsultada(
            o.asignacion,
            ejecuciones.get(o.asignacion.pk),
            puede_modificar(usuario, o.asignacion),
            vencida(o),
            o,
        )
        for o in ocurrencias
    ]


def horario_del_dia(estudiante, fecha: date):
    """Las casillas del horario escolar de su clase ese día (vacío en fin de semana)."""
    return (
        HorarioClase.objects.filter(clase=estudiante.clase, dia_semana=fecha.isoweekday())
        .select_related("franja", "asignatura")
        .order_by("franja__orden")
    )
