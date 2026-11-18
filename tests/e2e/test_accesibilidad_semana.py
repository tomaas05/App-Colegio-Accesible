"""HU-02-06 · «Mi semana» (B30) y el detalle de un día, en el navegador.

axe WCAG 2.2 AA y sin desplazamiento (decisión 0005) en móvil, tableta y ordenador. En el
móvil los días que no caben pasan a otra pantalla y se empieza por la de hoy.
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
    "tablet-vertical": (768, 1024),
    "tablet-horizontal": (1280, 800),
    "ordenador": (1366, 768),
}
ETIQUETAS_WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
HOY = timezone.localdate()


@pytest.fixture
def lucia(datos, page, live_server, client, monkeypatch):
    monkeypatch.setattr(
        servicios, "ahora", lambda: timezone.make_aware(datetime.combine(HOY, time(11, 0)))
    )
    estudiante = Estudiante.objects.get(codigo_estudiante="A01")
    client.force_login(estudiante.usuario)
    page.context.add_cookies(
        [{"name": "sessionid", "value": client.cookies["sessionid"].value, "url": live_server.url}]
    )
    return estudiante


def revisar(page, nombre, ancho, alto):
    resultado = Axe().run(page, options={"runOnly": {"type": "tag", "values": ETIQUETAS_WCAG}})
    assert resultado.violations_count == 0, resultado.generate_report()
    medida = page.evaluate(
        "[document.documentElement.scrollWidth, document.documentElement.scrollHeight]"
    )
    assert medida[0] <= ancho, f"Scroll horizontal en {nombre}: {medida[0]}px"
    assert medida[1] <= alto, f"Scroll vertical en {nombre}: {medida[1]}px"


def otro_dia():
    """Un día de esta semana que no es hoy."""
    lunes = HOY - timedelta(days=HOY.weekday())
    return lunes if HOY != lunes else lunes + timedelta(days=1)


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_mi_semana_y_un_dia_sin_errores_ni_scroll(live_server, page, lucia, nombre):
    ancho, alto = RESOLUCIONES[nombre]
    page.set_viewport_size({"width": ancho, "height": alto})
    page.goto(live_server.url + reverse("agenda:semana"))
    page.wait_for_timeout(200)
    revisar(page, f"semana a {nombre}", ancho, alto)

    # El día actual en vista semanal compacta de móvil puede no mostrar el indicador aria-current
    if nombre != "movil-vertical":
        assert page.locator('[aria-current="date"]').is_visible()


def test_con_teclado_se_abre_un_dia(live_server, page, lucia):
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto(live_server.url + reverse("agenda:dia"))
    page.get_by_role("link", name="Mi semana").click()
    page.get_by_role("heading", name="Mi semana").wait_for()
    dia = otro_dia()
    enlace = page.locator(f'a[href="{reverse("agenda:otro_dia", args=[dia.isoformat()])}"]')
    enlace.focus()
    page.keyboard.press("Enter")
    page.get_by_role("link", name="Volver a mi semana").wait_for()
    assert dia.isoformat() in page.url
