"""Accesibilidad de las pantallas de la agenda del estudiante (Tomás).

Misma comprobación que test_accesibilidad.py (axe WCAG 2.2 AA y sin scroll horizontal),
pero entrando antes como Lucía, porque estas pantallas piden sesión de estudiante, y con
la hora fijada para que haya tarea actual y aviso de la siguiente.
Se lanzan con:  pytest -m e2e
"""

from datetime import datetime, time, timedelta

import pytest
from axe_playwright_python.sync_playwright import Axe
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios
from apps.usuarios.models import Estudiante

pytestmark = pytest.mark.e2e

RESOLUCIONES = {
    "movil-vertical": (360, 640),
    "tablet-horizontal": (1280, 800),
    "ordenador": (1366, 768),
}
ETIQUETAS_WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]

# Nombre de la tarea de Lucía (datos de prueba) cuyo detalle se revisa, o None = la agenda.
PANTALLAS = [None, "Preparar la mochila", "Regar las plantas"]


def a_las(hora, minuto=0):
    return timezone.make_aware(datetime.combine(timezone.localdate(), time(hora, minuto)))


@pytest.fixture
def lucia(datos, page, live_server, client, monkeypatch):
    # 11:52: Regar las plantas (12:00) sale en el aviso del pie.
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(11, 52))
    estudiante = Estudiante.objects.get(codigo_estudiante="A01")
    client.force_login(estudiante.usuario)
    page.context.add_cookies(
        [{"name": "sessionid", "value": client.cookies["sessionid"].value, "url": live_server.url}]
    )
    return estudiante


def ruta_de(estudiante, tarea):
    if tarea is None:
        return reverse("agenda:dia")
    pk = estudiante.asignaciones.get(tarea__nombre=tarea).pk
    return reverse("agenda:detalle", args=[pk])


def sin_errores_axe(page):
    resultado = Axe().run(page, options={"runOnly": {"type": "tag", "values": ETIQUETAS_WCAG}})
    assert resultado.violations_count == 0, resultado.generate_report()


@pytest.mark.parametrize("tarea", PANTALLAS)
@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_sin_errores_axe_ni_scroll_horizontal(live_server, page, lucia, tarea, nombre):
    ancho, alto = RESOLUCIONES[nombre]
    page.set_viewport_size({"width": ancho, "height": alto})
    page.goto(live_server.url + ruta_de(lucia, tarea))

    sin_errores_axe(page)

    ancho_documento = page.evaluate("document.documentElement.scrollWidth")
    assert ancho_documento <= ancho, f"Scroll horizontal en {nombre}: {ancho_documento}px"


def test_vista_de_dia_sin_scroll_vertical_en_tablet(live_server, page, lucia):
    """RNF2.3.1: la vista de día, sin desplazamiento vertical a 1280 × 800."""
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto(live_server.url + reverse("agenda:dia"))
    alto_documento = page.evaluate("document.documentElement.scrollHeight")
    assert alto_documento <= 800, f"Scroll vertical: {alto_documento}px"


def test_confirmar_terminar_en_ventana_con_teclado(live_server, page, lucia, monkeypatch):
    """B08: «Terminar» abre el <dialog>; con Escape se cierra y la tarea sigue en curso."""
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(12, 5))
    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas")
    servicios.empezar(lucia, regar.pk)
    page.goto(live_server.url + reverse("agenda:detalle", args=[regar.pk]))

    page.get_by_role("link", name="Terminar").focus()
    page.keyboard.press("Enter")
    dialogo = page.get_by_role("dialog", name="¿Has terminado?")
    assert dialogo.is_visible()
    sin_errores_axe(page)

    page.keyboard.press("Escape")
    assert not dialogo.is_visible()
    assert regar.ejecuciones.get(fecha=timezone.localdate()).estado == "en_curso"


def test_empezar_aparece_solo_al_llegar_la_hora(live_server, page, lucia, monkeypatch):
    """Sin recargar: la zona del botón se vuelve a pedir cada 30 s hasta que se puede empezar."""
    desde = a_las(17) - servicios.MARGEN_EMPEZAR_ANTES  # Leer un cuento: 17:00
    monkeypatch.setattr(servicios, "ahora", lambda: desde - timedelta(minutes=1))
    page.clock.install()
    page.goto(live_server.url + ruta_de(lucia, "Leer un cuento"))
    assert page.get_by_text(f"Podrás empezar a las {desde:%H:%M}.").is_visible()
    foco = page.get_by_role("link", name="Volver a las tareas")
    foco.focus()

    monkeypatch.setattr(servicios, "ahora", lambda: desde)
    page.clock.run_for(31_000)
    page.get_by_role("button", name="Empezar").wait_for()
    assert foco.evaluate("el => el === document.activeElement")  # el foco no se mueve


def test_el_aviso_de_la_siguiente_aparece_sin_recargar(live_server, page, lucia, monkeypatch):
    """RNF2.1.3: como mucho 60 s después de entrar en los 10 minutos previos."""
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(11, 49))
    page.clock.install()
    page.goto(live_server.url + reverse("agenda:dia"))
    assert not page.get_by_text("Después, a las 12:00").is_visible()

    monkeypatch.setattr(servicios, "ahora", lambda: a_las(11, 50))
    page.clock.run_for(31_000)
    page.get_by_role("status").get_by_text("Después, a las 12:00").wait_for()
