"""Lógica de la agenda del estudiante: HU-02-01 a HU-02-05 y HU-07-04 (plan B).

Dueño: Tomás (HU-02-05, seguir los pasos: Javi). Las vistas (views.py) solo piden datos y
llaman a estas funciones.
Javi reutiliza `agenda_del_dia` en HU-01-09 (agenda de solo lectura del profesional):
recibe un Estudiante, no mira quién está conectado.

Los estados «vencida» y «tiempo agotado» NO se guardan: se calculan a partir de las
horas cada vez que se consulta (no hay tareas programadas en segundo plano). Tampoco
«cancelada»: sale de la planificación (apps/tareas/planificacion.py, HU-03-04 y HU-03-05),
que también da las horas de cada día si se han cambiado solo para ese día.

Plan B (HU-07-04, RF2.15.1 y RF2.15.2): una tarea escolar pendiente o en marcha se puede
marcar como «no realizable». Si tiene plan B, el estudiante elige una alternativa, que la
sustituye ese día: la ejecución vuelve a «pendiente», ahora de la alternativa (con sus
pasos), y guarda cuál eligió (`Ejecucion.plan_b`). `TareaDelDia.tarea` es siempre la que
toca hacer; `tarea_original`, la que estaba planificada.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import cached_property
from typing import NamedTuple

from django.db import transaction
from django.utils import timezone

from apps.comun.models import Notificacion, TipoAviso, avisar
from apps.tareas import planificacion
from apps.tareas.models import Ambito, Asignacion, Tarea

from .models import Ejecucion, EjecucionPaso, EstadoEjecucion, EstadoPaso

# La siguiente tarea se anuncia al pie 10 minutos antes (RF2.10.1, boceto B06).
AVISO_MINUTOS = 10

# Cuánto antes de su hora se puede empezar una tarea. Retrospectiva del 19/11 (la profesora):
# no hay que ser tan estrictos con la hora; si quiere empezar ya una tarea que tiene dentro de
# un rato, puede, en cualquier momento del día. Solo hace falta que no tenga otra en marcha
# (una cosa cada vez). Antes eran 15 minutos; con timedelta(0) sería como decía RF2.3.2.
MARGEN_EMPEZAR_ANTES = None  # None = desde el principio del día

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
    # Cómo queda ese día (planificacion.Ocurrencia): horas de ese día y si está cancelada.
    ocurrencia: "planificacion.Ocurrencia | None" = None

    @property
    def cancelada(self):
        return bool(self.ocurrencia and self.ocurrencia.cancelada)

    @property
    def cambiada(self):
        """Ese día tiene otras horas («solo este día», HU-03-04)."""
        return bool(self.ocurrencia and self.ocurrencia.cambiada)

    @property
    def tarea_original(self):
        """La tarea planificada, aunque ese día se haya cambiado por una del plan B."""
        return self.asignacion.tarea

    @property
    def es_plan_b(self):
        return bool(self.ejecucion and self.ejecucion.plan_b_id)

    @property
    def tarea(self):
        """La que toca hacer: la del plan B elegida o, si no, la planificada."""
        return self.ejecucion.plan_b if self.es_plan_b else self.asignacion.tarea

    @cached_property
    def alternativas(self):
        """El plan B de la tarea planificada, por orden de prioridad (HU-03-06)."""
        return self.tarea_original.alternativas

    @property
    def puede_decir_no_puedo(self):
        """RF2.15.1: solo las del horario escolar, pendientes o en marcha. Las de casa y
        las de ocio no tienen «No puedo hacerla» (boceto B07)."""
        return self.tarea_original.ambito == Ambito.ESCOLAR and self.estado in (
            EstadoEjecucion.PENDIENTE,
            EstadoEjecucion.EN_CURSO,
            EstadoEjecucion.TIEMPO_AGOTADO,
        )

    @property
    def debe_elegir_plan_b(self):
        """No se ha podido hacer, aún no ha elegido otra cosa, tiene plan B y todavía
        queda tiempo de hacerla (B11)."""
        return (
            self.estado == EstadoEjecucion.NO_REALIZABLE
            and not self.es_plan_b
            and self.ahora < self.fin
            and bool(self.alternativas)
        )

    @cached_property
    def inicio(self):
        hora = self.ocurrencia.hora_inicio if self.ocurrencia else self.asignacion.hora_inicio
        return _momento(self.fecha, hora)

    @cached_property
    def fin(self):
        hora = self.ocurrencia.hora_fin if self.ocurrencia else self.asignacion.hora_fin
        return _momento(self.fecha, hora)

    @cached_property
    def inicio_tarea(self):
        """Cuándo empezó de verdad si la empezó antes de su hora; si no, su hora de inicio."""
        ejecucion = self.ejecucion
        if ejecucion and ejecucion.inicio_real and ejecucion.inicio_real < self.inicio:
            return ejecucion.inicio_real
        return self.inicio

    @cached_property
    def fin_tarea(self):
        """Hasta cuándo tiene para hacerla (temporizador y «se acabó el tiempo»).

        Retrospectiva del 19/11: se puede empezar en cualquier momento. Si la empieza antes de
        su hora, tiene lo que dura la tarea desde que empieza (una de 30 minutos empezada a las
        12:22 acaba a las 12:52), no hasta su hora de fin prevista. Si la empieza a su hora o
        más tarde, el final no se mueve (RF2.7.2).
        """
        return self.inicio_tarea + (self.fin - self.inicio)

    @property
    def empezada_antes(self):
        return self.inicio_tarea < self.inicio

    @cached_property
    def estado(self):
        guardado = self.ejecucion.estado if self.ejecucion else EstadoEjecucion.PENDIENTE
        # Cancelada (HU-03-05): solo si no la había empezado (no se cancela lo empezado).
        if self.cancelada and guardado == EstadoEjecucion.PENDIENTE:
            return EstadoEjecucion.CANCELADA
        if guardado == EstadoEjecucion.PENDIENTE and self.ahora >= self.fin:
            return EstadoEjecucion.VENCIDA
        if guardado == EstadoEjecucion.EN_CURSO and self.ahora >= self.fin_tarea:
            return EstadoEjecucion.TIEMPO_AGOTADO
        return guardado

    @property
    def en_su_hora(self):
        return self.inicio <= self.ahora < self.fin

    @property
    def se_puede_empezar_desde(self):
        if MARGEN_EMPEZAR_ANTES is None:
            return self.inicio.replace(hour=0, minute=0, second=0, microsecond=0)
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
        # Se numeran por su posición, como en la pantalla («Paso 2 de 4»), aunque el campo
        # `orden` tenga huecos.
        partes += [
            f"Paso {i}: {p.paso.descripcion or p.paso.descripcion_imagen}"
            for i, p in enumerate(self.pasos, start=1)
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

    @cached_property
    def paso_actual(self):
        """HU-02-05: el paso que toca hacer (el primero sin hacer), solo con la tarea en
        marcha. None si la tarea no está en curso o ya están todos hechos."""
        if not self.en_curso:
            return None
        return next((p for p in self.pasos if not p.hecho), None)

    @property
    def posicion_paso_actual(self):
        """Número del paso que toca, contando desde 1 («Paso 2 de 4»)."""
        return self.pasos.index(self.paso_actual) + 1 if self.paso_actual else None

    @property
    def puede_empezar(self):
        """HU-02-03: en cualquier momento del día hasta su hora de fin (retrospectiva del
        19/11), si no hay otra tarea en marcha."""
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
    en_alcance: list = None  # las que entran según `alcance_agenda` (HU-04-02)
    alcance: str = "semana"
    puede_ver_semana: bool = True


def _registrar_tiempo_agotado(estudiante, t):
    """HU-07-03 (PA2, PA4): registra que se agotó el tiempo sin terminar y avisa al tutor."""
    ejecucion = t.ejecucion
    if ejecucion is None or ejecucion.estado != EstadoEjecucion.EN_CURSO or t.ahora < t.fin_tarea:
        return
    ejecucion.estado = EstadoEjecucion.TIEMPO_AGOTADO
    ejecucion.save(update_fields=["estado"])
    tutor = getattr(estudiante, "tutor", None)
    if tutor is not None:
        mensaje = (
            f"A {estudiante.usuario.first_name} se le ha acabado el tiempo en "
            f"«{t.tarea.nombre}» sin terminarla."
        )
        if not Notificacion.objects.filter(
            destinatario=tutor, tarea=t.tarea, mensaje=mensaje
        ).exists():
            avisar(tutor, mensaje, tipo=TipoAviso.CAMBIO, tarea=t.tarea)


def tareas_del_dia(estudiante, fecha, ahora_):
    """Las tareas de un día con su ejecución, ordenadas por la hora de ese día.

    Incluye las canceladas que el estudiante aún tiene que ver tachadas (HU-03-05, PA1).
    """
    ocurrencias = planificacion.ocurrencias_del_dia(estudiante, fecha)
    ejecuciones = {
        e.asignacion_id: e
        for e in Ejecucion.objects.filter(
            asignacion__in=[o.asignacion for o in ocurrencias], fecha=fecha
        ).select_related("plan_b")
    }
    lista = [
        TareaDelDia(o.asignacion, ejecuciones.get(o.asignacion.pk), fecha, ahora_, ocurrencia=o)
        for o in ocurrencias
    ]
    for t in lista:
        _registrar_tiempo_agotado(estudiante, t)
    return lista


def agenda_del_dia(estudiante, ahora_=None):
    """Tareas de hoy del estudiante, ordenadas por hora (HU-02-01)."""
    ahora_ = ahora_ or ahora()
    hoy = ahora_.date()
    tareas = tareas_del_dia(estudiante, hoy, ahora_)
    # Las canceladas se ven, tachadas, pero no cuentan como actual, anterior ni siguiente.
    activas = [t for t in tareas if t.estado != EstadoEjecucion.CANCELADA]

    # La actual: la que está en marcha (puede haberse empezado antes de su hora) o, si no
    # hay ninguna, la que toca por la hora. Anterior y siguiente, sus vecinas en la lista.
    en_marcha = next((t for t in activas if t.estado == EstadoEjecucion.EN_CURSO), None)
    actual = en_marcha or next((t for t in activas if t.en_su_hora), None)
    if actual:
        i = activas.index(actual)
        anterior = activas[i - 1] if i > 0 else None
        siguiente = activas[i + 1] if i + 1 < len(activas) else None
    else:
        siguiente = next((t for t in activas if t.inicio > ahora_), None)
        anteriores = [t for t in activas if t.fin <= ahora_]
        anterior = anteriores[-1] if anteriores else None

    # Empezar antes de la hora solo si no hay otra en marcha (una cosa cada vez). Desde la
    # retrospectiva del 19/11 ya no espera a la que le toca ahora: elige el estudiante.
    for t in activas:
        if ahora_ < t.inicio:
            t.bloqueada_por = next(
                (o for o in activas if o is not t and o.estado == EstadoEjecucion.EN_CURSO),
                None,
            )
    for tarea, momento in ((actual, "actual"), (siguiente, "siguiente"), (anterior, "anterior")):
        if tarea:
            tarea.momento = momento

    # Ventana de tarjetas (RNF2.3.2): como mucho el máximo del perfil. Siempre entra la
    # actual (o la siguiente) y, si cabe, la anterior; si caben todas, se ven todas.
    # Ventana de tarjetas y alcance de la agenda (RNF2.3.2, RF4.2.1, RF4.2.2, HU-04-02).
    perfil = getattr(estudiante, "perfil", None)
    maximo = perfil.max_tarjetas if perfil else 6
    alcance = (getattr(perfil, "alcance_agenda", None) if perfil else None) or "semana"
    puede_ver_semana = alcance == "semana"

    if alcance == "actual":
        en_alcance = [actual] if actual else ([siguiente] if siguiente else [])
        visibles = list(en_alcance)
        restantes = 0
    elif alcance == "actual_sig":
        en_alcance = [t for t in (actual, siguiente) if t]
        visibles = list(en_alcance)
        restantes = 0
    else:
        en_alcance = list(tareas)
        visibles, restantes = [], 0
        if tareas:
            ancla = tareas.index(actual or siguiente or tareas[-1])
            primera = ancla if maximo == 1 else max(ancla - 1, 0)
            primera = max(0, min(primera, len(tareas) - maximo))
            visibles = tareas[primera : primera + maximo]
            restantes = len(tareas) - (primera + len(visibles))

    aviso = None
    if (
        alcance != "actual"
        and siguiente
        and siguiente.estado == EstadoEjecucion.PENDIENTE
        and ahora_ + timedelta(minutes=AVISO_MINUTOS) >= siguiente.inicio
    ):
        aviso = siguiente

    return Agenda(
        tareas,
        actual,
        anterior,
        siguiente,
        visibles,
        restantes,
        aviso,
        en_alcance,
        alcance,
        puede_ver_semana,
    )


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
    for t in tareas_del_dia(estudiante, hoy, ahora_):
        if t.asignacion.pk == asignacion_id:
            return t
    raise Asignacion.DoesNotExist


def _tarea_de(ejecucion):
    """La que toca hacer en esa ejecución: la del plan B, si eligió una (HU-07-04)."""
    return ejecucion.plan_b if ejecucion.plan_b_id else ejecucion.asignacion.tarea


def _asegurar_pasos(ejecucion):
    """Crea el avance de cada paso de la tarea que aún no tenga fila."""
    existentes = set(ejecucion.pasos.values_list("paso_id", flat=True))
    EjecucionPaso.objects.bulk_create(
        EjecucionPaso(ejecucion=ejecucion, paso=paso)
        for paso in _tarea_de(ejecucion).pasos.all()
        if paso.pk not in existentes
    )


def empezar(estudiante, asignacion_id, ahora_=None):
    """HU-02-03: registra la hora real de inicio. Repetirlo no cambia la hora original.

    Se puede en cualquier momento del día antes de su hora de fin (retrospectiva del 19/11),
    si no hay otra tarea en marcha. El tiempo que queda se sigue contando hasta
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
        if ejecucion.estado in (EstadoEjecucion.EN_CURSO, EstadoEjecucion.TIEMPO_AGOTADO):
            return ejecucion  # cerró y reabrió la app: retoma con su hora original
        if t.cancelada:
            raise ErrorDeAgenda("Esta tarea se ha cancelado.")
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
        if ejecucion.estado not in (EstadoEjecucion.EN_CURSO, EstadoEjecucion.TIEMPO_AGOTADO):
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


