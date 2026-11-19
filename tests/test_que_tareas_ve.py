"""HU-04-02. Elegir qué tareas ve cada estudiante y cuántas (AGENDA-233).

Una prueba por cada prueba de aceptación de Jira (PA1 a PA6).
"""

from datetime import datetime, time
from pathlib import Path

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios
from apps.perfil.models import (
    AlcanceAgenda,
    ContenidoBotones,
    MaxTarjetas,
    Paleta,
    Perfil,
    TamanoBotones,
    TamanoLetra,
    Tema,
    TipoLetra,
)
from apps.usuarios.models import Estudiante, Usuario

pytestmark = pytest.mark.django_db


def a_las(hora, minuto=0):
    return timezone.make_aware(datetime.combine(timezone.localdate(), time(hora, minuto)))


def url_editar(codigo="A01"):
    return reverse("perfil:editar", args=[codigo])


def datos_form(**cambios):
    base = {
        "tema": Tema.CLARO,
        "paleta": Paleta.ESTANDAR,
        "tipo_letra": TipoLetra.NUNITO,
        "tamano_letra": TamanoLetra.GRANDE,
        "tamano_botones": TamanoBotones.GRANDE,
        "contenido_botones": ContenidoBotones.AMBOS,
        "alcance_agenda": AlcanceAgenda.SEMANA,
        "max_tarjetas": MaxTarjetas.SEIS,
        "usa_lector_pantalla": False,
    }
    base.update(cambios)
    return base


# --- PA1: en modo «solo la actual» el estudiante ve únicamente la tarea actual ---


def test_pa1_modo_solo_la_actual_muestra_unicamente_la_tarea_actual(client, datos, monkeypatch):
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(10, 35))
    client.force_login(Usuario.objects.get(username="tutor"))
    respuesta = client.post(url_editar("A01"), datos_form(alcance_agenda=AlcanceAgenda.ACTUAL))
    assert respuesta.status_code == 302

    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    agenda = servicios.agenda_del_dia(lucia, a_las(10, 35))
    assert [t.tarea.nombre for t in agenda.en_alcance] == ["Lavarse las manos"]
    assert [t.tarea.nombre for t in agenda.visibles] == ["Lavarse las manos"]

    client.force_login(lucia.usuario)
    html = client.get(reverse("agenda:dia")).content.decode()
    assert "Lavarse las manos" in html
    for otra in ("Preparar la mochila", "Regar las plantas", "Leer un cuento", "Poner la mesa"):
        assert otra not in html
    assert "Mi semana" not in html


# --- PA2: en modo «la actual y la siguiente» el estudiante ve esas dos tareas ---


def test_pa2_modo_actual_y_siguiente_muestra_esas_dos_tareas(client, datos, monkeypatch):
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(10, 35))
    client.force_login(Usuario.objects.get(username="tutor"))
    client.post(url_editar("A01"), datos_form(alcance_agenda=AlcanceAgenda.ACTUAL_SIGUIENTE))

    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    agenda = servicios.agenda_del_dia(lucia, a_las(10, 35))
    assert [t.tarea.nombre for t in agenda.en_alcance] == [
        "Lavarse las manos",
        "Regar las plantas",
    ]

    client.force_login(lucia.usuario)
    html = client.get(reverse("agenda:dia")).content.decode()
    assert "Lavarse las manos" in html
    assert "Regar las plantas" in html
    for otra in ("Preparar la mochila", "Leer un cuento", "Poner la mesa"):
        assert otra not in html
    assert "Mi semana" not in html


# --- PA3: en modo «día» o «semana» el estudiante ve todo el día o toda la semana ---


def test_pa3_modo_dia_muestra_todo_el_dia_sin_semana(client, datos, monkeypatch):
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(10, 35))
    client.force_login(Usuario.objects.get(username="tutor"))
    client.post(url_editar("A01"), datos_form(alcance_agenda=AlcanceAgenda.DIA))

    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    client.force_login(lucia.usuario)
    html = client.get(reverse("agenda:dia")).content.decode()
    for nombre in (
        "Preparar la mochila",
        "Lavarse las manos",
        "Regar las plantas",
        "Leer un cuento",
        "Poner la mesa",
    ):
        assert nombre in html
    assert "Mi semana" not in html
    # Si intenta abrir /agenda/semana/ en modo «día», vuelve a la vista del día.
    respuesta_semana = client.get(reverse("agenda:semana"))
    assert respuesta_semana.status_code == 302
    assert respuesta_semana["Location"] == reverse("agenda:dia")


