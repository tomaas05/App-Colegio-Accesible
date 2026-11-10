"""HU-07-01. Ver el tiempo que queda de una tarea (AGENDA-86).

Una prueba por cada prueba de aceptación de Jira (PA1 a PA6).
"""

from datetime import datetime, time

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios
from apps.perfil.models import (
    Paleta,
    TamanoBotones,
    TamanoLetra,
    Tema,
    TipoLetra,
    TipoTemporizador,
)
from apps.usuarios.models import Estudiante, Usuario

pytestmark = pytest.mark.django_db


def a_las(hora, minuto=0, segundo=0):
    return timezone.make_aware(datetime.combine(timezone.localdate(), time(hora, minuto, segundo)))


def url_tarea(estudiante, nombre="Regar las plantas"):
    pk = estudiante.asignaciones.get(tarea__nombre=nombre).pk
    return reverse("agenda:detalle", args=[pk])


# --- PA1: en una tarea en curso veo el tiempo que me queda ---


def test_pa1_en_tarea_en_curso_veo_el_tiempo_que_queda(client, datos, monkeypatch):
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    client.force_login(lucia.usuario)
    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas")  # 12:00 a 12:30

    # Antes de empezar la tarea, el temporizador no aparece.
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(12, 0))
    html_pendiente = client.get(url_tarea(lucia)).content.decode()
    assert "data-temporizador" not in html_pendiente

    # Al estar en curso a las 12:05, quedan 25 minutos (1500 s) hasta las 12:30.
    servicios.empezar(lucia, regar.pk)
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(12, 5))
    html_en_curso = client.get(url_tarea(lucia)).content.decode()
    assert "data-temporizador" in html_en_curso
    assert 'data-restante-seg="1500"' in html_en_curso
    assert "Quedan 25 min" in html_en_curso


def test_pa1_cuando_se_agota_el_tiempo_indica_que_se_acabo(client, datos, monkeypatch):
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    client.force_login(lucia.usuario)
    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas")  # 12:00 a 12:30

    monkeypatch.setattr(servicios, "ahora", lambda: a_las(12, 5))
    servicios.empezar(lucia, regar.pk)

    monkeypatch.setattr(servicios, "ahora", lambda: a_las(12, 31))
    html = client.get(url_tarea(lucia)).content.decode()
    assert 'data-restante-seg="0"' in html
    assert "Se acabó el tiempo" in html


# --- PA2: el temporizador avanza al pasar el tiempo ---


def test_pa2_el_temporizador_se_actualiza_al_avanzar_el_tiempo(client, datos, monkeypatch):
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    perfil = lucia.perfil
    perfil.tipo_temporizador = TipoTemporizador.NUMERICO
    perfil.save()
    client.force_login(lucia.usuario)
    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas")  # 12:00 a 12:30

    monkeypatch.setattr(servicios, "ahora", lambda: a_las(12, 5, 0))
    servicios.empezar(lucia, regar.pk)
    html_t0 = client.get(url_tarea(lucia)).content.decode()
    assert 'data-restante-seg="1500"' in html_t0
    assert "25:00" in html_t0

    # Un segundo después (12:05:01), quedan 1499 segundos (24:59).
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(12, 5, 1))
    html_t1 = client.get(url_tarea(lucia)).content.decode()
    assert 'data-restante-seg="1499"' in html_t1
    assert "24:59" in html_t1


# --- PA3: si mi tutor me lo permite, oculto el temporizador y lo vuelvo a mostrar ---


def test_pa3_si_el_tutor_lo_permite_aparece_el_boton_para_ocultar_y_mostrar(
    client, datos, monkeypatch
):
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    perfil = lucia.perfil
    perfil.puede_ocultar_temporizador = True
    perfil.temporizador_visible = True
    perfil.save()

    client.force_login(lucia.usuario)
    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas")
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(12, 5))
    servicios.empezar(lucia, regar.pk)

    html = client.get(url_tarea(lucia)).content.decode()
    assert "data-ocultar-temporizador" in html
    assert "Ocultar tiempo" in html
    assert 'aria-expanded="true"' in html

    # Si el tutor configura que empiece oculto pero permita mostrarlo:
    perfil.temporizador_visible = False
    perfil.save()
    html_oculto = client.get(url_tarea(lucia)).content.decode()
    assert "Mostrar tiempo" in html_oculto
    assert 'aria-expanded="false"' in html_oculto


# --- PA4: si mi tutor no me lo permite, no puedo ocultarlo ---


def test_pa4_si_el_tutor_no_lo_permite_no_aparece_el_boton_de_ocultar(client, datos, monkeypatch):
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    perfil = lucia.perfil
    perfil.puede_ocultar_temporizador = False
    perfil.save()

    client.force_login(lucia.usuario)
    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas")
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(12, 5))
    servicios.empezar(lucia, regar.pk)

    html = client.get(url_tarea(lucia)).content.decode()
    assert "data-temporizador" in html
    assert "data-ocultar-temporizador" not in html
    assert "Ocultar tiempo" not in html


# --- PA5: veo el tipo de temporizador que ha elegido mi tutor: lineal, radial o numérico ---


@pytest.mark.parametrize(
    ("tipo", "marcador_esperado"),
    [
        (TipoTemporizador.LINEAL, "data-temporizador-relleno"),
        (TipoTemporizador.RADIAL, "data-temporizador-arco"),
        (TipoTemporizador.NUMERICO, "data-temporizador-reloj"),
    ],
)
def test_pa5_veo_el_tipo_de_temporizador_elegido_por_el_tutor(
    client, datos, monkeypatch, tipo, marcador_esperado
):
    tutor = Usuario.objects.get(username="tutor")
    client.force_login(tutor)
    respuesta = client.post(
        reverse("perfil:editar", args=["A01"]),
        {
            "tema": Tema.CLARO,
            "paleta": Paleta.ESTANDAR,
            "tipo_letra": TipoLetra.NUNITO,
            "tamano_letra": TamanoLetra.GRANDE,
            "tamano_botones": TamanoBotones.GRANDE,
            "tipo_temporizador": tipo,
            "temporizador_visible": True,
            "puede_ocultar_temporizador": True,
            "usa_lector_pantalla": False,
        },
    )
    assert respuesta.status_code == 302

    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    assert lucia.perfil.tipo_temporizador == tipo

    client.force_login(lucia.usuario)
    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas")
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(12, 5))
    servicios.empezar(lucia, regar.pk)

    html = client.get(url_tarea(lucia)).content.decode()
    assert f'data-tipo="{tipo}"' in html
    assert marcador_esperado in html


# --- PA6: cuenta hasta la hora de fin prevista, aunque haya empezado tarde ---


def test_pa6_el_tiempo_se_cuenta_hasta_la_hora_de_fin_prevista_aunque_empiece_tarde(
    client, datos, monkeypatch
):
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    client.force_login(lucia.usuario)
    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas")  # 12:00 a 12:30 (30 min)

    # Lucía empieza 7 minutos tarde (a las 12:07). Quedan 23 min (1380 s) hasta las 12:30.
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(12, 7))
    servicios.empezar(lucia, regar.pk)

    html = client.get(url_tarea(lucia)).content.decode()
    assert 'data-restante-seg="1380"' in html
    assert 'data-duracion-seg="1800"' in html
    assert "Quedan 23 min" in html