def marcar_paso_hecho(estudiante, asignacion_id, paso_id, ahora_=None):
    """HU-02-05: «Hecho» en un paso. Solo vale para el paso que toca (RF2.4.3).

    Se puede con la tarea en marcha (también con el tiempo agotado). Si el paso no es el
    que toca, no cambia nada (RF2.4.4) y el mensaje dice cuál toca. Si ya estaba hecho
    (p. ej. un doble toque), tampoco cambia nada y no es un error. No se guarda la hora de
    cada paso: RF2.4.2 no está comprometido.

    Lanza Asignacion.DoesNotExist si la tarea no es del estudiante o no toca hoy, y
    Paso.DoesNotExist si el paso no es de esa tarea: la vista responde 404.
    """
    ahora_ = ahora_ or ahora()
    hoy = ahora_.date()
    asignacion = estudiante.asignaciones.select_related("tarea").get(pk=asignacion_id)
    if not asignacion.aplica_el(hoy):
        raise Asignacion.DoesNotExist  # como en tarea_del_dia: la pantalla daría 404
    # Los pasos son los de la tarea que toca: la del plan B, si ha elegido una.
    previa = Ejecucion.objects.filter(asignacion=asignacion, fecha=hoy).first()
    tarea = _tarea_de(previa) if previa else asignacion.tarea
    paso = tarea.pasos.get(pk=paso_id)
    with transaction.atomic():
        try:
            ejecucion = Ejecucion.objects.select_for_update().get(asignacion=asignacion, fecha=hoy)
        except Ejecucion.DoesNotExist:
            raise ErrorDeAgenda("Primero tienes que empezar la tarea.") from None
        avance = ejecucion.pasos.filter(paso=paso).first()
        if avance and avance.estado == EstadoPaso.HECHO:
            return avance
        if ejecucion.estado == EstadoEjecucion.PENDIENTE:
            raise ErrorDeAgenda("Primero tienes que empezar la tarea.")
        # «Tiempo agotado» se calcula y no se guarda, pero si algún día se guarda la tarea
        # sigue en marcha, igual que en la pantalla (TareaDelDia.en_curso).
        if ejecucion.estado not in (EstadoEjecucion.EN_CURSO, EstadoEjecucion.TIEMPO_AGOTADO):
            raise ErrorDeAgenda("Esta tarea ya no está en marcha.")
        # Solo con la tarea en marcha: crea el avance de los pasos añadidos tras empezar.
        _asegurar_pasos(ejecucion)
        avance = avance or ejecucion.pasos.get(paso=paso)
        toca = (
            ejecucion.pasos.filter(estado=EstadoPaso.PENDIENTE)
            .select_related("paso")
            .order_by("paso__orden")
            .first()
        )
        if toca.pk != avance.pk:
            numero = tarea.pasos.filter(orden__lt=toca.paso.orden).count() + 1
            raise ErrorDeAgenda(f"Primero haz el paso {numero}.")
        avance.estado = EstadoPaso.HECHO
        avance.save(update_fields=["estado"])
    return avance


