"""HU-05-03. Asignar el comedor y el reparto del menú (AGENDA-270). Dueño: Javi.

- PA1: el administrador asigna el comedor de un día (lunes a viernes) a un estudiante, con
  hora de inicio y de fin, y la tarea «Comedor» sale en la agenda del estudiante ese día.
- PA2: asigna el reparto del menú de un mes, con su horario (horas y días de la semana), y
  la tarea «Reparto del menú» sale en su agenda esos días del mes.
- PA3: sin horario no se guarda.
- PA4: asignar un día o un mes que ya tiene estudiante lo sustituye por el nuevo.
- PA5: los días y los meses sin estudiante se enseñan como «pendiente de asignar».

Las dos tareas son asignaciones normales (apps.tareas.Asignacion), así que salen en la
agenda (Tomás) y en la agenda que consulta el profesional (HU-01-09) sin tocar nada más.
Como en «asignar una tarea» (HU-03-03, Úrsula), no se guarda si el estudiante ya tiene
otra tarea a esa hora.

Además, el administrador puede subir el menú del mes (PDF o imagen) para que el familiar
lo vea en el día del estudiante (HU-06-03, Manu): `menu_del_mes(fecha)`.
"""

import calendar
import io
from dataclasses import dataclass
from datetime import date, timedelta

from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from PIL import Image, ImageDraw

from apps.comun import pictos_interfaz
from apps.comun.fuentes import fuente_titulos
from apps.tareas.models import Ambito, Asignacion, Paso, Tarea
from apps.usuarios.models import Estudiante

from .models import ComedorDelDia, RepartoMenu, TareaDelCentro, TipoTareaCentro

DIAS_LECTIVOS = [1, 2, 3, 4, 5]  # lunes a viernes (isoweekday)

# Nombres fijos en español: LocaleMiddleware usaría el idioma del navegador.
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]  # fmt: skip

# Nombre, descripción, palabra del pictograma y letras del dibujo de reserva de cada tarea.
DATOS_TAREA = {
    TipoTareaCentro.COMEDOR: (
        "Comedor",
        "Ve a cada clase y anota quién come hoy en el comedor.",
        "comedor",
        "Co",
    ),
    TipoTareaCentro.REPARTO_MENU: (
        "Reparto del menú",
        "Reparte el menú del mes en cada clase y anota a quién se lo has dado.",
        "menú",
        "Me",
    ),
    TipoTareaCentro.REPROGRAFIA: (
        "Reprografía",
        "Recoge el material en el aula, haz el trabajo en el taller y llévalo al aula.",
        "fotocopiadora",
        "Re",
    ),
}

# Los pasos con los que se crea cada tarea del catálogo: (texto, palabra del pictograma,
# letras). Después el tutor los puede cambiar como los de cualquier tarea (RF3.1.4).
PASOS_TAREA = {
    # RF5.1.6 (HU-05-01, PA3): las tres fases de la reprografía.
    TipoTareaCentro.REPROGRAFIA: [
        ("Recoger el material en el aula", "recoger", "1"),
        ("Imprimir, fotocopiar o plastificar en el taller", "fotocopiadora", "2"),
        ("Repartir el original y las copias en el aula", "repartir", "3"),
    ],
}


class ErrorDeCentro(Exception):
    """Algo que no se puede guardar. El mensaje se enseña tal cual."""


def hoy():
    """La fecha de hoy en el centro. Las pruebas la sustituyen (monkeypatch)."""
    return timezone.localdate()


# --- Fechas -----------------------------------------------------------------------------


def primer_dia(fecha):
    return fecha.replace(day=1)


def ultimo_dia(fecha):
    return fecha.replace(day=calendar.monthrange(fecha.year, fecha.month)[1])


def mes_siguiente(mes):
    return ultimo_dia(mes) + timedelta(days=1)


def mes_anterior(mes):
    return primer_dia(primer_dia(mes) - timedelta(days=1))


def dias_lectivos(mes):
    """Los días de lunes a viernes del mes, en orden."""
    dia, fin = primer_dia(mes), ultimo_dia(mes)
    dias = []
    while dia <= fin:
        if dia.isoweekday() in DIAS_LECTIVOS:
            dias.append(dia)
        dia += timedelta(days=1)
    return dias


def nombre_mes(mes):
    """«noviembre de 2026»."""
    return f"{MESES[mes.month - 1]} de {mes.year}"


def texto_fecha(fecha):
    """«miércoles 18 de noviembre»."""
    return f"{DIAS[fecha.weekday()]} {fecha.day} de {MESES[fecha.month - 1]}"


