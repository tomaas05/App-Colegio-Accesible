"""HU-02-05 Seguir los pasos de una tarea (AGENDA-187).

Pruebas de aceptación (Jira y Plan de Entregas):
  1. Veo la lista de pasos con la imagen, la descripción y el estado de cada uno.
  2. Al pasar al siguiente paso, el actual queda como hecho.
  3. No puedo saltarme un paso.
  4. No puedo terminar la tarea con pasos sin hacer.
Además, de la descripción de la HU: sé en qué paso estoy y cuántos me quedan.

Datos de prueba de Lucía: «Preparar la mochila» (9:00–9:15) tiene 4 pasos: Coger la
agenda, Meter el estuche, Meter el almuerzo y Cerrar la mochila. «Regar las plantas»
(12:00–12:30) no tiene pasos.
"""

from datetime import datetime, time
from html.parser import HTMLParser

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios
from apps.agenda.models import Ejecucion, EjecucionPaso, EstadoEjecucion
from apps.agenda.servicios import ErrorDeAgenda
from apps.tareas.models import Asignacion, Paso
from apps.usuarios.models import Estudiante

pytestmark = pytest.mark.django_db

PASOS_MOCHILA = ["Coger la agenda", "Meter el estuche", "Meter el almuerzo", "Cerrar la mochila"]


def a_las(hora, minuto=0):
    return timezone.make_aware(datetime.combine(timezone.localdate(), time(hora, minuto)))


@pytest.fixture
def hora(monkeypatch):
    """Fija la hora de las pantallas: hora(9, 5)."""

    def fijar(h, m=0):
        monkeypatch.setattr(servicios, "ahora", lambda: a_las(h, m))

    return fijar


@pytest.fixture
def lucia(datos):
    return Estudiante.objects.get(codigo_estudiante="A01")


@pytest.fixture
def mochila(lucia):
    return lucia.asignaciones.get(tarea__nombre="Preparar la mochila")


@pytest.fixture
def pasos(mochila):
    """Los 4 pasos de la mochila, en orden."""
    return list(mochila.tarea.pasos.order_by("orden"))


@pytest.fixture
def empezada(lucia, mochila):
    """La mochila empezada a las 9:01 (vale con o sin margen para empezar antes)."""
    return servicios.empezar(lucia, mochila.pk, a_las(9, 1))


def estados(ejecucion):
    return list(ejecucion.pasos.order_by("paso__orden").values_list("estado", flat=True))


def hacer(estudiante, asignacion, paso, minuto=5):
    return servicios.marcar_paso_hecho(estudiante, asignacion.pk, paso.pk, a_las(9, minuto))


# --- Lógica (apps/agenda/servicios.py) ----------------------------------------------


def test_al_pasar_al_siguiente_el_actual_queda_hecho(lucia, mochila, pasos, empezada):
    """Prueba de aceptación 2."""
    hacer(lucia, mochila, pasos[0])
    assert estados(empezada) == ["hecho", "pendiente", "pendiente", "pendiente"]
    t = servicios.tarea_del_dia(lucia, mochila.pk, a_las(9, 5))
    assert t.paso_actual.paso == pasos[1]
    assert t.posicion_paso_actual == 2
    assert t.pasos_pendientes == 3


def test_no_puedo_saltarme_un_paso(lucia, mochila, pasos, empezada):
    """Prueba de aceptación 3 (RF2.4.4): fuera de orden no cambia ningún estado."""
    with pytest.raises(ErrorDeAgenda, match="Primero haz el paso 1"):
        hacer(lucia, mochila, pasos[2])
    assert estados(empezada) == ["pendiente"] * 4

    hacer(lucia, mochila, pasos[0])
    with pytest.raises(ErrorDeAgenda, match="Primero haz el paso 2"):
        hacer(lucia, mochila, pasos[3])
    assert estados(empezada) == ["hecho", "pendiente", "pendiente", "pendiente"]


