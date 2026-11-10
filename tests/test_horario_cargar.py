"""HU-03-11. Cargar el horario escolar de una clase (AGENDA-222).

Una o más pruebas por cada prueba de aceptación de Jira y algunas de permisos.
Datos de prueba: 5 franjas (9:00 a 14:30), 7 asignaturas y talleres, y el horario
completo de PTVAL 1 y PTVAL 2 de lunes a viernes.
"""

from datetime import date, time

import pytest
from django.urls import reverse

from apps.horario import servicios
from apps.horario.models import Asignatura, Franja, HorarioClase
from apps.tareas.models import Tarea
from apps.usuarios.models import Clase, Estudiante, Usuario

pytestmark = pytest.mark.django_db

URL = reverse("horario:cargar")


@pytest.fixture
def admin(client, datos):
    usuario = Usuario.objects.get(username="admin")
    client.force_login(usuario)
    return usuario


@pytest.fixture
def ptval1(datos):
    return Clase.objects.get(nombre="PTVAL 1")


def primera_franja():
    return Franja.objects.order_by("orden").first()


def casilla(clase, dia, franja):
    return HorarioClase.objects.filter(clase=clase, dia_semana=dia, franja=franja).first()


def poner(client, clase, dia, franja, asignatura):
    return client.post(
        URL,
        {"clase": clase.pk, "dia": dia, "franja": franja.pk, "asignatura": asignatura.pk},
    )


def quitar(client, clase, dia, franja):
    return client.post(URL, {"clase": clase.pk, "dia": dia, "franja": franja.pk, "quitar": "1"})


# --- PA1: elijo una clase y, para cada día y franja, una asignatura; sus estudiantes lo ven ---


def test_pa1_elijo_la_clase_y_veo_su_horario(client, admin, ptval1):
    respuesta = client.get(URL, {"clase": ptval1.pk})
    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    assert "Horario de PTVAL 1" in html
    for dia in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]:
        assert f'<th scope="col">{dia}</th>' in html
    assert html.count("Quitar</button>") == 25  # 5 franjas × 5 días, todo ocupado


def test_pa1_pongo_una_asignatura_en_una_casilla_libre(client, admin, ptval1):
    franja = primera_franja()
    huerto = Asignatura.objects.get(nombre="Huerto")
    quitar(client, ptval1, 1, franja)
    assert casilla(ptval1, 1, franja) is None

    respuesta = poner(client, ptval1, 1, franja, huerto)
    assert respuesta.status_code == 302
    assert respuesta["Location"] == f"{URL}?clase={ptval1.pk}"
    assert casilla(ptval1, 1, franja).asignatura == huerto
    html = client.get(respuesta["Location"]).content.decode()
    assert "Guardado: Huerto el lunes de 09:00 a 10:00." in html


def test_pa1_quito_una_asignatura_y_la_casilla_queda_libre(client, admin, ptval1):
    franja = primera_franja()
    respuesta = quitar(client, ptval1, 2, franja)
    assert respuesta.status_code == 302
    assert casilla(ptval1, 2, franja) is None
    assert "Libre" in client.get(respuesta["Location"]).content.decode()


def test_pa1_sus_estudiantes_ven_el_horario_de_su_clase(client, ptval1):
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    client.force_login(lucia.usuario)
    respuesta = client.get(reverse("horario:mi_horario"), {"dia": 1})
    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    for c in HorarioClase.objects.filter(clase=ptval1, dia_semana=1):
        assert c.asignatura.nombre in html
    assert "09:00 – 10:00" in html


def test_pa1_lo_que_pone_el_administrador_lo_ve_el_estudiante(client, admin, ptval1):
    franja = primera_franja()
    huerto = Asignatura.objects.get(nombre="Huerto")
    quitar(client, ptval1, 3, franja)
    poner(client, ptval1, 3, franja, huerto)
    client.force_login(Estudiante.objects.get(codigo_estudiante="A01").usuario)
    html = client.get(reverse("horario:mi_horario"), {"dia": 3}).content.decode()
    assert "Huerto" in html


