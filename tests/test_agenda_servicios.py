"""HU-02-01 a HU-02-04: lógica de la agenda (apps/agenda/servicios.py)."""

from datetime import datetime, time, timedelta

import pytest
from django.utils import timezone

from apps.agenda import servicios
from apps.agenda.models import Ejecucion, EstadoEjecucion, EstadoPaso
from apps.agenda.servicios import ErrorDeAgenda
from apps.tareas.models import Asignacion
from apps.usuarios.models import Estudiante

pytestmark = pytest.mark.django_db


def a_las(hora, minuto=0):
    """Hoy a esa hora, en la zona del centro. Los datos de prueba valen todos los días."""
    return timezone.make_aware(datetime.combine(timezone.localdate(), time(hora, minuto)))


@pytest.fixture
def margen_15(monkeypatch):
    """Permite empezar 15 minutos antes, para probar las reglas de ese margen."""
    monkeypatch.setattr(servicios, "MARGEN_EMPEZAR_ANTES", timedelta(minutes=15))


@pytest.fixture
def lucia(datos):
    return Estudiante.objects.get(codigo_estudiante="A01")


def asignacion(estudiante, nombre):
    return estudiante.asignaciones.get(tarea__nombre=nombre)


# Datos de prueba de Lucía: mochila 9:00–9:15, manos 10:30–10:45,
# regar 12:00–12:30, cuento 17:00–17:30 y poner la mesa 20:00–20:20.


def test_agenda_ordenada_con_actual_anterior_y_siguiente(lucia):
    agenda = servicios.agenda_del_dia(lucia, a_las(10, 35))
    assert [t.tarea.nombre for t in agenda.tareas] == [
        "Preparar la mochila",
        "Lavarse las manos",
        "Regar las plantas",
        "Leer un cuento",
        "Poner la mesa",
    ]
    assert agenda.actual.tarea.nombre == "Lavarse las manos"
    assert agenda.anterior.tarea.nombre == "Preparar la mochila"
    assert agenda.siguiente.tarea.nombre == "Regar las plantas"


def test_sin_tarea_actual_no_hay_destacada(lucia):
    agenda = servicios.agenda_del_dia(lucia, a_las(11, 0))
    assert agenda.actual is None
    assert agenda.siguiente.tarea.nombre == "Regar las plantas"


def test_antes_de_la_primera_no_hay_anterior_y_despues_de_la_ultima_no_hay_siguiente(lucia):
    assert servicios.agenda_del_dia(lucia, a_las(7, 0)).anterior is None
    assert servicios.agenda_del_dia(lucia, a_las(23, 0)).siguiente is None


def test_si_caben_todas_se_ven_todas(lucia):
    agenda = servicios.agenda_del_dia(lucia, a_las(12, 5))  # 5 tareas, máximo 6
    assert len(agenda.visibles) == 5 and agenda.restantes == 0


def test_maximo_de_tarjetas_del_perfil_y_cuantas_quedan(lucia):
    perfil = lucia.perfil
    perfil.max_tarjetas = 3
    perfil.save()
    agenda = servicios.agenda_del_dia(lucia, a_las(10, 35))
    # Empieza en la anterior: mochila, manos, regar. Quedan cuento y mesa.
    assert [t.tarea.nombre for t in agenda.visibles] == [
        "Preparar la mochila",
        "Lavarse las manos",
        "Regar las plantas",
    ]
    assert agenda.restantes == 2


def test_con_una_sola_tarjeta_se_ve_la_actual(lucia):
    perfil = lucia.perfil
    perfil.max_tarjetas = 1
    perfil.save()
    agenda = servicios.agenda_del_dia(lucia, a_las(10, 35))
    assert [t.tarea.nombre for t in agenda.visibles] == ["Lavarse las manos"]
    assert agenda.restantes == 3


def test_aviso_de_la_siguiente_10_minutos_antes(lucia):
    # RF2.10.1. Regar las plantas empieza a las 12:00.
    assert servicios.agenda_del_dia(lucia, a_las(11, 50)).aviso.tarea.nombre == "Regar las plantas"
    assert servicios.agenda_del_dia(lucia, a_las(11, 49)).aviso is None


def test_estado_como_en_el_boceto(lucia):
    manos = asignacion(lucia, "Lavarse las manos")
    assert servicios.tarea_del_dia(lucia, manos.pk, a_las(10, 0)).etiqueta == "Pendiente"
    # Pendiente y en su hora: «Ahora», como la tarjeta del boceto B06.
    assert servicios.tarea_del_dia(lucia, manos.pk, a_las(10, 35)).etiqueta == "Ahora"
    assert servicios.tarea_del_dia(lucia, manos.pk, a_las(10, 50)).etiqueta == "Vencida"


def test_titulo_en_espanol(lucia):
    assert servicios.titulo_de_hoy(a_las(10)).startswith("Hoy, ")
    assert servicios.titulo_de_hoy(a_las(10))[5:] in servicios.DIAS