def test_solo_hay_un_paso_actual_y_es_el_primero_sin_hacer(lucia, mochila, pasos, empezada):
    t = servicios.tarea_del_dia(lucia, mochila.pk, a_las(9, 2))
    assert t.paso_actual.paso == pasos[0]
    assert [p for p in t.pasos if p == t.paso_actual] == [t.paso_actual]


def test_no_puedo_terminar_con_pasos_sin_hacer_y_si_al_hacerlos_todos(
    lucia, mochila, pasos, empezada
):
    """Prueba de aceptación 4, ahora marcando los pasos de verdad."""
    for i, paso in enumerate(pasos[:-1]):
        hacer(lucia, mochila, paso, minuto=2 + i)
    with pytest.raises(ErrorDeAgenda, match="Te falta 1 paso"):
        servicios.terminar(lucia, mochila.pk, a_las(9, 8))

    hacer(lucia, mochila, pasos[-1], minuto=9)
    t = servicios.tarea_del_dia(lucia, mochila.pk, a_las(9, 9))
    assert t.paso_actual is None and t.puede_terminar
    assert servicios.terminar(lucia, mochila.pk, a_las(9, 10)).estado == EstadoEjecucion.HECHA


def test_un_doble_toque_no_cambia_nada_ni_da_error(lucia, mochila, pasos, empezada):
    hacer(lucia, mochila, pasos[0])
    hacer(lucia, mochila, pasos[0])
    assert estados(empezada) == ["hecho", "pendiente", "pendiente", "pendiente"]


def test_sin_empezar_la_tarea_no_se_marcan_pasos(lucia, mochila, pasos):
    with pytest.raises(ErrorDeAgenda, match="Primero tienes que empezar la tarea"):
        hacer(lucia, mochila, pasos[0])
    assert not EjecucionPaso.objects.filter(ejecucion__fecha=timezone.localdate()).exists()
    t = servicios.tarea_del_dia(lucia, mochila.pk, a_las(9, 5))
    assert t.paso_actual is None  # pendiente: ningún paso «Ahora»


def test_con_el_tiempo_agotado_se_pueden_seguir_haciendo_los_pasos(lucia, mochila, pasos, empezada):
    """La tarea sigue en marcha después de su hora de fin (9:15): se puede acabar."""
    servicios.marcar_paso_hecho(lucia, mochila.pk, pasos[0].pk, a_las(9, 20))
    t = servicios.tarea_del_dia(lucia, mochila.pk, a_las(9, 20))
    assert t.estado == EstadoEjecucion.TIEMPO_AGOTADO
    assert t.paso_actual.paso == pasos[1]


def test_una_tarea_ya_terminada_no_cambia(lucia, mochila, pasos, empezada):
    empezada.estado = EstadoEjecucion.CANCELADA
    empezada.save()
    with pytest.raises(ErrorDeAgenda, match="ya no está en marcha"):
        hacer(lucia, mochila, pasos[0])
    assert estados(empezada) == ["pendiente"] * 4


def test_un_paso_de_otra_tarea_o_de_otro_estudiante_no_existe(lucia, mochila, empezada):
    manos = lucia.asignaciones.get(tarea__nombre="Lavarse las manos")
    paso_ajeno = manos.tarea.pasos.first()
    with pytest.raises(Paso.DoesNotExist):
        hacer(lucia, mochila, paso_ajeno)
    mateo = Estudiante.objects.get(codigo_estudiante="A02")
    with pytest.raises(Asignacion.DoesNotExist):
        hacer(mateo, mochila, mochila.tarea.pasos.first())
    assert estados(empezada) == ["pendiente"] * 4


