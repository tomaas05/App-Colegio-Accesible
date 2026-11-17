"""HU-03-04 · Modificar una tarea planificada (B44 y su pantalla de cambio).

Datos de prueba (cargar_datos_prueba): Lucía (A01), de la tutora Ana («tutor»), tiene
todos los días mochila 9:00–9:15, manos 10:30–10:45, regar 12:00–12:30 y cuento
17:00–17:30, que puso Ana, y «Poner la mesa» 20:00–20:20, que puso su familiar Carmen.
"""

from datetime import time, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.agenda.models import Ejecucion, EstadoEjecucion
from apps.comun.models import Notificacion, TipoAviso
from apps.tareas import planificacion
from apps.tareas.models import ExcepcionAsignacion, TipoExcepcion
from apps.usuarios.models import Estudiante, Usuario

pytestmark = pytest.mark.django_db


@pytest.fixture
def lucia(datos):
    return Estudiante.objects.get(codigo_estudiante="A01")


def entrar(client, usuario):
    client.force_login(Usuario.objects.get(username=usuario))
    return client


def de(estudiante, nombre):
    return estudiante.asignaciones.get(tarea__nombre=nombre)


def url_editar(asignacion, **parametros):
    url = reverse("tareas:editar_asignacion", args=[asignacion.pk])
    if parametros:
        url += "?" + "&".join(f"{k}={v}" for k, v in parametros.items())
    return url


def serie(asignacion, **cambios):
    datos = {
        "alcance": "serie",
        "hora_inicio": asignacion.hora_inicio.strftime("%H:%M"),
        "hora_fin": asignacion.hora_fin.strftime("%H:%M"),
        "dias_semana": [str(d) for d in asignacion.dias_semana],
        "vigencia_desde": asignacion.vigencia_desde.isoformat(),
        "vigencia_hasta": asignacion.vigencia_hasta.isoformat()
        if asignacion.vigencia_hasta
        else "",
    }
    datos.update(cambios)
    return datos


def manana():
    return timezone.localdate() + timedelta(days=1)


def avisos_de(estudiante):
    return Notificacion.objects.filter(destinatario=estudiante.usuario)


def proximo_dia_lectivo():
    """El próximo día de lunes a viernes a partir de mañana (dentro de los 14 de la lista)."""
    dia = manana()
    while dia.isoweekday() > 5:
        dia += timedelta(days=1)
    return dia


# --- Toda la serie --------------------------------------------------------------------


def test_cambiar_la_serie_cambia_la_agenda_y_avisa_al_estudiante(client, lucia):
    regar = de(lucia, "Regar las plantas")
    respuesta = entrar(client, "tutor").post(
        url_editar(regar), serie(regar, hora_inicio="12:45", hora_fin="13:15")
    )
    assert respuesta.status_code == 302
    regar.refresh_from_db()
    assert (regar.hora_inicio, regar.hora_fin) == (time(12, 45), time(13, 15))

    # PA1: la agenda del estudiante la tiene a la nueva hora (hoy y cualquier otro día).
    hoy = planificacion.ocurrencias_del_dia(lucia, timezone.localdate())
    assert [o.hora_inicio for o in hoy if o.asignacion == regar] == [time(12, 45)]

    # PA4: un aviso corto con el pictograma de la tarea.
    aviso = avisos_de(lucia).get()
    assert aviso.tipo == TipoAviso.CAMBIO and aviso.tarea == regar.tarea and not aviso.leida
    assert aviso.mensaje == "«Regar las plantas» cambia: ahora es de 12:45 a 13:15, todos los días."


def test_cambiar_los_dias_de_la_serie(client, lucia):
    regar = de(lucia, "Regar las plantas")
    entrar(client, "tutor").post(url_editar(regar), serie(regar, dias_semana=["1", "3"]))
    regar.refresh_from_db()
    assert regar.dias_semana == [1, 3]
    assert "los lunes y miércoles" in avisos_de(lucia).get().mensaje


