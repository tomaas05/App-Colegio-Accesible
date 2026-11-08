"""Lógica de la agenda del estudiante: HU-02-01, HU-02-02, HU-02-03 y HU-02-04.

Dueño: Tomás. Las vistas (views.py) solo piden datos y llaman a estas funciones.
Javi reutiliza `agenda_del_dia` en HU-01-09 (agenda de solo lectura del profesional):
recibe un Estudiante, no mira quién está conectado.

Los estados «vencida» y «tiempo agotado» NO se guardan: se calculan a partir de las
horas cada vez que se consulta (no hay tareas programadas en segundo plano).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import cached_property
from typing import NamedTuple

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.tareas.models import Asignacion

from .models import Ejecucion, EjecucionPaso, EstadoEjecucion, EstadoPaso

# La siguiente tarea se anuncia al pie 10 minutos antes (RF2.10.1, boceto B06).
AVISO_MINUTOS = 10

# Cuánto antes de su hora se puede empezar una tarea. 0 = como dice RF2.3.2 (esperar a la
# hora de inicio). Si es mayor, solo cuando no hay otra tarea en curso ni otra a la que le
# toque ahora (una cosa cada vez).
MARGEN_EMPEZAR_ANTES = timedelta(0)

# (símbolo, texto), los mismos del boceto v3. El color nunca es la única señal (RNF4.1.3).
ETIQUETAS_ESTADO = {
    EstadoEjecucion.PENDIENTE: ("○", "Pendiente"),
    EstadoEjecucion.EN_CURSO: ("▶", "Ahora"),
    EstadoEjecucion.TIEMPO_AGOTADO: ("⏰", "Se acabó el tiempo"),
    EstadoEjecucion.HECHA: ("✓", "Hecha"),
    EstadoEjecucion.VENCIDA: ("–", "Vencida"),
    EstadoEjecucion.CANCELADA: ("✕", "Cancelada"),
    EstadoEjecucion.NO_REALIZABLE: ("✕", "No se ha podido"),
}


# Nombres fijos en español: LocaleMiddleware usaría el idioma del navegador.
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def titulo_de_hoy(ahora_):
    """«Hoy, jueves», como el título del boceto B06."""
    return f"Hoy, {DIAS[ahora_.weekday()]}"


class ErrorDeAgenda(Exception):
    """Algo que el estudiante no puede hacer ahora. El mensaje se le muestra tal cual."""


def ahora():
    """Hora actual en la zona del centro. Las pruebas la sustituyen (monkeypatch)."""
    return timezone.localtime()


def _momento(fecha, hora):
    return timezone.make_aware(datetime.combine(fecha, hora))


class PasoVista(NamedTuple):
    paso: object
    hecho: bool


@dataclass
class TareaDelDia:
    """Una asignación en un día concreto, con su ejecución (si ya existe)."""

    asignacion: Asignacion
    ejecucion: Ejecucion | None
    fecha: object
    ahora: datetime
    momento: str = ""  # «anterior», «actual», «siguiente» o vacío
    # Otra tarea que impide empezar esta antes de su hora (la rellena agenda_del_dia).
    bloqueada_por: "TareaDelDia | None" = None

    @property
    def tarea(self):
        return self.asignacion.tarea

    @cached_property
    def inicio(self):
        return _momento(self.fecha, self.asignacion.hora_inicio)

    @cached_property
    def fin(self):
        return _momento(self.fecha, self.asignacion.hora_fin)

    @cached_property
    def estado(self):
        guardado = self.ejecucion.estado if self.ejecucion else EstadoEjecucion.PENDIENTE
        if guardado == EstadoEjecucion.PENDIENTE and self.ahora >= self.fin:
            return EstadoEjecucion.VENCIDA
        if guardado == EstadoEjecucion.EN_CURSO and self.ahora >= self.fin:
            return EstadoEjecucion.TIEMPO_AGOTADO
        return guardado

    @property
    def en_su_hora(self):
        return self.inicio <= self.ahora < self.fin

    @property
    def se_puede_empezar_desde(self):
        return self.inicio - MARGEN_EMPEZAR_ANTES

    @property
    def destacada(self):
        """La tarjeta de ahora (borde grueso y fondo menta): la actual de la agenda."""
        return self.momento == "actual" or self.estado == EstadoEjecucion.TIEMPO_AGOTADO

    @property
    def _etiqueta(self):
        # Como en el boceto: una tarea pendiente en su hora se marca «Ahora».
        if self.estado == EstadoEjecucion.PENDIENTE and self.en_su_hora:
            return ETIQUETAS_ESTADO[EstadoEjecucion.EN_CURSO]
        return ETIQUETAS_ESTADO[self.estado]

    @property
    def simbolo(self):
        return self._etiqueta[0]

    @property
    def etiqueta(self):
        return self._etiqueta[1]

    @property
    def texto_para_escuchar(self):
        """Lo que lee «Escuchar»: nombre, descripción y pasos, sin símbolos decorativos."""
        partes = [self.tarea.nombre, self.tarea.descripcion]
        partes += [
            f"Paso {p.paso.orden}: {p.paso.descripcion or p.paso.descripcion_imagen}"
            for p in self.pasos
        ]
        return ". ".join(x.strip().rstrip(".") for x in partes if x and x.strip()) + "."

    @cached_property
    def pasos(self):
        hechos = set()
        if self.ejecucion:
            hechos = set(
                self.ejecucion.pasos.filter(estado=EstadoPaso.HECHO).values_list(
                    "paso_id", flat=True
                )
            )
        return [PasoVista(p, p.pk in hechos) for p in self.tarea.pasos.all()]

    @cached_property
    def pasos_pendientes(self):
        return sum(1 for p in self.pasos if not p.hecho)

    @property
    def puede_empezar(self):
        """HU-02-03: desde MARGEN_EMPEZAR_ANTES antes de su hora hasta la hora de fin, y
        sin otra tarea en marcha ni otra a la que le toque ahora."""
        return (
            self.estado == EstadoEjecucion.PENDIENTE
            and self.se_puede_empezar_desde <= self.ahora < self.fin
            and self.bloqueada_por is None
        )

    @property
    def aun_no_es_la_hora(self):
        return self.estado == EstadoEjecucion.PENDIENTE and self.ahora < self.se_puede_empezar_desde

    @property
    def texto_espera(self):
        return _texto_espera(self.bloqueada_por) if self.bloqueada_por else ""

    @property
    def esperando(self):
        """Ya se podría empezar por la hora, pero otra tarea va primero."""
        return (
            self.estado == EstadoEjecucion.PENDIENTE
            and not self.aun_no_es_la_hora
            and self.bloqueada_por is not None
        )

    @property
    def en_curso(self):
        return self.estado in (EstadoEjecucion.EN_CURSO, EstadoEjecucion.TIEMPO_AGOTADO)

    @property
    def puede_terminar(self):
        """HU-02-04: en curso y con todos los pasos hechos."""
        return self.en_curso and self.pasos_pendientes == 0


@dataclass
class Agenda:
    tareas: list
    actual: TareaDelDia | None
    anterior: TareaDelDia | None
    siguiente: TareaDelDia | None
    visibles: list  # las que se pintan (máximo `max_tarjetas` del perfil)
    restantes: int  # cuántas quedan sin pintar después de las visibles
    aviso: TareaDelDia | None  # la siguiente, si empieza dentro de AVISO_MINUTOS (RF2.10.1)


def agenda_del_dia(estudiante, ahora_=None):
    """Tareas de hoy del estudiante, ordenadas por hora (HU-02-01)."""
    ahora_ = ahora_ or ahora()
    hoy = ahora_.date()
    asignaciones = list(
        estudiante.asignaciones.select_related("tarea")
        .filter(vigencia_desde__lte=hoy, dias_semana__contains=[hoy.isoweekday()])
        .filter(Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=hoy))
        .order_by("hora_inicio")
    )
    ejecuciones = {
        e.asignacion_id: e for e in Ejecucion.objects.filter(asignacion__in=asignaciones, fecha=hoy)
    }
    tareas = [TareaDelDia(a, ejecuciones.get(a.pk), hoy, ahora_) for a in asignaciones]

    # La actual: la que está en marcha (puede haberse empezado antes de su hora) o, si no
    # hay ninguna, la que toca por la hora. Anterior y siguiente, sus vecinas en la lista.
    en_marcha = next((t for t in tareas if t.estado == EstadoEjecucion.EN_CURSO), None)
    actual = en_marcha or next((t for t in tareas if t.en_su_hora), None)
    if actual:
        i = tareas.index(actual)
        anterior = tareas[i - 1] if i > 0 else None
        siguiente = tareas[i + 1] if i + 1 < len(tareas) else None
    else:
        siguiente = next((t for t in tareas if t.inicio > ahora_), None)
        anteriores = [t for t in tareas if t.fin <= ahora_]
        anterior = anteriores[-1] if anteriores else None

    # Empezar antes de la hora solo si no hay otra en marcha ni otra a la que le toque ahora.
    for t in tareas:
        if ahora_ < t.inicio:
            t.bloqueada_por = next(
                (
                    o
                    for o in tareas
                    if o is not t
                    and (
                        o.estado == EstadoEjecucion.EN_CURSO
                        or (o.estado == EstadoEjecucion.PENDIENTE and o.en_su_hora)
                    )
                ),
                None,
            )
    for tarea, momento in ((actual, "actual"), (siguiente, "siguiente"), (anterior, "anterior")):
        if tarea:
            tarea.momento = momento

    # Ventana de tarjetas (RNF2.3.2): como mucho el máximo del perfil. Siempre entra la
    # actual (o la siguiente) y, si cabe, la anterior; si caben todas, se ven todas.
    perfil = getattr(estudiante, "perfil", None)
    maximo = perfil.max_tarjetas if perfil else 6
    visibles, restantes = [], 0
    if tareas:
        ancla = tareas.index(actual or siguiente or tareas[-1])
        primera = ancla if maximo == 1 else max(ancla - 1, 0)
        primera = max(0, min(primera, len(tareas) - maximo))
        visibles = tareas[primera : primera + maximo]
        restantes = len(tareas) - (primera + len(visibles))

    aviso = None
    if (
        siguiente
        and siguiente.estado == EstadoEjecucion.PENDIENTE
        and ahora_ + timedelta(minutes=AVISO_MINUTOS) >= siguiente.inicio
    ):
        aviso = siguiente

    return Agenda(tareas, actual, anterior, siguiente, visibles, restantes, aviso)


def con_contexto(agenda, asignacion_id):
    """La tarea de la agenda con su anterior y su siguiente en la lista (recuadros
    «Antes» y «Después» del boceto B07). Lanza Asignacion.DoesNotExist si no está."""
    for i, t in enumerate(agenda.tareas):
        if t.asignacion.pk == asignacion_id:
            antes = agenda.tareas[i - 1] if i > 0 else None
            despues = agenda.tareas[i + 1] if i + 1 < len(agenda.tareas) else None
            return t, antes, despues
    raise Asignacion.DoesNotExist


def tarea_del_dia(estudiante, asignacion_id, ahora_=None):
    """Una tarea de hoy del estudiante (HU-02-02).

    Lanza Asignacion.DoesNotExist si no es suya o no toca hoy: la vista responde 404.
    """
    ahora_ = ahora_ or ahora()
    hoy = ahora_.date()
    asignacion = estudiante.asignaciones.select_related("tarea").get(pk=asignacion_id)
    if not asignacion.aplica_el(hoy):
        raise Asignacion.DoesNotExist
    ejecucion = Ejecucion.objects.filter(asignacion=asignacion, fecha=hoy).first()
    return TareaDelDia(asignacion, ejecucion, hoy, ahora_)


def _asegurar_pasos(ejecucion):
    """Crea el avance de cada paso de la tarea que aún no tenga fila."""
    existentes = set(ejecucion.pasos.values_list("paso_id", flat=True))
    EjecucionPaso.objects.bulk_create(
        EjecucionPaso(ejecucion=ejecucion, paso=paso)
        for paso in ejecucion.asignacion.tarea.pasos.all()
        if paso.pk not in existentes
    )


def empezar(estudiante, asignacion_id, ahora_=None):
    """HU-02-03: registra la hora real de inicio. Repetirlo no cambia la hora original.

    Se puede desde MARGEN_EMPEZAR_ANTES antes de la hora de inicio, si no hay otra tarea
    en marcha ni otra a la que le toque ahora. El tiempo que queda se sigue contando hasta
    la hora de fin prevista (RF2.7.2): empezar antes da más tiempo, no mueve el final.
    """
    ahora_ = ahora_ or ahora()
    hoy = ahora_.date()
    # Lanza Asignacion.DoesNotExist si no es suya o no toca hoy.
    t, _, _ = con_contexto(agenda_del_dia(estudiante, ahora_), asignacion_id)
    with transaction.atomic():
        ejecucion, _ = Ejecucion.objects.select_for_update().get_or_create(
            asignacion=t.asignacion, fecha=hoy
        )
        if ejecucion.estado == EstadoEjecucion.EN_CURSO:
            return ejecucion  # cerró y reabrió la app: retoma con su hora original
        if ejecucion.estado != EstadoEjecucion.PENDIENTE:
            raise ErrorDeAgenda("Esta tarea ya no se puede empezar.")
        if t.aun_no_es_la_hora:
            raise ErrorDeAgenda(
                f"Todavía no es la hora. Podrás empezar a las {t.se_puede_empezar_desde:%H:%M}."
            )
        if ahora_ >= t.fin:
            raise ErrorDeAgenda("Ya ha pasado la hora de esta tarea.")
        if t.bloqueada_por:
            raise ErrorDeAgenda(_texto_espera(t.bloqueada_por))
        _asegurar_pasos(ejecucion)
        ejecucion.estado = EstadoEjecucion.EN_CURSO
        ejecucion.inicio_real = ahora_
        ejecucion.save(update_fields=["estado", "inicio_real"])
    return ejecucion


def _texto_espera(otra):
    if otra.estado == EstadoEjecucion.EN_CURSO:
        return f"Primero termina «{otra.tarea.nombre}»."
    return f"Ahora toca «{otra.tarea.nombre}»."


def terminar(estudiante, asignacion_id, ahora_=None):
    """HU-02-04: pasa la tarea en curso a «hecha». Con pasos sin hacer no se puede."""
    ahora_ = ahora_ or ahora()
    hoy = ahora_.date()
    asignacion = estudiante.asignaciones.select_related("tarea").get(pk=asignacion_id)
    with transaction.atomic():
        try:
            ejecucion = Ejecucion.objects.select_for_update().get(asignacion=asignacion, fecha=hoy)
        except Ejecucion.DoesNotExist:
            raise ErrorDeAgenda("Primero tienes que empezar la tarea.") from None
        if ejecucion.estado == EstadoEjecucion.HECHA:
            return ejecucion
        if ejecucion.estado != EstadoEjecucion.EN_CURSO:
            raise ErrorDeAgenda("Esta tarea no se puede terminar.")
        _asegurar_pasos(ejecucion)
        pendientes = ejecucion.pasos.filter(estado=EstadoPaso.PENDIENTE).count()
        if pendientes:
            raise ErrorDeAgenda(
                "Te falta 1 paso por hacer."
                if pendientes == 1
                else f"Te faltan {pendientes} pasos por hacer."
            )
        ejecucion.estado = EstadoEjecucion.HECHA
        ejecucion.fin_real = ahora_
        ejecucion.save(update_fields=["estado", "fin_real"])
    return ejecucion
