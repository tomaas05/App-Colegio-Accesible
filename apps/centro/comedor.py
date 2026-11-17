"""HU-05-04. Anotar quién come cada día (AGENDA-276). Dueño: Javi.

El estudiante encargado del comedor de hoy (HU-05-03) recorre las clases:

- PA1: ve los estudiantes de cada clase con su avatar.
- PA2: marca si cada compañero come o no come (boceto B61: cada toque cambia la marca,
  «Sin marcar» → «Come» → «No come» → «Come»…).
- PA3: puede corregir una marca mientras no haya terminado la clase.
- PA4: marca la clase como terminada y ve qué clases le faltan.
- PA5: no puede terminar una clase con compañeros sin marcar.

Además, el total del centro que come hoy (RF5.2.7) y `comedor_de(estudiante, fecha)` para
que el familiar vea si ha ido al comedor (HU-06-03, Manu).

Se entra desde la tarea «Comedor» ya empezada (el enlace solo sale entonces), pero el
servidor deja entrar al encargado todo el día: si se le olvida pulsar «Empezar» o ya la ha
terminado, puede seguir anotando. Lo que importa es que hoy el comedor es suyo.

Lo que se guarda (cada día, cada estudiante y quién lo anota; cada clase terminada y quién)
es lo que lleva hoy la hoja «Registro semanal de comedor» del colegio, por aula y de lunes a
viernes: el listado en PDF (HU-05-05) puede sacarla de aquí.
"""

from dataclasses import dataclass, field

from django.db import IntegrityError, transaction
from django.db.models import Exists

from apps.usuarios.models import Clase, Estudiante

from . import servicios
from .models import AsistenciaComedor, ClaseComedorTerminada, ComedorDelDia
from .servicios import ErrorDeCentro


def encargo_de_hoy(estudiante):
    """El ComedorDelDia de hoy si el encargado es este estudiante; si no, None."""
    return (
        ComedorDelDia.objects.select_related("asignacion")
        .filter(fecha=servicios.hoy(), asignacion__estudiante=estudiante)
        .first()
    )


def _companeros(clase):
    """Los estudiantes activos de la clase, por nombre (como en «¿Quién eres?»)."""
    return list(
        Estudiante.objects.filter(clase=clase, usuario__is_active=True)
        .select_related("usuario")
        .order_by("usuario__first_name", "usuario__last_name")
    )


def clases_del_centro():
    """Las clases con algún estudiante activo, por nombre (RF5.2.2)."""
    return list(
        Clase.objects.filter(estudiantes__usuario__is_active=True).distinct().order_by("nombre")
    )


@dataclass
class Companero:
    estudiante: Estudiante
    marca: AsistenciaComedor | None
    nombre: str = ""  # el nombre de pila y, si se repite en la clase, la inicial del apellido

    @property
    def siguiente(self):
        """Lo que dejará marcado el próximo toque (lo envía el formulario: si el mismo toque
        llega dos veces, la segunda no cambia nada)."""
        return siguiente_marca(self.marca)

    @property
    def marcado(self):
        return self.marca is not None

    @property
    def come(self):
        return self.marca is not None and self.marca.come

    @property
    def no_come(self):
        return self.marca is not None and not self.marca.come


@dataclass
class ClaseDelDia:
    clase: Clase
    companeros: list = field(default_factory=list)
    terminada: bool = False
    tutor: str = ""  # «A. Martín», como en «¿Cuál es tu clase?» y en la hoja del comedor

    @property
    def total(self):
        return len(self.companeros)

    @property
    def marcados(self):
        return sum(1 for c in self.companeros if c.marcado)

    @property
    def sin_marcar(self):
        return self.total - self.marcados

    @property
    def comen(self):
        return sum(1 for c in self.companeros if c.come)


def clase_del_dia(clase, fecha):
    """Una clase ese día: cada compañero con su marca y si ya está terminada."""
    companeros = _companeros(clase)
    marcas = {
        m.estudiante_id: m
        for m in AsistenciaComedor.objects.filter(fecha=fecha, estudiante__in=companeros)
    }
    terminada = ClaseComedorTerminada.objects.filter(fecha=fecha, clase=clase).exists()
    return ClaseDelDia(
        clase,
        [Companero(e, marcas.get(e.pk), nombre) for e, nombre in _con_nombres(companeros)],
        terminada,
    )


def _con_nombres(companeros):
    """Cada compañero con el nombre que se enseña: «Ana» o, si hay dos, «Ana M.» y «Ana R.»."""
    veces = {}
    for e in companeros:
        veces[e.usuario.first_name] = veces.get(e.usuario.first_name, 0) + 1
    for e in companeros:
        nombre = e.usuario.first_name
        if veces[nombre] > 1 and e.usuario.last_name:
            nombre = f"{nombre} {e.usuario.last_name[:1]}."
        yield e, nombre


def comen_hoy(fecha):
    """RF5.2.7 en una consulta: cuántos comen ese día en todo el centro."""
    return AsistenciaComedor.objects.filter(
        fecha=fecha, come=True, estudiante__usuario__is_active=True
    ).count()


