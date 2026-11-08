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

import pytest
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


# --- Pantalla (apps/agenda/views.py y tarea.html) -----------------------------------


@pytest.fixture
def entra_lucia(client, lucia):
    client.force_login(lucia.usuario)
    return client


def url_detalle(asignacion):
    return reverse("agenda:detalle", args=[asignacion.pk])


def url_hecho(asignacion, paso):
    return reverse("agenda:paso_hecho", args=[asignacion.pk, paso.pk])


def test_veo_la_lista_de_pasos_con_imagen_descripcion_y_estado(entra_lucia, hora, mochila):
    """Prueba de aceptación 1, antes de empezar: todos pendientes y ninguno se puede pulsar."""
    hora(9, 0)
    html = entra_lucia.get(url_detalle(mochila)).content.decode()
    for numero, texto in enumerate(PASOS_MOCHILA, start=1):
        assert f'alt="{texto}"' in html and f"Paso {numero}</span>" in html
    assert html.count("○</span> Pendiente") == 4
    assert "data-paso" not in html and 'aria-current="step"' not in html


def test_en_marcha_veo_en_que_paso_estoy_y_cuantos_me_quedan(
    entra_lucia, hora, lucia, mochila, pasos, empezada
):
    hacer(lucia, mochila, pasos[0])
    hora(9, 5)
    html = entra_lucia.get(url_detalle(mochila)).content.decode()
    assert "Paso 2 de 4" in html
    assert "faltan 3 pasos" in html
    assert html.count("✓</span> Hecho</span>") == 1  # chip del paso 1
    assert html.count('aria-current="step"') == 1
    assert html.count("▶</span> Ahora</span>") == 1
    assert html.count("○</span> Pendiente") == 2
    # Un solo botón «Hecho», el del paso 2, que se anuncia con su número y su texto.
    assert html.count("data-paso") == 1
    assert f'action="{url_hecho(mochila, pasos[1])}"' in html
    assert 'aria-label="Hecho, paso 2"' in html
    assert f'aria-describedby="paso-{pasos[1].pk}-texto"' in html


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
    assert 'hx-target="#pasos" hx-select="#pasos"' in html
    assert 'hx-select-oob="#botones-tarea,#mensajes,#confirmar-zona"' in html
    for zona in ('id="pasos"', 'id="botones-tarea"', 'id="mensajes"', 'id="confirmar-zona"'):
        assert zona in html


def test_marcar_un_paso_pide_post_y_sesion_del_estudiante(
    client, entra_lucia, hora, mochila, pasos, empezada
):
    hora(9, 5)
    assert entra_lucia.get(url_hecho(mochila, pasos[0])).status_code == 405
    # Un paso de la mochila con la URL de otra tarea suya (Lavarse las manos): 404.
    manos = mochila.estudiante.asignaciones.get(tarea__nombre="Lavarse las manos")
    assert entra_lucia.post(url_hecho(manos, pasos[0])).status_code == 404
    mateo = Estudiante.objects.get(codigo_estudiante="A02")
    client.force_login(mateo.usuario)
    assert client.post(url_hecho(mochila, pasos[0])).status_code == 404
    client.logout()
    assert client.post(url_hecho(mochila, pasos[0])).status_code == 302  # a la entrada
    assert estados(empezada) == ["pendiente"] * 4


def test_una_tarea_sin_pasos_no_muestra_la_zona_de_pasos(entra_lucia, hora, lucia):
    hora(12, 5)
    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas")
    servicios.empezar(lucia, regar.pk, a_las(12, 5))
    html = entra_lucia.get(url_detalle(regar)).content.decode()
    assert 'id="pasos"' not in html and ">Terminar<" in html
    assert Ejecucion.objects.get(asignacion=regar, fecha=timezone.localdate()).pasos.count() == 0
