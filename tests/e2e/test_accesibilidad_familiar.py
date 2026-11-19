"""HU-06-03 · Día del estudiante para el familiar (B34 y B35) en el navegador.

axe WCAG 2.2 AA, sin desplazarse (decisión 0005) y con el teclado, con el comedor anotado
y el menú del mes subido como imagen. Mismas resoluciones que el resto.
Se lanzan con:  pytest -m e2e
"""

import io

import pytest
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.usuarios.models import Usuario
from tests.e2e.test_accesibilidad_usuarios import RESOLUCIONES, con_sesion, revisar
from tests.test_seguimiento_dia_familiar import anotar, dia_lectivo, lucia, subir_menu

pytestmark = pytest.mark.e2e


def imagen_menu():
    """Un menú de tamaño real (A4 vertical), para ver que cabe sin desplazarse."""
    salida = io.BytesIO()
    Image.new("RGB", (800, 1130), "#FFFFFF").save(salida, format="PNG")
    return salida.getvalue()


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_dia_del_estudiante(live_server, page, client, datos, nombre):
    dia = dia_lectivo()
    anotar(lucia(), dia, come=True)
    subir_menu(dia)
    # El servidor de pruebas no sirve /media/: el navegador recibe una imagen de verdad.
    png = imagen_menu()
    page.route("**/media/**", lambda ruta: ruta.fulfill(body=png, content_type="image/png"))

    con_sesion(page, live_server, client, Usuario.objects.get(username="familiar"))
    page.set_viewport_size(dict(zip(("width", "height"), RESOLUCIONES[nombre], strict=True)))
    page.goto(live_server.url + reverse("usuarios:panel"))
    page.evaluate("document.fonts.ready.then(() => true)")
    revisar(page, nombre)

    # Desde «Tus estudiantes», con el teclado, se abre el día de Lucía.
    enlace = page.locator("a.panel__estudiante--enlace", has_text="Lucía")
    enlace.focus()
    page.keyboard.press("Enter")
    page.wait_for_url(f"**{reverse('seguimiento:dia', args=['A01'])}")
    url = f"{live_server.url}{reverse('seguimiento:dia', args=['A01'])}?dia={dia.isoformat()}"
    if dia != timezone.localdate():
        page.goto(url)
    page.evaluate("document.fonts.ready.then(() => true)")
    assert "Solo consulta" in page.content()
    revisar(page, nombre)
    main = page.locator("main")
    assert main.evaluate("m => m.scrollHeight <= m.clientHeight + 1")

    # Si las dos partes no caben a la vez, el paginador lleva a «Comedor y menú».
    comedor = page.locator(".dia-comedor")
    if not comedor.is_visible():
        page.locator("[data-paginador=partes] [data-pag='1']").click()
    assert "Lucía ha ido al comedor." in comedor.inner_text()
    assert comedor.get_by_role("link", name="Ver el menú en grande").is_visible()
    revisar(page, nombre)
    assert main.evaluate("m => m.scrollHeight <= m.clientHeight + 1")
