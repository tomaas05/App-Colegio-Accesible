"""HU-02-06 · Ver mi semana y mi horario de clases (boceto B30).

Datos de prueba de Lucía (A01), todos los días: mochila 9:00, manos 10:30, regar 12:00,
cuento 17:00 y «Poner la mesa» 20:00.
"""

import re
from datetime import datetime, time, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios
from apps.horario.models import Franja
from apps.tareas import planificacion
from apps.tareas.models import Asignacion, ExcepcionAsignacion, Tarea, TipoExcepcion
from apps.usuarios.models import Estudiante, Usuario

pytestmark = pytest.mark.django_db

HOY = timezone.localdate()
LUNES = HOY - timedelta(days=HOY.weekday())
NOMBRES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
LETRAS = ["L", "M", "X", "J", "V", "S", "D"]


def a_las(hora, minuto=0, dia=HOY):
    return timezone.make_aware(datetime.combine(dia, time(hora, minuto)))


@pytest.fixture(autouse=True)
def hora(monkeypatch):
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(8))


@pytest.fixture
def lucia(datos, client):
    estudiante = Estudiante.objects.get(codigo_estudiante="A01")
    client.force_login(estudiante.usuario)
    return estudiante


def semana_html(client):
    return client.get(reverse("agenda:semana")).content.decode()


def tarjeta_de(html, n):
    """El enlace del día n (1 = lunes) en «Mi semana»."""
    return re.search(rf'<a class="semana-dia semana-dia--{n}[ "].*?</a>', html, re.S).group(0)


def otro_dia(fecha):
    return reverse("agenda:otro_dia", args=[fecha.isoformat()])


def test_la_semana_va_de_lunes_a_domingo_y_marca_hoy(lucia):
    dias = servicios.semana(lucia, a_las(8))
    assert [d.fecha for d in dias] == [LUNES + timedelta(days=n) for n in range(7)]
    assert [d.nombre for d in dias] == NOMBRES
    assert [d.es_hoy for d in dias].count(True) == 1 and dias[HOY.weekday()].es_hoy


def test_cada_dia_con_su_nombre_completo_y_su_inicial(client, lucia):
    """PA1: cada día con su nombre completo y su inicial (en su forma, nunca solo color)."""
    html = semana_html(client)
    for n, (nombre, letra) in enumerate(zip(NOMBRES, LETRAS, strict=True), start=1):
        tarjeta = tarjeta_de(html, n)
        assert f'{nombre} <span class="semana-dia__fecha">' in tarjeta
        assert (
            f'class="dia-forma dia-forma--{n}" aria-hidden="true"><span>{letra}</span>' in tarjeta
        )
    hoy = tarjeta_de(html, HOY.isoweekday())
    assert 'aria-current="date"' in hoy and "Hoy</span>" in hoy
    assert html.count('aria-current="date"') == 1


def test_cada_tarea_con_su_hora_y_su_pictograma(client, lucia):
    """PA2: en cada día, la hora y el pictograma de sus tareas."""
    html = semana_html(client)
    tarjeta = tarjeta_de(html, 3)
    for asignacion in lucia.asignaciones.order_by("hora_inicio"):
        assert f"{asignacion.hora_inicio:%H:%M}</span>" in tarjeta
        assert asignacion.tarea.imagen.url in tarjeta
    assert "5 tareas" in tarjeta and "+2 más" in tarjeta  # en estrecho se ven 3


def test_con_muchas_tareas_se_ven_6_y_cuantas_quedan(client, lucia):
    for hora_ in (13, 14, 15):
        Asignacion.objects.create(
            tarea=Tarea.objects.get(nombre="Escuchar música"),
            estudiante=lucia,
            asignado_por=lucia.tutor,
            hora_inicio=time(hora_),
            hora_fin=time(hora_, 30),
            dias_semana=[1],
            vigencia_desde=LUNES - timedelta(days=7),
        )
    tarjeta = tarjeta_de(semana_html(client), 1)
    assert "8 tareas" in tarjeta
    assert tarjeta.count('class="semana-dia__tarea"') == 6
    assert "+5 más" in tarjeta and "+2 más" in tarjeta  # en estrecho y en ancho


def test_un_dia_sin_tareas(client, lucia):
    lucia.asignaciones.update(dias_semana=[1, 2, 3, 4, 5])
    assert "Sin tareas" in tarjeta_de(semana_html(client), 7)


def test_lo_cancelado_no_cuenta_y_los_cambios_de_un_dia_si(client, lucia):
    regar, manos = (
        lucia.asignaciones.get(tarea__nombre="Regar las plantas"),
        lucia.asignaciones.get(tarea__nombre="Lavarse las manos"),
    )
    tutor = Usuario.objects.get(username="tutor")
    domingo = LUNES + timedelta(days=6)
    ExcepcionAsignacion.objects.create(
        asignacion=regar, fecha=domingo, tipo=TipoExcepcion.CANCELADA, creada_por=tutor
    )
    ExcepcionAsignacion.objects.create(
        asignacion=manos,
        fecha=domingo,
        tipo=TipoExcepcion.MODIFICADA,
        hora_inicio=time(11, 5),
        hora_fin=time(11, 20),
        creada_por=tutor,
    )
    tarjeta = tarjeta_de(semana_html(client), 7)
    assert "4 tareas" in tarjeta and regar.tarea.imagen.url not in tarjeta
    assert "11:05</span>" in tarjeta and "10:30</span>" not in tarjeta