def test_pa1_cada_estudiante_ve_solo_su_clase(client, datos):
    ptval2 = Clase.objects.get(nombre="PTVAL 2")
    robotica = Asignatura.objects.create(
        nombre="Robótica", imagen="asignaturas/robotica.png", descripcion_imagen="Robot"
    )
    franja = primera_franja()
    servicios.quitar(ptval2, 1, franja)
    servicios.poner(ptval2, 1, franja, robotica)

    client.force_login(Estudiante.objects.get(codigo_estudiante="B01").usuario)
    assert "Robótica" in client.get(reverse("horario:mi_horario"), {"dia": 1}).content.decode()
    client.force_login(Estudiante.objects.get(codigo_estudiante="A01").usuario)
    assert "Robótica" not in client.get(reverse("horario:mi_horario"), {"dia": 1}).content.decode()


def test_pa1_el_estudiante_tiene_un_enlace_a_su_horario_en_la_agenda(client, datos):
    client.force_login(Estudiante.objects.get(codigo_estudiante="A01").usuario)
    assert reverse("horario:mi_horario") in client.get(reverse("agenda:dia")).content.decode()


def test_pa1_un_dia_que_no_es_lectivo_ensena_otro(client, datos):
    client.force_login(Estudiante.objects.get(codigo_estudiante="A01").usuario)
    assert client.get(reverse("horario:mi_horario"), {"dia": 7}).status_code == 200


# --- PA2: las franjas son las mismas para todo el centro y todos los días ---


def test_pa2_todas_las_clases_tienen_las_mismas_franjas(client, admin, datos):
    franjas = [f"{f.hora_inicio:%H:%M} – {f.hora_fin:%H:%M}" for f in Franja.objects.all()]
    for clase in Clase.objects.all():
        html = client.get(URL, {"clase": clase.pk}).content.decode()
        for texto in franjas:
            assert f'<th scope="row">{texto}</th>' in html


def test_pa2_la_rejilla_tiene_una_fila_por_franja_y_una_columna_por_dia(ptval1):
    filas = servicios.rejilla(ptval1)
    assert [f.franja for f in filas] == list(Franja.objects.order_by("orden"))
    assert all(len(f.casillas) == 5 for f in filas)


# --- PA3: si pongo dos asignaturas en la misma franja del mismo día, no se guarda y se indica ---


def test_pa3_no_se_pisa_una_casilla_ocupada_y_se_indica(client, admin, ptval1):
    franja = primera_franja()
    antes = casilla(ptval1, 1, franja).asignatura
    otra = Asignatura.objects.exclude(pk=antes.pk).first()
    respuesta = poner(client, ptval1, 1, franja, otra)
    assert respuesta.status_code == 400
    html = respuesta.content.decode()
    assert 'role="alert"' in html
    assert f"ya tiene «{antes.nombre}»" in html
    assert casilla(ptval1, 1, franja).asignatura == antes


def test_pa3_el_formulario_conserva_lo_elegido_tras_el_error(client, admin, ptval1):
    franja = primera_franja()
    otra = Asignatura.objects.get(nombre="Huerto")
    html = poner(client, ptval1, 1, franja, otra).content.decode()
    assert f'<option value="{otra.pk}" selected>' in html


def test_pa3_el_servicio_lanza_error_si_esta_ocupada(ptval1):
    franja = primera_franja()
    with pytest.raises(servicios.ErrorDeHorario):
        servicios.poner(ptval1, 1, franja, Asignatura.objects.first())


def test_pa3_sin_asignatura_no_se_guarda(client, admin, ptval1):
    franja = primera_franja()
    quitar(client, ptval1, 1, franja)
    respuesta = client.post(URL, {"clase": ptval1.pk, "dia": 1, "franja": franja.pk})
    assert respuesta.status_code == 400
    assert casilla(ptval1, 1, franja) is None


def test_pa3_el_sabado_no_se_puede_poner(client, admin, ptval1):
    respuesta = client.post(
        URL,
        {
            "clase": ptval1.pk,
            "dia": 6,
            "franja": primera_franja().pk,
            "asignatura": Asignatura.objects.first().pk,
        },
    )
    assert respuesta.status_code == 400
    assert not HorarioClase.objects.filter(dia_semana=6).exists()


