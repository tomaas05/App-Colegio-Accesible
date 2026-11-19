"""HU-05-01. Crear una tarea de reprografía (AGENDA-260).

Una o más pruebas por cada prueba de aceptación de Jira, más los permisos:

1. Creo la tarea con copias, tipo de trabajo, color y aula, y aparece en la agenda.
2. Si falta un dato obligatorio, no se guarda y se indica cuál.
3. La tarea trae las fases recoger, imprimir o fotocopiar y repartir, y puedo cambiarlas.
4. No puedo cambiar los datos si el estudiante ya la ha empezado.

Datos de prueba: Lucía (A01, PTVAL 1, tutora Ana) tiene cada día «Preparar la mochila» de
9:00 a 9:15, «Lavarse las manos» de 10:30 a 10:45, «Regar las plantas» de 12:00 a 12:30 y
«Leer un cuento» de 17:00 a 17:30. Daniela (B01) es de PTVAL 2 (tutor Pedro) y tiene
«Lavarse las manos» de 11:00 a 11:15: con ella se usa otra hora (DANIELA).

Hoy es siempre el próximo miércoles a las 10:00, para no depender del día en que se pasan.
"""

import re
from datetime import date, datetime, time, timedelta

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios as agenda
from apps.agenda.models import Ejecucion, EstadoEjecucion
from apps.centro import reprografia, servicios
from apps.centro.models import TareaDelCentro, TipoTareaCentro, TrabajoReprografia
from apps.tareas.models import Asignacion, ExcepcionAsignacion, TipoExcepcion
from apps.usuarios.models import Estudiante, Usuario

pytestmark = pytest.mark.django_db

TAREAS = reverse("centro:tareas")
LISTA = reverse("centro:reprografia")
NUEVA = reverse("centro:reprografia_nueva")
FASES = reverse("centro:reprografia_fases")


def proximo_miercoles():
    hoy = timezone.localdate()
    return hoy + timedelta(days=(2 - hoy.weekday()) % 7)


MIERCOLES = proximo_miercoles()
JUEVES = MIERCOLES + timedelta(days=1)
SABADO = MIERCOLES + timedelta(days=3)


def a_las(dia, hora, minuto=0):
    return timezone.make_aware(datetime.combine(dia, time(hora, minuto)))


@pytest.fixture(autouse=True)
def hoy_es_miercoles(monkeypatch):
    monkeypatch.setattr(servicios, "hoy", lambda: MIERCOLES)
    monkeypatch.setattr(agenda, "ahora", lambda: a_las(MIERCOLES, 10))


def est(codigo):
    return Estudiante.objects.select_related("usuario").get(codigo_estudiante=codigo)


@pytest.fixture
def lucia(datos):
    return est("A01")


@pytest.fixture
def daniela(datos):
    return est("B01")


def entrar(client, username):
    usuario = Usuario.objects.get(username=username)
    client.force_login(usuario)
    return usuario


@pytest.fixture
def tutor(client, datos):
    return entrar(client, "tutor")


@pytest.fixture
def admin(client, datos):
    return entrar(client, "admin")


def datos_form(quien, **cambios):
    datos = {
        "reprografia-estudiante": quien.pk,
        "reprografia-dia": JUEVES.isoformat(),
        "reprografia-hora_inicio": "11:00",
        "reprografia-hora_fin": "11:30",
        "reprografia-copias": "20",
        "reprografia-trabajos": ["fotocopiar"],
        "reprografia-color": "bn",
        "reprografia-aula": "Aula 3",
        "accion": "guardar",
    }
    datos.update({f"reprografia-{k}": v for k, v in cambios.items()})
    return {k: v for k, v in datos.items() if v is not None}


DANIELA = {"hora_inicio": "13:00", "hora_fin": "13:30"}


def crear(client, estudiante, **cambios):
    return client.post(NUEVA, datos_form(estudiante, **cambios))


def nombres_en_agenda(estudiante, dia):
    return [t.tarea.nombre for t in agenda.agenda_del_dia(estudiante, a_las(dia, 8)).tareas]


def html(respuesta):
    return respuesta.content.decode()


# --- 1. Creo la tarea con sus datos y aparece en la agenda del estudiante --------------