# --- HU-07-04 · Cuando una tarea no se puede hacer ------------------------------------


def no_puedo(estudiante, asignacion_id, *, por, motivo="", ahora_=None):
    """Marca la tarea de hoy como «no realizable» (RF2.15.1). La marca el estudiante
    («No puedo hacerla») o un adulto, que dice el motivo.

    Si era ya una del plan B, se queda así: no se ofrece otra. Devuelve la tarea del día
    tal y como queda. Lanza Asignacion.DoesNotExist si no toca hoy.
    """
    ahora_ = ahora_ or ahora()
    t = tarea_del_dia(estudiante, asignacion_id, ahora_)
    if not t.puede_decir_no_puedo:
        raise ErrorDeAgenda("Esta tarea ya no se puede marcar.")
    with transaction.atomic():
        ejecucion, _ = Ejecucion.objects.select_for_update().get_or_create(
            asignacion=t.asignacion, fecha=t.fecha
        )
        ejecucion.estado = EstadoEjecucion.NO_REALIZABLE
        ejecucion.no_realizable_el = ahora_
        ejecucion.no_realizable_por = por
        ejecucion.motivo = motivo.strip()
        ejecucion.save(update_fields=["estado", "no_realizable_el", "no_realizable_por", "motivo"])
    return tarea_del_dia(estudiante, asignacion_id, ahora_)


