"""Accesibilidad de las pantallas de gestión de tareas (HU-03-01 y HU-03-03 - Úrsula).

Comprobación axe WCAG 2.2 AA y sin scroll horizontal para diferentes resoluciones,
iniciando sesión previamente como usuario tutor.
"""

import pytest
from axe_playwright_python.sync_playwright import Axe

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
        defaults={"first_name": "Úrsula", "last_name": "Tutor", "rol": "tutor"},
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
def test_gestion_tareas_sin_errores_axe_ni_scroll_horizontal(
    live_server, page, tutor_logueado, ruta, nombre
):
    ancho, alto = RESOLUCIONES[nombre]
    page.set_viewport_size({"width": ancho, "height": alto})
    page.goto(live_server.url + ruta)

    # Validamos que cumple estrictamente con el nivel WCAG 2.2 AA
    sin_errores_axe(page)

    # Validamos que no genera desplazamiento horizontal en dispositivos móviles o tablets
    ancho_documento = page.evaluate("document.documentElement.scrollWidth")
    assert ancho_documento <= ancho, f"Scroll horizontal en {nombre} ({ruta}): {ancho_documento}px"


# --- Buscador de pictogramas (decisión 0004) ---------------------------------------


@pytest.mark.parametrize("ancho, alto", [(360, 640), (768, 1024), (1366, 768)])
def test_buscador_de_pictogramas_con_resultados_y_un_paso(
    live_server, page, client, datos, arasaac, ancho, alto
):
    """Estado nuevo: resultados a la vista, uno elegido y un paso añadido. Con axe."""
    from axe_playwright_python.sync_playwright import Axe

    from apps.usuarios.models import Usuario

    client.force_login(Usuario.objects.get(username="tutor"))
    page.context.add_cookies(
        [{"name": "sessionid", "value": client.cookies["sessionid"].value, "url": live_server.url}]
    )
    pedidas = []
    page.on("request", lambda peticion: pedidas.append(peticion.url))
    page.set_viewport_size({"width": ancho, "height": alto})
    page.goto(live_server.url + "/tareas/crear/")

    # Con teclado: escribir, Intro busca (no envía el formulario) y el foco no se pierde.
    page.focus("#q-arasaac_id_tarea")
    page.keyboard.type("perro")
    page.keyboard.press("Enter")
    estado = page.locator("#estado-arasaac_id_tarea")
    estado.get_by_text("2 pictogramas de «perro»").wait_for()
    assert estado.get_attribute("role") == "status"
    assert page.evaluate("document.activeElement.id") == "q-arasaac_id_tarea"
    assert page.url.endswith("/tareas/crear/")

    # Cada pictograma es un botón de opción con su palabra como nombre accesible.
    opcion = page.get_by_role("radio", name="perro guía")
    opcion.check(force=True)
    assert opcion.is_checked()
    assert page.input_value("#id_descripcion_imagen") == "perro guía"
    caja = page.locator("label.picto", has_text="perro guía").bounding_box()
    assert caja["width"] >= 48 and caja["height"] >= 48

    page.get_by_role("button", name="Añadir paso").click()
    page.get_by_text("Paso 1 añadido.").wait_for()
    assert page.evaluate("document.activeElement.name") == "pasos-0-descripcion"

    resultado = Axe().run(
        page,
        options={
            "runOnly": {
                "type": "tag",
                "values": ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"],
            }
        },
    )
    assert resultado.violations_count == 0, resultado.generate_report()
    assert page.evaluate("document.documentElement.scrollWidth") <= ancho
    # RNF1.1.2: el navegador solo ha hablado con nuestro servidor.
    assert [u for u in pedidas if not u.startswith((live_server.url, "data:", "blob:"))] == []