def test_pa1_el_tutor_crea_la_tarea_y_sale_en_la_agenda(client, tutor, lucia):
    respuesta = crear(client, lucia)
    assert respuesta.status_code == 302 and respuesta.url == LISTA

    trabajo = TrabajoReprografia.objects.select_related("asignacion__tarea").get()
    assert (trabajo.copias, trabajo.fotocopiar, trabajo.imprimir, trabajo.plastificar) == (
        20,
        True,
        False,
        False,
    )
    assert trabajo.color is False  # blanco y negro
    assert trabajo.aula == "Aula 3"
    a = trabajo.asignacion
    assert a.tarea.nombre == "Reprografía"
    assert a.estudiante == lucia and a.asignado_por == tutor
    assert (a.vigencia_desde, a.vigencia_hasta, a.dias_semana) == (JUEVES, JUEVES, [4])
    assert (a.hora_inicio, a.hora_fin) == (time(11), time(11, 30))

    assert "Reprografía" in nombres_en_agenda(lucia, JUEVES)
    assert "Reprografía" not in nombres_en_agenda(lucia, MIERCOLES)  # solo ese día
    assert "Reprografía" not in nombres_en_agenda(lucia, JUEVES + timedelta(days=7))


def test_pa1_sale_en_la_lista_con_sus_datos_y_el_mensaje(client, tutor, lucia):
    crear(client, lucia, trabajos=["imprimir", "plastificar"], color="color", copias="1")
    pagina = html(client.get(LISTA))
    assert "Reprografía creada en la agenda de Lucía" in pagina
    assert "1 copia · Imprimir y plastificar · en color · Aula 3" in pagina
    assert "Sin empezar" in pagina
    assert reverse("centro:reprografia_cambiar", args=[TrabajoReprografia.objects.get().pk]) in (
        pagina
    )


def test_pa1_el_administrador_tambien_la_crea_y_para_cualquier_clase(client, admin, daniela):
    assert crear(client, daniela, **DANIELA).status_code == 302
    assert TrabajoReprografia.objects.get().asignacion.asignado_por == admin
    assert "Daniela" in html(client.get(LISTA))


def test_pa1_blanco_y_negro_por_defecto(client, tutor, lucia):
    pagina = html(client.get(NUEVA))
    assert re.search(
        r'<input type="radio" name="reprografia-color" value="bn"[^>]* checked', pagina
    )
    crear(client, lucia, color=None)  # sin elegir: blanco y negro
    assert TrabajoReprografia.objects.get().color is False


def test_pa1_si_solo_se_plastifica_el_color_no_aplica(client, tutor, lucia):
    crear(client, lucia, trabajos=["plastificar"], color="color")
    trabajo = TrabajoReprografia.objects.get()
    assert trabajo.color is None and trabajo.texto_color == ""


def test_pa1_la_tarea_del_catalogo_se_crea_una_sola_vez(client, tutor, lucia):
    crear(client, lucia)
    crear(client, lucia, dia=(JUEVES + timedelta(days=1)).isoformat())
    assert TrabajoReprografia.objects.count() == 2
    assert TareaDelCentro.objects.filter(tipo=TipoTareaCentro.REPROGRAFIA).count() == 1


def test_pa1_no_se_guarda_si_choca_con_otra_tarea(client, tutor, lucia):
    respuesta = crear(client, lucia, hora_inicio="12:15", hora_fin="12:45")
    assert respuesta.status_code == 400
    assert "Lucía ya tiene «Regar las plantas» (de 12:00 a 12:30" in html(respuesta)
    assert not TrabajoReprografia.objects.exists()


def test_pa1_dos_trabajos_a_la_misma_hora_chocan(client, tutor, lucia):
    crear(client, lucia)
    respuesta = crear(client, lucia, hora_inicio="11:15", hora_fin="11:45")
    assert respuesta.status_code == 400 and "«Reprografía»" in html(respuesta)
    assert TrabajoReprografia.objects.count() == 1


def test_pa1_solo_de_lunes_a_viernes_y_no_en_el_pasado(client, tutor, lucia):
    respuesta = crear(client, lucia, dia=SABADO.isoformat())
    assert respuesta.status_code == 400 and "Elige un día de lunes a viernes." in html(respuesta)
    ayer = MIERCOLES - timedelta(days=1)
    respuesta = crear(client, lucia, dia=ayer.isoformat())
    assert respuesta.status_code == 400 and "Ese día ya ha pasado." in html(respuesta)
    assert not TrabajoReprografia.objects.exists()


