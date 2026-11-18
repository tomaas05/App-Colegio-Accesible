"""HU-07-04 (plan B del estudiante) y HU-02-07 (confirmar) en el navegador.

axe WCAG 2.2 AA y sin desplazamiento (decisión 0005) en las pantallas nuevas, y el
recorrido con teclado: «No puedo hacerla» → «¿No puedes hacerla?» → elegir del plan B.
Hora fijada a las 11:50 (Regar las plantas, de 12:00 a 12:30, tiene plan B).
"""

from datetime import datetime, time

import pytest
from axe_playwright_python.sync_playwright import Axe
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios
from apps.comun.models import TipoAviso, avisar
from apps.tareas.models import Tarea
from apps.usuarios.models import Estudiante, Usuario

pytestmark = pytest.mark.e2e

RESOLUCIONES = {
    "movil-vertical": (360, 640),
    "tablet-vertical": (768, 1024),
    "tablet-horizontal": (1280, 800),
    "ordenador": (1366, 768),
}
ETIQUETAS_WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]


def a_las(hora, minuto=0):
    return timezone.make_aware(datetime.combine(timezone.localdate(), time(hora, minuto)))


@pytest.fixture
def lucia(datos, monkeypatch):
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(11, 50))
    return Estudiante.objects.get(codigo_estudiante="A01")


def entrar(page, live_server, client, usuario):
    client.force_login(usuario)
    page.context.add_cookies(
        [{"name": "sessionid", "value": client.cookies["sessionid"].value, "url": live_server.url}]
    )


def regar(lucia):
    return lucia.asignaciones.get(tarea__nombre="Regar las plantas")


def revisar(page, nombre, ancho, alto):
    resultado = Axe().run(page, options={"runOnly": {"type": "tag", "values": ETIQUETAS_WCAG}})
    assert resultado.violations_count == 0, resultado.generate_report()
    medida = page.evaluate(
        "[document.documentElement.scrollWidth, document.documentElement.scrollHeight]"
    )
    assert medida[0] <= ancho, f"Scroll horizontal en {nombre}: {medida[0]}px"
    assert medida[1] <= alto, f"Scroll vertical en {nombre}: {medida[1]}px"


def test_no_puedo_y_elegir_con_teclado(live_server, page, client, lucia):
    entrar(page, live_server, client, lucia.usuario)
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto(live_server.url + reverse("agenda:detalle", args=[regar(lucia).pk]))

    page.get_by_role("link", name="No puedo hacerla").click()
    dialogo = page.get_by_role("dialog", name="¿No puedes hacerla?")
    dialogo.wait_for()
    # El foco empieza en «No»: pulsar sin querer no cambia nada (HU-02-07).
    assert page.evaluate("document.activeElement.textContent") == "No"
    revisar(page, "¿No puedes hacerla?", 1280, 800)
    page.keyboard.press("Enter")
    assert not dialogo.is_visible()

    page.get_by_role("link", name="No puedo hacerla").click()
    dialogo.get_by_role("button", name="Sí").click()
    page.get_by_role("heading", name="Puedes hacer esto").wait_for()
    page.get_by_role("button", name="Escuchar música").focus()
    page.keyboard.press("Enter")
    page.get_by_role("heading", name="Tareas de hoy").wait_for()
    assert page.get_by_text("Escuchar música (plan B)").is_visible()


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_pantallas_del_estudiante_sin_errores_ni_scroll(live_server, page, client, lucia, nombre):
    ancho, alto = RESOLUCIONES[nombre]
    entrar(page, live_server, client, lucia.usuario)
    page.set_viewport_size({"width": ancho, "height": alto})
    pk = regar(lucia).pk

    # La tarea con «No puedo hacerla» y la pregunta sin JavaScript (página).
    for ruta in (reverse("agenda:detalle", args=[pk]), reverse("agenda:no_puedo", args=[pk])):
        page.goto(live_server.url + ruta)
        page.wait_for_timeout(200)
        revisar(page, f"{ruta} a {nombre}", ancho, alto)

    # B11 · Puedes hacer esto.
    servicios.no_puedo(lucia, pk, por=lucia.usuario)
    page.goto(live_server.url + reverse("agenda:plan_b", args=[pk]))
    page.wait_for_timeout(200)
    revisar(page, f"plan B a {nombre}", ancho, alto)


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_pantallas_del_adulto_sin_errores_ni_scroll(live_server, page, client, lucia, nombre):
    ancho, alto = RESOLUCIONES[nombre]
    tutor = Usuario.objects.get(username="tutor")
    avisar(
        tutor,
        "Lucía no ha podido hacer «Regar las plantas» y ha elegido «Escuchar música».",
        tipo=TipoAviso.PLAN_B,
        tarea=Tarea.objects.get(nombre="Escuchar música"),
    )
    avisar(tutor, "Otro aviso.")
    entrar(page, live_server, client, tutor)
    page.set_viewport_size({"width": ancho, "height": alto})
    for ruta in (
        reverse("usuarios:panel"),
        reverse("tareas:no_se_puede", args=[regar(lucia).pk]),
        reverse("tareas:tareas_planificadas") + f"?fecha={timezone.localdate().isoformat()}",
    ):
        page.goto(live_server.url + ruta)
        page.wait_for_timeout(200)
        revisar(page, f"{ruta} a {nombre}", ancho, alto)
