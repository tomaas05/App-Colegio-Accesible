"""HU-06-02 · Ver el estado de las tareas de mis estudiantes (Manu).

El panel «Seguimiento de hoy» del tutor y del profesional: de cada estudiante suyo, cuántas
tareas lleva hechas, cuántas le quedan, cuáles no ha podido hacer y cuáles ha cambiado por
una del plan B. Si alguna no se ha podido hacer, un aviso con la tarea y el plan B elegido o
el que se le ofrece (PA2).

No guarda nada: lo calcula con la misma agenda que ve el estudiante
(apps/agenda/servicios.py), así el panel y su agenda dicen siempre lo mismo. Quién ve a
quién lo decide `estudiantes_de` (apps/usuarios/vinculos.py): el tutor, a los suyos (PA3);
el profesional, a los que atiende (PA4).
"""

from dataclasses import dataclass, field

from apps.agenda import servicios
from apps.agenda.models import EstadoEjecucion
from apps.usuarios.vinculos import estudiantes_de

POR_HACER = (EstadoEjecucion.PENDIENTE, EstadoEjecucion.EN_CURSO, EstadoEjecucion.TIEMPO_AGOTADO)
SIN_HACER = (EstadoEjecucion.VENCIDA, EstadoEjecucion.NO_REALIZABLE)


@dataclass
class Aviso:
    """Una tarea que hoy no se ha podido hacer (HU-07-04), contada para el adulto."""

    t: servicios.TareaDelDia

    @property
    def tarea(self):
        """La tarea planificada, la que no se ha podido hacer."""
        return self.t.tarea_original

    @property
    def cuando(self):
        return self.t.ejecucion.no_realizable_el

    @property
    def motivo(self):
        return self.t.ejecucion.motivo

    @property
    def marcado_por_un_adulto(self):
        """Lo marcó un adulto (y no el propio estudiante con «No puedo hacerla»)."""
        por = self.t.ejecucion.no_realizable_por
        return bool(por and por.es_adulto)

    @property
    def plan_b_elegido(self):
        return self.t.tarea if self.t.es_plan_b else None

    @property
    def plan_b_tampoco(self):
        """Eligió una del plan B y tampoco la ha podido hacer."""
        return self.t.es_plan_b and self.t.estado == EstadoEjecucion.NO_REALIZABLE

    @property
    def plan_b_sugerido(self):
        """La primera del plan B, si aún no ha elegido ninguna (RF3.4.3)."""
        if self.t.es_plan_b or not self.t.alternativas:
            return None
        return self.t.alternativas[0]

    @property
    def sin_plan_b(self):
        return not self.t.es_plan_b and not self.t.alternativas


@dataclass
class EstadoDeHoy:
    """Cómo va hoy un estudiante (PA1)."""

    estudiante: object
    hechas: int = 0
    por_hacer: int = 0
    sin_hacer: int = 0
    con_plan_b: int = 0
    avisos: list = field(default_factory=list)

    @property
    def total(self):
        return self.hechas + self.por_hacer + self.sin_hacer


def estado_de_hoy(estudiante, ahora_):
    """Las tareas de hoy del estudiante, contadas. Las canceladas no cuentan."""
    estado = EstadoDeHoy(estudiante)
    for t in servicios.tareas_del_dia(estudiante, ahora_.date(), ahora_):
        if t.estado == EstadoEjecucion.CANCELADA:
            continue
        if t.estado == EstadoEjecucion.HECHA:
            estado.hechas += 1
        elif t.estado in SIN_HACER:
            estado.sin_hacer += 1
        else:
            estado.por_hacer += 1
        if t.es_plan_b:
            estado.con_plan_b += 1
        if t.ejecucion and t.ejecucion.no_realizable_el:
            estado.avisos.append(Aviso(t))
    estado.avisos.sort(key=lambda a: a.cuando, reverse=True)
    return estado


def seguimiento(usuario, ahora_=None):
    """El panel: un estado por estudiante. Primero los que tienen avisos (el aviso más
    reciente arriba) y después los demás, por nombre."""
    ahora_ = ahora_ or servicios.ahora()
    estudiantes = estudiantes_de(usuario).order_by("usuario__first_name", "usuario__last_name")
    estados = [estado_de_hoy(e, ahora_) for e in estudiantes]
    con_aviso = sorted(
        (e for e in estados if e.avisos), key=lambda e: e.avisos[0].cuando, reverse=True
    )
    return con_aviso + [e for e in estados if not e.avisos]