def test_pa1_hoy_si_se_puede(client, tutor, lucia):
    assert crear(client, lucia, dia=MIERCOLES.isoformat()).status_code == 302
    assert "(hoy)" in html(client.get(LISTA))


# --- 2. Si falta un dato obligatorio, no se guarda y se indica cuál ----------------------


@pytest.mark.parametrize(
    "campo, mensaje",
    [
        ("estudiante", "Elige un estudiante."),
        ("dia", "Elige el día."),
        ("hora_inicio", "Pon la hora de inicio."),
        ("hora_fin", "Pon la hora de fin."),
        ("copias", "Pon el número de copias."),
        ("trabajos", "Elige el tipo de trabajo: imprimir, fotocopiar o plastificar."),
        ("aula", "Escribe el aula."),
    ],
)
def test_pa2_sin_un_dato_no_se_guarda_y_dice_cual(client, tutor, lucia, campo, mensaje):
    respuesta = client.post(NUEVA, datos_form(lucia, **{campo: None}))
    assert respuesta.status_code == 400
    pagina = html(respuesta)
    assert mensaje in pagina
    assert "Revisa este dato" in pagina  # el resumen enlaza al campo
    assert not TrabajoReprografia.objects.exists()


@pytest.mark.parametrize(
    "copias, mensaje",
    [
        ("0", "Tiene que ser al menos 1 copia."),
        ("100", "Como mucho, 99 copias."),
        ("muchas", "Escribe un número."),
    ],
)
def test_pa2_copias_de_1_a_99(client, tutor, lucia, copias, mensaje):
    respuesta = crear(client, lucia, copias=copias)
    assert respuesta.status_code == 400 and mensaje in html(respuesta)
    assert not TrabajoReprografia.objects.exists()


def test_pa2_aula_de_50_letras_como_mucho(client, tutor, lucia):
    respuesta = crear(client, lucia, aula="A" * 51)
    assert respuesta.status_code == 400 and "Como mucho, 50 letras." in html(respuesta)
    assert crear(client, lucia, aula="A" * 50).status_code == 302


def test_pa2_aula_solo_con_espacios_no_vale(client, tutor, lucia):
    respuesta = crear(client, lucia, aula="   ")
    assert respuesta.status_code == 400 and "Escribe el aula." in html(respuesta)


def test_pa2_la_hora_de_fin_despues_de_la_de_inicio(client, tutor, lucia):
    respuesta = crear(client, lucia, hora_inicio="11:30", hora_fin="11:00")
    assert respuesta.status_code == 400
    assert "La hora de fin tiene que ser después de la de inicio." in html(respuesta)


def test_pa2_la_base_de_datos_tambien_lo_impide(lucia, datos):
    tutor = Usuario.objects.get(username="tutor")
    trabajo = reprografia.crear(
        reprografia.Datos(lucia, JUEVES, time(11), time(11, 30), 5, ["imprimir"], False, "A3"),
        tutor,
    )
    for cambios in (
        {"copias": 0},
        {"copias": 100},
        {"imprimir": False},  # ningún trabajo
        {"color": None},  # imprime: tiene que decir el color
        {"aula": ""},
    ):
        with pytest.raises(IntegrityError), transaction.atomic():
            TrabajoReprografia.objects.filter(pk=trabajo.pk).update(**cambios)


# --- 3. La tarea trae las fases y se pueden cambiar --------------------------------------


def test_pa3_la_tarea_trae_las_tres_fases_en_orden(client, tutor, lucia):
    crear(client, lucia)
    tarea = TrabajoReprografia.objects.get().asignacion.tarea
    assert [p.descripcion for p in tarea.pasos.order_by("orden")] == [
        "Recoger el material en el aula",
        "Imprimir, fotocopiar o plastificar en el taller",
        "Repartir el original y las copias en el aula",
    ]
    assert all(p.imagen and p.descripcion_imagen for p in tarea.pasos.all())


def test_pa3_el_estudiante_ve_las_fases_en_su_tarea(client, tutor, lucia):
    crear(client, lucia, dia=MIERCOLES.isoformat())
    asignacion = TrabajoReprografia.objects.get().asignacion
    t = agenda.tarea_del_dia(lucia, asignacion.pk, a_las(MIERCOLES, 11))
    agenda.empezar(lucia, asignacion.pk, a_las(MIERCOLES, 11))
    t = agenda.tarea_del_dia(lucia, asignacion.pk, a_las(MIERCOLES, 11, 5))
    assert [p.paso.descripcion for p in t.pasos][0] == "Recoger el material en el aula"


