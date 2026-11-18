"""HU-06-02 · Ver el estado de las tareas de mis estudiantes (AGENDA-64).

Una prueba por cada prueba de aceptación de Jira (PA1 a PA4). Datos de prueba de Lucía
(A01, tutora Ana): mochila 9:00–9:15 (escolar, sin plan B), manos 10:30–10:45, regar
12:00–12:30 (escolar, plan B: «Escuchar música» y «Leer un cuento»), cuento 17:00–17:30
(ocio) y «Poner la mesa» 20:00–20:20 (casa). Luis (profesional) atiende a Lucía y a Hugo.
"""

from datetime import datetime, time

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios as agenda
from apps.agenda.models import Ejecucion, EstadoEjecucion
from apps.seguimiento import servicios
from apps.tareas.models import Tarea
from apps.usuarios.models import Estudiante, Usuario

pytestmark = pytest.mark.django_db

URL = reverse("seguimiento:hoy")


def a_las(hora, minuto=0):
    return timezone.make_aware(datetime.combine(timezone.localdate(), time(hora, minuto)))


@pytest.fixture
def hora(monkeypatch):
    def fijar(h, m=0):
        monkeypatch.setattr(agenda, "ahora", lambda: a_las(h, m))
        return a_las(h, m)

    return fijar


@pytest.fixture
def lucia(datos):
    if timezone.localdate().isoweekday() > 5:
        pytest.skip("Las tareas escolares de los datos de prueba son de lunes a viernes")
    return Estudiante.objects.select_related("usuario").get(codigo_estudiante="A01")


def de(estudiante, nombre):
    return estudiante.asignaciones.get(tarea__nombre=nombre)


def como(client, usuario):
    client.force_login(Usuario.objects.get(username=usuario))
    return client


def estado_de(usuario, codigo, ahora):
    estados = servicios.seguimiento(Usuario.objects.get(username=usuario), ahora)
    return next(e for e in estados if e.estudiante.codigo_estudiante == codigo)


def no_puede_regar(lucia, *, elige=None, por=None, motivo=""):
    regar = de(lucia, "Regar las plantas")
    agenda.no_puedo(lucia, regar.pk, por=por or lucia.usuario, motivo=motivo, ahora_=a_las(12, 5))
    if elige:
        alternativa = Tarea.objects.get(nombre=elige)
        agenda.elegir_plan_b(lucia, regar.pk, alternativa.pk, ahora_=a_las(12, 6))
    return regar


# --- PA1: por estudiante, completadas, pendientes y las que usaron plan B ---


def test_pa1_cuenta_hechas_por_hacer_y_sin_hacer(client, lucia, hora):
    ahora = hora(12, 10)
    Ejecucion.objects.create(
        asignacion=de(lucia, "Preparar la mochila"),
        fecha=ahora.date(),
        estado=EstadoEjecucion.HECHA,
    )
    estado = estado_de("tutor", "A01", ahora)
    # Mochila hecha; manos ya pasó sin hacerse; regar, cuento y mesa, por hacer.
    assert (estado.hechas, estado.sin_hacer, estado.por_hacer) == (1, 1, 3)
    assert estado.total == 5 and estado.con_plan_b == 0 and not estado.avisos

    html = como(client, "tutor").get(URL).content.decode()
    assert "1 hecha" in html and "3 por hacer" in html and "1 sin hacer" in html
    assert "de 5 tareas hoy." in html


def test_pa1_cuenta_las_que_han_usado_plan_b(client, lucia, hora):
    ahora = hora(12, 10)
    no_puede_regar(lucia, elige="Escuchar música")
    estado = estado_de("tutor", "A01", ahora)
    assert estado.con_plan_b == 1
    html = como(client, "tutor").get(URL).content.decode()
    assert "1 con plan B" in html


def test_pa1_las_canceladas_no_cuentan(client, lucia, hora):
    from apps.tareas.models import ExcepcionAsignacion, TipoExcepcion

    ahora = hora(12, 10)
    ExcepcionAsignacion.objects.create(
        asignacion=de(lucia, "Leer un cuento"),
        fecha=ahora.date(),
        tipo=TipoExcepcion.CANCELADA,
        creada_por=Usuario.objects.get(username="tutor"),
    )
    assert estado_de("tutor", "A01", ahora).total == 4


# --- PA2: si no puede completar una tarea, aviso con la tarea y el plan B ---


def test_pa2_aviso_con_el_plan_b_sugerido_mientras_no_elige(client, lucia, hora):
    hora(12, 10)
    no_puede_regar(lucia)
    html = como(client, "tutor").get(URL).content.decode()
    assert "1 estudiante no ha podido hacer una tarea" in html
    assert "No ha podido hacer «Regar las plantas»</strong> (12:05)" in html
    assert "Plan B sugerido: «Escuchar música» (aún no ha elegido)." in html
    # El aviso se distingue con texto e icono, no solo con color.
    assert 'class="seg-est seg-est--aviso"' in html and "⚠" in html