def test_texto_para_escuchar_lee_nombre_descripcion_y_pasos(lucia):
    mochila = asignacion(lucia, "Preparar la mochila")
    texto = servicios.tarea_del_dia(lucia, mochila.pk, a_las(9, 5)).texto_para_escuchar
    assert texto.startswith("Preparar la mochila. Meter en la mochila lo que necesito para hoy.")
    assert "Paso 4: Cerrar la mochila." in texto
    assert "○" not in texto


def test_antes_y_despues_de_una_tarea(lucia):
    agenda = servicios.agenda_del_dia(lucia, a_las(10, 0))
    mochila = asignacion(lucia, "Preparar la mochila")
    t, antes, despues = servicios.con_contexto(agenda, mochila.pk)
    assert antes is None and despues.tarea.nombre == "Lavarse las manos"
    mesa = asignacion(lucia, "Poner la mesa")
    t, antes, despues = servicios.con_contexto(agenda, mesa.pk)
    assert antes.tarea.nombre == "Leer un cuento" and despues is None


def test_no_incluye_tareas_de_otros_dias(lucia):
    hoy = timezone.localdate()
    a = asignacion(lucia, "Leer un cuento")
    a.dias_semana = [d for d in range(1, 8) if d != hoy.isoweekday()]
    a.save()
    nombres = [t.tarea.nombre for t in servicios.agenda_del_dia(lucia, a_las(10, 0)).tareas]
    assert "Leer un cuento" not in nombres


def test_pendiente_pasada_su_hora_es_vencida_y_en_curso_es_tiempo_agotado(lucia):
    manos = asignacion(lucia, "Lavarse las manos")
    assert servicios.tarea_del_dia(lucia, manos.pk, a_las(10, 40)).estado == "pendiente"
    assert servicios.tarea_del_dia(lucia, manos.pk, a_las(10, 50)).estado == "vencida"
    servicios.empezar(lucia, manos.pk, a_las(10, 31))
    assert servicios.tarea_del_dia(lucia, manos.pk, a_las(10, 40)).estado == "en_curso"
    assert servicios.tarea_del_dia(lucia, manos.pk, a_las(10, 50)).estado == "tiempo_agotado"


def test_empezar_registra_la_hora_real(lucia):
    manos = asignacion(lucia, "Lavarse las manos")
    ejecucion = servicios.empezar(lucia, manos.pk, a_las(10, 32))
    assert ejecucion.estado == EstadoEjecucion.EN_CURSO
    assert ejecucion.inicio_real == a_las(10, 32)


def test_se_puede_empezar_hasta_15_minutos_antes(lucia, margen_15):
    manos = asignacion(lucia, "Lavarse las manos")  # 10:30
    with pytest.raises(ErrorDeAgenda, match="10:15"):
        servicios.empezar(lucia, manos.pk, a_las(10, 14))
    assert not Ejecucion.objects.filter(asignacion=manos, fecha=timezone.localdate()).exists()
    ejecucion = servicios.empezar(lucia, manos.pk, a_las(10, 15))
    assert ejecucion.inicio_real == a_las(10, 15)
    # La empezada antes es la actual; el final no se mueve (RF2.7.2).
    agenda = servicios.agenda_del_dia(lucia, a_las(10, 16))
    assert agenda.actual.tarea.nombre == "Lavarse las manos"
    assert agenda.actual.fin == a_las(10, 45)


@pytest.fixture
def seguidas(lucia):
    """Regar 12:00–12:30 y, justo después, el cuento 12:30–13:00 (las dos sin pasos)."""
    cuento = asignacion(lucia, "Leer un cuento")
    cuento.hora_inicio, cuento.hora_fin = time(12, 30), time(13, 0)
    cuento.save()
    return asignacion(lucia, "Regar las plantas"), cuento


def test_no_se_empieza_antes_si_a_otra_le_toca_ahora(lucia, seguidas, margen_15):
    regar, cuento = seguidas
    with pytest.raises(ErrorDeAgenda, match="Ahora toca «Regar las plantas»"):
        servicios.empezar(lucia, cuento.pk, a_las(12, 20))


def test_no_se_empieza_antes_si_otra_esta_en_curso(lucia, seguidas, margen_15):
    regar, cuento = seguidas
    servicios.empezar(lucia, regar.pk, a_las(12, 18))
    with pytest.raises(ErrorDeAgenda, match="Primero termina «Regar las plantas»"):
        servicios.empezar(lucia, cuento.pk, a_las(12, 20))
    t = servicios.con_contexto(servicios.agenda_del_dia(lucia, a_las(12, 20)), cuento.pk)[0]
    assert t.esperando and not t.puede_empezar