def test_un_paso_nuevo_tras_empezar_tambien_hay_que_hacerlo(lucia, mochila, pasos, empezada):
    """Si el tutor añade un paso con la tarea en marcha, se crea su avance al marcar."""
    for i, paso in enumerate(pasos):
        hacer(lucia, mochila, paso, minuto=2 + i)
    nuevo = Paso.objects.create(
        tarea=mochila.tarea, orden=5, imagen=pasos[0].imagen.name, descripcion_imagen="Colgarla"
    )
    with pytest.raises(ErrorDeAgenda, match="1 paso"):
        servicios.terminar(lucia, mochila.pk, a_las(9, 10))
    hacer(lucia, mochila, nuevo, minuto=11)
    assert servicios.terminar(lucia, mochila.pk, a_las(9, 12)).estado == EstadoEjecucion.HECHA


def test_los_pasos_se_numeran_por_su_posicion_aunque_el_orden_tenga_huecos(
    lucia, mochila, pasos, empezada
):
    Paso.objects.filter(pk=pasos[1].pk).update(orden=20)  # Meter el estuche, al final
    with pytest.raises(ErrorDeAgenda, match="Primero haz el paso 1"):
        hacer(lucia, mochila, pasos[1])
    hacer(lucia, mochila, pasos[0])
    with pytest.raises(ErrorDeAgenda, match="Primero haz el paso 2"):
        hacer(lucia, mochila, pasos[1])
    t = servicios.tarea_del_dia(lucia, mochila.pk, a_las(9, 5))
    assert t.paso_actual.paso == pasos[2] and t.posicion_paso_actual == 2
    assert "Paso 4: Meter el estuche" in t.texto_para_escuchar


def test_una_tarea_que_ya_no_toca_hoy_no_se_toca(lucia, mochila, pasos, empezada):
    """Si quitan el día de hoy a la asignación con la tarea empezada, la pantalla da 404:
    marcar un paso tampoco debe guardar nada."""
    hoy = timezone.localdate().isoweekday()
    mochila.dias_semana = [d for d in range(1, 8) if d != hoy]
    mochila.save()
    with pytest.raises(Asignacion.DoesNotExist):
        hacer(lucia, mochila, pasos[0])
    assert estados(empezada) == ["pendiente"] * 4


def test_un_toque_tardio_en_una_tarea_hecha_no_crea_nada(lucia, mochila, pasos, empezada):
    """RF2.4.4: «sin generar marcas». Aunque el tutor haya añadido un paso después."""
    for i, paso in enumerate(pasos):
        hacer(lucia, mochila, paso, minuto=2 + i)
    servicios.terminar(lucia, mochila.pk, a_las(9, 10))
    Paso.objects.create(
        tarea=mochila.tarea, orden=5, imagen=pasos[0].imagen.name, descripcion_imagen="Colgarla"
    )
    hacer(lucia, mochila, pasos[0], minuto=11)  # ya hecho: no es un error
    assert empezada.pasos.count() == 4


def test_con_tiempo_agotado_guardado_tambien_se_sigue(lucia, mochila, pasos, empezada):
    """Hoy «tiempo agotado» solo se calcula; si algún día se guarda, la pantalla sigue
    ofreciendo «Hecho» (en_curso) y el servidor debe aceptarlo igual."""
    empezada.estado = EstadoEjecucion.TIEMPO_AGOTADO
    empezada.save()
    hacer(lucia, mochila, pasos[0], minuto=20)
    assert estados(empezada) == ["hecho", "pendiente", "pendiente", "pendiente"]


# --- Pantalla (apps/agenda/views.py y tarea.html) -----------------------------------


@pytest.fixture
def entra_lucia(client, lucia):
    client.force_login(lucia.usuario)
    return client


def url_detalle(asignacion):
    return reverse("agenda:detalle", args=[asignacion.pk])


def url_hecho(asignacion, paso):
    return reverse("agenda:paso_hecho", args=[asignacion.pk, paso.pk])