def test_guardar_sin_cambiar_nada_no_avisa(client, lucia):
    regar = de(lucia, "Regar las plantas")
    respuesta = entrar(client, "tutor").post(url_editar(regar), serie(regar), follow=True)
    assert "No has cambiado nada." in respuesta.content.decode()
    assert not avisos_de(lucia).exists()


def test_un_solape_no_se_guarda_y_dice_con_que_tarea(client, lucia):
    """PA3: si se solapa con otra tarea, no se guarda y se dice con cuál."""
    regar = de(lucia, "Regar las plantas")
    respuesta = entrar(client, "tutor").post(
        url_editar(regar), serie(regar, hora_inicio="10:40", hora_fin="11:00")
    )
    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    assert "Se solapa con «Lavarse las manos» (de 10:30 a 10:45" in html
    regar.refresh_from_db()
    assert regar.hora_inicio == time(12, 0)
    assert not avisos_de(lucia).exists()


def test_la_hora_de_fin_tiene_que_ser_despues_de_la_de_inicio(client, lucia):
    regar = de(lucia, "Regar las plantas")
    respuesta = entrar(client, "tutor").post(
        url_editar(regar), serie(regar, hora_inicio="13:00", hora_fin="12:30")
    )
    assert respuesta.status_code == 200
    regar.refresh_from_db()
    assert regar.hora_inicio == time(12, 0)


def test_hay_que_elegir_al_menos_un_dia(client, lucia):
    regar = de(lucia, "Regar las plantas")
    respuesta = entrar(client, "tutor").post(url_editar(regar), serie(regar, dias_semana=[]))
    assert "Elige al menos un día." in respuesta.content.decode()


def test_el_aula_ya_no_se_cambia_aqui(client, lucia):
    """Úrsula, 17/11: el aula va con la clase del estudiante, no con la tarea."""
    html = entrar(client, "tutor").get(url_editar(de(lucia, "Regar las plantas"))).content
    assert b"aula" not in html.lower()


def test_no_se_cambia_la_serie_mientras_la_esta_haciendo(client, lucia):
    regar = de(lucia, "Regar las plantas")
    Ejecucion.objects.create(
        asignacion=regar,
        fecha=timezone.localdate(),
        estado=EstadoEjecucion.EN_CURSO,
        inicio_real=timezone.now(),
    )
    respuesta = entrar(client, "tutor").post(
        url_editar(regar), serie(regar, hora_inicio="12:45", hora_fin="13:15"), follow=True
    )
    assert "ya ha empezado «Regar las plantas» hoy" in respuesta.content.decode()
    regar.refresh_from_db()
    assert regar.hora_inicio == time(12, 0)


# --- Solo este día -----------------------------------------------------------------------


def test_cambiar_solo_un_dia_no_toca_los_demas(client, lucia):
    regar, dia = de(lucia, "Regar las plantas"), manana()
    respuesta = entrar(client, "tutor").post(
        url_editar(regar, alcance="dia", fecha=dia.isoformat()),
        {"hora_inicio": "13:00", "hora_fin": "13:30"},
    )
    assert respuesta.status_code == 302
    regar.refresh_from_db()
    assert regar.hora_inicio == time(12, 0)  # la serie sigue igual

    excepcion = ExcepcionAsignacion.objects.get(asignacion=regar, fecha=dia)
    assert excepcion.tipo == TipoExcepcion.MODIFICADA
    ese_dia = {o.asignacion: o for o in planificacion.ocurrencias_del_dia(lucia, dia)}[regar]
    assert (ese_dia.hora_inicio, ese_dia.cambiada) == (time(13, 0), True)
    otro_dia = {
        o.asignacion: o for o in planificacion.ocurrencias_del_dia(lucia, dia + timedelta(days=1))
    }[regar]
    assert (otro_dia.hora_inicio, otro_dia.cambiada) == (time(12, 0), False)

    aviso = avisos_de(lucia).get()
    assert aviso.mensaje == (
        f"«Regar las plantas» cambia el {planificacion.fecha_en_texto(dia)}: será de 13:00 a 13:30."
    )