def test_al_terminar_la_anterior_se_puede_empezar_la_siguiente_antes(lucia, seguidas, margen_15):
    regar, cuento = seguidas
    servicios.empezar(lucia, regar.pk, a_las(12, 5))
    servicios.terminar(lucia, regar.pk, a_las(12, 20))
    servicios.empezar(lucia, cuento.pk, a_las(12, 21))
    agenda = servicios.agenda_del_dia(lucia, a_las(12, 22))
    assert agenda.actual.tarea.nombre == "Leer un cuento"
    assert agenda.anterior.tarea.nombre == "Regar las plantas"
    assert [t.tarea.nombre for t in agenda.tareas if t.destacada] == ["Leer un cuento"]


def test_con_margen_cero_es_como_rf_2_3_2(lucia, monkeypatch):
    monkeypatch.setattr(servicios, "MARGEN_EMPEZAR_ANTES", timedelta(0))
    manos = asignacion(lucia, "Lavarse las manos")
    with pytest.raises(ErrorDeAgenda, match="10:30"):
        servicios.empezar(lucia, manos.pk, a_las(10, 29))


def test_no_se_puede_empezar_despues_de_la_hora_de_fin(lucia):
    manos = asignacion(lucia, "Lavarse las manos")
    with pytest.raises(ErrorDeAgenda):
        servicios.empezar(lucia, manos.pk, a_las(10, 45))


def test_reabrir_conserva_la_hora_de_inicio_original(lucia):
    manos = asignacion(lucia, "Lavarse las manos")
    servicios.empezar(lucia, manos.pk, a_las(10, 31))
    ejecucion = servicios.empezar(lucia, manos.pk, a_las(10, 40))
    assert ejecucion.inicio_real == a_las(10, 31)


def test_terminar_pasa_a_hecha(lucia):
    regar = asignacion(lucia, "Regar las plantas")
    servicios.empezar(lucia, regar.pk, a_las(12, 1))
    ejecucion = servicios.terminar(lucia, regar.pk, a_las(12, 20))
    assert ejecucion.estado == EstadoEjecucion.HECHA
    assert ejecucion.fin_real == a_las(12, 20)


def test_no_se_puede_terminar_sin_empezar(lucia):
    regar = asignacion(lucia, "Regar las plantas")
    with pytest.raises(ErrorDeAgenda):
        servicios.terminar(lucia, regar.pk, a_las(12, 20))


def test_no_se_puede_terminar_con_pasos_sin_hacer(lucia):
    mochila = asignacion(lucia, "Preparar la mochila")
    ejecucion = servicios.empezar(lucia, mochila.pk, a_las(9, 1))
    assert ejecucion.pasos.count() == 4
    with pytest.raises(ErrorDeAgenda, match="4 pasos"):
        servicios.terminar(lucia, mochila.pk, a_las(9, 10))
    ejecucion.pasos.update(estado=EstadoPaso.HECHO)  # esto lo hará HU-02-05 (Javi)
    assert servicios.terminar(lucia, mochila.pk, a_las(9, 10)).estado == EstadoEjecucion.HECHA


def test_tras_terminar_la_siguiente_es_la_actual_cuando_llega_su_hora(lucia):
    regar = asignacion(lucia, "Regar las plantas")
    ejecucion = servicios.empezar(lucia, regar.pk, a_las(12, 0))
    ejecucion.pasos.update(estado=EstadoPaso.HECHO)
    servicios.terminar(lucia, regar.pk, a_las(12, 10))
    assert servicios.agenda_del_dia(lucia, a_las(12, 10)).actual.tarea.nombre == "Regar las plantas"
    assert servicios.agenda_del_dia(lucia, a_las(17, 5)).actual.tarea.nombre == "Leer un cuento"


def test_un_estudiante_no_toca_las_tareas_de_otro(datos, lucia):
    mateo = Estudiante.objects.get(codigo_estudiante="A02")
    ajena = asignacion(lucia, "Regar las plantas")
    with pytest.raises(Asignacion.DoesNotExist):
        servicios.tarea_del_dia(mateo, ajena.pk, a_las(12, 5))
    with pytest.raises(Asignacion.DoesNotExist):
        servicios.empezar(mateo, ajena.pk, a_las(12, 5))
    with pytest.raises(Asignacion.DoesNotExist):
        servicios.terminar(mateo, ajena.pk, a_las(12, 5))


def test_una_asignacion_que_no_toca_hoy_no_se_abre(lucia):
    hoy = timezone.localdate()
    cuento = asignacion(lucia, "Leer un cuento")
    cuento.dias_semana = [d for d in range(1, 8) if d != hoy.isoweekday()]
    cuento.save()
    with pytest.raises(Asignacion.DoesNotExist):
        servicios.tarea_del_dia(lucia, cuento.pk, a_las(17, 5))


def test_por_defecto_se_puede_empezar_15_minutos_antes(lucia):
    """RF2.3.2 cambiado: se puede empezar desde 15 minutos antes de la hora de inicio."""
    manos = asignacion(lucia, "Lavarse las manos")  # 10:30
    with pytest.raises(ErrorDeAgenda, match="10:15"):
        servicios.empezar(lucia, manos.pk, a_las(10, 14))
    assert servicios.empezar(lucia, manos.pk, a_las(10, 15)).inicio_real == a_las(10, 15)