class PasosEnPantalla(HTMLParser):
    """Lee cada <li class="paso"> de la pantalla: si es el actual, el texto alternativo de
    la imagen, el texto, el estado (chip) y el nombre del botón «Hecho», si lo tiene.

    Así las pruebas miran lo que se ve y lo que anuncia el lector de pantalla, y no se
    rompen si cambian los espacios o el orden de los atributos de la plantilla.
    """

    def __init__(self, html):
        super().__init__()
        self.pasos = []
        self._en_paso = self._en_boton = False
        self._en_chip = 0
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        atributos = dict(attrs)
        clases = (atributos.get("class") or "").split()
        if tag == "li" and "paso" in clases:
            self._en_paso = True
            actual = atributos.get("aria-current") == "step"
            self.pasos.append(
                {"actual": actual, "imagen": None, "texto": "", "estado": "", "boton": None}
            )
        elif not self._en_paso:
            return
        elif tag == "img":
            self.pasos[-1]["imagen"] = atributos.get("alt")
        elif tag == "button":
            self._en_boton = True
            self.pasos[-1]["boton"] = atributos.get("aria-label")
        elif tag == "span" and ("chip" in clases or self._en_chip):
            self._en_chip += 1

    def handle_endtag(self, tag):
        if tag == "li":
            self._en_paso = False
        elif tag == "button":
            self._en_boton = False
        elif tag == "span" and self._en_chip:
            self._en_chip -= 1

    def handle_data(self, data):
        if not self._en_paso or self._en_boton:
            return
        paso = self.pasos[-1]
        clave = "estado" if self._en_chip else "texto"
        paso[clave] = " ".join(f"{paso[clave]} {data}".split())


def pasos_en_pantalla(cliente, asignacion):
    return PasosEnPantalla(cliente.get(url_detalle(asignacion)).content.decode()).pasos


def test_veo_la_lista_de_pasos_con_imagen_descripcion_y_estado(entra_lucia, hora, mochila):
    """Prueba de aceptación 1, antes de empezar: todos pendientes y ninguno se puede pulsar."""
    hora(9, 0)
    assert pasos_en_pantalla(entra_lucia, mochila) == [
        {
            "actual": False,
            "imagen": texto,
            "texto": f"Paso {numero} {texto}",
            "estado": "○ Pendiente",
            "boton": None,
        }
        for numero, texto in enumerate(PASOS_MOCHILA, start=1)
    ]


def test_en_marcha_veo_en_que_paso_estoy_y_cuantos_me_quedan(
    entra_lucia, hora, lucia, mochila, pasos, empezada
):
    """Prueba de aceptación 1 con la tarea en marcha y el paso 1 hecho."""
    hacer(lucia, mochila, pasos[0])
    hora(9, 5)
    en_pantalla = pasos_en_pantalla(entra_lucia, mochila)
    estados_vistos = [p["estado"] for p in en_pantalla]
    assert estados_vistos == ["✓ Hecho", "▶ Ahora", "○ Pendiente", "○ Pendiente"]
    assert [p["actual"] for p in en_pantalla] == [False, True, False, False]
    # Un solo botón «Hecho», el del paso 2: no se puede saltar ninguno (prueba 3).
    assert [p["boton"] for p in en_pantalla] == [None, "Hecho, paso 2", None, None]
    assert [p["imagen"] for p in en_pantalla] == PASOS_MOCHILA

    html = entra_lucia.get(url_detalle(mochila)).content.decode()
    assert "Paso 2 de 4" in html and "faltan 3 pasos" in html
    assert f'action="{url_hecho(mochila, pasos[1])}"' in html
    # El botón se describe con el texto del paso, que el lector lee tras su nombre.
    assert f'aria-describedby="paso-{pasos[1].pk}-texto"' in html
    assert f'id="paso-{pasos[1].pk}-texto"' in html


def test_hecho_marca_el_paso_y_vuelve_a_los_pasos(entra_lucia, hora, mochila, pasos, empezada):
    """Sin JavaScript: el formulario recarga la página y baja hasta los pasos."""
    hora(9, 5)
    respuesta = entra_lucia.post(url_hecho(mochila, pasos[0]))
    assert respuesta.status_code == 302
    assert respuesta["Location"] == url_detalle(mochila) + "#pasos"
    assert estados(empezada) == ["hecho", "pendiente", "pendiente", "pendiente"]
    assert "Paso 2 de 4" in entra_lucia.get(respuesta["Location"]).content.decode()


