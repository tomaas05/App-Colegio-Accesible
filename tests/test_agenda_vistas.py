"""HU-02-01 a HU-02-04: pantallas de la agenda (apps/agenda/views.py)."""

from datetime import datetime, time, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios
from apps.agenda.models import Ejecucion, EstadoEjecucion
from apps.usuarios.models import Estudiante, Usuario

pytestmark = pytest.mark.django_db


def a_las(hora, minuto=0):
    return timezone.make_aware(datetime.combine(timezone.localdate(), time(hora, minuto)))


def desde(hora, minuto=0):
    """Desde cuándo se puede empezar una tarea de esa hora (resta el margen)."""
    return a_las(hora, minuto) - servicios.MARGEN_EMPEZAR_ANTES


@pytest.fixture
def hora(monkeypatch):
    """Fija la hora de las pantallas: hora(10, 35)."""

    def fijar(h, m=0):
        monkeypatch.setattr(servicios, "ahora", lambda: a_las(h, m))

    return fijar


@pytest.fixture
def lucia(datos, client):
    estudiante = Estudiante.objects.get(codigo_estudiante="A01")
    client.force_login(estudiante.usuario)
    return estudiante


def de_hoy():
    return Ejecucion.objects.filter(fecha=timezone.localdate())


def url_de(estudiante, nombre, vista="detalle"):
    pk = estudiante.asignaciones.get(tarea__nombre=nombre).pk
    return reverse(f"agenda:{vista}", args=[pk])


def test_sin_sesion_redirige_a_la_entrada(client, datos):
    respuesta = client.get(reverse("agenda:dia"))
    assert respuesta.status_code == 302
    assert "next=" in respuesta["Location"]


def test_un_adulto_no_abre_la_agenda_del_estudiante(client, datos):
    client.force_login(Usuario.objects.get(username="tutor"))
    assert client.get(reverse("agenda:dia")).status_code == 403


def test_agenda_del_dia(client, lucia, hora):
    hora(10, 35)
    respuesta = client.get(reverse("agenda:dia"))
    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    assert '<h1 id="titulo">Hoy, ' in html
    assert html.index("Preparar la mochila") < html.index("Lavarse las manos")
    assert "Ahora" in html and 'aria-current="true"' in html
    assert 'alt="Lavarse las manos"' in html


def test_agenda_vacia_con_mensajes(client, lucia, hora):
    lucia.asignaciones.all().delete()
    hora(10, 0)
    html = client.get(reverse("agenda:dia")).content.decode()
    assert "Hoy no tienes tareas" in html


def test_mensajes_sin_anterior_ni_siguiente(client, lucia, hora):
    hora(7, 0)
    assert "No hay tarea antes" in client.get(reverse("agenda:dia")).content.decode()
    hora(23, 0)
    assert "No hay más tareas hoy" in client.get(reverse("agenda:dia")).content.decode()


def test_la_agenda_no_ofrece_modificar_ni_borrar(client, lucia, hora):
    hora(10, 35)
    html = client.get(reverse("agenda:dia")).content.decode()
    assert "<form" not in html


def test_detalle_con_pasos_e_imagenes(client, lucia, hora):
    hora(9, 5)
    html = client.get(url_de(lucia, "Preparar la mochila")).content.decode()
    assert "Preparar la mochila" in html
    assert "Meter el estuche" in html and 'alt="Meter el estuche"' in html
    assert "Paso 4" in html


def test_detalle_sin_pasos_muestra_la_descripcion(client, lucia, hora):
    hora(12, 5)
    html = client.get(url_de(lucia, "Regar las plantas")).content.decode()
    assert "Regar las plantas del huerto con la regadera." in html
    assert "<h2>Pasos</h2>" not in html


def test_la_voz_no_se_ofrece_con_lector_de_pantalla_y_nunca_suena_sola(client, datos, hora):
    hora(12, 5)
    sofia = Estudiante.objects.get(codigo_estudiante="A03")  # usa lector de pantalla
    client.force_login(sofia.usuario)
    assert "data-escuchar" not in client.get(url_de(sofia, "Regar las plantas")).content.decode()
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    client.force_login(lucia.usuario)
    html = client.get(url_de(lucia, "Regar las plantas")).content.decode()
    assert "data-escuchar" in html and "hidden" in html and "autoplay" not in html


def test_otro_estudiante_recibe_404(client, lucia, hora):
    hora(12, 5)
    url = url_de(lucia, "Regar las plantas")
    mateo = Estudiante.objects.get(codigo_estudiante="A02")
    client.force_login(mateo.usuario)
    assert client.get(url).status_code == 404
    assert client.post(url_de_empezar(url)).status_code == 404


def url_de_empezar(url_detalle):
    return url_detalle + "empezar/"


def test_empezar_y_terminar_con_confirmacion(client, lucia, hora):
    hora(12, 5)
    detalle = url_de(lucia, "Regar las plantas")
    assert "Empezar" in client.get(detalle).content.decode()

    client.post(url_de(lucia, "Regar las plantas", "empezar"))
    ejecucion = de_hoy().get(asignacion__tarea__nombre="Regar las plantas")
    assert ejecucion.estado == EstadoEjecucion.EN_CURSO

    # Antes de registrar el fin se pide confirmar (B08): un <dialog> en la pantalla de la
    # tarea y, sin JavaScript, la misma pregunta en una página. Ninguna de las dos registra.
    detalle_html = client.get(detalle).content.decode()
    assert '<dialog class="confirmar"' in detalle_html and "¿Has terminado?" in detalle_html
    terminar = url_de(lucia, "Regar las plantas", "terminar")
    pantalla = client.get(terminar)
    assert "¿Has terminado?" in pantalla.content.decode()
    ejecucion.refresh_from_db()
    assert ejecucion.estado == EstadoEjecucion.EN_CURSO

    client.post(terminar)
    ejecucion.refresh_from_db()
    assert ejecucion.estado == EstadoEjecucion.HECHA
    assert "¡Hecha!" in client.get(detalle).content.decode()


