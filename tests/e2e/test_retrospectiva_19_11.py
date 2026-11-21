"""Retrospectiva de la profesora del 19/11: lo que necesita navegador.

Pantallas nuevas o cambiadas, en los 6 tamaños de revisión (ayudas.RESOLUCIONES) con
`revisar` (axe, sin desplazamiento, nada fuera de su caja, objetivos de 48 px y, con el peor
perfil, letra del perfil), y la flecha «Ahora» que avanza por la línea de tiempo.
Se lanzan con:  pytest -m e2e tests/e2e/test_retrospectiva_19_11.py
"""

import re
from datetime import datetime, time

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios
from apps.tareas.models import Tarea
from apps.usuarios.models import Estudiante, Usuario
from tests.e2e.ayudas import PEOR_PERFIL, RESOLUCIONES, con_sesion, revisar

pytestmark = pytest.mark.e2e

ESTUDIANTES = {"defecto": "A04", "peor": PEOR_PERFIL}


def a_las(hora, minuto=0):
    return timezone.make_aware(datetime.combine(timezone.localdate(), time(hora, minuto)))


@pytest.fixture
def estudiante(request, datos, page, live_server, client, monkeypatch):
    """El estudiante del perfil pedido, a las 10:40, con «Lavarse las manos» ya terminada."""
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(10, 40))
    est = Estudiante.objects.get(codigo_estudiante=ESTUDIANTES[request.param])
    con_sesion(page, live_server, client, est.usuario)
    manos = est.asignaciones.get(tarea__nombre__icontains="manos")
    servicios.empezar(est, manos.pk, a_las(10, 30))
    t = servicios.tarea_del_dia(est, manos.pk, a_las(10, 35))
    for p in t.pasos:
        servicios.marcar_paso_hecho(est, manos.pk, p.paso.pk, a_las(10, 35))
    servicios.terminar(est, manos.pk, a_las(10, 36))
    est.manos = manos
    return est


@pytest.mark.parametrize("pantalla", ["bravo", "agenda", "mi-horario"])
@pytest.mark.parametrize("tamano", RESOLUCIONES)
@pytest.mark.parametrize("estudiante", ESTUDIANTES, indirect=True)
def test_pantallas_del_estudiante(live_server, page, estudiante, tamano, pantalla):
    ruta = {
        "bravo": reverse("agenda:bravo", args=[estudiante.manos.pk]),
        "agenda": reverse("agenda:dia"),
        "mi-horario": reverse("horario:mi_horario"),
    }[pantalla]
    page.set_viewport_size(dict(zip(("width", "height"), RESOLUCIONES[tamano], strict=True)))
    page.goto(live_server.url + ruta)
    revisar(page, letra=estudiante.codigo_estudiante == PEOR_PERFIL)


@pytest.mark.parametrize("estudiante", ["defecto"], indirect=True)
def test_la_flecha_ahora_esta_en_la_tarea_de_ahora_y_avanza(live_server, page, estudiante):
    """A las 10:40 entre «Lavarse las manos» (10:30-10:45) y «Regar» (12:00): dentro de la
    de las manos, a dos tercios. En la tableta, la flecha va encima de la línea."""
    page.set_viewport_size({"width": 1024, "height": 768})
    page.goto(live_server.url + reverse("agenda:dia"))
    flecha = page.locator(".linea__flecha")
    flecha.wait_for()
    assert flecha.get_attribute("aria-hidden") == "true"
    tarjeta = page.locator("li", has=page.locator(".linea__flecha"))
    assert "Lavarse las manos" in tarjeta.inner_text()
    avance = float(flecha.evaluate("e => e.style.getPropertyValue('--avance')"))
    assert 0.6 < avance < 0.75
    caja, punta = tarjeta.bounding_box(), flecha.bounding_box()
    centro = punta["x"] + punta["width"] / 2
    assert caja["x"] + caja["width"] * 0.55 < centro < caja["x"] + caja["width"] * 0.8


@pytest.mark.parametrize("estudiante", ["defecto"], indirect=True)
def test_entre_dos_tareas_la_flecha_queda_en_el_hueco(live_server, page, estudiante, monkeypatch):
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(11, 0))
    page.set_viewport_size({"width": 1024, "height": 768})
    page.goto(live_server.url + reverse("agenda:dia"))
    flecha = page.locator(".linea__flecha")
    flecha.wait_for()
    assert "linea__flecha--hueco" in flecha.get_attribute("class")
    tarjeta = page.locator("li", has=page.locator(".linea__flecha"))
    assert "Regar las plantas" in tarjeta.inner_text()


def rutas_de_adulto():
    regar = Tarea.objects.get(nombre="Regar las plantas")
    return {
        "plan-b": ("tutor", reverse("tareas:plan_b", args=[regar.pk])),
        "plan-b-buscar": ("tutor", reverse("tareas:plan_b", args=[regar.pk]) + "?q=cuento"),
        "biblioteca": ("tutor", reverse("tareas:catalogo")),
        "biblioteca-buscar": ("tutor", reverse("tareas:catalogo") + "?q=mochila"),
        "alumnos-buscar": ("tutor", reverse("perfil:lista") + "?q=sof"),
        "planificadas": ("tutor", reverse("tareas:tareas_planificadas")),
        "asignar": ("tutor", reverse("tareas:asignar_tarea")),
    }


@pytest.mark.parametrize(
    "pantalla",
    [
        "plan-b",
        "plan-b-buscar",
        "biblioteca",
        "biblioteca-buscar",
        "alumnos-buscar",
        "planificadas",
        "asignar",
    ],
)
@pytest.mark.parametrize("tamano", RESOLUCIONES)
def test_pantallas_del_tutor(live_server, page, client, datos, tamano, pantalla):
    usuario, ruta = rutas_de_adulto()[pantalla]
    con_sesion(page, live_server, client, Usuario.objects.get(username=usuario))
    page.set_viewport_size(dict(zip(("width", "height"), RESOLUCIONES[tamano], strict=True)))
    page.goto(live_server.url + ruta)
    revisar(page)


def test_plan_b_con_teclado(live_server, page, client, datos):
    """Se añade y se quita con el teclado, y el foco vuelve a la tarjeta pulsada."""
    regar = Tarea.objects.get(nombre="Regar las plantas")
    regar.planes_b.all().delete()
    con_sesion(page, live_server, client, Usuario.objects.get(username="tutor"))
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto(live_server.url + reverse("tareas:plan_b", args=[regar.pk]))
    musica = page.locator("#biblioteca-plan-b").get_by_role("button", name="Escuchar música")
    musica.focus()
    with page.expect_navigation():
        page.keyboard.press("Enter")
    page.wait_for_load_state()
    tarjeta = page.locator("#biblioteca-plan-b").get_by_role(
        "button", name=re.compile(r"^Escuchar música")
    )
    assert tarjeta.get_attribute("aria-pressed") == "true"
    assert tarjeta.evaluate("e => e === document.activeElement")
    assert [a.nombre for a in regar.alternativas] == ["Escuchar música"]