def test_pulsar_un_paso_posterior_no_cambia_nada_y_lo_dice(
    entra_lucia, hora, mochila, pasos, empezada
):
    hora(9, 5)
    respuesta = entra_lucia.post(url_hecho(mochila, pasos[2]), follow=True)
    html = respuesta.content.decode()
    assert "Primero haz el paso 1." in html and 'role="alert"' in html
    # Sin #pasos: la página se queda arriba, donde sale el aviso.
    assert respuesta.redirect_chain == [(url_detalle(mochila), 302)]
    assert estados(empezada) == ["pendiente"] * 4


def test_al_hacer_el_ultimo_paso_aparece_terminar(entra_lucia, hora, mochila, pasos, empezada):
    hora(9, 5)
    for paso in pasos[:-1]:
        entra_lucia.post(url_hecho(mochila, paso))
    html = entra_lucia.get(url_detalle(mochila)).content.decode()
    assert "falta 1 paso" in html and ">Terminar<" not in html and "<dialog" not in html

    entra_lucia.post(url_hecho(mochila, pasos[-1]))
    html = entra_lucia.get(url_detalle(mochila)).content.decode()
    assert "Todos los pasos hechos" in html and "data-paso" not in html
    assert ">Terminar<" in html and '<dialog class="confirmar"' in html
    entra_lucia.post(reverse("agenda:terminar", args=[mochila.pk]))
    empezada.refresh_from_db()
    assert empezada.estado == EstadoEjecucion.HECHA
    assert "Todos los pasos hechos" in entra_lucia.get(url_detalle(mochila)).content.decode()


def test_con_htmx_solo_cambian_los_trozos_que_hacen_falta(entra_lucia, hora, mochila, empezada):
    """El formulario pide con HTMX la misma pantalla y cambia solo estas zonas, que
    tienen que estar siempre en la página aunque estén vacías."""
    hora(9, 5)
    html = entra_lucia.get(url_detalle(mochila)).content.decode()
    assert 'hx-target="#pasos"' in html and 'hx-select="#pasos"' in html
    assert 'hx-select-oob="#botones-tarea,#mensajes,#confirmar-zona"' in html
    for zona in ('id="pasos"', 'id="botones-tarea"', 'id="mensajes"', 'id="confirmar-zona"'):
        assert zona in html


def test_marcar_un_paso_pide_post_y_sesion_del_estudiante(
    entra_lucia, hora, mochila, pasos, empezada
):
    hora(9, 5)
    assert entra_lucia.get(url_hecho(mochila, pasos[0])).status_code == 405
    # Un paso de la mochila con la URL de otra tarea suya (Lavarse las manos): 404.
    manos = mochila.estudiante.asignaciones.get(tarea__nombre="Lavarse las manos")
    assert entra_lucia.post(url_hecho(manos, pasos[0])).status_code == 404
    mateo = Client()
    mateo.force_login(Estudiante.objects.get(codigo_estudiante="A02").usuario)
    assert mateo.post(url_hecho(mochila, pasos[0])).status_code == 404
    sin_sesion = Client()
    assert sin_sesion.post(url_hecho(mochila, pasos[0])).status_code == 302  # a la entrada
    assert estados(empezada) == ["pendiente"] * 4


def test_una_tarea_sin_pasos_no_muestra_la_zona_de_pasos(entra_lucia, hora, lucia):
    hora(12, 5)
    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas")
    servicios.empezar(lucia, regar.pk, a_las(12, 5))
    html = entra_lucia.get(url_detalle(regar)).content.decode()
    assert 'id="pasos"' not in html and ">Terminar<" in html
    assert Ejecucion.objects.get(asignacion=regar, fecha=timezone.localdate()).pasos.count() == 0
