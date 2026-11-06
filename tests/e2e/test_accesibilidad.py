"""Pruebas de accesibilidad en navegador (Playwright + axe-core).

Se lanzan con:  pytest -m e2e
Requisitos: RNF4.1.1 (WCAG 2.2 AA sin errores en axe) y RNF4.2.1 (sin
desplazamiento horizontal a 360×640, 1280×800 y 1366×768).

Cada pantalla nueva debe añadirse a PANTALLAS.
"""

import pytest
from axe_playwright_python.sync_playwright import Axe

pytestmark = pytest.mark.e2e

RESOLUCIONES = {
    "movil-vertical": (360, 640),
    "tablet-horizontal": (1280, 800),
    "ordenador": (1366, 768),
}

PANTALLAS = [
    "/",
]

ETIQUETAS_WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]


@pytest.mark.parametrize("ruta", PANTALLAS)
@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_sin_errores_axe_ni_scroll_horizontal(live_server, page, ruta, nombre):
    ancho, alto = RESOLUCIONES[nombre]
    page.set_viewport_size({"width": ancho, "height": alto})
    page.goto(live_server.url + ruta)

    resultado = Axe().run(page, options={"runOnly": {"type": "tag", "values": ETIQUETAS_WCAG}})
    assert resultado.violations_count == 0, resultado.generate_report()

    ancho_documento = page.evaluate("document.documentElement.scrollWidth")
    assert ancho_documento <= ancho, f"Scroll horizontal en {nombre}: {ancho_documento}px"
