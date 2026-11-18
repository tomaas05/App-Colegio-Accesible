"""HU-05-01. Crear una tarea de reprografía (AGENDA-260). Dueño: Javi.

El tutor (con los estudiantes de su clase) o el administrador (con todos) pone en la agenda
de un estudiante, un día de lunes a viernes y a una hora, la tarea «Reprografía» con:
número de copias (1 a 99), tipo de trabajo (imprimir, fotocopiar o plastificar; uno o
varios), color o blanco y negro (si se imprime o se fotocopia; por defecto, blanco y negro)
y aula de recogida y entrega (RF5.1.1 a RF5.1.3).

- PA1: se crea y sale en la agenda del estudiante (es una Asignacion normal, de un día).
- PA2: si falta un dato, no se guarda (los errores de cada campo, en forms.py).
- PA3: la tarea trae las fases recoger, imprimir o fotocopiar y repartir (servicios.py,
  PASOS_TAREA). El tutor las cambia en «Pasos de la tarea» (HU-03-02, Úrsula).
- PA4: si el estudiante ya la ha empezado, sus datos no se pueden cambiar (RF5.1.5).

Como al asignar cualquier tarea (HU-03-03), no se guarda si el estudiante ya tiene otra a
esa hora ese día (planificacion.choque_en_fecha, de Úrsula).
"""

from dataclasses import dataclass
from datetime import date, time

from django.db import IntegrityError, transaction

from apps.agenda import servicios as agenda
from apps.agenda.models import Ejecucion, EstadoEjecucion
from apps.tareas import planificacion
from apps.tareas.models import Asignacion, ExcepcionAsignacion
from apps.usuarios.models import Estudiante, Rol
from apps.usuarios.vinculos import estudiantes_de

from . import servicios
from .models import TipoTareaCentro, TrabajoReprografia
from .servicios import (
    DIAS_LECTIVOS,
    OTRO_A_LA_VEZ,
    ErrorDeCentro,
    _bloquear,
    _comprobar_horas,
    _nombre,
    tarea_de,
    texto_fecha,
)

YA_EMPEZADA = (
    "No se ha guardado: {nombre} ya ha empezado esta tarea, así que sus datos no se pueden cambiar."
)


def puede_crear(usuario):
    """Solo el tutor y el administrador (la HU: «Como tutor o administrador…»)."""
    return usuario.is_authenticated and usuario.rol in (Rol.TUTOR, Rol.ADMINISTRADOR)


@dataclass(frozen=True)
class Datos:
    """Lo que se elige en el formulario."""

    estudiante: Estudiante
    fecha: date
    hora_inicio: time
    hora_fin: time
    copias: int
    trabajos: list  # de "imprimir", "fotocopiar" y "plastificar"
    color: bool  # True color, False blanco y negro (se ignora si solo se plastifica)
    aula: str


def _comprobar(datos):
    if datos.fecha.isoweekday() not in DIAS_LECTIVOS:
        raise ErrorDeCentro("No se ha guardado: la reprografía es de lunes a viernes.")
    if datos.fecha < servicios.hoy():
        raise ErrorDeCentro("No se ha guardado: ese día ya ha pasado.")
    _comprobar_horas(datos.hora_inicio, datos.hora_fin)
    if datos.fecha == servicios.hoy() and datos.hora_fin <= agenda.ahora().time():
        raise ErrorDeCentro("No se ha guardado: hoy esa hora ya ha pasado.")


def _comprobar_que_no_choca(datos, excluir=None):
    choque = planificacion.choque_en_fecha(
        datos.estudiante, datos.fecha, datos.hora_inicio, datos.hora_fin, excluir=excluir
    )
    if choque:
        raise ErrorDeCentro(
            f"No se ha guardado: {datos.estudiante.usuario.first_name} ya tiene "
            f"{choque.texto}. Elige otra hora u otro día."
        )


def _poner_datos(trabajo, datos):
    trabajo.copias = datos.copias
    trabajo.imprimir = "imprimir" in datos.trabajos
    trabajo.fotocopiar = "fotocopiar" in datos.trabajos
    trabajo.plastificar = "plastificar" in datos.trabajos
    # RF5.1.2: el color solo se pregunta si se imprime o se fotocopia.
    trabajo.color = bool(datos.color) if (trabajo.imprimir or trabajo.fotocopiar) else None
    trabajo.aula = datos.aula.strip()


