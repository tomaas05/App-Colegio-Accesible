"""Accesibilidad de las pantallas de usuarios y acceso (Manu).

Misma comprobación que test_accesibilidad.py (axe WCAG 2.2 AA y sin scroll horizontal) para
las pantallas que no se ven sin más: la entrada con errores, el bloqueo y el panel de cada
rol, que pide sesión.
Se lanzan con:  pytest -m e2e
"""

import pytest
from axe_playwright_python.sync_playwright import Axe
from django.urls import reverse

from apps.usuarios.models import Usuario

pytestmark = pytest.mark.e2e

RESOLUCIONES = {
    "movil-vertical": (360, 640),
    "tablet-horizontal": (1280, 800),
    "ordenador": (1366, 768),
}
ETIQUETAS_WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]


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


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_entrar_con_errores(live_server, page, datos, nombre):
    """B12 con los mensajes de error a la vista (campos vacíos y datos que no coinciden)."""
    page.set_viewport_size(dict(zip(("width", "height"), RESOLUCIONES[nombre], strict=True)))
    page.goto(live_server.url + reverse("usuarios:entrar"))
    page.click("button[type=submit]")
    revisar(page, nombre)
    page.fill("#id_username", "tutor")
    page.fill("#id_password", "no-es-esta")
    page.click("button[type=submit]")
    assert page.locator("[role=alert]").is_visible()
    revisar(page, nombre)


@pytest.mark.parametrize("rol", ["admin", "tutor", "profesional", "familiar"])
@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_panel_de_cada_rol(live_server, page, client, datos, rol, nombre):
    """B13 · Panel."""
    con_sesion(page, live_server, client, Usuario.objects.get(username=rol))
    page.set_viewport_size(dict(zip(("width", "height"), RESOLUCIONES[nombre], strict=True)))
    page.goto(live_server.url + reverse("usuarios:panel"))
    revisar(page, nombre)


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_bloqueo(live_server, page, settings, datos, nombre):
    """Pantalla de axes tras 5 fallos (HU-01-07, PA5)."""
    settings.AXES_ENABLED = True
    page.set_viewport_size(dict(zip(("width", "height"), RESOLUCIONES[nombre], strict=True)))
    page.goto(live_server.url + reverse("usuarios:entrar"))
    for _ in range(5):
        page.fill("#id_username", "tutor")
        page.fill("#id_password", "no-es-esta")
        page.click("button[type=submit]")
    assert "Espera 5 minutos" in page.content()
    revisar(page, nombre)