def test_volver_a_las_horas_de_siempre_quita_el_cambio_de_ese_dia(client, lucia):
    regar, dia = de(lucia, "Regar las plantas"), manana()
    url = url_editar(regar, alcance="dia", fecha=dia.isoformat())
    entrar(client, "tutor").post(url, {"hora_inicio": "13:00", "hora_fin": "13:30"})
    client.post(url, {"hora_inicio": "12:00", "hora_fin": "12:30"})
    assert not ExcepcionAsignacion.objects.filter(asignacion=regar).exists()
    assert avisos_de(lucia).count() == 2  # el estudiante sabe que vuelve a ser como siempre


def test_un_solape_de_un_dia_tiene_en_cuenta_los_cambios_de_ese_dia(client, lucia):
    """Si ese día otra tarea se ha movido, el solape se mira con sus horas de ese día."""
    manos, regar, dia = de(lucia, "Lavarse las manos"), de(lucia, "Regar las plantas"), manana()
    entrar(client, "tutor").post(
        url_editar(manos, alcance="dia", fecha=dia.isoformat()),
        {"hora_inicio": "13:00", "hora_fin": "13:15"},
    )
    respuesta = client.post(
        url_editar(regar, alcance="dia", fecha=dia.isoformat()),
        {"hora_inicio": "13:05", "hora_fin": "13:20"},
    )
    assert "Se solapa con «Lavarse las manos» (de 13:00 a 13:15" in respuesta.content.decode()

    # Y a la hora de siempre de «manos» ese día ya hay hueco.
    respuesta = client.post(
        url_editar(regar, alcance="dia", fecha=dia.isoformat()),
        {"hora_inicio": "10:30", "hora_fin": "10:45"},
    )
    assert respuesta.status_code == 302


def test_un_cambio_de_la_serie_choca_con_el_cambio_de_un_dia_de_otra(client, lucia):
    manos, regar, dia = de(lucia, "Lavarse las manos"), de(lucia, "Regar las plantas"), manana()
    entrar(client, "tutor").post(
        url_editar(manos, alcance="dia", fecha=dia.isoformat()),
        {"hora_inicio": "13:00", "hora_fin": "13:15"},
    )
    respuesta = client.post(url_editar(regar), serie(regar, hora_inicio="13:00", hora_fin="13:30"))
    assert respuesta.status_code == 200
    assert f"el {planificacion.fecha_en_texto(dia)}" in respuesta.content.decode()


@pytest.mark.parametrize("dias", [-1, None])
def test_solo_este_dia_necesita_un_dia_valido(client, lucia, dias):
    regar = de(lucia, "Regar las plantas")
    fecha = (timezone.localdate() + timedelta(days=dias)).isoformat() if dias else "x"
    respuesta = entrar(client, "tutor").post(
        url_editar(regar, alcance="dia", fecha=fecha),
        {"hora_inicio": "13:00", "hora_fin": "13:30"},
        follow=True,
    )
    assert "Ese día no se puede cambiar." in respuesta.content.decode()
    assert not ExcepcionAsignacion.objects.exists()


def test_no_se_cambia_un_dia_que_ya_ha_empezado(client, lucia):
    regar, hoy = de(lucia, "Regar las plantas"), timezone.localdate()
    Ejecucion.objects.create(
        asignacion=regar, fecha=hoy, estado=EstadoEjecucion.HECHA, inicio_real=timezone.now()
    )
    respuesta = entrar(client, "tutor").post(
        url_editar(regar, alcance="dia", fecha=hoy.isoformat()),
        {"hora_inicio": "13:00", "hora_fin": "13:30"},
        follow=True,
    )
    assert "ya ha empezado «Regar las plantas» ese día" in respuesta.content.decode()
    assert not ExcepcionAsignacion.objects.exists()


