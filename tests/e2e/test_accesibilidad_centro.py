"""Accesibilidad de las pantallas de las tareas del centro (Javi).

HU-05-03 · Comedor y menú (administrador): la lista del mes con días asignados y
pendientes, y cada formulario, también con errores. Misma comprobación que
test_accesibilidad.py (axe WCAG 2.2 AA y sin scroll horizontal) y, además, sin
desplazamiento vertical (decisión 0005).
Se lanzan con:  pytest -m e2e
"""

from datetime import time, timedelta

import pytest
from axe_playwright_python.sync_playwright import Axe
from django.urls import reverse
from django.utils import timezone

from apps.centro import servicios
from apps.usuarios.models import Estudiante, Usuario

pytestmark = pytest.mark.e2e

RESOLUCIONES = {
    "movil-vertical": (360, 640),
    "tablet-horizontal": (1280, 800),
    "ordenador": (1366, 768),
}
ETIQUETAS_WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
URL = reverse("centro:comedor")


def revisar(page, nombre):
    ancho, alto = RESOLUCIONES[nombre]
    resultado = Axe().run(page, options={"runOnly": {"type": "tag", "values": ETIQUETAS_WCAG}})
    assert resultado.violations_count == 0, resultado.generate_report()
    tamano = page.evaluate(
        "[document.documentElement.scrollWidth, document.documentElement.scrollHeight]"
    )
    assert tamano[0] <= ancho, f"Scroll horizontal en {nombre}: {tamano[0]}px"
    assert tamano[1] <= alto, f"Scroll vertical en {nombre}: {tamano[1]}px"


@pytest.fixture
def admin(datos, page, live_server, client):
    usuario = Usuario.objects.get(username="admin")
    client.force_login(usuario)
    page.context.add_cookies(
        [{"name": "sessionid", "value": client.cookies["sessionid"].value, "url": live_server.url}]
    )
    # Un día con estudiante y el reparto del mes, para ver las dos cosas en la lista.
    hoy = timezone.localdate()
    dia = next(hoy + timedelta(days=n) for n in range(7) if (hoy + timedelta(days=n)).weekday() < 5)
    hugo = Estudiante.objects.get(codigo_estudiante="A04")
    servicios.asignar_comedor(dia, hugo, time(13), time(14), usuario)
    if servicios.ultimo_dia(hoy) >= dia:
        servicios.asignar_reparto(hoy, hugo, time(11), time(11, 30), [1, 2, 3, 4, 5], usuario)
    return usuario


@pytest.mark.parametrize("abrir", ["", "comedor", "reparto", "menu"])
@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_comedor_y_menu(live_server, page, admin, abrir, nombre):
    page.set_viewport_size(dict(zip(("width", "height"), RESOLUCIONES[nombre], strict=True)))
    page.goto(f"{live_server.url}{URL}?abrir={abrir}")
    revisar(page, nombre)


@pytest.mark.parametrize("abrir", ["comedor", "reparto"])
@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_formularios_con_errores(live_server, page, admin, abrir, nombre):
    """Guardar sin rellenar nada: el resumen de errores y cada campo marcado."""
    page.set_viewport_size(dict(zip(("width", "height"), RESOLUCIONES[nombre], strict=True)))
    page.goto(f"{live_server.url}{URL}?abrir={abrir}")
    if abrir == "reparto":
        page.evaluate(
            "document.querySelectorAll('input[type=checkbox]')"
            ".forEach((c) => { c.checked = false; })"
        )
    with page.expect_navigation():
        page.evaluate(
            "(accion) => { const f = document.querySelector('form.centro__form');"
            " f.requestSubmit(f.querySelector(`button[value=${accion}]`)); }",
            abrir,
        )
    assert page.locator("[role=alert]").first.is_visible()
    revisar(page, nombre)


# --- HU-05-04 · Anotar quién come (el estudiante encargado, B60 y B61) ------------------


@pytest.fixture
def encargado(datos, page, live_server, client, monkeypatch):
    """Hugo es hoy (un día lectivo) el encargado del comedor y ya ha marcado a alguno."""
    from apps.centro import comedor

    hoy = timezone.localdate()
    dia = next(hoy + timedelta(days=n) for n in range(7) if (hoy + timedelta(days=n)).weekday() < 5)
    monkeypatch.setattr(servicios, "hoy", lambda: dia)
    admin = Usuario.objects.get(username="admin")
    hugo = Estudiante.objects.select_related("usuario").get(codigo_estudiante="A04")
    servicios.asignar_comedor(dia, hugo, time(13), time(14), admin)
    comedor.marcar(hugo, Estudiante.objects.get(codigo_estudiante="A01"), True)
    comedor.marcar(hugo, Estudiante.objects.get(codigo_estudiante="A02"), False)
    client.force_login(hugo.usuario)
    page.context.add_cookies(
        [{"name": "sessionid", "value": client.cookies["sessionid"].value, "url": live_server.url}]
    )
    return hugo


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_anotar_quien_come_clases(live_server, page, encargado, nombre):
    page.set_viewport_size(dict(zip(("width", "height"), RESOLUCIONES[nombre], strict=True)))
    page.goto(f"{live_server.url}{reverse('centro:comedor_hoy')}")
    revisar(page, nombre)


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_anotar_quien_come_companeros(live_server, page, encargado, nombre):
    """B61, también tras tocar a un compañero (HTMX) y al intentar terminar sin marcar a todos."""
    from apps.usuarios.models import Clase

    page.set_viewport_size(dict(zip(("width", "height"), RESOLUCIONES[nombre], strict=True)))
    clase = Clase.objects.get(nombre="PTVAL 1")
    page.goto(f"{live_server.url}{reverse('centro:comedor_clase', args=[clase.pk])}")
    revisar(page, nombre)

    boton = page.locator("form[data-marcar] button").first
    boton.focus()
    with page.expect_response(lambda r: "/marcar/" in r.url):
        page.keyboard.press("Enter")
    page.wait_for_timeout(300)
    assert page.evaluate("document.activeElement.closest('form[data-marcar]') !== null")
    revisar(page, nombre)

    with page.expect_navigation():
        page.get_by_role("button", name="Clase terminada").click(force=True)
    assert page.locator("[role=alert]").first.is_visible()
    revisar(page, nombre)


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_anotar_quien_come_todas_terminadas(live_server, page, encargado, nombre):
    """B60 al acabar: «Volver a la tarea» pasa a ser el botón grande del pie."""
    from apps.centro import comedor

    for clase in comedor.clases_del_centro():
        for e in Estudiante.objects.filter(clase=clase, usuario__is_active=True):
            comedor.marcar(encargado, e, True)
        comedor.terminar_clase(encargado, clase)
    page.set_viewport_size(dict(zip(("width", "height"), RESOLUCIONES[nombre], strict=True)))
    page.goto(f"{live_server.url}{reverse('centro:comedor_hoy')}")
    assert page.get_by_role("link", name="Volver a la tarea", exact=True).is_visible()
    revisar(page, nombre)