def elegir_plan_b(estudiante, asignacion_id, alternativa_id, ahora_=None):
    """B11 · El estudiante elige una actividad del plan B, que sustituye a la tarea en su
    agenda ese día (RF2.15.2). Empieza de cero: pendiente y sin pasos hechos.

    Lanza Asignacion.DoesNotExist si la tarea no toca hoy y Tarea.DoesNotExist si la
    alternativa no es de su plan B.
    """
    ahora_ = ahora_ or ahora()
    t = tarea_del_dia(estudiante, asignacion_id, ahora_)
    alternativa = next((a for a in t.alternativas if a.pk == alternativa_id), None)
    if alternativa is None:
        raise Tarea.DoesNotExist
    if not t.debe_elegir_plan_b:
        raise ErrorDeAgenda("Ahora no puedes elegir otra cosa para esta tarea.")
    with transaction.atomic():
        ejecucion = Ejecucion.objects.select_for_update().get(pk=t.ejecucion.pk)
        ejecucion.pasos.all().delete()  # eran de la tarea que no se ha podido hacer
        ejecucion.plan_b = alternativa
        ejecucion.estado = EstadoEjecucion.PENDIENTE
        ejecucion.inicio_real = None
        ejecucion.fin_real = None
        ejecucion.save(update_fields=["plan_b", "estado", "inicio_real", "fin_real"])
    return tarea_del_dia(estudiante, asignacion_id, ahora_)