def texto_dias(dias):
    """[1, 2, 3, 4, 5] → «de lunes a viernes»; [1, 3] → «lunes y miércoles»."""
    dias = sorted(dias)
    if dias == DIAS_LECTIVOS:
        return "de lunes a viernes"
    nombres = [DIAS[d - 1] for d in dias]
    return nombres[0] if len(nombres) == 1 else ", ".join(nombres[:-1]) + " y " + nombres[-1]


# --- Tareas del catálogo ----------------------------------------------------------------


def _imagen_de(tipo):
    _, _, palabra, letras = DATOS_TAREA[tipo]
    return _imagen(palabra, letras, f"centro-{tipo}.png")


def _imagen(palabra, letras, nombre):
    """El pictograma de la interfaz si ya está descargado; si no, un dibujo con letras."""
    descargado = pictos_interfaz.archivo(palabra)
    if descargado:
        return ContentFile(descargado.read_bytes(), name=nombre)
    lado = 256
    lienzo = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(lienzo)
    dibujo.rounded_rectangle((0, 0, lado - 1, lado - 1), radius=40, fill="#0B3C49")
    fuente = fuente_titulos(120)
    caja = dibujo.textbbox((0, 0), letras, font=fuente)
    x = (lado - (caja[2] - caja[0])) / 2 - caja[0]
    y = (lado - (caja[3] - caja[1])) / 2 - caja[1]
    dibujo.text((x, y), letras, font=fuente, fill="white")
    salida = io.BytesIO()
    lienzo.save(salida, format="PNG")
    return ContentFile(salida.getvalue(), name=nombre)


def tarea_de(tipo, creador):
    """La tarea «Comedor», «Reparto del menú» o «Reprografía» del catálogo. La crea (con sus
    pasos, si los tiene) la primera vez."""
    existente = TareaDelCentro.objects.select_related("tarea").filter(tipo=tipo).first()
    if existente:
        return existente.tarea
    nombre, descripcion, _, _ = DATOS_TAREA[tipo]
    try:
        with transaction.atomic():
            tarea = Tarea(
                nombre=nombre,
                descripcion=descripcion,
                descripcion_imagen=nombre,
                ambito=Ambito.ESCOLAR,
                creador=creador,
            )
            tarea.imagen.save(f"centro-{tipo}.png", _imagen_de(tipo), save=False)
            tarea.save()
            for orden, (texto, palabra, letras) in enumerate(PASOS_TAREA.get(tipo, []), 1):
                paso = Paso(
                    tarea=tarea,
                    orden=orden,
                    descripcion=texto,
                    descripcion_imagen=palabra.capitalize(),
                )
                paso.imagen.save(
                    f"centro-{tipo}-{orden}.png",
                    _imagen(palabra, letras, f"centro-{tipo}-{orden}.png"),
                    save=False,
                )
                paso.save()
            TareaDelCentro.objects.create(tipo=tipo, tarea=tarea)
            return tarea
    except IntegrityError:
        # Otro administrador la ha creado a la vez: se usa la suya.
        return TareaDelCentro.objects.get(tipo=tipo).tarea


# --- Comprobaciones comunes -------------------------------------------------------------


def _comprobar_horas(hora_inicio, hora_fin):
    """PA3: sin horario no se guarda."""
    if not hora_inicio or not hora_fin:
        raise ErrorDeCentro("No se ha guardado: pon la hora de inicio y la de fin.")
    if hora_fin <= hora_inicio:
        raise ErrorDeCentro(
            "No se ha guardado: la hora de fin tiene que ser después de la de inicio."
        )


def tarea_que_choca(estudiante, dias, desde, hasta, hora_inicio, hora_fin, excluir=None):
    """La asignación del estudiante que coincide en algún día y hora con la nueva, o None.

    `excluir`: la asignación que se va a sustituir (no choca consigo misma).
    """
    candidatas = (
        estudiante.asignaciones.select_related("tarea")
        .filter(hora_inicio__lt=hora_fin, hora_fin__gt=hora_inicio)
        .filter(vigencia_desde__lte=hasta, dias_semana__overlap=list(dias))
        .filter(Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=desde))
        .order_by("hora_inicio")
    )
    if excluir is not None:
        candidatas = candidatas.exclude(pk=excluir.pk)
    for otra in candidatas:
        # Que tengan días de la semana en común no basta: tiene que haber una fecha de
        # verdad en la que toquen las dos.
        dia = max(desde, otra.vigencia_desde)
        fin = min(hasta, otra.vigencia_hasta or hasta)
        while dia <= fin:
            if dia.isoweekday() in dias and otra.aplica_el(dia):
                return otra
            dia += timedelta(days=1)
    return None


