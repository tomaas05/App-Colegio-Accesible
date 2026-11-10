"""Accesibilidad de las pantallas de perfil visual (Jorge, HU-04-01).

Comprueba con axe-core (WCAG 2.2 AA) y ausencia de scroll horizontal:
- La lista (/perfil/) y el formulario B52 (/perfil/A01/) en las 3 resoluciones.
- La agenda del estudiante con cada combinación de tema y paleta (PA4).
Se lanzan con:  pytest -m e2e
"""

import pytest
from axe_playwright_python.sync_playwright import Axe
from django.urls import reverse

from apps.perfil.models import Paleta, Tema
from apps.usuarios.models import Estudiante, Usuario

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
    """PA4 en navegador real: axe comprueba el contraste >= 4,5:1 en cada combinación."""
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    perfil = lucia.perfil
    perfil.tema = tema
    perfil.paleta = paleta
    perfil.save()

    con_sesion(page, live_server, client, lucia.usuario)
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto(live_server.url + reverse("agenda:dia"))
    revisar(page, "tablet-horizontal")
