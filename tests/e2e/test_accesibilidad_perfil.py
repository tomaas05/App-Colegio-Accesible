"""Accesibilidad de las pantallas de perfil visual y temporizador (Jorge, HU-04-01 y HU-07-01).

Comprueba con axe-core (WCAG 2.2 AA) y ausencia de scroll horizontal:
- La lista (/perfil/) y el formulario B52 (/perfil/A01/) en las 3 resoluciones.
- La agenda del estudiante con cada combinación de tema y paleta (HU-04-01 PA4).
- El temporizador en curso (lineal, radial y numérico), su avance por segundo (HU-07-01 PA2)
  y el botón de ocultar/mostrar (HU-07-01 PA3).
Se lanzan con:  pytest -m e2e
"""

from datetime import datetime, time

import pytest
from axe_playwright_python.sync_playwright import Axe
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios
from apps.perfil.models import Paleta, Tema, TipoTemporizador
from apps.usuarios.models import Estudiante, Usuario

pytestmark = pytest.mark.e2e

RESOLUCIONES = {
    "movil-vertical": (360, 640),
    "tablet-horizontal": (1280, 800),
    "ordenador": (1366, 768),
}
ETIQUETAS_WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]


def a_las(hora, minuto=0, segundo=0):
    return timezone.make_aware(datetime.combine(timezone.localdate(), time(hora, minuto, segundo)))


def revisar(page, nombre):
    ancho, _ = RESOLUCIONES[nombre]
    resultado = Axe().run(page, options={"runOnly": {"type": "tag", "values": ETIQUETAS_WCAG}})
    assert resultado.violations_count == 0, resultado.generate_report()
    ancho_documento = page.evaluate("document.documentElement.scrollWidth")
    assert ancho_documento <= ancho, f"Scroll horizontal en {nombre}: {ancho_documento}px"


def con_sesion(page, live_server, client, usuario):
    client.force_login(usuario)
    page.context.add_cookies(
        [{"name": "sessionid", "value": client.cookies["sessionid"].value, "url": live_server.url}]
    )


@pytest.mark.parametrize("ruta", ["/perfil/", "/perfil/A01/"])
@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_pantallas_tutor_perfil_accesibles(live_server, page, client, datos, ruta, nombre):
    con_sesion(page, live_server, client, Usuario.objects.get(username="tutor"))
    ancho, alto = RESOLUCIONES[nombre]
    page.set_viewport_size({"width": ancho, "height": alto})
    page.goto(live_server.url + ruta)
    revisar(page, nombre)


@pytest.mark.parametrize("tema", Tema.values)
@pytest.mark.parametrize("paleta", Paleta.values)
def test_agenda_estudiante_accesible_con_cada_tema_y_paleta(
    live_server, page, client, datos, tema, paleta
):
    """HU-04-01 PA4 en navegador real: axe comprueba el contraste >= 4,5:1 en cada combinación."""
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    perfil = lucia.perfil
    perfil.tema = tema
    perfil.paleta = paleta
    perfil.save()

    con_sesion(page, live_server, client, lucia.usuario)
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto(live_server.url + reverse("agenda:dia"))
    revisar(page, "tablet-horizontal")


@pytest.mark.parametrize("tipo", TipoTemporizador.values)
@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_temporizador_accesible_en_los_tres_tipos_y_resoluciones(
    live_server, page, client, datos, monkeypatch, tipo, nombre
):
    """HU-07-01 PA5: temporizador lineal, radial y numérico sin fallos axe ni scroll horizontal."""
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(12, 5))
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    perfil = lucia.perfil
    perfil.tipo_temporizador = tipo
    perfil.puede_ocultar_temporizador = True
    perfil.save()

    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas")
    servicios.empezar(lucia, regar.pk)

    con_sesion(page, live_server, client, lucia.usuario)
    ancho, alto = RESOLUCIONES[nombre]
    page.set_viewport_size({"width": ancho, "height": alto})
    page.goto(live_server.url + reverse("agenda:detalle", args=[regar.pk]))
    revisar(page, nombre)


def test_temporizador_avanza_por_segundo_y_permite_ocultar_y_mostrar(
    live_server, page, client, datos, monkeypatch
):
    """HU-07-01 PA2 y PA3: avanza cada segundo y permite ocultar y mostrar."""
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(12, 5, 0))
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    perfil = lucia.perfil
    perfil.tipo_temporizador = TipoTemporizador.NUMERICO
    perfil.puede_ocultar_temporizador = True
    perfil.temporizador_visible = True
    perfil.save()

    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas")
    servicios.empezar(lucia, regar.pk)

    con_sesion(page, live_server, client, lucia.usuario)
    page.clock.install()
    page.goto(live_server.url + reverse("agenda:detalle", args=[regar.pk]))

    reloj = page.locator("[data-temporizador-reloj]")
    assert reloj.inner_text().strip() == "25:00"

    # PA2: tras avanzar 2 segundos el reloj del navegador, la cuenta atrás baja a 24:58.
    page.clock.run_for(2_000)
    assert reloj.inner_text().strip() == "24:58"

    # PA3: al pulsar «Ocultar tiempo» se oculta y al pulsar «Mostrar tiempo» vuelve a verse.
    boton = page.locator("[data-ocultar-temporizador]")
    cuerpo = page.locator("[data-temporizador-cuerpo]")
    assert cuerpo.is_visible()
    boton.click()
    assert not cuerpo.is_visible()
    assert boton.inner_text().strip() == "Mostrar tiempo"

    boton.click()
    assert cuerpo.is_visible()
    assert boton.inner_text().strip() == "Ocultar tiempo"