def _comprobar_que_no_choca(estudiante, dias, desde, hasta, hora_inicio, hora_fin, excluir):
    otra = tarea_que_choca(estudiante, dias, desde, hasta, hora_inicio, hora_fin, excluir)
    if otra:
        raise ErrorDeCentro(
            f"No se ha guardado: {estudiante.usuario.first_name} ya tiene «{otra.tarea.nombre}» "
            f"de {otra.hora_inicio:%H:%M} a {otra.hora_fin:%H:%M}. "
            "Elige otra hora u otro estudiante."
        )


def _nombre(estudiante):
    return estudiante.usuario.get_full_name() or estudiante.codigo_estudiante


# --- Comedor de un día (PA1, PA3, PA4) --------------------------------------------------


@dataclass
class Resultado:
    """Lo que ha pasado al guardar, para el mensaje de la pantalla."""

    texto: str
    sustituido: object = None  # el estudiante que estaba antes (PA4), si había otro


def _bloquear(estudiante):
    """Bloquea al estudiante hasta el final de la transacción: dos asignaciones a la vez
    no pueden quedar solapadas en su agenda sin que la comprobación de choques lo vea."""
    Estudiante.objects.select_for_update().filter(pk=estudiante.pk).exists()


def _ultimo_dia_hecho(asignacion, desde):
    """El último día, desde `desde`, en el que el estudiante ya ha empezado o terminado la
    tarea (hay ejecución), o None."""
    return (
        asignacion.ejecuciones.filter(fecha__gte=desde)
        .order_by("-fecha")
        .values_list("fecha", flat=True)
        .first()
    )


def _retirar(asignacion, desde):
    """La asignación deja de tocar desde `desde` sin perder lo que el estudiante ya ha hecho:
    si ya la ha empezado ese día (o después), se queda hasta ese día; si no había empezado
    nunca, se borra; si no, termina el día antes."""
    hasta = desde - timedelta(days=1)
    hecho = _ultimo_dia_hecho(asignacion, desde)
    if hecho:
        hasta = hecho
    if hasta < asignacion.vigencia_desde and not asignacion.ejecuciones.exists():
        asignacion.delete()
    elif asignacion.vigencia_hasta is None or asignacion.vigencia_hasta > hasta:
        asignacion.vigencia_hasta = max(hasta, asignacion.vigencia_desde)
        asignacion.save(update_fields=["vigencia_hasta"])


OTRO_A_LA_VEZ = "No se ha guardado: otra persona lo estaba cambiando a la vez. Vuelve a probar."


def asignar_comedor(fecha, estudiante, hora_inicio, hora_fin, por):
    """PA1: pone la tarea «Comedor» en la agenda del estudiante ese día, a esa hora.

    PA4: si ese día ya tenía otro estudiante, lo sustituye: su tarea desaparece de su
    agenda, salvo que ya la haya empezado (lo que ha hecho no se pierde). Con el mismo
    estudiante, solo cambia la hora.
    """
    if fecha.isoweekday() not in DIAS_LECTIVOS:
        raise ErrorDeCentro("No se ha guardado: el comedor solo se asigna de lunes a viernes.")
    if fecha < hoy():
        raise ErrorDeCentro("No se ha guardado: ese día ya ha pasado.")
    _comprobar_horas(hora_inicio, hora_fin)

    try:
        with transaction.atomic():
            _bloquear(estudiante)
            anterior = (
                ComedorDelDia.objects.select_for_update()
                .select_related("asignacion__estudiante__usuario")
                .filter(fecha=fecha)
                .first()
            )
            vieja = anterior.asignacion if anterior else None
            _comprobar_que_no_choca(
                estudiante, [fecha.isoweekday()], fecha, fecha, hora_inicio, hora_fin, vieja
            )
            sustituido = None
            if vieja and vieja.estudiante_id == estudiante.pk:
                vieja.hora_inicio, vieja.hora_fin = hora_inicio, hora_fin
                vieja.save(update_fields=["hora_inicio", "hora_fin"])
            else:
                nueva = Asignacion.objects.create(
                    tarea=tarea_de(TipoTareaCentro.COMEDOR, por),
                    estudiante=estudiante,
                    asignado_por=por,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    dias_semana=[fecha.isoweekday()],
                    vigencia_desde=fecha,
                    vigencia_hasta=fecha,
                )
                if anterior:
                    sustituido = vieja.estudiante
                    anterior.asignacion = nueva
                    anterior.save(update_fields=["asignacion"])
                    _retirar(vieja, fecha)
                else:
                    ComedorDelDia.objects.create(fecha=fecha, asignacion=nueva)
    except IntegrityError as error:
        raise ErrorDeCentro(OTRO_A_LA_VEZ) from error

    texto = (
        f"Comedor del {texto_fecha(fecha)}: {_nombre(estudiante)}, "
        f"de {hora_inicio:%H:%M} a {hora_fin:%H:%M}."
    )
    if sustituido:
        texto += f" Sustituye a {_nombre(sustituido)}."
    return Resultado(texto, sustituido)