def test_pa3_el_tutor_ve_las_fases_y_el_enlace_para_cambiarlas(client, tutor):
    pagina = html(client.get(FASES))
    assert "Recoger el material en el aula" in pagina
    assert "Repartir el original y las copias en el aula" in pagina
    tarea = TareaDelCentro.objects.get(tipo=TipoTareaCentro.REPROGRAFIA).tarea
    enlace = reverse("tareas:editar_pasos_tarea", args=[tarea.pk])
    assert enlace in pagina
    # Y el tutor puede cambiarlas en «Pasos de la tarea» (HU-03-02).
    assert client.get(enlace).status_code == 200


def test_pa3_lo_que_cambia_el_tutor_vale_para_los_trabajos(client, tutor, lucia):
    crear(client, lucia)
    tarea = TrabajoReprografia.objects.get().asignacion.tarea
    tarea.pasos.filter(orden=3).update(descripcion="Llevarlo a la clase de la profe")
    assert "Llevarlo a la clase de la profe" in html(client.get(FASES))


def test_pa3_el_administrador_ve_las_fases_sin_enlace(client, admin):
    pagina = html(client.get(FASES))
    assert "Recoger el material en el aula" in pagina
    assert "Las fases las cambia el tutor" in pagina
    assert "Cambiar las fases" not in pagina


# --- 4. No se pueden cambiar los datos si ya la ha empezado ------------------------------


def _creada(client, estudiante, **cambios):
    crear(client, estudiante, **cambios)
    return TrabajoReprografia.objects.select_related("asignacion").latest("pk")


def url_cambiar(trabajo):
    return reverse("centro:reprografia_cambiar", args=[trabajo.pk])


def test_pa4_si_no_la_ha_empezado_se_puede_cambiar(client, tutor, lucia):
    trabajo = _creada(client, lucia)
    pagina = html(client.get(url_cambiar(trabajo)))
    assert 'value="20"' in pagina and 'value="Aula 3"' in pagina
    respuesta = client.post(
        url_cambiar(trabajo),
        datos_form(lucia, copias="30", aula="Aula 5", trabajos=["imprimir"], color="color"),
    )
    assert respuesta.status_code == 302
    trabajo.refresh_from_db()
    assert (trabajo.copias, trabajo.aula, trabajo.imprimir, trabajo.color) == (
        30,
        "Aula 5",
        True,
        True,
    )
    assert "Reprografía cambiada" in html(client.get(LISTA))


def test_pa4_cambiar_de_dia_y_de_estudiante(client, tutor, lucia):
    trabajo = _creada(client, lucia)
    mateo = est("A02")
    viernes = JUEVES + timedelta(days=1)
    client.post(url_cambiar(trabajo), datos_form(mateo, dia=viernes.isoformat()))
    a = Asignacion.objects.get(pk=trabajo.asignacion_id)
    assert (a.estudiante, a.vigencia_desde, a.vigencia_hasta, a.dias_semana) == (
        mateo,
        viernes,
        viernes,
        [5],
    )
    assert "Reprografía" not in nombres_en_agenda(lucia, JUEVES)
    assert "Reprografía" in nombres_en_agenda(mateo, viernes)


def test_pa4_al_cambiar_no_choca_consigo_misma(client, tutor, lucia):
    trabajo = _creada(client, lucia)
    respuesta = client.post(
        url_cambiar(trabajo), datos_form(lucia, hora_inicio="11:15", hora_fin="11:45")
    )
    assert respuesta.status_code == 302


def test_pa4_si_ya_la_ha_empezado_no_se_puede_cambiar(client, tutor, lucia):
    trabajo = _creada(client, lucia, dia=MIERCOLES.isoformat())
    agenda.empezar(lucia, trabajo.asignacion_id, a_las(MIERCOLES, 11))

    pagina = html(client.get(LISTA))
    assert "Empezada" in pagina and ">Ver<" in pagina
    respuesta = client.get(url_cambiar(trabajo))
    pagina = html(respuesta)
    assert respuesta.status_code == 200
    assert "Lucía ya ha empezado esta tarea: sus datos no se pueden cambiar." in pagina
    assert "<form" not in pagina.split("<main", 1)[1]  # solo se ven los datos

    respuesta = client.post(url_cambiar(trabajo), datos_form(lucia, copias="99"))
    assert respuesta.status_code == 302
    trabajo.refresh_from_db()
    assert trabajo.copias == 20
    assert "ya ha empezado esta tarea" in html(client.get(respuesta.url))