def test_el_plan_b_elegido_hoy_sale_en_la_semana(client, lucia, monkeypatch):
    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas")
    musica = Tarea.objects.get(nombre="Escuchar música")
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(11, 50))
    servicios.no_puedo(lucia, regar.pk, por=lucia.usuario)
    servicios.elegir_plan_b(lucia, regar.pk, musica.pk)
    tarjeta = tarjeta_de(semana_html(client), HOY.isoweekday())
    assert musica.imagen.url in tarjeta and regar.tarea.imagen.url not in tarjeta


def test_al_tocar_un_dia_se_abre_entero(client, lucia):
    """PA3: cada día lleva a su detalle; hoy, a la agenda de siempre."""
    html = semana_html(client)
    for n in range(7):
        fecha = LUNES + timedelta(days=n)
        destino = reverse("agenda:dia") if fecha == HOY else otro_dia(fecha)
        assert f'href="{destino}"' in tarjeta_de(html, n + 1)


def test_el_detalle_de_otro_dia_tiene_todas_sus_tareas_solo_para_ver(client, lucia):
    fecha = LUNES + (timedelta(days=1) if HOY == LUNES else timedelta(days=0))
    html = client.get(otro_dia(fecha)).content.decode()
    assert planificacion.fecha_en_texto(fecha).capitalize() in html
    for asignacion in lucia.asignaciones.all():
        assert asignacion.tarea.nombre in html
        assert reverse("agenda:detalle", args=[asignacion.pk]) not in html  # no se abren
    assert reverse("agenda:semana") in html  # «‹ Semana»


def test_en_el_detalle_lo_cancelado_sale_tachado(client, lucia):
    fecha = LUNES + timedelta(days=6) if HOY.weekday() != 6 else LUNES
    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas")
    ExcepcionAsignacion.objects.create(
        asignacion=regar,
        fecha=fecha,
        tipo=TipoExcepcion.CANCELADA,
        creada_por=Usuario.objects.get(username="tutor"),
    )
    html = client.get(otro_dia(fecha)).content.decode()
    assert "tarjeta--cancelada" in html and "Cancelada" in html


def test_el_detalle_de_hoy_es_la_agenda(client, lucia):
    assert client.get(otro_dia(HOY)).url == reverse("agenda:dia")


@pytest.mark.parametrize("fecha", ["2020-01-01", "manana", "2026-02-30"])
def test_solo_los_dias_de_esta_semana(client, lucia, fecha):
    assert client.get(reverse("agenda:otro_dia", args=[fecha])).status_code == 404


def test_la_semana_que_viene_no(client, lucia):
    assert client.get(otro_dia(LUNES + timedelta(days=7))).status_code == 404


def test_el_horario_de_la_clase_desde_la_semana_y_desde_cada_dia(client, lucia):
    """PA4: el horario de clase de hoy y de la semana, con nombre y pictograma (es la
    pantalla de HU-03-11). Desde un día lectivo, el horario de ese día."""
    assert reverse("horario:mi_horario") in semana_html(client)
    viernes = LUNES + timedelta(days=4)
    if viernes != HOY:
        html = client.get(otro_dia(viernes)).content.decode()
        assert f"{reverse('horario:mi_horario')}?dia=5" in html
    domingo = LUNES + timedelta(days=6)
    if domingo != HOY:
        assert reverse("horario:mi_horario") not in client.get(otro_dia(domingo)).content.decode()


def test_el_horario_de_clase_no_se_puede_cambiar(client, lucia):
    """PA5: solo para ver: ni formularios ni se acepta un POST."""
    url = reverse("horario:mi_horario")
    html = client.get(url, {"dia": 1}).content.decode()
    # El único formulario es «Salir» (es su pantalla de inicio, retrospectiva del 19/11).
    principal = html.split("<main", 1)[1]
    assert principal.count("<form") == 1 and 'class="salir-est"' in principal
    assert Franja.objects.exists() and lucia.clase.horario.exists()
    assert client.post(url, {"dia": 1}).status_code == 405


def test_la_agenda_lleva_a_mi_semana(client, lucia):
    html = client.get(reverse("agenda:dia")).content.decode()
    assert f'href="{reverse("agenda:semana")}"' in html and "Mi semana" in html


def test_un_adulto_no_abre_mi_semana(client, datos):
    client.force_login(Usuario.objects.get(username="tutor"))
    assert client.get(reverse("agenda:semana")).status_code == 403
    assert client.get(otro_dia(HOY)).status_code == 403
