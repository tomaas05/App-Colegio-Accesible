"""Tareas planificadas: quién puede cambiarlas, cómo quedan un día concreto y los solapes.

HU-03-04 (modificar), HU-03-05 (cancelar) y HU-03-03 (asignar sin solapes). Lo usan las
vistas de tareas y la agenda del estudiante (apps/agenda/servicios.py), para que todas
las pantallas vean la misma tarea con las mismas horas.

- «Toda la serie» cambia la asignación. «Solo este día» guarda una excepción para esa
  fecha (ExcepcionAsignacion, RI3.2.3): otras horas o cancelada.
- Una serie cancelada deja de hacerse desde `cancelada_el`. Durante DIAS_VISIBLE_CANCELADA
  días el estudiante la sigue viendo en su agenda tachada como «Cancelada» (prueba de
  aceptación de HU-03-05); después ya no sale.
"""

from dataclasses import dataclass
from datetime import date, time, timedelta

from django.db.models import Q
from django.utils import timezone

from apps.usuarios.models import Rol
from apps.usuarios.vinculos import estudiantes_de

from .models import Asignacion, ExcepcionAsignacion, TipoExcepcion

DIAS_VISIBLE_CANCELADA = 7

# Nombres fijos en español (LocaleMiddleware usaría el idioma del navegador).
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
DIAS_CORTOS = ["L", "M", "X", "J", "V", "S", "D"]
MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]  # fmt: skip


def fecha_en_texto(fecha):
    """«jueves 19 de noviembre»."""
    return f"{DIAS[fecha.weekday()]} {fecha.day} de {MESES[fecha.month - 1]}"


def dias_en_texto(dias):
    """[1, 3] → «los lunes y miércoles»; los 7 → «todos los días»."""
    dias = sorted(dias)
    if dias == list(range(1, 8)):
        return "todos los días"
    if dias == list(range(1, 6)):
        return "de lunes a viernes"
    nombres = [DIAS[d - 1] + ("" if DIAS[d - 1].endswith("s") else "s") for d in dias]
    if len(nombres) == 1:
        return f"los {nombres[0]}"
    return "los " + ", ".join(nombres[:-1]) + " y " + nombres[-1]


def horas_en_texto(inicio, fin):
    return f"de {inicio:%H:%M} a {fin:%H:%M}"


# --- Quién puede cambiar una tarea planificada ---


def puede_cambiar(usuario, asignacion):
    """Si `usuario` puede modificar o cancelar esta asignación.

    - Solo de los estudiantes que ve (estudiantes_de, docs/contribuir.md).
    - El tutor, todas las de sus estudiantes salvo las del familiar (RF3.3.5: las ve,
      pero no las cambia).
    - El profesional y el familiar, solo las que han puesto ellos (HU-03-08, HU-03-07).
    """
    if not estudiantes_de(usuario).filter(pk=asignacion.estudiante_id).exists():
        return False
    if usuario.rol == Rol.TUTOR:
        return asignacion.asignado_por.rol != Rol.FAMILIAR
    if usuario.rol in (Rol.PROFESIONAL, Rol.FAMILIAR):
        return asignacion.asignado_por_id == usuario.pk
    return False


def que_puede_cambiar(usuario):
    """Las asignaciones que `usuario` puede modificar o cancelar (mismas reglas)."""
    base = Asignacion.objects.filter(estudiante__in=estudiantes_de(usuario))
    if usuario.rol == Rol.TUTOR:
        return base.exclude(asignado_por__rol=Rol.FAMILIAR)
    if usuario.rol in (Rol.PROFESIONAL, Rol.FAMILIAR):
        return base.filter(asignado_por=usuario)
    return base.none()


# --- Cómo queda una asignación un día concreto ---


@dataclass(frozen=True)
class Ocurrencia:
    """Una asignación en una fecha, con las horas de ese día y si está cancelada."""

    asignacion: Asignacion
    fecha: date
    hora_inicio: time
    hora_fin: time
    cancelada: bool = False
    cambiada: bool = False  # ese día tiene otras horas («solo este día»)


def serie_cancelada_el(asignacion, fecha):
    return bool(
        asignacion.cancelada and asignacion.cancelada_el and fecha >= asignacion.cancelada_el
    )


def ocurrencia(asignacion, fecha, excepcion=None):
    """La asignación tal como queda en `fecha` (no comprueba que toque ese día)."""
    if excepcion is not None and excepcion.tipo == TipoExcepcion.MODIFICADA:
        inicio, fin, cambiada = excepcion.hora_inicio, excepcion.hora_fin, True
    else:
        inicio, fin, cambiada = asignacion.hora_inicio, asignacion.hora_fin, False
    cancelada = serie_cancelada_el(asignacion, fecha) or (
        excepcion is not None and excepcion.tipo == TipoExcepcion.CANCELADA
    )
    return Ocurrencia(asignacion, fecha, inicio, fin, cancelada, cambiada)