def test_pa4_tampoco_si_esta_hecha_o_no_se_ha_podido_hacer(client, tutor, lucia):
    trabajo = _creada(client, lucia, dia=MIERCOLES.isoformat())
    ejecucion = Ejecucion.objects.create(
        asignacion=trabajo.asignacion, fecha=MIERCOLES, estado=EstadoEjecucion.HECHA
    )
    with pytest.raises(servicios.ErrorDeCentro):
        reprografia.cambiar(
            trabajo,
            reprografia.Datos(lucia, MIERCOLES, time(11), time(11, 30), 1, ["imprimir"], 0, "B"),
            tutor,
        )
    ejecucion.estado = EstadoEjecucion.NO_REALIZABLE
    ejecucion.save()
    assert reprografia.empezada(trabajo)
    assert "Sin hacer" in html(client.get(LISTA))


def test_pa4_una_ejecucion_sin_tocar_no_cuenta_como_empezada(client, tutor, lucia):
    """Si la agenda tiene la ejecución del día creada pero sin nada (pendiente, sin hora de
    inicio, sin «No puedo» ni plan B), aún se puede cambiar, y esa ejecución sobra."""
    trabajo = _creada(client, lucia, dia=MIERCOLES.isoformat())
    Ejecucion.objects.create(asignacion=trabajo.asignacion, fecha=MIERCOLES)
    respuesta = client.post(
        url_cambiar(trabajo), datos_form(lucia, dia=JUEVES.isoformat(), copias="7")
    )
    assert respuesta.status_code == 302
    assert not Ejecucion.objects.filter(asignacion=trabajo.asignacion).exists()


def test_pa4_con_plan_b_ya_no_se_cambia_ni_se_borra_lo_hecho(client, tutor, lucia):
    trabajo = _creada(client, lucia, dia=MIERCOLES.isoformat())
    otra = Asignacion.objects.exclude(pk=trabajo.asignacion_id).first().tarea
    ejecucion = Ejecucion.objects.create(
        asignacion=trabajo.asignacion,
        fecha=MIERCOLES,
        no_realizable_el=a_las(MIERCOLES, 10),
        no_realizable_por=lucia.usuario,
        plan_b=otra,
    )
    assert "Sin hacer" in html(client.get(LISTA))
    client.post(url_cambiar(trabajo), datos_form(lucia, copias="7"))
    client.post(url_cambiar(trabajo), {"accion": "quitar"})
    trabajo.refresh_from_db()
    assert trabajo.copias == 20
    ejecucion.refresh_from_db()
    assert ejecucion.plan_b == otra


def test_pa4_si_ya_paso_su_hora_no_se_cambia(client, tutor, lucia, monkeypatch):
    trabajo = _creada(client, lucia, dia=MIERCOLES.isoformat())  # de 11:00 a 11:30
    monkeypatch.setattr(agenda, "ahora", lambda: a_las(MIERCOLES, 12))
    assert "Sin hacer" in html(client.get(LISTA))
    pagina = html(client.get(url_cambiar(trabajo)))
    assert "Esta tarea ya no está pendiente" in pagina
    client.post(url_cambiar(trabajo), {"accion": "quitar"})
    assert TrabajoReprografia.objects.filter(pk=trabajo.pk).exists()


def test_pa4_un_dia_pasado_solo_se_ve(client, tutor, lucia):
    trabajo = _creada(client, lucia)
    Asignacion.objects.filter(pk=trabajo.asignacion_id).update(
        vigencia_desde=date(2020, 1, 1), vigencia_hasta=date(2020, 1, 1), dias_semana=[3]
    )
    assert "Esta tarea ya no está pendiente" in html(client.get(url_cambiar(trabajo)))
    client.post(url_cambiar(trabajo), {"accion": "quitar"})
    client.post(url_cambiar(trabajo), datos_form(lucia, copias="7"))
    trabajo.refresh_from_db()
    assert trabajo.copias == 20


def test_pa1_hoy_con_la_hora_ya_pasada_no_se_crea(client, tutor, lucia):
    respuesta = crear(client, lucia, dia=MIERCOLES.isoformat(), hora_inicio="9:30", hora_fin="9:45")
    assert respuesta.status_code == 400 and "hoy esa hora ya ha pasado" in html(respuesta)


