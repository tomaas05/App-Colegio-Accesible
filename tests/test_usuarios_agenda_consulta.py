"""HU-01-09. Consultar la agenda de mis estudiantes (AGENDA-159).

Una prueba por cada prueba de aceptación de Jira y algunas más de permisos.
Datos de prueba: Luis (profesional) atiende a Lucía (A01) y a Hugo (A04). Las tareas
de Lucía las creó y las puso Ana (tutora), y «Poner la mesa», Carmen (familiar).
"""

from datetime import date, time, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.tareas.models import Ambito, Asignacion, Tarea
from apps.usuarios import consulta
from apps.usuarios.models import Estudiante, Usuario

pytestmark = pytest.mark.django_db


def url(codigo, dia=None):
    base = reverse("usuarios:agenda_estudiante", args=[codigo])
    return f"{base}?dia={dia:%Y-%m-%d}" if dia else base


def dia_con_tareas():
    """Hoy o el lunes siguiente: un día con tareas y con horario de clase (lunes a viernes)."""
    dia = timezone.localdate()
    while dia.isoweekday() > 5:
        dia += timedelta(days=1)
    return dia


@pytest.fixture
def luis(client, datos):
    profesional = Usuario.objects.get(username="profesional")
    client.force_login(profesional)
    return profesional


# --- PA1: abro la agenda de un estudiante que atiendo y veo sus tareas ---


def test_pa1_veo_las_tareas_del_estudiante_que_atiendo(client, luis):
    respuesta = client.get(url("A01", dia_con_tareas()))
    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    assert "Agenda de Lucía Fernández" in html
    for nombre in ["Preparar la mochila", "Lavarse las manos", "Regar las plantas"]:
        assert nombre in html
    assert "Creada por Ana Martín Ruiz" in html
    # Ordenadas por hora.
    assert html.index("Preparar la mochila") < html.index("Lavarse las manos")


def test_pa1_veo_el_estado_de_cada_tarea_ese_dia(client, luis):
    # Los datos de prueba dejan a Lucía una tarea hecha y otra vencida ayer.
    ayer = timezone.localdate() - timedelta(days=1)
    html = client.get(url("A01", ayer)).content.decode()
    assert "Hecha" in html
    assert "Vencida" in html


def test_pa1_veo_el_horario_de_clase_del_dia(client, luis):
    html = client.get(url("A01", dia_con_tareas())).content.decode()
    assert "Horario de clase" in html
    assert "09:00 – 10:00" in html


def test_pa1_la_fecha_sale_en_espanol_aunque_el_navegador_este_en_ingles(client, luis):
    respuesta = client.get(url("A01", date(2026, 11, 10)), HTTP_ACCEPT_LANGUAGE="en-US")
    assert "Martes 10 de noviembre" in respuesta.content.decode()


def test_pa1_paso_de_un_dia_a_otro(client, luis):
    dia = dia_con_tareas()
    html = client.get(url("A01", dia)).content.decode()
    assert f"?dia={dia + timedelta(days=1):%Y-%m-%d}" in html
    assert f"?dia={dia - timedelta(days=1):%Y-%m-%d}" in html


def test_pa1_un_dia_sin_tareas_lo_dice(client, luis):
    # Las tareas de prueba empiezan hace 7 días: un sábado de hace un mes no tiene ninguna.
    sabado = timezone.localdate() - timedelta(days=30)
    while sabado.isoweekday() != 6:
        sabado -= timedelta(days=1)
    html = client.get(url("A01", sabado)).content.decode()
    assert "Este día no tiene tareas." in html
    assert "Este día no hay horario de clase." in html


def test_pa1_una_fecha_mal_escrita_ensena_hoy(client, luis):
    respuesta = client.get(reverse("usuarios:agenda_estudiante", args=["A01"]) + "?dia=ayer")
    assert respuesta.status_code == 200
    assert "(hoy)" in respuesta.content.decode()


def test_pa1_desde_mis_estudiantes_hay_un_enlace_a_su_agenda(client, luis):
    html = client.get(reverse("usuarios:mis_estudiantes")).content.decode()
    assert url("A01") in html
    assert url("A04") in html
    assert url("A02") not in html


