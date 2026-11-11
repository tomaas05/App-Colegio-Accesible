"""Accesibilidad de la estructura común (decisión 0003): cabecera, panel lateral y pie.

axe (WCAG 2.2 AA) y sin scroll horizontal con el panel cerrado y abierto, en móvil,
tableta y ordenador, también con letra de 32 px; y el recorrido con teclado.
Se lanzan con:  pytest -m e2e
"""

import pytest
from axe_playwright_python.sync_playwright import Axe
from django.urls import reverse

from apps.usuarios.models import Usuario

pytestmark = pytest.mark.e2e

# Los tamaños de la mejora de interfaz: primero móvil y tableta, después ordenador.
RESOLUCIONES = {
    "movil-vertical": (360, 640),
    "tablet-vertical": (768, 1024),
    "tablet-horizontal": (1024, 768),
    "ordenador": (1366, 768),
}
# A partir de 64rem (1024 px con letra normal) el panel lateral se ve siempre.
ESTRECHAS = ["movil-vertical", "tablet-vertical"]
ETIQUETAS_WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
LETRA_32 = "html { font-size: 32px !important; }"


def revisar(page, ancho):
    resultado = Axe().run(page, options={"runOnly": {"type": "tag", "values": ETIQUETAS_WCAG}})
    assert resultado.violations_count == 0, resultado.generate_report()
    ancho_documento = page.evaluate("document.documentElement.scrollWidth")
    assert ancho_documento <= ancho, f"Scroll horizontal: {ancho_documento}px en {ancho}px"


def abrir(page, live_server, client, usuario, nombre, ruta=None, letra_32=False):
    client.force_login(Usuario.objects.get(username=usuario))
    page.context.add_cookies(
        [{"name": "sessionid", "value": client.cookies["sessionid"].value, "url": live_server.url}]
    )
    ancho, alto = RESOLUCIONES[nombre]
    page.set_viewport_size({"width": ancho, "height": alto})
    page.goto(live_server.url + (ruta or reverse("usuarios:panel")))
    if letra_32:
        page.add_style_tag(content=LETRA_32)
    return ancho


@pytest.fixture
def page_letra_32(browser_type, browser_type_launch_args):
    """Un navegador con la letra por defecto a 32 px (ajuste del navegador, no CSS).

    Los puntos de corte están en rem y dependen de ese ajuste: con letra de 32 px,
    64rem son 2048 px y el panel lateral se pliega también en el ordenador.
    """
    argumentos = {**browser_type_launch_args}
    argumentos["args"] = [*argumentos.get("args", []), "--blink-settings=defaultFontSize=32"]
    navegador = browser_type.launch(**argumentos)
    yield navegador.new_page()
    navegador.close()


def comprobar_plegado(page, ancho):
    """Plegado: el botón «Menú» lo abre y lo cierra, y dice en qué estado está."""
    menu = page.get_by_role("button", name="Menú")
    lateral = page.locator("#lateral")
    assert menu.is_visible() and not lateral.is_visible()
    assert menu.get_attribute("aria-expanded") == "false"
    revisar(page, ancho)
    menu.click()
    assert menu.get_attribute("aria-expanded") == "true"
    assert lateral.is_visible()


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_panel_lateral_cerrado_y_abierto(live_server, page, client, datos, nombre):
    ancho = abrir(page, live_server, client, "tutor", nombre)
    lateral = page.locator("#lateral")
    if nombre in ESTRECHAS:
        comprobar_plegado(page, ancho)
    else:
        assert not page.get_by_role("button", name="Menú").is_visible()
    assert lateral.is_visible()
    assert lateral.get_by_role("link", name="Inicio").get_attribute("aria-current") == "page"
    revisar(page, ancho)


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_panel_lateral_con_letra_de_32_px(live_server, page_letra_32, client, datos, nombre):
    """Con letra de 32 px el panel se pliega en todos los tamaños: no quita sitio útil."""
    page = page_letra_32
    ancho = abrir(page, live_server, client, "tutor", nombre)
    assert page.evaluate("parseFloat(getComputedStyle(document.documentElement).fontSize)") == 32
    comprobar_plegado(page, ancho)
    revisar(page, ancho)


@pytest.mark.parametrize("nombre", ESTRECHAS)
def test_el_boton_menu_mide_48_px_y_tiene_texto(live_server, page, client, datos, nombre):
    abrir(page, live_server, client, "admin", nombre)
    caja = page.get_by_role("button", name="Menú").bounding_box()
    assert caja["width"] >= 48 and caja["height"] >= 48
    assert page.get_by_role("button", name="Menú").inner_text().strip() == "Menú"