def test_empezada_y_luego_cancelada_cuenta_como_empezada(client, tutor, lucia):
    trabajo = _creada(client, lucia, dia=MIERCOLES.isoformat())
    agenda.empezar(lucia, trabajo.asignacion_id, a_las(MIERCOLES, 11))
    ExcepcionAsignacion.objects.create(
        asignacion=trabajo.asignacion,
        fecha=MIERCOLES,
        tipo=TipoExcepcion.CANCELADA,
        creada_por=tutor,
    )
    assert "Empezada" in html(client.get(LISTA))
    with pytest.raises(servicios.ErrorDeCentro):
        reprografia.quitar(trabajo)


def test_pa4_quitar_si_no_la_ha_empezado(client, tutor, lucia):
    trabajo = _creada(client, lucia)
    respuesta = client.post(url_cambiar(trabajo), {"accion": "quitar"})
    assert respuesta.status_code == 302
    assert not TrabajoReprografia.objects.exists()
    assert not Asignacion.objects.filter(pk=trabajo.asignacion_id).exists()
    assert "Quitada la reprografía de la agenda de Lucía" in html(client.get(LISTA))


def test_pa4_no_se_quita_si_ya_la_ha_empezado(client, tutor, lucia):
    trabajo = _creada(client, lucia, dia=MIERCOLES.isoformat())
    agenda.empezar(lucia, trabajo.asignacion_id, a_las(MIERCOLES, 11))
    client.post(url_cambiar(trabajo), {"accion": "quitar"})
    assert TrabajoReprografia.objects.filter(pk=trabajo.pk).exists()


def test_cancelada_en_tareas_planificadas_se_ve_pero_no_se_cambia(client, tutor, lucia):
    trabajo = _creada(client, lucia)
    ExcepcionAsignacion.objects.create(
        asignacion=trabajo.asignacion,
        fecha=JUEVES,
        tipo=TipoExcepcion.CANCELADA,
        creada_por=tutor,
    )
    assert "Cancelada" in html(client.get(LISTA))
    assert "Esta tarea está cancelada" in html(client.get(url_cambiar(trabajo)))


def test_horas_cambiadas_solo_ese_dia_se_ven_y_se_respetan(client, tutor, lucia):
    trabajo = _creada(client, lucia)
    ExcepcionAsignacion.objects.create(
        asignacion=trabajo.asignacion,
        fecha=JUEVES,
        tipo=TipoExcepcion.MODIFICADA,
        hora_inicio=time(13),
        hora_fin=time(13, 30),
        creada_por=tutor,
    )
    assert "de 13:00 a 13:30" in html(client.get(LISTA))
    assert 'value="13:00"' in html(client.get(url_cambiar(trabajo)))
    client.post(url_cambiar(trabajo), datos_form(lucia, hora_inicio="13:00", hora_fin="13:30"))
    a = Asignacion.objects.get(pk=trabajo.asignacion_id)
    assert (a.hora_inicio, a.hora_fin) == (time(13), time(13, 30))
    assert not a.excepciones.exists()


# --- Permisos y lista -------------------------------------------------------------------


def test_sin_sesion_a_la_portada(client, datos):
    for url in (TAREAS, LISTA, NUEVA, FASES):
        respuesta = client.get(url)
        assert respuesta.status_code == 302 and "next=" in respuesta.url


@pytest.mark.parametrize("username", ["profesional", "familiar"])
def test_otros_adultos_no_entran(client, datos, username):
    entrar(client, username)
    for url in (TAREAS, LISTA, NUEVA, FASES):
        assert client.get(url).status_code == 403


def test_el_estudiante_no_entra(client, lucia):
    client.force_login(lucia.usuario)
    assert client.get(TAREAS).status_code in (302, 403)
    assert client.get(LISTA).status_code in (302, 403)
    assert client.get(NUEVA).status_code in (302, 403)


def test_el_tutor_solo_elige_alumnos_de_su_clase(client, tutor, lucia, daniela):
    pagina = html(client.get(NUEVA))
    assert "Lucía" in pagina and "Daniela" not in pagina
    respuesta = crear(client, daniela, **DANIELA)
    assert respuesta.status_code == 400 and "Elige uno de la lista." in html(respuesta)