def crear(datos, por):
    """PA1: pone la tarea «Reprografía» en la agenda del estudiante ese día, a esa hora."""
    _comprobar(datos)
    try:
        with transaction.atomic():
            _bloquear(datos.estudiante)
            _comprobar_que_no_choca(datos)
            asignacion = Asignacion.objects.create(
                tarea=tarea_de(TipoTareaCentro.REPROGRAFIA, por),
                estudiante=datos.estudiante,
                asignado_por=por,
                hora_inicio=datos.hora_inicio,
                hora_fin=datos.hora_fin,
                dias_semana=[datos.fecha.isoweekday()],
                vigencia_desde=datos.fecha,
                vigencia_hasta=datos.fecha,
            )
            trabajo = TrabajoReprografia(asignacion=asignacion)
            _poner_datos(trabajo, datos)
            trabajo.save()
    except IntegrityError as error:
        raise ErrorDeCentro(OTRO_A_LA_VEZ) from error
    return trabajo


def _sin_tocar(ejecucion):
    """La agenda a veces crea la ejecución del día antes de empezar (al pulsar «Empezar»
    cuando aún no es la hora, por ejemplo): si sigue pendiente y no tiene nada, cuenta como
    que el estudiante no la ha tocado. Con plan B o «No puedo», sí la ha tocado."""
    return (
        ejecucion.estado == EstadoEjecucion.PENDIENTE
        and ejecucion.inicio_real is None
        and ejecucion.no_realizable_el is None
        and ejecucion.plan_b_id is None
    )


def como_queda(trabajo):
    """El día de la tarea: (fecha, hora de inicio, hora de fin, estado).

    Estado: "pendiente", "empezada", "hecha", "sin_hacer" (ya pasó su hora, no ha podido o
    eligió el plan B) o "cancelada". Las horas son las de ese día (pueden estar cambiadas
    «solo este día» en «Tareas planificadas», de Úrsula). Usa las excepciones y ejecuciones
    ya cargadas con prefetch_related, si las hay.

    Como en la agenda (Tomás), lo que el estudiante ya ha hecho manda sobre la cancelación.
    """
    a = trabajo.asignacion
    fecha = a.vigencia_desde
    excepcion = next((e for e in a.excepciones.all() if e.fecha == fecha), None)
    o = planificacion.ocurrencia(a, fecha, excepcion)
    ejecucion = next((e for e in a.ejecuciones.all() if e.fecha == fecha), None)
    if ejecucion and ejecucion.estado == EstadoEjecucion.HECHA:
        estado = "hecha"
    elif ejecucion and ejecucion.estado in (
        EstadoEjecucion.EN_CURSO,
        EstadoEjecucion.TIEMPO_AGOTADO,
    ):
        estado = "empezada"  # RF5.1.5: ya no está «pendiente»
    elif ejecucion and not _sin_tocar(ejecucion) and ejecucion.estado != EstadoEjecucion.CANCELADA:
        estado = "sin_hacer"
    elif o.cancelada or (ejecucion and ejecucion.estado == EstadoEjecucion.CANCELADA):
        estado = "cancelada"
    elif fecha < servicios.hoy() or (
        fecha == servicios.hoy() and agenda.ahora().time() >= o.hora_fin
    ):
        estado = "sin_hacer"  # vencida: su hora ya ha pasado
    else:
        estado = "pendiente"
    return fecha, o.hora_inicio, o.hora_fin, estado


def empezada(trabajo):
    """PA4: no está «pendiente»: la ha empezado, hecho o no ha podido, o ya pasó su hora."""
    return como_queda(trabajo)[3] in ("empezada", "hecha", "sin_hacer")


def por_que_no_se_cambia(trabajo, estado):
    """El mensaje de por qué ya no se puede cambiar ni quitar."""
    nombre = _nombre(trabajo.asignacion.estudiante)
    if estado == "cancelada":
        return "No se ha guardado: esta tarea está cancelada."
    if estado == "sin_hacer":
        return "No se ha guardado: esta tarea ya no está pendiente, así que no se puede cambiar."
    return YA_EMPEZADA.format(nombre=nombre)


def _bloquear_trabajo(trabajo):
    """Vuelve a leer el trabajo bloqueando su asignación y sus ejecuciones hasta el final de
    la transacción. Mientras, el estudiante no puede empezarla: para crear su ejecución,
    PostgreSQL tiene que comprobar la asignación, que está bloqueada (FOR UPDATE)."""
    Asignacion.objects.select_for_update().filter(pk=trabajo.asignacion_id).exists()
    list(Ejecucion.objects.select_for_update().filter(asignacion_id=trabajo.asignacion_id))
    return (
        TrabajoReprografia.objects.select_for_update(of=("self",))
        .select_related("asignacion__estudiante__usuario")
        .get(pk=trabajo.pk)
    )


