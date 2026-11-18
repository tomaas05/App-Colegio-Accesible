"""Accesibilidad de las pantallas de gestión de tareas (HU-03-01, HU-03-03 a HU-03-06 y HU-03-08).

axe WCAG 2.2 AA, sin scroll horizontal y sin scroll vertical (decisión 0005) en móvil,
tableta y ordenador, entrando como la tutora Ana o como un profesional con datos de prueba.
"""

from datetime import date, time, timedelta

import pytest
from axe_playwright_python.sync_playwright import Axe
from django.urls import reverse
from django.utils import timezone

from apps.comun.models import TipoAviso, avisar
from apps.tareas.models import Ambito, Asignacion, DiaSemana, Tarea
from apps.usuarios.models import Atencion, Estudiante, Usuario
from tests.e2e.ayudas import ir_a

pytestmark = pytest.mark.e2e

RESOLUCIONES = {
    "movil-vertical": (360, 640),
    "tablet-vertical": (768, 1024),
    "tablet-horizontal": (1280, 800),
    "ordenador": (1366, 768),
}
ETIQUETAS_WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]


def _regar():
    return Asignacion.objects.get(
        estudiante__codigo_estudiante="A01", tarea__nombre="Regar las plantas"
    )


def _manana():
    return (timezone.localdate() + timedelta(days=1)).isoformat()


# Cada pantalla: nombre → ruta (se calcula con los datos de prueba ya cargados).
PANTALLAS = {
    "crear": lambda: reverse("tareas:crear_tarea"),
    "asignar": lambda: reverse("tareas:asignar_tarea"),
    "catalogo": lambda: reverse("tareas:catalogo"),
    "planificadas": lambda: reverse("tareas:tareas_planificadas"),
    "planificadas-un-dia": lambda: reverse("tareas:tareas_planificadas") + f"?fecha={_manana()}",
    "editar-serie": lambda: reverse("tareas:editar_asignacion", args=[_regar().pk]),
    "editar-dia": lambda: (
        reverse("tareas:editar_asignacion", args=[_regar().pk]) + f"?alcance=dia&fecha={_manana()}"
    ),
    "cancelar-serie": lambda: reverse("tareas:confirmar_cancelacion", args=[_regar().pk]),
    "cancelar-dia": lambda: (
        reverse("tareas:confirmar_cancelacion", args=[_regar().pk])
        + f"?alcance=dia&fecha={_manana()}"
    ),
    "plan-b": lambda: reverse("tareas:plan_b", args=[_regar().tarea_id]),
    "pasos": lambda: reverse("tareas:editar_pasos_tarea", args=[_regar().tarea_id]),  # HU-03-02
}

# Pantallas de prueba para el rol profesional (HU-03-08)
PANTALLAS_PROFESIONAL = [
    "/tareas/crear/",
    "/tareas/asignar/",
    "/tareas/asignaciones/2/editar/",
    "/tareas/asignaciones/2/cancelar/",
    "/tareas/2/pasos/",
]


def entrar(page, live_server, client, usuario):
    client.force_login(usuario)
    page.context.add_cookies(
        [{"name": "sessionid", "value": client.cookies["sessionid"].value, "url": live_server.url}]
    )


@pytest.fixture
def tutor_logueado(live_server, page, client, datos):
    tutor = Usuario.objects.get(username="tutor")
    entrar(page, live_server, client, tutor)
    return tutor