# --- PA2: no puedo modificar ni borrar las tareas creadas por el tutor u otro profesional ---


def test_pa2_las_tareas_de_otros_salen_como_solo_consulta(client, luis):
    html = client.get(url("A01", dia_con_tareas())).content.decode()
    assert "Solo consulta" in html
    assert "Creada por ti" not in html
    # Ninguna acción de cambiar: la página no tiene formularios POST salvo «Salir».
    assert html.count('method="post"') == 1


def test_pa2_la_regla_solo_deja_cambiar_lo_que_creo_y_puso_uno_mismo(luis):
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    de_la_tutora = lucia.asignaciones.select_related("tarea").first()
    assert not consulta.puede_modificar(luis, de_la_tutora)

    propia = Tarea.objects.create(
        nombre="Ejercicios de voz",
        imagen="tareas/voz.png",
        descripcion_imagen="Boca abierta",
        ambito=Ambito.ESCOLAR,
        creador=luis,
    )
    mia = Asignacion.objects.create(
        tarea=propia,
        estudiante=lucia,
        asignado_por=luis,
        hora_inicio=time(16, 0),
        hora_fin=time(16, 30),
        dias_semana=[1, 2, 3, 4, 5],
        vigencia_desde=timezone.localdate() - timedelta(days=1),
    )
    assert consulta.puede_modificar(luis, mia)
    # Una tarea de la tutora que pone él tampoco es suya: no la puede cambiar.
    puesta = Asignacion.objects.create(
        tarea=de_la_tutora.tarea,
        estudiante=lucia,
        asignado_por=luis,
        hora_inicio=time(16, 30),
        hora_fin=time(16, 45),
        dias_semana=[1],
        vigencia_desde=timezone.localdate(),
    )
    assert not consulta.puede_modificar(luis, puesta)


def test_pa2_lo_que_creo_yo_sale_marcado_como_mio(client, luis):
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    propia = Tarea.objects.create(
        nombre="Ejercicios de voz",
        imagen="tareas/voz.png",
        descripcion_imagen="Boca abierta",
        ambito=Ambito.ESCOLAR,
        creador=luis,
    )
    Asignacion.objects.create(
        tarea=propia,
        estudiante=lucia,
        asignado_por=luis,
        hora_inicio=time(16, 0),
        hora_fin=time(16, 30),
        dias_semana=[1, 2, 3, 4, 5],
        vigencia_desde=timezone.localdate() - timedelta(days=1),
    )
    html = client.get(url("A01", dia_con_tareas())).content.decode()
    assert "Creada por ti" in html
    assert "Solo consulta" in html


def test_pa2_la_pagina_no_admite_post(client, luis):
    assert client.post(url("A01")).status_code == 405


# --- PA3: no veo la agenda de los estudiantes que no atiendo ---


def test_pa3_no_veo_la_agenda_de_quien_no_atiendo(client, luis):
    respuesta = client.get(url("A02", dia_con_tareas()))
    assert respuesta.status_code == 404
    assert "Mateo" not in respuesta.content.decode()


def test_pa3_si_dejo_de_atenderlo_dejo_de_ver_su_agenda(client, luis):
    assert client.get(url("A04")).status_code == 200
    client.post(reverse("usuarios:mis_estudiantes"), {"quitar": "A04"})
    assert client.get(url("A04")).status_code == 404


def test_pa3_un_codigo_que_no_existe_da_404(client, luis):
    assert client.get(url("Z99")).status_code == 404


def test_pa3_el_codigo_en_minusculas_tambien_vale(client, luis):
    assert client.get(url("a01")).status_code == 200


@pytest.mark.parametrize("usuario", ["tutor", "familiar", "admin", "est-a01"])
def test_pa3_solo_el_profesional_usa_esta_pantalla(client, datos, usuario):
    client.force_login(Usuario.objects.get(username=usuario))
    assert client.get(url("A01")).status_code == 403


def test_sin_sesion_va_a_la_portada(client, datos):
    respuesta = client.get(url("A01"))
    assert respuesta.status_code == 302
    assert respuesta["Location"].startswith(reverse("inicio"))
