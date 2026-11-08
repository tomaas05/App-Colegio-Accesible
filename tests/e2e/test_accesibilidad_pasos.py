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
# Tras mover el foco, agenda.js ignora «Hecho» y «Terminar» durante 500 ms (pulsación larga).
TRAS_LA_ESPERA_MS = 600
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
    a «Terminar», que abre «¿Has terminado?». Entre pulsación y pulsación se deja pasar
    la espera de agenda.js, como haría una persona.
    """
    page.goto(url(live_server, mochila))
    page.evaluate("() => { window.misma_pagina = true; }")

    terminar = page.get_by_role("link", name="Terminar")
    for numero in range(1, 5):
        assert page.get_by_text(f"Paso {numero} de 4").is_visible()
        boton_hecho(page, numero).focus()
        page.wait_for_timeout(TRAS_LA_ESPERA_MS)
        page.keyboard.press("Enter")
        siguiente = boton_hecho(page, numero + 1) if numero < 4 else terminar
        siguiente.wait_for()
        assert es_el_foco(siguiente)
        assert estados(mochila) == ["hecho"] * numero + ["pendiente"] * (4 - numero)
        # Ningún paso posterior tiene botón: no se puede saltar ninguno (prueba 3).
        assert page.locator("[data-paso] button").count() == (1 if numero < 4 else 0)

    assert page.get_by_text("Todos los pasos hechos").is_visible()
    assert page.evaluate("() => window.misma_pagina === true")  # HTMX: no se ha recargado

    page.wait_for_timeout(TRAS_LA_ESPERA_MS)
    page.keyboard.press("Enter")
    dialogo = page.get_by_role("dialog", name="¿Has terminado?")
    assert dialogo.is_visible()
    sin_errores_axe(page)
    dialogo.get_by_role("button", name="Sí").click()
    page.get_by_text("¡Hecha!").wait_for()
    assert mochila.ejecuciones.get(fecha=timezone.localdate()).estado == "hecha"


def test_cuantos_pasos_faltan_se_actualiza_en_la_zona_viva(live_server, page, mochila):
    """«Te faltan N pasos» está en una zona aria-live (el lector la anuncia al cambiar) y se
    actualiza sin recargar. Que el lector lo diga de verdad hay que probarlo a mano."""
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


def test_mantener_pulsado_intro_no_marca_el_paso_siguiente(live_server, page, mochila):
    """Una pulsación larga (la tecla se repite sola) o dos pulsaciones seguidas sin querer
    marcan un solo paso: cada paso, un «Hecho» (RF2.4.3)."""
    page.goto(url(live_server, mochila))
    boton_hecho(page, 1).focus()
    page.keyboard.down("Enter")
    boton_hecho(page, 2).wait_for()
    page.keyboard.down("Enter")  # la repetición automática de la tecla
    page.keyboard.up("Enter")
    page.keyboard.press("Enter")  # otra pulsación justo después de mover el foco
    page.wait_for_timeout(TRAS_LA_ESPERA_MS)
    assert estados(mochila) == ["hecho", "pendiente", "pendiente", "pendiente"]
    assert es_el_foco(boton_hecho(page, 2))

    page.keyboard.press("Enter")  # pasada la espera, sí cuenta
    boton_hecho(page, 3).wait_for()
    assert estados(mochila) == ["hecho", "hecho", "pendiente", "pendiente"]


def test_con_otra_pestana_desfasada_sale_el_aviso_sin_recargar(live_server, page, mochila):
    """Si la tarea ya no está en marcha (p. ej. se cerró desde otra pestaña), «Hecho» no
    cambia nada, sale el aviso y la lista se pone al día sin recargar la página."""
    page.goto(url(live_server, mochila))
    page.evaluate("() => { window.misma_pagina = true; }")
    mochila.ejecuciones.filter(fecha=timezone.localdate()).update(estado="cancelada")

    boton_hecho(page, 1).click()
    aviso = page.get_by_role("alert")
    aviso.wait_for()
    assert "Esta tarea ya no está en marcha." in aviso.inner_text()
    assert page.locator("[data-paso] button").count() == 0
    assert es_el_foco(page.locator("#pasos"))
    assert page.evaluate("() => window.misma_pagina === true")
    assert estados(mochila) == ["pendiente"] * 4


def test_si_la_sesion_ha_caducado_se_recarga_y_no_se_borra_la_lista(live_server, page, mochila):
    """Sin sesión, la respuesta no es la pantalla de la tarea: en vez de cambiar la lista
    por nada, se recarga la página entera (lo mismo que sin JavaScript)."""
    page.goto(url(live_server, mochila))
    page.context.clear_cookies(name="sessionid")
    with page.expect_navigation():
        boton_hecho(page, 1).click()
    # Va a la entrada y, al volver, a la pantalla de la tarea (no a la URL del POST).
    ruta = reverse("agenda:detalle", args=[mochila.pk])
    assert f"next={ruta}" in page.url
    assert estados(mochila) == ["pendiente"] * 4


def test_sin_conexion_avisa_y_se_puede_volver_a_pulsar(live_server, page, mochila):
    page.goto(url(live_server, mochila))
    page.route("**/paso/**", lambda ruta: ruta.abort())
    boton = boton_hecho(page, 1)
    boton.click()
    aviso = page.get_by_role("alert")
    aviso.wait_for()
    assert "No se ha podido guardar" in aviso.inner_text()
    assert boton.is_visible()
    assert estados(mochila) == ["pendiente"] * 4

    page.unroute("**/paso/**")
    boton.click()
    boton_hecho(page, 2).wait_for()
    assert estados(mochila) == ["hecho", "pendiente", "pendiente", "pendiente"]
