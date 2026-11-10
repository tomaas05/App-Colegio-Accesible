"""Accesibilidad de las pantallas de usuarios y acceso (Manu).

Misma comprobación que test_accesibilidad.py (axe WCAG 2.2 AA y sin scroll horizontal) para
las pantallas que no se ven sin más: la entrada de adultos con errores, el bloqueo, el panel
de cada rol (pide sesión) y la entrada del estudiante con datos de prueba (HU-01-06).
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


# --- HU-01-06 · Entrar como estudiante ---


def tamano(nombre):
    return dict(zip(("width", "height"), RESOLUCIONES[nombre], strict=True))


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_portada_clases_y_avatares(live_server, page, datos, nombre):
    """B01 · ¿Quién eres?, B02 · ¿Cuál es tu clase? y B03 · avatares de PTVAL 1."""
    page.set_viewport_size(tamano(nombre))
    page.goto(live_server.url + reverse("inicio"))
    revisar(page, nombre)
    page.click("text=Estudiante")
    revisar(page, nombre)
    page.click("text=PTVAL 1")
    assert page.locator(".loseta__nombre", has_text="Lucía").is_visible()
    revisar(page, nombre)


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_rejilla_de_imagenes_con_error(live_server, page, datos, nombre):
    """Rejilla de Lucía: sin elegir nada, con el aviso de error y con 3 elegidas."""
    page.set_viewport_size(tamano(nombre))
    page.goto(live_server.url + reverse("usuarios:entrar_estudiante", args=["A01"]))
    revisar(page, nombre)
    for palabra in ("perro", "sol", "gato"):
        page.locator("label.loseta--marcar", has_text=palabra).click()
    page.click("button[type=submit]")
    assert page.locator("[role=alert]").is_visible()
    revisar(page, nombre)


def test_rejilla_no_deja_marcar_una_cuarta_imagen(live_server, page, datos):
    page.goto(live_server.url + reverse("usuarios:entrar_estudiante", args=["A01"]))
    loseta = lambda palabra: page.locator("label.loseta--marcar", has_text=palabra)  # noqa: E731
    for palabra in ("perro", "sol", "flor"):
        loseta(palabra).click()
    assert page.locator("[data-contador-n]").inner_text() == "3"
    assert page.locator("input[name=imagenes]:disabled").count() == 9
    loseta("sol").click()  # quitar una vuelve a dejar elegir
    assert page.locator("input[name=imagenes]:disabled").count() == 0
    loseta("sol").click()
    page.click("button[type=submit]")
    page.wait_for_url("**/agenda/")


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_contrasena_del_estudiante(live_server, page, datos, nombre):
    """Mateo escribe su contraseña; con una equivocada sale el aviso."""
    page.set_viewport_size(tamano(nombre))
    page.goto(live_server.url + reverse("usuarios:entrar_estudiante", args=["A02"]))
    revisar(page, nombre)
    page.fill("#id_password", "no-es-esta")
    page.click("button[type=submit]")
    assert page.locator("[role=alert]").is_visible()
    revisar(page, nombre)


# --- HU-01-01 · Pantallas del administrador ---


def como_admin(page, live_server, client):
    con_sesion(page, live_server, client, Usuario.objects.get(username="admin"))


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_lista_de_usuarios(live_server, page, client, datos, nombre):
    """B20 · Usuarios, con la tabla y los filtros."""
    como_admin(page, live_server, client)
    page.set_viewport_size(tamano(nombre))
    page.goto(live_server.url + reverse("usuarios:lista"))
    revisar(page, nombre)


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_crear_cuenta_con_errores_y_por_rol(live_server, page, client, datos, nombre):
    """B21 · Crear cuenta: vacía con errores, y con las secciones de estudiante y de adulto."""
    como_admin(page, live_server, client)
    page.set_viewport_size(tamano(nombre))
    page.goto(live_server.url + reverse("usuarios:crear"))
    page.click("main form button[type=submit]")
    assert page.locator("[role=alert]").is_visible()
    revisar(page, nombre)

    page.select_option("#id_rol", "estudiante")
    assert page.locator('[data-solo="estudiante"]').is_visible()
    assert not page.locator('[data-solo="adulto"]').is_visible()
    revisar(page, nombre)

    page.select_option("#id_rol", "tutor")
    assert page.locator('[data-solo="adulto"]').is_visible()
    assert not page.locator('[data-solo="estudiante"]').is_visible()
    revisar(page, nombre)


def test_crear_un_estudiante_desde_el_navegador(live_server, page, client, datos):
    """El recorrido completo con JavaScript: rol, clase, 3 imágenes y crear."""
    como_admin(page, live_server, client)
    page.goto(live_server.url + reverse("usuarios:crear"))
    page.select_option("#id_rol", "estudiante")
    page.fill("#id_nombre", "Noa")
    page.select_option("#id_clase", label="PTVAL 1 (2026-2027)")
    for palabra in ("luna", "pez", "casa"):
        page.locator("label.loseta--marcar", has_text=palabra).click()
    page.click("main form button[type=submit]")
    page.wait_for_url("**/usuarios/?clase=*")
    assert "Cuenta creada: Noa" in page.content()


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_cargar_lista_con_resultado(live_server, page, client, datos, nombre, tmp_path):
    """Cargar una lista: el resultado con una fila buena y una mala."""
    como_admin(page, live_server, client)
    archivo = tmp_path / "lista.csv"
    archivo.write_text(
        "nombre;apellidos;imagenes;contrasena\nIris;Sol;gato luna pez;\nMal;Uno;perro;\n",
        encoding="utf-8",
    )
    page.set_viewport_size(tamano(nombre))
    page.goto(live_server.url + reverse("usuarios:cargar"))
    revisar(page, nombre)
    page.select_option("#id_clase", label="PTVAL 1 (2026-2027)")
    page.set_input_files("#id_archivo", str(archivo))
    page.click("main form button[type=submit]")
    assert "Se ha creado 1 cuenta" in page.content()
    revisar(page, nombre)


# --- HU-01-04 · Vínculos (B25) y «Tus estudiantes» en el panel ---


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_vinculos_con_el_aviso_de_un_segundo_familiar(live_server, page, client, datos, nombre):
    """B25 con Lucía elegida, el aviso de cambio de tutor y el error de un segundo familiar."""
    como_admin(page, live_server, client)
    page.set_viewport_size(tamano(nombre))
    page.goto(live_server.url + reverse("usuarios:vinculos"))
    revisar(page, nombre)
    page.goto(live_server.url + reverse("usuarios:vinculos") + "?estudiante=A01")
    revisar(page, nombre)

    page.select_option("#id_tutor", label="Pedro Gómez Sanz")
    aviso = page.locator("[data-aviso-tutor]")
    assert aviso.is_visible()
    assert "de Ana Martín Ruiz a Pedro Gómez Sanz" in aviso.inner_text()
    revisar(page, nombre)

    page.select_option("#id_nuevo_familiar", label="Javier Ortega Ramos")
    page.click("button[value=anadir]")
    assert page.locator("[role=alert]").is_visible()
    assert "Solo puede tener uno" in page.content()
    revisar(page, nombre)


def test_vinculos_buscar_filtra_la_lista_sin_recargar(live_server, page, client, datos):
    como_admin(page, live_server, client)
    page.goto(live_server.url + reverse("usuarios:vinculos"))
    page.fill("#vinculos-q", "pablo")
    opciones = page.locator("#vinculos-est option")
    assert opciones.count() == 1
    assert opciones.first.inner_text() == "Pablo Díaz"
    page.fill("#vinculos-q", "nadie")
    assert page.locator("#vinculos-est option").first.inner_text() == "Ningún estudiante coincide"
    page.fill("#vinculos-q", "lucia")  # sin tilde también la encuentra
    page.click("text=Ver sus vínculos")
    assert page.locator("h2", has_text="Lucía Fernández").is_visible()


def test_vinculos_cambiar_familiar_y_guardar(live_server, page, client, datos):
    """El recorrido completo: quitar a Carmen, añadir a Javier y guardar."""
    como_admin(page, live_server, client)
    page.goto(live_server.url + reverse("usuarios:vinculos") + "?estudiante=A01")
    page.click("button[value=quitar]")
    assert page.locator("text=Hay cambios sin guardar").is_visible()
    page.select_option("#id_nuevo_familiar", label="Javier Ortega Ramos")
    page.click("button[value=anadir]")
    page.click("button[value=guardar]")
    assert "Vínculos de Lucía Fernández guardados." in page.content()
    assert page.locator(".vinculos__persona", has_text="Javier Ortega Ramos").is_visible()
