"""HU-07-03. Ver qué puedo hacer cuando se acaba el tiempo (AGENDA-112).

Una prueba por cada prueba de aceptación de Jira (PA1 a PA4).
"""

from datetime import datetime, time

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios
from apps.agenda.models import Ejecucion, EstadoEjecucion, EstadoPaso
from apps.comun.models import Notificacion
from apps.usuarios import consulta
from apps.usuarios.models import Estudiante, Usuario

pytestmark = pytest.mark.django_db


def a_las(hora, minuto=0, segundo=0):
    return timezone.make_aware(datetime.combine(timezone.localdate(), time(hora, minuto, segundo)))


def url_tarea(estudiante, nombre="Preparar la mochila"):
    pk = estudiante.asignaciones.get(tarea__nombre=nombre).pk
    return reverse("agenda:detalle", args=[pk])


# --- PA1: cuando se acaba el tiempo, se muestra un mensaje con pictograma y opciones ---


def test_pa1_cuando_se_acaba_el_tiempo_muestra_mensaje_con_pictograma_y_opciones(
    client, datos, monkeypatch
):
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    client.force_login(lucia.usuario)
    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas")  # 12:00 a 12:30 (con plan B)

    monkeypatch.setattr(servicios, "ahora", lambda: a_las(12, 10))
    servicios.empezar(lucia, regar.pk)
    html_en_curso = client.get(url_tarea(lucia, "Regar las plantas")).content.decode()
    assert 'data-tiempo-agotado="false"' in html_en_curso

    # A las 12:31 se ha agotado el tiempo: muestra mensaje, pictograma y opciones disponibles.
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(12, 31))
    html_agotado = client.get(url_tarea(lucia, "Regar las plantas")).content.decode()
    assert 'data-tiempo-agotado="true"' in html_agotado
    assert "Se acabó el tiempo." in html_agotado
    assert "¿Qué quieres hacer?" in html_agotado
    assert regar.tarea.imagen.url in html_agotado
    assert "Seguir con la tarea" in html_agotado
    assert "Elegir plan B" in html_agotado
    assert "Ir a «Leer un cuento»" in html_agotado
    assert "Volver a las tareas" in html_agotado


# --- PA2: la tarea queda registrada como no terminada ---


def test_pa2_la_tarea_queda_registrada_como_no_terminada(client, datos, monkeypatch):
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    client.force_login(lucia.usuario)
    mochila = lucia.asignaciones.get(tarea__nombre="Preparar la mochila")  # 9:00 a 9:15

    monkeypatch.setattr(servicios, "ahora", lambda: a_las(9, 2))
    servicios.empezar(lucia, mochila.pk)

    monkeypatch.setattr(servicios, "ahora", lambda: a_las(9, 16))
    client.get(url_tarea(lucia, "Preparar la mochila"))

    ejecucion = Ejecucion.objects.get(asignacion=mochila, fecha=timezone.localdate())
    assert ejecucion.estado == EstadoEjecucion.TIEMPO_AGOTADO
    assert ejecucion.estado != EstadoEjecucion.HECHA
    assert ejecucion.fin_real is None


# --- PA3: lo que hubiera completado en sus pasos no se pierde ---


def test_pa3_lo_completado_en_los_pasos_no_se_pierde(client, datos, monkeypatch):
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    client.force_login(lucia.usuario)
    mochila = lucia.asignaciones.get(tarea__nombre="Preparar la mochila")  # 4 pasos, 9:00 a 9:15
    pasos = list(mochila.tarea.pasos.order_by("orden"))

    # Lucía empieza a las 9:02 y completa los 2 primeros pasos antes de las 9:15.
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(9, 2))
    ejecucion = servicios.empezar(lucia, mochila.pk)
    servicios.marcar_paso_hecho(lucia, mochila.pk, pasos[0].pk, a_las(9, 5))
    servicios.marcar_paso_hecho(lucia, mochila.pk, pasos[1].pk, a_las(9, 8))

    # Se acaba el tiempo a las 9:16: los 2 pasos completados siguen como hechos.
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(9, 16))
    html = client.get(url_tarea(lucia, "Preparar la mochila")).content.decode()
    estados = list(ejecucion.pasos.order_by("paso__orden").values_list("estado", flat=True))
    assert estados == [
        EstadoPaso.HECHO,
        EstadoPaso.HECHO,
        EstadoPaso.PENDIENTE,
        EstadoPaso.PENDIENTE,
    ]
    assert "Paso 3 de 4" in html

    # Además puede seguir completando los pasos restantes en tiempo extra y terminar la tarea.
    servicios.marcar_paso_hecho(lucia, mochila.pk, pasos[2].pk, a_las(9, 17))
    servicios.marcar_paso_hecho(lucia, mochila.pk, pasos[3].pk, a_las(9, 18))
    servicios.terminar(lucia, mochila.pk, a_las(9, 19))
    ejecucion.refresh_from_db()
    assert ejecucion.estado == EstadoEjecucion.HECHA


# --- PA4: el tutor ve la tarea como no terminada en su panel ---


def test_pa4_el_tutor_ve_la_tarea_como_no_terminada_en_su_panel(client, datos, monkeypatch):
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    mochila = lucia.asignaciones.get(tarea__nombre="Preparar la mochila")  # 9:00 a 9:15

    monkeypatch.setattr(servicios, "ahora", lambda: a_las(9, 2))
    servicios.empezar(lucia, mochila.pk)

    # A las 9:16 se agota el tiempo sin haber terminado la tarea.
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(9, 16))
    servicios.agenda_del_dia(lucia, a_las(9, 16))

    # El tutor recibe el aviso en su panel (/panel/) y la consulta del día figura «Tiempo agotado».
    tutor = Usuario.objects.get(username="tutor")
    assert Notificacion.objects.filter(
        destinatario=tutor,
        tarea=mochila.tarea,
    ).exists()

    client.force_login(tutor)
    html_panel = client.get(reverse("usuarios:panel")).content.decode()
    assert (
        "A Lucía se le ha acabado el tiempo en «Preparar la mochila» sin terminarla." in html_panel
    )

    tareas_consulta = consulta.tareas_del_dia(lucia, timezone.localdate(), tutor)
    estado_mochila = next(t.estado for t in tareas_consulta if t.asignacion == mochila)
    assert estado_mochila == "Tiempo agotado"