def test_pa3_modo_semana_muestra_el_dia_y_permite_ver_toda_la_semana(client, datos, monkeypatch):
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(10, 35))
    client.force_login(Usuario.objects.get(username="tutor"))
    client.post(url_editar("A01"), datos_form(alcance_agenda=AlcanceAgenda.SEMANA))

    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    client.force_login(lucia.usuario)
    html_dia = client.get(reverse("agenda:dia")).content.decode()
    assert "Mi semana" in html_dia

    respuesta_semana = client.get(reverse("agenda:semana"))
    assert respuesta_semana.status_code == 200
    html_semana = respuesta_semana.content.decode()
    for dia in ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"):
        assert dia in html_semana


# --- PA4: pongo un máximo de 3 tarjetas y en la vista de día nunca ve más de 3 a la vez ---


def test_pa4_maximo_3_tarjetas_en_la_vista_de_dia(client, datos, monkeypatch):
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(10, 35))
    client.force_login(Usuario.objects.get(username="tutor"))
    client.post(url_editar("A01"), datos_form(max_tarjetas=MaxTarjetas.TRES))

    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    assert Perfil.objects.get(estudiante=lucia).max_tarjetas == 3

    agenda = servicios.agenda_del_dia(lucia, a_las(10, 35))
    assert len(agenda.visibles) == 3
    assert agenda.restantes == 2

    client.force_login(lucia.usuario)
    html = client.get(reverse("agenda:dia")).content.decode()
    assert 'data-max="3"' in html


# --- PA5: los botones muestran pictograma, texto o ambos, según lo elegido ---


@pytest.mark.parametrize("contenido", ContenidoBotones.values)
def test_pa5_los_botones_muestran_imagen_texto_o_ambos(client, datos, contenido):
    client.force_login(Usuario.objects.get(username="tutor"))
    client.post(url_editar("A01"), datos_form(contenido_botones=contenido))

    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    assert Perfil.objects.get(estudiante=lucia).contenido_botones == contenido

    client.force_login(lucia.usuario)
    html = client.get(reverse("agenda:dia")).content.decode()
    assert f'data-contenido-botones="{contenido}"' in html

    css = Path("static/css/tokens.css").read_text(encoding="utf-8")
    assert 'html[data-contenido-botones="imagen"]' in css
    assert 'html[data-contenido-botones="texto"]' in css


# --- PA6: el cambio afecta solo a ese estudiante ---


def test_pa6_el_cambio_afecta_solo_a_ese_estudiante(client, datos, monkeypatch):
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(10, 35))
    client.force_login(Usuario.objects.get(username="tutor"))
    client.post(
        url_editar("A01"),
        datos_form(
            alcance_agenda=AlcanceAgenda.ACTUAL,
            max_tarjetas=MaxTarjetas.DOS,
            contenido_botones=ContenidoBotones.IMAGEN,
        ),
    )

    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    hugo = Estudiante.objects.get(codigo_estudiante="A04")

    # Lucía tiene sus ajustes nuevos.
    client.force_login(lucia.usuario)
    html_lucia = client.get(reverse("agenda:dia")).content.decode()
    assert 'data-contenido-botones="imagen"' in html_lucia
    assert "Lavarse las manos" in html_lucia
    assert "Preparar la mochila" not in html_lucia

    # Hugo conserva los valores por defecto (semana, 6 tarjetas, imagen y texto).
    assert hugo.perfil.alcance_agenda == AlcanceAgenda.SEMANA
    assert hugo.perfil.max_tarjetas == 6
    assert hugo.perfil.contenido_botones == ContenidoBotones.AMBOS

    client.force_login(hugo.usuario)
    html_hugo = client.get(reverse("agenda:dia")).content.decode()
    assert 'data-contenido-botones="ambos"' in html_hugo
    assert 'data-max="6"' in html_hugo
    assert "Preparar la mochila" in html_hugo
    assert "Mi semana" in html_hugo