def test_escape_cierra_el_panel_y_devuelve_el_foco(live_server, page, client, datos):
    abrir(page, live_server, client, "admin", "movil-vertical")
    menu = page.get_by_role("button", name="Menú")
    menu.focus()
    page.keyboard.press("Enter")
    assert page.locator("#lateral").is_visible()
    # No es un modal: el foco sigue hacia el panel, que va justo después de la cabecera.
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.textContent.trim()") == "Inicio"
    page.keyboard.press("Escape")
    assert not page.locator("#lateral").is_visible()
    assert menu.get_attribute("aria-expanded") == "false"
    assert page.evaluate("document.activeElement.hasAttribute('data-menu')")


def test_el_panel_no_atrapa_el_foco(live_server, page, client, datos):
    """Con el panel abierto, Tab sale de él y llega al contenido."""
    abrir(page, live_server, client, "admin", "movil-vertical")
    page.get_by_role("button", name="Menú").click()
    dentro_de_main = False
    for _ in range(15):
        page.keyboard.press("Tab")
        if page.evaluate("document.activeElement.closest('main') !== null"):
            dentro_de_main = True
            break
    assert dentro_de_main
    assert page.locator("#lateral").is_visible()  # sigue abierto: no se cierra solo


def test_recorrido_con_teclado_en_ordenador(live_server, page, client, datos):
    """Saltar al contenido → logotipo → panel lateral → «Salir» → contenido."""
    abrir(page, live_server, client, "tutor", "ordenador")
    recorrido = []
    for _ in range(8):
        page.keyboard.press("Tab")
        recorrido.append(
            page.evaluate(
                "(document.activeElement.textContent.trim() ||"
                " document.activeElement.querySelector('img')?.alt || '').replace(/\\s+/g, ' ')"
            )
        )
    assert recorrido[0] == "Saltar al contenido"
    assert recorrido[1] == "" or "Despega" in recorrido[1]
    assert recorrido[2:7] == [
        "Inicio",
        "Crear una tarea",
        "Tareas creadas",
        "Perfil visual",
        "Salir",
    ]
    # El primer Tab después de «Salir» ya está en el contenido.
    assert page.evaluate("document.activeElement.closest('main') !== null")


def test_el_logotipo_lleva_al_inicio_con_teclado(live_server, page, client, datos):
    abrir(page, live_server, client, "admin", "ordenador", ruta=reverse("usuarios:lista"))
    page.get_by_role("link", name="Despega, ir al inicio").focus()
    page.keyboard.press("Enter")
    page.wait_for_url("**" + reverse("usuarios:panel"))


def test_saltar_al_contenido_lleva_el_foco_a_main(live_server, page, client, datos):
    abrir(page, live_server, client, "tutor", "ordenador")
    page.keyboard.press("Tab")
    page.keyboard.press("Enter")
    assert page.evaluate("document.activeElement.id") == "contenido"


def test_sin_javascript_el_panel_se_ve_siempre(live_server, browser, client, datos):
    client.force_login(Usuario.objects.get(username="tutor"))
    contexto = browser.new_context(
        java_script_enabled=False, viewport={"width": 360, "height": 640}
    )
    contexto.add_cookies(
        [{"name": "sessionid", "value": client.cookies["sessionid"].value, "url": live_server.url}]
    )
    page = contexto.new_page()
    page.goto(live_server.url + reverse("usuarios:panel"))
    assert page.locator("#lateral").is_visible()
    assert not page.locator("[data-menu]").is_visible()
    assert page.locator("#lateral").get_by_role("button", name="Salir").is_visible()
    contexto.close()


@pytest.mark.parametrize("letra_32", [False, True], ids=["letra-normal", "letra-32"])
@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_el_estudiante_tiene_salir_y_no_tiene_panel(
    live_server, page, client, datos, nombre, letra_32
):
    ancho = abrir(
        page, live_server, client, "est-a01", nombre, ruta=reverse("agenda:dia"), letra_32=letra_32
    )
    assert page.locator("#lateral").count() == 0
    salir = page.locator("header").get_by_role("button", name="Salir")
    assert salir.is_visible()
    caja = salir.bounding_box()
    assert caja["width"] >= 48 and caja["height"] >= 48
    revisar(page, ancho)


def test_ninguna_peticion_a_terceros(live_server, page, client, datos):
    """RNF1.1.2: el navegador solo habla con nuestro servidor."""
    pedidas = []
    page.on("request", lambda peticion: pedidas.append(peticion.url))
    abrir(page, live_server, client, "tutor", "ordenador")
    page.wait_for_load_state("networkidle")
    fuera = [u for u in pedidas if not u.startswith(live_server.url) and not u.startswith("data:")]
    assert fuera == []