def quitar_comedor(fecha):
    """Deja el día pendiente de asignar. Devuelve el estudiante que tenía (o None). Si ya
    había empezado la tarea, la conserva en su agenda."""
    if fecha < hoy():
        raise ErrorDeCentro("Ese día ya ha pasado: no se puede cambiar.")
    with transaction.atomic():
        comedor = (
            ComedorDelDia.objects.select_for_update()
            .select_related("asignacion__estudiante__usuario")
            .filter(fecha=fecha)
            .first()
        )
        if comedor is None:
            return None
        vieja = comedor.asignacion
        comedor.delete()
        _retirar(vieja, fecha)
    return vieja.estudiante


# --- Reparto del menú de un mes (PA2, PA3, PA4) ------------------------------------------


def _desde_y_hasta(mes):
    """Del mes, los días en los que aún se puede repartir: de hoy (o del día 1) al último."""
    inicio, fin = primer_dia(mes), ultimo_dia(mes)
    if fin < hoy():
        raise ErrorDeCentro("No se ha guardado: ese mes ya ha pasado.")
    return max(inicio, hoy()), fin


def asignar_reparto(mes, estudiante, hora_inicio, hora_fin, dias, por):
    """PA2: pone la tarea «Reparto del menú» en la agenda del estudiante los días de la
    semana elegidos de ese mes (de hoy en adelante si el mes ya ha empezado).

    PA4: si el mes ya tenía otro estudiante, lo sustituye desde hoy. Lo que el anterior ya
    ha hecho se conserva: su tarea termina ayer (o hoy, si hoy ya la ha empezado) en lugar
    de borrarse. Con el mismo estudiante, solo cambian la hora y los días.
    """
    mes = primer_dia(mes)
    _comprobar_horas(hora_inicio, hora_fin)
    dias = sorted({int(d) for d in dias or []})
    if not dias or not set(dias) <= set(DIAS_LECTIVOS):
        raise ErrorDeCentro("No se ha guardado: elige al menos un día, de lunes a viernes.")
    desde, hasta = _desde_y_hasta(mes)
    if not any(d.isoweekday() in dias for d in dias_lectivos(mes) if d >= desde):
        raise ErrorDeCentro("No se ha guardado: en lo que queda de mes no hay esos días.")

    try:
        with transaction.atomic():
            _bloquear(estudiante)
            reparto, _ = RepartoMenu.objects.select_for_update().get_or_create(mes=mes)
            vieja = reparto.asignacion
            _comprobar_que_no_choca(estudiante, dias, desde, hasta, hora_inicio, hora_fin, vieja)
            sustituido = None
            if vieja and vieja.estudiante_id == estudiante.pk:
                vieja.hora_inicio, vieja.hora_fin, vieja.dias_semana = hora_inicio, hora_fin, dias
                vieja.save(update_fields=["hora_inicio", "hora_fin", "dias_semana"])
            else:
                sustituido = vieja.estudiante if vieja else None
                reparto.asignacion = Asignacion.objects.create(
                    tarea=tarea_de(TipoTareaCentro.REPARTO_MENU, por),
                    estudiante=estudiante,
                    asignado_por=por,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    dias_semana=dias,
                    vigencia_desde=desde,
                    vigencia_hasta=hasta,
                )
                reparto.save(update_fields=["asignacion"])
                if vieja:
                    _retirar(vieja, desde)
    except IntegrityError as error:
        raise ErrorDeCentro(OTRO_A_LA_VEZ) from error

    texto = (
        f"Reparto del menú de {nombre_mes(mes)}: {_nombre(estudiante)}, {texto_dias(dias)} "
        f"de {hora_inicio:%H:%M} a {hora_fin:%H:%M}."
    )
    if sustituido:
        texto += f" Sustituye a {_nombre(sustituido)}."
    return Resultado(texto, sustituido)