def test_el_tutor_no_ve_ni_cambia_los_trabajos_de_otra_clase(client, datos, daniela):
    entrar(client, "admin")
    crear(client, daniela, **DANIELA)
    client.get(LISTA)  # lee el mensaje de «creada»
    trabajo = TrabajoReprografia.objects.get()
    entrar(client, "tutor")
    assert "Daniela" not in html(client.get(LISTA))
    assert client.get(url_cambiar(trabajo)).status_code == 404
    assert client.post(url_cambiar(trabajo), {"accion": "quitar"}).status_code == 404
    assert TrabajoReprografia.objects.exists()


def test_la_lista_va_por_dia_y_hora_y_no_ensena_lo_pasado(client, tutor, lucia):
    crear(client, lucia, dia=(JUEVES + timedelta(days=1)).isoformat())
    crear(client, lucia, hora_inicio="13:00", hora_fin="13:30", aula="Segunda")
    crear(client, lucia, aula="Primera")
    pasado = _creada(client, lucia, dia=MIERCOLES.isoformat(), aula="Pasada")
    Asignacion.objects.filter(pk=pasado.asignacion_id).update(
        vigencia_desde=date(2020, 1, 1), vigencia_hasta=date(2020, 1, 1)
    )
    filas = reprografia.lista(tutor)
    assert [f.trabajo.aula for f in filas] == ["Primera", "Segunda", "Aula 3"]


def test_la_lista_vacia_lo_dice(client, tutor):
    pagina = html(client.get(LISTA))
    assert "Todavía no hay trabajos de reprografía" in pagina
    assert NUEVA in pagina


def test_la_lista_no_hace_una_consulta_por_trabajo(
    client, tutor, lucia, django_assert_max_num_queries
):
    for dia in range(3):
        crear(client, lucia, dia=(JUEVES + timedelta(days=7 * dia)).isoformat())
    with django_assert_max_num_queries(12):
        client.get(LISTA)


# --- «Tareas del centro»: la opción del menú lateral, con la reprografía dentro ---------


def lateral(pagina):
    return pagina[pagina.index('<aside class="lateral"') : pagina.index("</aside>")]


def test_tareas_del_centro_en_el_panel_del_tutor_y_del_administrador(client, datos):
    """En el panel y en el menú lateral sale «Tareas del centro», no «Reprografía»."""
    for username in ("tutor", "admin"):
        entrar(client, username)
        pagina = html(client.get(reverse("usuarios:panel")))
        assert f'href="{TAREAS}"' in pagina
        assert re.search(rf'href="{TAREAS}"[^>]*>Tareas del centro<', lateral(pagina))
        assert LISTA not in pagina and "Reprografía" not in lateral(pagina)
    for username in ("profesional", "familiar"):
        entrar(client, username)
        assert TAREAS not in html(client.get(reverse("usuarios:panel")))


@pytest.mark.parametrize("username", ["tutor", "admin"])
def test_dentro_de_tareas_del_centro_esta_la_reprografia(client, datos, username):
    entrar(client, username)
    respuesta = client.get(TAREAS)
    assert respuesta.status_code == 200
    pagina = html(respuesta)
    assert "<h1" in pagina and "Tareas del centro</h1>" in pagina
    assert re.search(rf'<a class="panel__opcion" href="{LISTA}">', pagina)
    assert "<b>Reprografía</b>" in pagina
    # En el lateral, «Tareas del centro» es la página actual.
    assert re.search(rf'href="{TAREAS}" aria-current="page">Tareas del centro<', lateral(pagina))


def test_en_reprografia_se_marca_tareas_del_centro_y_se_vuelve_alli(client, tutor):
    """Dentro de la reprografía, el lateral marca «Tareas del centro» como sección y el
    botón de volver de la lista lleva a «Tareas del centro»."""
    for url in (LISTA, NUEVA, FASES):
        menu = lateral(html(client.get(url)))
        assert re.search(rf'lateral__enlace--seccion" href="{TAREAS}">Tareas del centro<', menu)
        assert 'aria-current="page"' not in menu
    assert re.search(
        rf'href="{TAREAS}"[^>]*aria-label="Volver a tareas del centro"', html(client.get(LISTA))
    )


def test_el_comedor_del_administrador_no_se_marca_como_tareas_del_centro(client, admin):
    """/centro/comedor/ cuelga de /centro/, pero su sección es «Comedor y menú»."""
    menu = lateral(html(client.get(reverse("centro:comedor"))))
    assert 'aria-current="page">Comedor y menú<' in menu
    assert not re.search(rf'lateral__enlace--seccion" href="{TAREAS}"', menu)
