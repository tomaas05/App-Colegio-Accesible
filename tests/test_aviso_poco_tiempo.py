"""HU-07-02. Recibir un aviso cuando queda poco tiempo (AGENDA-91).

Una prueba por cada prueba de aceptación de Jira (PA1 a PA5).
"""

from datetime import datetime, time

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios
from apps.perfil.models import Paleta
from apps.usuarios.models import Estudiante

pytestmark = pytest.mark.django_db


def a_las(hora, minuto=0, segundo=0):
    return timezone.make_aware(datetime.combine(timezone.localdate(), time(hora, minuto, segundo)))


def url_tarea(estudiante, nombre="Regar las plantas"):
    pk = estudiante.asignaciones.get(tarea__nombre=nombre).pk
    return reverse("agenda:detalle", args=[pk])


# --- PA1: al llegar al umbral de aviso, se muestra un aviso visual ---


def test_pa1_al_llegar_al_umbral_se_muestra_un_aviso_visual(client, datos, monkeypatch):
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    client.force_login(lucia.usuario)
    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas")  # 12:00 a 12:30

    # A las 12:10 quedan 20 minutos: aún no se ha alcanzado el umbral de 5 minutos.
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(12, 10))
    servicios.empezar(lucia, regar.pk)
    html_lejos = client.get(url_tarea(lucia)).content.decode()
    assert 'data-aviso-activo="false"' in html_lejos

    # A las 12:25 quedan 5 minutos (300 s): el aviso visual está activo.
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(12, 25))
    html_5min = client.get(url_tarea(lucia)).content.decode()
    assert 'data-aviso-activo="true"' in html_5min
    assert "¡Quedan 5 minutos!" in html_5min

    # A las 12:29 queda 1 minuto (60 s): el aviso visual indica que queda 1 minuto.
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(12, 29))
    html_1min = client.get(url_tarea(lucia)).content.decode()
    assert 'data-aviso-activo="true"' in html_1min
    assert "¡Queda 1 minuto!" in html_1min


# --- PA2: si el sonido está activado, el aviso también reproduce un sonido ---


def test_pa2_si_el_sonido_esta_activado_incluye_y_activa_el_sonido_de_aviso(
    client, datos, monkeypatch
):
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    perfil = lucia.perfil
    perfil.sonidos_activos = True
    perfil.baja_sobrecarga_sensorial = False
    perfil.paleta = Paleta.ESTANDAR
    perfil.save()

    client.force_login(lucia.usuario)
    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas")
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(12, 25))
    servicios.empezar(lucia, regar.pk)

    html = client.get(url_tarea(lucia)).content.decode()
    assert 'data-sonido-activo="true"' in html
    assert "data-temporizador-audio" in html


# --- PA3: el aviso muestra la siguiente tarea con su pictograma ---


def test_pa3_el_aviso_muestra_la_siguiente_tarea_con_su_pictograma(client, datos, monkeypatch):
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    client.force_login(lucia.usuario)
    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas")  # 12:00 a 12:30
    cuento = lucia.asignaciones.get(tarea__nombre="Leer un cuento")  # siguiente: 17:00

    monkeypatch.setattr(servicios, "ahora", lambda: a_las(12, 26))
    servicios.empezar(lucia, regar.pk)

    html = client.get(url_tarea(lucia)).content.decode()
    assert "Siguiente tarea: <b>Leer un cuento</b> (17:00)" in html
    assert cuento.tarea.imagen.url in html
    assert f'alt="{cuento.tarea.descripcion_imagen}"' in html


def test_pa3_si_la_siguiente_esta_cancelada_muestra_la_posterior_activa(client, datos, monkeypatch):
    """HU-03-05: si «Leer un cuento» (17:00) se cancela, avisa de «Poner la mesa»."""
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas")
    cuento = lucia.asignaciones.get(tarea__nombre="Leer un cuento")
    cuento.cancelada = True
    cuento.cancelada_el = timezone.localdate()
    cuento.save()

    client.force_login(lucia.usuario)
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(12, 26))
    servicios.empezar(lucia, regar.pk)

    html = client.get(url_tarea(lucia)).content.decode()
    assert "Siguiente tarea: <b>Poner la mesa</b> (20:00)" in html
    assert "Leer un cuento" not in html


# --- PA4: si no hay siguiente tarea, el aviso lo indica ---


def test_pa4_si_no_hay_siguiente_tarea_el_aviso_lo_indica(client, datos, monkeypatch):
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    client.force_login(lucia.usuario)
    # «Poner la mesa» (20:00 a 20:20) es la última tarea del día de Lucía.
    mesa = lucia.asignaciones.get(tarea__nombre="Poner la mesa")

    monkeypatch.setattr(servicios, "ahora", lambda: a_las(20, 16))
    servicios.empezar(lucia, mesa.pk)

    html = client.get(url_tarea(lucia, "Poner la mesa")).content.decode()
    assert 'data-aviso-activo="true"' in html
    assert "No hay más tareas hoy" in html


# --- PA5: con el modo de baja sobrecarga sensorial activado, el aviso no emite sonido ---


def test_pa5_con_baja_sobrecarga_sensorial_el_aviso_no_emite_sonido(client, datos, monkeypatch):
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    perfil = lucia.perfil
    perfil.sonidos_activos = True
    perfil.baja_sobrecarga_sensorial = True
    perfil.save()

    client.force_login(lucia.usuario)
    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas")
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(12, 25))
    servicios.empezar(lucia, regar.pk)

    html = client.get(url_tarea(lucia)).content.decode()
    assert 'data-aviso-activo="true"' in html
    assert 'data-baja-sobrecarga="true"' in html
    assert 'data-sonido-activo="false"' in html
    assert "data-temporizador-audio" not in html