@dataclass
class Resumen:
    clases: list  # ClaseDelDia de cada clase del centro

    @property
    def comen(self):
        """RF5.2.7: cuántos comen hoy en todo el centro."""
        return sum(c.comen for c in self.clases)

    @property
    def faltan(self):
        """PA4: las clases que todavía no están terminadas."""
        return [c for c in self.clases if not c.terminada]

    @property
    def texto_faltan(self):
        faltan = [c.clase.nombre for c in self.faltan]
        if not faltan:
            return "Has terminado todas las clases."
        if len(faltan) == 1:
            return f"Te falta {faltan[0]}."
        return f"Te faltan {', '.join(faltan[:-1])} y {faltan[-1]}."


def resumen(fecha):
    """Todas las clases del centro ese día, con sus marcas (pantalla B60)."""
    clases = clases_del_centro()
    marcas = {
        m.estudiante_id: m
        for m in AsistenciaComedor.objects.filter(fecha=fecha, estudiante__clase__in=clases)
    }
    terminadas = set(
        ClaseComedorTerminada.objects.filter(fecha=fecha).values_list("clase_id", flat=True)
    )
    todos = (
        Estudiante.objects.filter(clase__in=clases, usuario__is_active=True)
        .select_related("usuario")
        .order_by("usuario__first_name", "usuario__last_name")
    )
    por_clase = {c.pk: ClaseDelDia(c, terminada=c.pk in terminadas) for c in clases}
    tutores = {}
    for e in todos.select_related("tutor"):
        por_clase[e.clase_id].companeros.append(Companero(e, marcas.get(e.pk)))
        if e.tutor:
            tutores.setdefault(e.clase_id, set()).add(_tutor_corto(e.tutor))
    for dia in por_clase.values():
        de_la_clase = tutores.get(dia.clase.pk, set())
        dia.tutor = next(iter(de_la_clase)) if len(de_la_clase) == 1 else ""
    return Resumen(list(por_clase.values()))


def _tutor_corto(tutor):
    """«Ana», «Martín Ruiz» → «A. Martín». Si la clase tiene más de un tutor, ninguno."""
    apellido = (tutor.last_name or "").split()
    return f"{tutor.first_name[:1]}. {apellido[0]}" if tutor.first_name and apellido else ""


def siguiente_marca(marca):
    """B61: cada toque cambia la marca. Sin marcar → come → no come → come…"""
    return marca is None or not marca.come


def cambiar(encargado, companero):
    """Un toque en el compañero (B61): pasa a la marca siguiente."""
    actual = AsistenciaComedor.objects.filter(fecha=servicios.hoy(), estudiante=companero).first()
    return marcar(encargado, companero, siguiente_marca(actual))


def marcar(encargado, companero, come):
    """PA2 y PA3: el encargado de hoy marca si un compañero come. Se puede cambiar
    mientras la clase del compañero no esté terminada."""
    fecha = servicios.hoy()
    if not encargo_de_hoy(encargado):
        raise ErrorDeCentro("Hoy no te toca el comedor.")
    if not companero.usuario.is_active:
        raise ErrorDeCentro("Ese compañero ya no está en el centro.")
    with transaction.atomic():
        # Bloquea la clase: «Clase terminada» no puede colarse entre la comprobación y la marca.
        Clase.objects.select_for_update().filter(pk=companero.clase_id).exists()
        if ClaseComedorTerminada.objects.filter(fecha=fecha, clase=companero.clase_id).exists():
            raise ErrorDeCentro(f"{companero.clase.nombre} ya está terminada: no se puede cambiar.")
        marca, _ = AsistenciaComedor.objects.update_or_create(
            fecha=fecha,
            estudiante=companero,
            defaults={"come": bool(come), "anotada_por": encargado.usuario},
        )
    return marca


def terminar_clase(encargado, clase):
    """PA4 y PA5: da la clase por terminada si todos sus compañeros tienen marca."""
    fecha = servicios.hoy()
    if not encargo_de_hoy(encargado):
        raise ErrorDeCentro("Hoy no te toca el comedor.")
    try:
        with transaction.atomic():
            # Bloquea la clase: ninguna marca cambia mientras se comprueba y se cierra.
            Clase.objects.select_for_update().filter(pk=clase.pk).exists()
            dia = clase_del_dia(clase, fecha)
            if dia.terminada:
                return dia
            if dia.sin_marcar:
                raise ErrorDeCentro(
                    "Te falta 1 compañero por marcar."
                    if dia.sin_marcar == 1
                    else f"Te faltan {dia.sin_marcar} compañeros por marcar."
                )
            ClaseComedorTerminada.objects.create(
                fecha=fecha, clase=clase, terminada_por=encargado.usuario
            )
    except IntegrityError:
        dia = clase_del_dia(clase, fecha)  # doble toque a la vez: ya estaba terminada
    dia.terminada = True
    return dia


# --- Para HU-06-03 (Manu): lo que ve el familiar --------------------------------------

COME = "come"
NO_COME = "no_come"


def comedor_de(estudiante, fecha):
    """Si el estudiante ha ido al comedor ese día: COME, NO_COME o None («todavía no se
    sabe»). Solo cuenta cuando el encargado ha terminado su clase: hasta entonces la marca
    se puede cambiar."""
    come = (
        AsistenciaComedor.objects.filter(fecha=fecha, estudiante=estudiante)
        .filter(
            Exists(ClaseComedorTerminada.objects.filter(fecha=fecha, clase=estudiante.clase_id))
        )
        .values_list("come", flat=True)
        .first()
    )
    if come is None:
        return None
    return COME if come else NO_COME
