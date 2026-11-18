"""HU-06-02 · Seguimiento de hoy (B50) en el navegador: axe WCAG 2.2 AA, sin desplazarse y
con el teclado, con avisos de plan B a la vista. Mismas resoluciones que el resto."""

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.agenda.models import Ejecucion, EstadoEjecucion
from apps.tareas.models import Tarea
from apps.usuarios.models import Estudiante, Usuario
from tests.e2e.test_accesibilidad_usuarios import RESOLUCIONES, con_sesion, revisar

pytestmark = pytest.mark.e2e


def con_avisos():
    """Lucía no ha podido regar (eligió música) ni preparar la mochila (sin plan B)."""
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    hoy, ahora = timezone.localdate(), timezone.now()
    for nombre, plan_b, estado in (
        (
            "Regar las plantas",
            Tarea.objects.get(nombre="Escuchar música"),
            EstadoEjecucion.PENDIENTE,
        ),
        ("Preparar la mochila", None, EstadoEjecucion.NO_REALIZABLE),
    ):
        asignacion = lucia.asignaciones.filter(tarea__nombre=nombre).first()
        if asignacion is None:
            continue
        Ejecucion.objects.update_or_create(
            asignacion=asignacion,
            fecha=hoy,
            defaults={
                "estado": estado,
                "no_realizable_el": ahora,
                "no_realizable_por": lucia.usuario,
                "plan_b": plan_b,
                "motivo": "Falta material" if plan_b is None else "",
            },
        )


@pytest.mark.parametrize("quien", ["tutor", "profesional"])
@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_seguimiento_con_avisos(live_server, page, client, datos, quien, nombre):
    con_avisos()
    con_sesion(page, live_server, client, Usuario.objects.get(username=quien))
    page.set_viewport_size(dict(zip(("width", "height"), RESOLUCIONES[nombre], strict=True)))
    page.goto(live_server.url + reverse("seguimiento:hoy"))
    page.evaluate("document.fonts.ready.then(() => true)")
    # La tarjeta de Lucía, con sus avisos, es la primera que se ve.
    primera = page.locator("#estudiantes > li:not([hidden])").first
    assert "Lucía" in primera.inner_text() and "No ha podido hacer" in primera.inner_text()
    revisar(page, nombre)
    # Sin desplazarse: lo que no cabe va a otra pantalla.
    main = page.locator("main")
    assert main.evaluate("m => m.scrollHeight <= m.clientHeight + 1")

    # Con el teclado se llega a «Ver su día» de Lucía y abre su agenda en modo consulta.
    enlace = primera.get_by_role("link", name="Ver su día de Lucía")
    enlace.focus()
    page.keyboard.press("Enter")
    page.wait_for_url("**/agenda/")
    assert "Solo consulta" in page.content()
    revisar(page, nombre)