def texto_para_el_tutor(t):
    """El aviso al tutor cuando su estudiante no ha podido hacer una tarea (HU-07-04):
    qué tarea y qué ha elegido en su lugar."""
    nombre = t.asignacion.estudiante.usuario.first_name
    original = t.tarea_original.nombre
    if t.es_plan_b and t.estado == EstadoEjecucion.NO_REALIZABLE:
        return f"{nombre} tampoco ha podido hacer «{t.tarea.nombre}», del plan B de «{original}»."
    if t.es_plan_b:
        return f"{nombre} no ha podido hacer «{original}» y ha elegido «{t.tarea.nombre}»."
    return f"{nombre} no ha podido hacer «{original}» y no tiene plan B."


# --- HU-02-06 · Ver mi semana (boceto B30) ------------------------------------------


@dataclass
class DiaDeLaSemana:
    """Un día de la semana del estudiante: sus tareas, por hora, sin las canceladas."""

    fecha: object
    es_hoy: bool
    tareas: list

    @property
    def numero(self):
        """1 = lunes … 7 = domingo, como `dias_semana` y `_dia_forma.html`."""
        return self.fecha.isoweekday()

    @property
    def nombre(self):
        return DIAS[self.fecha.weekday()].capitalize()

    @property
    def es_lectivo(self):
        return self.numero <= 5


def lunes_de(fecha):
    return fecha - timedelta(days=fecha.weekday())


def semana(estudiante, ahora_=None):
    """Los 7 días de esta semana, de lunes a domingo (RF2.1.3). Las tareas de cada día son
    las de su agenda (con los cambios de un día y el plan B elegido); las canceladas no se
    cuentan, pero se ven tachadas al abrir el día."""
    ahora_ = ahora_ or ahora()
    hoy = ahora_.date()
    lunes = lunes_de(hoy)
    dias = []
    for n in range(7):
        fecha = lunes + timedelta(days=n)
        tareas = [
            t
            for t in tareas_del_dia(estudiante, fecha, ahora_)
            if t.estado != EstadoEjecucion.CANCELADA
        ]
        dias.append(DiaDeLaSemana(fecha, fecha == hoy, tareas))
    return dias