def quitar_reparto(mes):
    """Deja el mes pendiente de asignar desde hoy. Devuelve el estudiante que tenía."""
    mes = primer_dia(mes)
    desde, _ = _desde_y_hasta(mes)
    with transaction.atomic():
        reparto = (
            RepartoMenu.objects.select_for_update()
            .select_related("asignacion__estudiante__usuario")
            .filter(mes=mes)
            .first()
        )
        if reparto is None or reparto.asignacion is None:
            return None
        vieja = reparto.asignacion
        reparto.asignacion = None
        reparto.save(update_fields=["asignacion"])
        _retirar(vieja, desde)
    return vieja.estudiante


# --- Menú del mes (para HU-06-03) -------------------------------------------------------


def _mes_que_se_puede_cambiar(mes):
    mes = primer_dia(mes)
    if ultimo_dia(mes) < hoy():
        raise ErrorDeCentro("No se ha guardado: ese mes ya ha pasado.")
    return mes


def subir_menu(mes, archivo):
    """Guarda (o cambia) el menú del mes. El anterior se borra del disco.

    Solo se guarda la columna del menú: si otro administrador asigna el reparto a la vez,
    no se pisa su estudiante."""
    mes = _mes_que_se_puede_cambiar(mes)
    try:
        with transaction.atomic():
            reparto, _ = RepartoMenu.objects.select_for_update().get_or_create(mes=mes)
            anterior = reparto.menu.name
            reparto.menu.save(f"menu-{mes:%Y-%m}{_extension(archivo.name)}", archivo, save=False)
            reparto.save(update_fields=["menu"])
            nuevo = reparto.menu.name
            if anterior and anterior != nuevo:
                almacen = reparto.menu.storage
                transaction.on_commit(lambda: almacen.delete(anterior))
    except IntegrityError as error:
        raise ErrorDeCentro(OTRO_A_LA_VEZ) from error
    return reparto


def quitar_menu(mes):
    mes = _mes_que_se_puede_cambiar(mes)
    with transaction.atomic():
        reparto = RepartoMenu.objects.select_for_update().filter(mes=mes).first()
        if reparto is None or not reparto.menu:
            return
        anterior = reparto.menu.name
        almacen = reparto.menu.storage
        reparto.menu = ""
        reparto.save(update_fields=["menu"])
        transaction.on_commit(lambda: almacen.delete(anterior))


def _extension(nombre):
    punto = nombre.rfind(".")
    return nombre[punto:].lower() if punto >= 0 else ""


def menu_del_mes(fecha):
    """El menú del mes de esa fecha (un FieldFile con .url y .name), o None si no se ha
    subido. Para HU-06-03 (Manu): el familiar ve el menú en el día del estudiante."""
    reparto = RepartoMenu.objects.filter(mes=primer_dia(fecha)).exclude(menu="").first()
    return reparto.menu if reparto else None


def menu_es_imagen(menu):
    return _extension(menu.name) in (".png", ".jpg", ".jpeg", ".webp")


# --- Lo que ve el administrador (PA5) ---------------------------------------------------


@dataclass
class DiaDeComedor:
    fecha: date
    comedor: ComedorDelDia | None
    pasado: bool
    inicio: bool = False  # la lista empieza en esta página: hoy o el primer día que queda

    @property
    def texto(self):
        return texto_fecha(self.fecha)

    @property
    def texto_corto(self):
        """«miércoles 18» (el mes ya está en el título)."""
        return f"{DIAS[self.fecha.weekday()]} {self.fecha.day}"

    @property
    def es_hoy(self):
        return self.fecha == hoy()

    @property
    def pendiente(self):
        return self.comedor is None


def comedor_del_mes(mes):
    """PA5: cada día lectivo del mes con su encargado del comedor o pendiente de asignar."""
    dias = dias_lectivos(mes)
    asignados = {
        c.fecha: c
        for c in ComedorDelDia.objects.filter(fecha__range=(dias[0], dias[-1])).select_related(
            "asignacion__estudiante__usuario", "asignacion__estudiante__clase"
        )
    }
    hoy_ = hoy()
    lista = [DiaDeComedor(d, asignados.get(d), d < hoy_) for d in dias]
    primero = next((d for d in lista if not d.pasado), None)
    if primero:
        primero.inicio = True
    return lista


def reparto_del_mes(mes):
    """El RepartoMenu del mes (con o sin estudiante) o None si no hay nada guardado."""
    return (
        RepartoMenu.objects.select_related(
            "asignacion__estudiante__usuario", "asignacion__estudiante__clase"
        )
        .filter(mes=primer_dia(mes))
        .first()
    )
