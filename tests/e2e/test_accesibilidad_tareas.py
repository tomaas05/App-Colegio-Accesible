"""Accesibilidad de las pantallas de gestión de tareas (HU-03-01 y HU-03-03 - Úrsula).

Comprobación axe WCAG 2.2 AA y sin scroll horizontal para diferentes resoluciones,
iniciando sesión previamente como usuario tutor.
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

# Rutas de las pantallas de creación y asignación de tareas
PANTALLAS = [
    "/tareas/crear/",
    "/tareas/asignar/",
]


@pytest.fixture
def tutor_logueado(live_server, page, client):
    # Creamos o recuperamos un usuario con rol de tutor para las pruebas E2E
    tutor, _ = Usuario.objects.get_or_create(
        username="tutor_gestion_e2e",
        defaults={"first_name": "Úrsula", "last_name": "Tutor", "rol": "tutor"}
    )
    tutor.set_password("despega2026")
    tutor.save()

    client.force_login(tutor)
    page.context.add_cookies(
        [{"name": "sessionid", "value": client.cookies["sessionid"].value, "url": live_server.url}]
    )
    return tutor


def sin_errores_axe(page):
    resultado = Axe().run(page, options={"runOnly": {"type": "tag", "values": ETIQUETAS_WCAG}})
    assert resultado.violations_count == 0, resultado.generate_report()


@pytest.mark.parametrize("ruta", PANTALLAS)
@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_gestion_tareas_sin_errores_axe_ni_scroll_horizontal(live_server, page, tutor_logueado, ruta, nombre):
    ancho, alto = RESOLUCIONES[nombre]
    page.set_viewport_size({"width": ancho, "height": alto})
    page.goto(live_server.url + ruta)

    # Validamos que cumple estrictamente con el nivel WCAG 2.2 AA
    sin_errores_axe(page)

    # Validamos que no genera desplazamiento horizontal en dispositivos móviles o tablets
    ancho_documento = page.evaluate("document.documentElement.scrollWidth")
    assert ancho_documento <= ancho, f"Scroll horizontal en {nombre} ({ruta}): {ancho_documento}px"
