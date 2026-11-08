"""HU-02-05 Seguir los pasos de una tarea: accesibilidad en navegador (AGENDA-187).

La pantalla es la de la tarea (B07), ya revisada en test_accesibilidad_agenda.py antes de
empezar. Aquí se revisa con la tarea en marcha, que es cuando aparecen el paso destacado
y su botón «Hecho», y se comprueba que se puede seguir con teclado y sin JavaScript.
Se lanzan con:  pytest -m e2e
"""

from datetime import datetime, time

import pytest
from axe_playwright_python.sync_playwright import Axe
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios
from apps.usuarios.models import Estudiante

pytestmark = pytest.mark.e2e

RESOLUCIONES = {
    "movil-vertical": (360, 640),
    "tablet-horizontal": (1280, 800),
    "ordenador": (1366, 768),
}
ETIQUETAS_WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
PASOS_MOCHILA = ["Coger la agenda", "Meter el estuche", "Meter el almuerzo", "Cerrar la mochila"]


def a_las(hora, minuto=0):
    return timezone.make_aware(datetime.combine(timezone.localdate(), time(hora, minuto)))


def entrar(client, page, live_server, estudiante):
    client.force_login(estudiante.usuario)
    page.context.add_cookies(
        [{"name": "sessionid", "value": client.cookies["sessionid"].value, "url": live_server.url}]
    )


@pytest.fixture
def mochila(datos, page, live_server, client, monkeypatch):
    """Lucía, a las 9:05, con «Preparar la mochila» (4 pasos) empezada."""
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(9, 5))
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    entrar(client, page, live_server, lucia)
    asignacion = lucia.asignaciones.get(tarea__nombre="Preparar la mochila")
    servicios.empezar(lucia, asignacion.pk, a_las(9, 1))
    return asignacion


def url(live_server, asignacion):
    return live_server.url + reverse("agenda:detalle", args=[asignacion.pk])


def sin_errores_axe(page):
    resultado = Axe().run(page, options={"runOnly": {"type": "tag", "values": ETIQUETAS_WCAG}})
    assert resultado.violations_count == 0, resultado.generate_report()


def estados(asignacion):
    ejecucion = asignacion.ejecuciones.get(fecha=timezone.localdate())
    return list(ejecucion.pasos.order_by("paso__orden").values_list("estado", flat=True))


def boton_hecho(page, numero):
    return page.get_by_role("button", name=f"Hecho, paso {numero}", exact=True)


def es_el_foco(localizador):
    return localizador.evaluate("el => el === document.activeElement")


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_tarea_en_marcha_sin_errores_axe_ni_scroll_horizontal(live_server, page, mochila, nombre):
    servicios.marcar_paso_hecho(mochila.estudiante, mochila.pk, mochila.tarea.pasos.first().pk)
    ancho, alto = RESOLUCIONES[nombre]
    page.set_viewport_size({"width": ancho, "height": alto})
    page.goto(url(live_server, mochila))
    assert page.get_by_text("Paso 2 de 4").is_visible()

    sin_errores_axe(page)

    ancho_documento = page.evaluate("document.documentElement.scrollWidth")
    assert ancho_documento <= ancho, f"Scroll horizontal en {nombre}: {ancho_documento}px"
    caja = boton_hecho(page, 2).bounding_box()
    assert caja["width"] >= 44 and caja["height"] >= 44  # objetivo táctil (WCAG 2.5.8 y RNF)


def test_letra_mas_grande_sin_scroll_horizontal_en_movil(live_server, page, mochila):
    """RF4.1.2 permite letra de hasta 32 px (raíz al 200 %): «Hecho» sigue cabiendo."""
    page.set_viewport_size({"width": 360, "height": 640})
    page.goto(url(live_server, mochila))
    page.evaluate("document.documentElement.style.fontSize = '200%'")
    ancho_documento = page.evaluate("document.documentElement.scrollWidth")
    assert ancho_documento <= 360, f"Scroll horizontal con letra grande: {ancho_documento}px"


def test_seguir_todos_los_pasos_con_teclado(live_server, page, mochila):
    """Pruebas de aceptación 2 y 4 en el navegador, solo con teclado y sin recargar.

    Cada «Hecho» marca su paso, el foco pasa al «Hecho» del siguiente y, tras el último,
    a «Terminar», que abre «¿Has terminado?».
    """
    page.goto(url(live_server, mochila))
    page.evaluate("() => { window.misma_pagina = true; }")

    terminar = page.get_by_role("link", name="Terminar")
    for numero in range(1, 5):
        assert page.get_by_text(f"Paso {numero} de 4").is_visible()
        boton_hecho(page, numero).focus()
        page.keyboard.press("Enter")
        siguiente = boton_hecho(page, numero + 1) if numero < 4 else terminar
        siguiente.wait_for()
        assert es_el_foco(siguiente)
        assert estados(mochila) == ["hecho"] * numero + ["pendiente"] * (4 - numero)
        # Ningún paso posterior tiene botón: no se puede saltar ninguno (prueba 3).
        assert page.locator("[data-paso] button").count() == (1 if numero < 4 else 0)

    assert page.get_by_text("Todos los pasos hechos").is_visible()
    assert page.evaluate("() => window.misma_pagina === true")  # HTMX: no se ha recargado

    page.keyboard.press("Enter")
    dialogo = page.get_by_role("dialog", name="¿Has terminado?")
    assert dialogo.is_visible()
    sin_errores_axe(page)
    dialogo.get_by_role("button", name="Sí").click()
    page.get_by_text("¡Hecha!").wait_for()
    assert mochila.ejecuciones.get(fecha=timezone.localdate()).estado == "hecha"


def test_el_lector_anuncia_cuantos_pasos_faltan(live_server, page, mochila):
    """«Te faltan N pasos» está en una zona aria-live que se actualiza sin recargar."""
    page.goto(url(live_server, mochila))
    zona = page.locator(".zona-botones[aria-live='polite']")
    assert "faltan 4 pasos" in zona.inner_text()
    boton_hecho(page, 1).click()
    boton_hecho(page, 2).wait_for()
    assert "faltan 3 pasos" in zona.inner_text()


def test_sin_javascript_tambien_se_siguen_los_pasos(live_server, browser, client, mochila):
    """Sin JavaScript, «Hecho» es un formulario normal: recarga la página en los pasos."""
    contexto = browser.new_context(java_script_enabled=False)
    contexto.add_cookies(
        [{"name": "sessionid", "value": client.cookies["sessionid"].value, "url": live_server.url}]
    )
    pagina = contexto.new_page()
    pagina.goto(url(live_server, mochila))
    boton_hecho(pagina, 1).click()
    pagina.get_by_text("Paso 2 de 4").wait_for()
    assert pagina.url.endswith("#pasos")
    assert estados(mochila) == ["hecho", "pendiente", "pendiente", "pendiente"]
    contexto.close()