def test_pa2_aviso_con_el_plan_b_elegido(client, lucia, hora):
    hora(12, 10)
    no_puede_regar(lucia, elige="Leer un cuento")
    html = como(client, "tutor").get(URL).content.decode()
    assert "Plan B elegido: «Leer un cuento»." in html
    assert "sugerido" not in html


def test_pa2_sin_plan_b_y_con_el_motivo_de_un_adulto(client, lucia, hora):
    hora(9, 10)
    mochila = de(lucia, "Preparar la mochila")
    tutora = Usuario.objects.get(username="tutor")
    agenda.no_puedo(lucia, mochila.pk, por=tutora, motivo="Falta material", ahora_=a_las(9, 5))
    html = como(client, "tutor").get(URL).content.decode()
    assert "No ha podido hacer «Preparar la mochila»" in html
    assert "No tiene plan B." in html and "Motivo: Falta material." in html


def test_pa2_con_dos_avisos_se_ve_el_ultimo_y_cuantos_mas(client, lucia, hora):
    """Para que la tarjeta quepa en un móvil: el aviso más reciente y «Y 1 aviso más»."""
    hora(12, 10)
    mochila = de(lucia, "Preparar la mochila")
    agenda.no_puedo(lucia, mochila.pk, por=lucia.usuario, ahora_=a_las(9, 5))
    no_puede_regar(lucia)
    html = como(client, "tutor").get(URL).content.decode()
    assert "No ha podido hacer «Regar las plantas»" in html
    assert "«Preparar la mochila»" not in html
    assert "Y 1 aviso más de hoy: en «Ver su día»." in html


def test_pa2_quien_tiene_avisos_sale_el_primero(client, lucia, hora):
    """Lucía no es la primera por nombre en PTVAL 1 (ni la última): con aviso, va arriba."""
    ahora = hora(12, 10)
    estados = servicios.seguimiento(Usuario.objects.get(username="tutor"), ahora)
    assert estados[0].estudiante != lucia
    no_puede_regar(lucia)
    estados = servicios.seguimiento(Usuario.objects.get(username="tutor"), ahora)
    assert estados[0].estudiante == lucia and estados[0].avisos
    assert not any(e.avisos for e in estados[1:])


# --- PA3: el panel muestra solo a mis estudiantes ---


def test_pa3_el_tutor_ve_solo_a_los_suyos(client, lucia, hora):
    hora(12, 10)
    no_puede_regar(lucia)
    tutora = Usuario.objects.get(username="tutor")
    estados = servicios.seguimiento(tutora, a_las(12, 10))
    assert {e.estudiante.tutor_id for e in estados} == {tutora.pk}
    assert len(estados) == Estudiante.objects.filter(tutor=tutora).count() == 6

    html = como(client, "tutor2").get(URL).content.decode()
    assert "Lucía" not in html and "no ha podido" not in html
    assert "Daniela" in html


# --- PA4: un profesional ve el panel de los que atiende, sin poder modificarlo ---


def test_pa4_el_profesional_ve_a_los_que_atiende_y_solo_consulta(client, lucia, hora):
    hora(12, 10)
    no_puede_regar(lucia)
    estados = servicios.seguimiento(Usuario.objects.get(username="profesional"), a_las(12, 10))
    assert {e.estudiante.codigo_estudiante for e in estados} == {"A01", "A04"}

    html = como(client, "profesional").get(URL).content.decode()
    assert "Plan B sugerido: «Escuchar música»" in html
    # Nada que enviar en la pantalla: solo el «Salir» del panel lateral.
    principal = html.split('id="contenido"', 1)[1]
    assert "<form" not in principal and 'method="post"' not in principal
    # «Ver su día» abre su agenda en modo consulta.
    ver = reverse("usuarios:agenda_estudiante", args=["A01"])
    assert f'href="{ver}"' in html
    assert "Solo consulta" in client.get(ver).content.decode()


@pytest.mark.parametrize("quien", ["familiar", "admin", "est-a01"])
def test_los_demas_no_ven_el_seguimiento(client, datos, quien):
    assert como(client, quien).get(URL).status_code == 403


def test_sin_sesion_va_a_la_portada(client, datos):
    respuesta = client.get(URL)
    assert respuesta.status_code == 302 and respuesta["Location"].startswith(reverse("inicio"))


@pytest.mark.parametrize("quien", ["tutor", "profesional"])
def test_esta_en_el_menu_del_tutor_y_del_profesional(client, datos, quien):
    html = como(client, quien).get(reverse("usuarios:panel")).content.decode()
    assert f'href="{URL}"' in html and "Seguimiento de hoy" in html


def test_sin_estudiantes_lo_dice(client, datos):
    nuevo = Usuario.objects.create_user(
        "nuevo", password="Colegio-2026", first_name="Nuevo", rol="profesional"
    )
    client.force_login(nuevo)
    html = client.get(URL).content.decode()
    assert "Todavía no atiendes a ningún estudiante" in html