def ocurrencias_del_dia(estudiante, fecha, *, con_canceladas=True):
    """Las tareas del estudiante en `fecha`, ordenadas por la hora de ese día.

    Con `con_canceladas`, también las canceladas que el estudiante aún tiene que ver
    tachadas: la de ese día y la serie cancelada hace menos de DIAS_VISIBLE_CANCELADA días.
    """
    limite = fecha - timedelta(days=DIAS_VISIBLE_CANCELADA)
    asignaciones = (
        estudiante.asignaciones.select_related("tarea", "tarea__creador", "asignado_por")
        .filter(vigencia_desde__lte=fecha, dias_semana__contains=[fecha.isoweekday()])
        .filter(Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=fecha))
        .filter(Q(cancelada=False) | Q(cancelada_el__gt=fecha if not con_canceladas else limite))
    )
    asignaciones = list(asignaciones)
    excepciones = {
        e.asignacion_id: e
        for e in ExcepcionAsignacion.objects.filter(asignacion__in=asignaciones, fecha=fecha)
    }
    lista = [ocurrencia(a, fecha, excepciones.get(a.pk)) for a in asignaciones]
    if not con_canceladas:
        lista = [o for o in lista if not o.cancelada]
    return sorted(lista, key=lambda o: (o.hora_inicio, o.hora_fin, o.asignacion.pk))


# --- Solapes (HU-03-03 y HU-03-04: «no puede haber tareas solapadas») ---


@dataclass(frozen=True)
class Choque:
    """Con qué tarea choca un horario: se le dice a quien planifica (HU-03-03, PA3)."""

    asignacion: Asignacion
    hora_inicio: time
    hora_fin: time
    fecha: date | None = None

    @property
    def texto(self):
        cuando = f" el {fecha_en_texto(self.fecha)}" if self.fecha else ""
        return (
            f"«{self.asignacion.tarea.nombre}» ({horas_en_texto(self.hora_inicio, self.hora_fin)}"
            f"{cuando})"
        )


def _se_cruzan(inicio_a, fin_a, inicio_b, fin_b):
    return inicio_a < fin_b and fin_a > inicio_b


def choque_en_fecha(estudiante, fecha, hora_inicio, hora_fin, *, excluir=None):
    """La primera tarea del estudiante que se cruza con ese horario en `fecha`, o None."""
    for o in ocurrencias_del_dia(estudiante, fecha, con_canceladas=False):
        if excluir is not None and o.asignacion.pk == excluir.pk:
            continue
        if _se_cruzan(hora_inicio, hora_fin, o.hora_inicio, o.hora_fin):
            return Choque(o.asignacion, o.hora_inicio, o.hora_fin, fecha)
    return None


def choque_en_serie(
    estudiante, dias, hora_inicio, hora_fin, desde, hasta=None, *, excluir=None, hoy=None
):
    """La primera tarea que se cruza con una serie (unos días de la semana entre dos fechas).

    Compara con las otras series por sus horas de siempre y, además, con los días sueltos
    que otra tarea tiene cambiados («solo este día»). Lo ya pasado no cuenta.
    """
    hoy = hoy or timezone.localdate()
    desde = max(desde or hoy, hoy)
    hasta_ = hasta or date.max
    if desde > hasta_:
        return None
    dias = set(dias)
    otras = estudiante.asignaciones.select_related("tarea").filter(
        Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=desde), vigencia_desde__lte=hasta_
    )
    if excluir is not None:
        otras = otras.exclude(pk=excluir.pk)
    for otra in otras:
        # Una serie cancelada solo cuenta hasta el día antes de cancelarse.
        fin_otra = otra.vigencia_hasta or date.max
        if otra.cancelada:
            fin_otra = min(fin_otra, otra.cancelada_el - timedelta(days=1))
        if max(desde, otra.vigencia_desde) > min(hasta_, fin_otra):
            continue
        if dias & set(otra.dias_semana) and _se_cruzan(
            hora_inicio, hora_fin, otra.hora_inicio, otra.hora_fin
        ):
            # Puede que justo esos días la otra tenga otras horas o esté cancelada; para no
            # rechazar de más, se mira día a día solo si la otra tiene excepciones.
            if not otra.excepciones.exists():
                return Choque(otra, otra.hora_inicio, otra.hora_fin)
            for fecha in _fechas(desde, min(hasta_, fin_otra), dias & set(otra.dias_semana)):
                o = ocurrencia(otra, fecha, otra.excepciones.filter(fecha=fecha).first())
                if not o.cancelada and _se_cruzan(hora_inicio, hora_fin, o.hora_inicio, o.hora_fin):
                    return Choque(otra, o.hora_inicio, o.hora_fin, fecha if o.cambiada else None)
        # Días sueltos de la otra con otras horas que sí se cruzan.
        cambiadas = otra.excepciones.filter(
            tipo=TipoExcepcion.MODIFICADA, fecha__gte=desde, fecha__lte=min(hasta_, fin_otra)
        )
        for excepcion in cambiadas:
            if excepcion.fecha.isoweekday() in dias and _se_cruzan(
                hora_inicio, hora_fin, excepcion.hora_inicio, excepcion.hora_fin
            ):
                return Choque(otra, excepcion.hora_inicio, excepcion.hora_fin, excepcion.fecha)
    return None


def _fechas(desde, hasta, dias, maximo=400):
    """Las fechas entre `desde` y `hasta` que caen en esos días de la semana (como mucho
    `maximo`, para una serie sin fin: más de un año de clases)."""
    fecha, n = desde, 0
    while fecha <= hasta and n < maximo:
        if fecha.isoweekday() in dias:
            yield fecha
        fecha += timedelta(days=1)
        n += 1