def test_empezar_antes_de_la_hora_da_aviso_y_no_registra(client, lucia, hora):
    hora(12, 0)
    # Cuento: 17:00. El botón no se ofrece y, si se fuerza, el servidor lo rechaza.
    html = client.get(url_de(lucia, "Leer un cuento")).content.decode()
    assert f"Podrás empezar a las {desde(17):%H:%M}" in html and "Empezar</button>" not in html
    respuesta = client.post(url_de(lucia, "Leer un cuento", "empezar"), follow=True)
    assert "Todavía no es la hora" in respuesta.content.decode()
    assert not de_hoy().exists()


def test_terminar_con_pasos_sin_hacer_no_se_ofrece(client, lucia, hora):
    hora(9, 1)
    client.post(url_de(lucia, "Preparar la mochila", "empezar"))
    html = client.get(url_de(lucia, "Preparar la mochila")).content.decode()
    assert "faltan 4 pasos" in html and ">Terminar<" not in html
    respuesta = client.post(url_de(lucia, "Preparar la mochila", "terminar"), follow=True)
    assert "faltan 4 pasos" in respuesta.content.decode()
    assert de_hoy().get().estado == EstadoEjecucion.EN_CURSO


def test_retomar_tras_cerrar_y_reabrir(client, lucia, hora):
    hora(12, 2)
    client.post(url_de(lucia, "Regar las plantas", "empezar"))
    hora(12, 20)
    client.post(url_de(lucia, "Regar las plantas", "empezar"))
    assert de_hoy().get().inicio_real == a_las(12, 2)
    assert "Terminar" in client.get(url_de(lucia, "Regar las plantas")).content.decode()


def test_atajo_de_desarrollo_solo_con_debug_y_la_variable(
    client, datos, settings, hora, monkeypatch
):
    hora(10, 0)
    url = reverse("agenda:dia") + "?como=A01"
    settings.DEBUG = True
    monkeypatch.delenv("AGENDA_ENTRAR_COMO", raising=False)
    assert client.get(url).status_code == 302  # DEBUG solo no basta: la demo lo tiene
    monkeypatch.setenv("AGENDA_ENTRAR_COMO", "1")
    settings.DEBUG = False
    assert client.get(url).status_code == 302
    settings.DEBUG = True
    assert client.get(url).status_code == 200


def test_el_titulo_sale_en_espanol_aunque_el_navegador_pida_ingles(client, lucia, hora):
    hora(10, 0)
    html = client.get(reverse("agenda:dia"), headers={"accept-language": "en-US"}).content.decode()
    titulo = html.split('<h1 id="titulo">')[1].split("</h1>")[0]
    assert titulo == servicios.titulo_de_hoy(a_las(10, 0))


def test_aviso_de_la_siguiente_al_pie(client, lucia, hora):
    hora(11, 0)
    assert "Después, a las" not in client.get(reverse("agenda:dia")).content.decode()
    hora(11, 52)
    html = client.get(reverse("agenda:dia")).content.decode()
    assert "Después, a las 12:00" in html and 'role="status"' in html
    assert "Después, a las 12:00" in client.get(url_de(lucia, "Lavarse las manos")).content.decode()


def test_el_aviso_solo_se_vuelve_a_pintar_si_cambia(client, lucia, hora):
    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas").pk
    url = reverse("agenda:aviso")
    hora(11, 0)
    assert client.get(url + "?mostrado=0").status_code == 204
    hora(11, 52)
    respuesta = client.get(url + "?mostrado=0")
    assert respuesta.status_code == 200 and "Regar las plantas" in respuesta.content.decode()
    assert f"mostrado={regar}" in respuesta.content.decode()
    assert client.get(url + f"?mostrado={regar}").status_code == 204


def test_antes_y_despues_en_la_tarea(client, lucia, hora):
    hora(9, 5)
    html = client.get(url_de(lucia, "Preparar la mochila")).content.decode()
    assert "No hay tarea antes" in html and "Lavarse las manos · 10:30" in html
    html = client.get(url_de(lucia, "Poner la mesa")).content.decode()
    assert "No hay más tareas hoy" in html and "Leer un cuento · Pendiente" in html


def test_antes_de_la_hora_la_zona_del_boton_se_actualiza_sola(client, lucia, hora):
    antes = desde(17) - timedelta(minutes=5)
    hora(antes.hour, antes.minute)
    html = client.get(url_de(lucia, "Leer un cuento")).content.decode()
    assert 'hx-select=".botones-tarea"' in html and 'hx-trigger="every 30s"' in html
    hora(desde(17).hour, desde(17).minute)
    html = client.get(url_de(lucia, "Leer un cuento")).content.decode()
    assert "Empezar</button>" in html and 'every 30s" hx-swap="outerHTML' not in html


def test_si_otra_tarea_va_primero_se_dice_cual(client, lucia, hora, monkeypatch):
    monkeypatch.setattr(servicios, "MARGEN_EMPEZAR_ANTES", timedelta(minutes=15))
    cuento = lucia.asignaciones.get(tarea__nombre="Leer un cuento")
    cuento.hora_inicio, cuento.hora_fin = time(12, 30), time(13, 0)
    cuento.save()
    hora(12, 20)
    html = client.get(url_de(lucia, "Leer un cuento")).content.decode()
    assert "Ahora toca «Regar las plantas»." in html and "Empezar</button>" not in html
    assert 'hx-trigger="every 30s"' in html