def cambiar(trabajo, datos, por):
    """Cambia el estudiante, el día, las horas o los datos, si aún no la ha empezado (PA4).

    Si en «Tareas planificadas» (Úrsula) se le cambiaron las horas «solo ese día», ese
    cambio se quita: el formulario ya traía esas horas y desde ahora mandan las de aquí."""
    _comprobar(datos)
    try:
        with transaction.atomic():
            _bloquear(datos.estudiante)
            trabajo = _bloquear_trabajo(trabajo)
            asignacion = trabajo.asignacion
            estado = como_queda(trabajo)[3]
            if estado != "pendiente":
                raise ErrorDeCentro(por_que_no_se_cambia(trabajo, estado))
            _comprobar_que_no_choca(datos, excluir=asignacion)
            # La ejecución que la agenda tenía preparada sin tocar (ver _sin_tocar) sobra.
            for ejecucion in asignacion.ejecuciones.all():
                if _sin_tocar(ejecucion):
                    ejecucion.delete()
            ExcepcionAsignacion.objects.filter(asignacion=asignacion).delete()
            asignacion.estudiante = datos.estudiante
            asignacion.hora_inicio, asignacion.hora_fin = datos.hora_inicio, datos.hora_fin
            asignacion.dias_semana = [datos.fecha.isoweekday()]
            asignacion.vigencia_desde = asignacion.vigencia_hasta = datos.fecha
            asignacion.save()
            _poner_datos(trabajo, datos)
            trabajo.save()
    except IntegrityError as error:
        raise ErrorDeCentro(OTRO_A_LA_VEZ) from error
    return trabajo


def quitar(trabajo):
    """Quita la tarea de la agenda del estudiante si aún está pendiente (o cancelada sin
    que la llegara a hacer)."""
    with transaction.atomic():
        trabajo = _bloquear_trabajo(trabajo)
        estado = como_queda(trabajo)[3]
        if estado not in ("pendiente", "cancelada"):
            raise ErrorDeCentro(
                por_que_no_se_cambia(trabajo, estado)
                .replace("No se ha guardado", "No se ha quitado")
                .replace("no se puede cambiar", "no se puede quitar")
                .replace("sus datos no se pueden cambiar", "no se puede quitar")
            )
        trabajo.asignacion.delete()  # el trabajo se borra con ella (CASCADE)


# --- Lo que se ve en la lista ------------------------------------------------------------


@dataclass
class Fila:
    """Un trabajo de reprografía tal como queda su día (con las horas de ese día)."""

    trabajo: TrabajoReprografia
    fecha: date
    hora_inicio: time
    hora_fin: time
    estado: str  # ver como_queda

    @property
    def estudiante(self):
        return self.trabajo.asignacion.estudiante

    @property
    def texto_fecha(self):
        return texto_fecha(self.fecha)

    @property
    def es_hoy(self):
        return self.fecha == servicios.hoy()

    @property
    def se_puede_cambiar(self):
        return self.estado == "pendiente"

    @property
    def texto_estado(self):
        return {
            "pendiente": "Sin empezar",
            "empezada": "Empezada",
            "hecha": "Hecha",
            "sin_hacer": "Sin hacer",
            "cancelada": "Cancelada",
        }[self.estado]


def visibles(usuario):
    """Los trabajos de los estudiantes que ve el usuario (el tutor, los de su clase)."""
    return TrabajoReprografia.objects.filter(asignacion__estudiante__in=estudiantes_de(usuario))


def lista(usuario):
    """Los trabajos de hoy en adelante, por día y hora (PA1: se ve lo que se ha creado)."""
    trabajos = list(
        visibles(usuario)
        .filter(asignacion__vigencia_desde__gte=servicios.hoy())
        .select_related("asignacion__estudiante__usuario", "asignacion__estudiante__clase")
        .prefetch_related("asignacion__excepciones", "asignacion__ejecuciones")
    )
    filas = [Fila(t, *como_queda(t)) for t in trabajos]
    filas.sort(key=lambda f: (f.fecha, f.hora_inicio, f.trabajo.pk))
    return filas


def fases(usuario):
    """Las fases (pasos) de la tarea «Reprografía» del catálogo (PA3)."""
    tarea = tarea_de(TipoTareaCentro.REPROGRAFIA, usuario)
    return tarea, list(tarea.pasos.order_by("orden"))