# --- PA4: cada asignatura o taller se muestra con su imagen y su nombre ---


def test_pa4_cada_casilla_tiene_imagen_y_nombre(client, admin, ptval1):
    html = client.get(URL, {"clase": ptval1.pk}).content.decode()
    for c in HorarioClase.objects.filter(clase=ptval1).select_related("asignatura"):
        assert c.asignatura.imagen.url in html
        assert c.asignatura.nombre in html


def test_pa4_el_estudiante_tambien_ve_imagen_y_nombre(client, ptval1):
    client.force_login(Estudiante.objects.get(codigo_estudiante="A01").usuario)
    html = client.get(reverse("horario:mi_horario"), {"dia": 2}).content.decode()
    for c in HorarioClase.objects.filter(clase=ptval1, dia_semana=2).select_related("asignatura"):
        assert c.asignatura.imagen.url in html
        assert f"<b>{c.asignatura.nombre}</b>" in html


# --- PA5: fuera de las franjas del horario, el familiar puede crear tareas para casa ---


def test_pa5_saber_si_unas_horas_son_de_horario_escolar(datos):
    lunes_a_viernes = [1, 2, 3, 4, 5]
    assert servicios.choca_con_horario_escolar(lunes_a_viernes, time(10, 30), time(10, 45))
    assert not servicios.choca_con_horario_escolar(lunes_a_viernes, time(17, 0), time(17, 30))
    # El recreo (11:00 a 11:30) no es ninguna franja.
    assert not servicios.choca_con_horario_escolar(lunes_a_viernes, time(11, 0), time(11, 30))
    # El fin de semana no hay horario escolar.
    assert not servicios.choca_con_horario_escolar([6, 7], time(10, 0), time(11, 0))


def asignar_como_familiar(client, inicio, fin, dias):
    carmen = Usuario.objects.get(username="familiar")
    client.force_login(carmen)
    mesa = Tarea.objects.get(nombre="Poner la mesa")
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    return client.post(
        reverse("tareas:asignar_tarea"),
        {
            "tarea": mesa.pk,
            "estudiantes": [lucia.pk],
            "hora_inicio": inicio,
            "hora_fin": fin,
            "dias_semana": dias,
            "vigencia_desde": date.today().isoformat(),
        },
    )


def test_pa5_el_familiar_pone_una_tarea_fuera_del_horario_escolar(client, datos):
    respuesta = asignar_como_familiar(client, "18:00", "18:20", ["1", "3"])
    assert respuesta.status_code == 302
    assert (
        Estudiante.objects.get(codigo_estudiante="A01")
        .asignaciones.filter(hora_inicio=time(18, 0))
        .exists()
    )


def test_pa5_el_familiar_no_puede_poner_una_tarea_en_horario_escolar(client, datos):
    respuesta = asignar_como_familiar(client, "09:30", "09:45", ["2"])
    assert respuesta.status_code == 200
    assert "Esas horas son de horario escolar" in respuesta.content.decode()
    assert (
        not Estudiante.objects.get(codigo_estudiante="A01")
        .asignaciones.filter(hora_inicio=time(9, 30))
        .exists()
    )


def test_pa5_el_familiar_si_puede_en_horas_de_clase_el_fin_de_semana(client, datos):
    respuesta = asignar_como_familiar(client, "09:30", "09:45", ["6"])
    assert respuesta.status_code == 302


# --- Permisos ---


@pytest.mark.parametrize("usuario", ["tutor", "profesional", "familiar", "est-a01"])
def test_solo_el_administrador_carga_el_horario(client, datos, usuario):
    client.force_login(Usuario.objects.get(username=usuario))
    assert client.get(URL).status_code == 403
    assert client.post(URL, {}).status_code == 403


def test_sin_sesion_va_a_la_portada(client, datos):
    respuesta = client.get(URL)
    assert respuesta.status_code == 302


def test_un_adulto_no_abre_mi_horario(client, datos):
    client.force_login(Usuario.objects.get(username="tutor"))
    assert client.get(reverse("horario:mi_horario")).status_code == 403


def test_el_panel_del_administrador_enlaza_el_horario(client, admin):
    assert URL in client.get(reverse("usuarios:panel")).content.decode()