def test_el_familiar_no_pone_una_tarea_de_casa_en_horario_escolar(client, lucia):
    mesa, dia = de(lucia, "Poner la mesa"), proximo_dia_lectivo()
    respuesta = entrar(client, "familiar").post(
        url_editar(mesa, alcance="dia", fecha=dia.isoformat()),
        {"hora_inicio": "10:00", "hora_fin": "10:20"},
    )
    assert respuesta.status_code == 200
    assert "Esas horas son de horario escolar." in respuesta.content.decode()
    assert not ExcepcionAsignacion.objects.exists()


# --- Quién puede cambiar qué ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("usuario", "tarea", "puede"),
    [
        ("tutor", "Regar las plantas", True),
        ("tutor", "Poner la mesa", False),  # RF3.3.5: la del familiar la ve, no la cambia
        ("tutor2", "Regar las plantas", False),  # no es su estudiante
        ("profesional", "Regar las plantas", False),  # no la ha puesto él
        ("familiar", "Poner la mesa", True),
        ("familiar", "Regar las plantas", False),
        ("familiar2", "Poner la mesa", False),
    ],
)
def test_quien_puede_cambiar_cada_tarea(client, lucia, usuario, tarea, puede):
    asignacion = de(lucia, tarea)
    respuesta = entrar(client, usuario).get(url_editar(asignacion))
    assert respuesta.status_code == (200 if puede else 404)
    # Y por POST tampoco.
    respuesta = client.post(url_editar(asignacion), serie(asignacion, hora_inicio="21:00"))
    if not puede:
        assert respuesta.status_code == 404
        asignacion.refresh_from_db()
        assert asignacion.hora_inicio != time(21, 0)


def test_un_estudiante_no_entra(client, lucia):
    respuesta = entrar(client, "est-a01").get(url_editar(de(lucia, "Regar las plantas")))
    assert respuesta.status_code == 403


# --- Lista de tareas planificadas (B44) --------------------------------------------------


def test_la_lista_solo_trae_lo_que_puedo_cambiar(client, lucia):
    html = entrar(client, "tutor").get(reverse("tareas:tareas_planificadas")).content.decode()
    assert "Regar las plantas" in html and "Poner la mesa" not in html
    html = entrar(client, "familiar").get(reverse("tareas:tareas_planificadas")).content.decode()
    assert "Poner la mesa" in html and "Regar las plantas" not in html


def test_con_un_dia_elegido_se_ofrece_solo_este_dia_o_toda_la_serie(client, lucia):
    dia = manana().isoformat()
    html = (
        entrar(client, "tutor")
        .get(reverse("tareas:tareas_planificadas"), {"estudiante": lucia.pk, "fecha": dia})
        .content.decode()
    )
    assert "Solo este día" in html and "Toda la serie" in html
    assert f"({planificacion.fecha_en_texto(manana())})" in html  # para el lector de pantalla
    sin_dia = client.get(reverse("tareas:tareas_planificadas")).content.decode()
    assert "Solo este día" not in sin_dia and "Para cambiar un solo día, elige el día" in sin_dia


def test_la_lista_muestra_las_horas_cambiadas_de_ese_dia(client, lucia):
    regar, dia = de(lucia, "Regar las plantas"), manana()
    ExcepcionAsignacion.objects.create(
        asignacion=regar,
        fecha=dia,
        tipo=TipoExcepcion.MODIFICADA,
        hora_inicio=time(13, 0),
        hora_fin=time(13, 30),
        creada_por=Usuario.objects.get(username="tutor"),
    )
    html = (
        entrar(client, "tutor")
        .get(reverse("tareas:tareas_planificadas"), {"fecha": dia.isoformat()})
        .content.decode()
    )
    assert "13:00" in html and "cambiada ese día" in html