@pytest.fixture
def profesional_logueado(live_server, page, client, datos):
    """Fixture para realizar pruebas E2E con el rol Profesional (HU-03-08)."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    profesional, _ = Usuario.objects.get_or_create(
        username="profesional",
        defaults={"first_name": "Luis", "last_name": "Navarro", "rol": "profesional"},
    )
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    Atencion.objects.get_or_create(profesional=profesional, estudiante=lucia)

    # Creamos una imagen simulada para evitar el error de archivo no asociado
    imagen_falsa = SimpleUploadedFile(
        "profesional.png", b"contenido_falso", content_type="image/png"
    )

    tarea, _ = Tarea.objects.get_or_create(
        id=2,
        defaults={
            "nombre": "Tarea Profesional E2E",
            "descripcion_imagen": "Icono profesional",
            "imagen": imagen_falsa,
            "creador": profesional,
            "ambito": Ambito.ESCOLAR,
        },
    )
    Asignacion.objects.get_or_create(
        id=2,
        defaults={
            "tarea": tarea,
            "estudiante": lucia,
            "asignado_por": profesional,
            "hora_inicio": time(11, 0),
            "hora_fin": time(11, 15),
            "dias_semana": [DiaSemana.MIERCOLES],
            "vigencia_desde": date(2026, 1, 1),
        },
    )

    entrar(page, live_server, client, profesional)
    return profesional


def sin_errores_axe(page):
    resultado = Axe().run(page, options={"runOnly": {"type": "tag", "values": ETIQUETAS_WCAG}})
    assert resultado.violations_count == 0, resultado.generate_report()


def sin_scroll(page, nombre, ancho, alto):
    medida = page.evaluate(
        "[document.documentElement.scrollWidth, document.documentElement.scrollHeight]"
    )
    assert medida[0] <= ancho, f"Scroll horizontal en {nombre}: {medida[0]}px"
    assert medida[1] <= alto, f"Scroll vertical en {nombre}: {medida[1]}px"


@pytest.mark.parametrize("pantalla", PANTALLAS)
@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_gestion_tareas_sin_errores_axe_ni_scroll(
    live_server, page, tutor_logueado, pantalla, nombre
):
    ancho, alto = RESOLUCIONES[nombre]
    page.set_viewport_size({"width": ancho, "height": alto})
    respuesta = page.goto(live_server.url + PANTALLAS[pantalla]())
    assert respuesta.status == 200
    page.wait_for_timeout(200)
    sin_errores_axe(page)
    sin_scroll(page, f"{pantalla} a {nombre}", ancho, alto)


@pytest.mark.parametrize("ruta", PANTALLAS_PROFESIONAL)
@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_gestion_tareas_profesional_sin_errores_axe_ni_scroll(
    live_server, page, profesional_logueado, ruta, nombre
):
    """Valida WCAG y ausencia de scroll para las pantallas del rol profesional (HU-03-08)."""
    ancho, alto = RESOLUCIONES[nombre]
    page.set_viewport_size({"width": ancho, "height": alto})
    respuesta = page.goto(live_server.url + ruta)
    assert respuesta.status == 200
    page.wait_for_timeout(200)
    sin_errores_axe(page)
    sin_scroll(page, f"profesional {ruta} a {nombre}", ancho, alto)


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_el_aviso_de_un_cambio_al_estudiante(live_server, page, client, datos, nombre):
    """HU-03-04 y HU-03-05: el aviso, uno por pantalla, con pictograma y «Entendido»."""
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    regar = _regar()
    avisar(
        lucia.usuario,
        "«Regar las plantas» se ha cancelado. Ya no la tienes que hacer.",
        tipo=TipoAviso.CANCELACION,
        tarea=regar.tarea,
    )
    avisar(lucia.usuario, "«Leer un cuento» cambia: ahora es de 17:30 a 18:00, todos los días.")
    entrar(page, live_server, client, lucia.usuario)
    ancho, alto = RESOLUCIONES[nombre]
    page.set_viewport_size({"width": ancho, "height": alto})
    page.goto(live_server.url + reverse("agenda:dia"))
    page.get_by_text("Ya no la tienes que hacer.").wait_for()
    sin_errores_axe(page)
    sin_scroll(page, f"aviso a {nombre}", ancho, alto)

    page.get_by_role("button", name="Entendido").click()
    page.get_by_text("«Leer un cuento» cambia").wait_for()
    page.get_by_role("button", name="Entendido").click()
    page.get_by_role("heading", name="Tareas de hoy").wait_for()


def test_plan_b_ordenar_con_teclado_y_el_foco_vuelve_al_boton(live_server, page, tutor_logueado):
    """B42: «Subir» recarga la página y el foco vuelve al mismo botón (no se pierde)."""
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto(live_server.url + PANTALLAS["plan-b"]())
    page.get_by_role("button", name="Subir «Leer un cuento»").click()
    page.get_by_text("«Leer un cuento» es ahora la número 1.").wait_for()
    enfocado = page.evaluate(
        "[document.activeElement.textContent, document.activeElement.getAttribute('aria-disabled')]"
    )
    assert enfocado == ["Subir «Leer un cuento»", "true"]
    regar = Tarea.objects.get(nombre="Regar las plantas")
    assert [a.nombre for a in regar.alternativas] == ["Leer un cuento", "Escuchar música"]


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

    ir_a(page, "#q-arasaac_id_tarea")
    page.focus("#q-arasaac_id_tarea")
    page.keyboard.type("perro")
    page.keyboard.press("Enter")
    estado = page.locator("#estado-arasaac_id_tarea")
    estado.get_by_text("2 pictogramas de «perro»").wait_for()
    assert estado.get_attribute("role") == "status"
    assert page.evaluate("document.activeElement.id") == "q-arasaac_id_tarea"
    assert page.url.endswith("/tareas/crear/")

    opcion = page.get_by_role("radio", name="perro guía")
    if not opcion.is_visible():
        page.locator(".pictos .siguiente, .pictos .paginador button").last.click()

    opcion.check(force=True)
    assert opcion.is_checked()
    assert page.input_value("#id_descripcion_imagen") == "perro guía"
    caja = page.locator("label.picto", has_text="perro guía").bounding_box()
    assert caja["width"] >= 48 and caja["height"] >= 48

    ir_a(page, "[data-anadir-paso]")
    page.get_by_role("button", name="Añadir paso").click()
    page.locator("[data-paso]").first.wait_for()
    assert page.evaluate("document.activeElement.tagName") in ["TEXTAREA", "INPUT", "BUTTON"]

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
    assert [u for u in pedidas if not u.startswith((live_server.url, "data:", "blob:"))] == []
