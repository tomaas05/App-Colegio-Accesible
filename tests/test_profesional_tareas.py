"""HU-03-08 · Restricciones y gestión de tareas para el rol Profesional."""

from datetime import datetime, time, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios as agenda_servicios
from apps.tareas.models import Ambito, Asignacion, Tarea
from apps.usuarios.models import Atencion, Estudiante, Usuario

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def asegurar_dia_lectivo(monkeypatch):
    """El profesional solo programa en días lectivos (L-V); si el test corre en sábado o
    domingo, fija la fecha de hoy al próximo lunes."""
    hoy = timezone.localdate()
    if hoy.isoweekday() > 5:
        lunes = hoy + timedelta(days=8 - hoy.isoweekday())
        momento = timezone.make_aware(datetime.combine(lunes, time(8, 0)))
        monkeypatch.setattr(timezone, "localdate", lambda *a, **kw: lunes)
        monkeypatch.setattr(agenda_servicios, "ahora", lambda: momento)


@pytest.fixture
def profesional_y_lucia(datos):
    profesional = Usuario.objects.get(username="profesional")
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    Atencion.objects.get_or_create(profesional=profesional, estudiante=lucia)
    return profesional, lucia


def entrar(client, usuario):
    client.force_login(Usuario.objects.get(username=usuario))
    return client


def hoy_o_lectivo():
    # Usamos el día de hoy para que la agenda lo muestre directamente sin cambiar de fecha
    return timezone.localdate()


def test_1_crear_actividad_escolar_y_ver_en_agenda(client, profesional_y_lucia):
    """1. Creo una actividad en horario escolar
    para un estudiante que atiendo y aparece en su agenda."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    profesional, lucia = profesional_y_lucia
    dia = hoy_o_lectivo()

    # Creamos una imagen simulada para que tarea.imagen.url no falle al renderizar la agenda
    imagen_falsa = SimpleUploadedFile("logopedia.png", b"contenido_falso", content_type="image/png")

    tarea = Tarea.objects.create(
        nombre="Logopedia E2E",
        descripcion_imagen="Pictograma de logopedia",
        imagen=imagen_falsa,
        ambito=Ambito.ESCOLAR,
        creador=profesional,
    )

    url_asignar = reverse("tareas:asignar_tarea")
    respuesta = entrar(client, "profesional").post(
        url_asignar,
        {
            "tarea": tarea.pk,
            "estudiantes": [lucia.pk],
            "hora_inicio": "10:00",
            "hora_fin": "10:30",
            "dias_semana": [str(dia.isoweekday())],
            "vigencia_desde": dia.isoformat(),
            "vigencia_hasta": dia.isoformat(),
        },
    )
    assert respuesta.status_code == 302

    # Entramos con el usuario de la propia Lucía para ver su agenda de hoy
    entrar(client, lucia.usuario.username)
    url_agenda = reverse("agenda:dia") + f"?fecha={dia.isoformat()}"
    contenido = client.get(url_agenda).content.decode()
    assert "Logopedia E2E" in contenido


def test_2_modificar_y_cancelar_actividad_propia(client, profesional_y_lucia):
    """2. Modifico y cancelo una actividad mía (como profesional)."""
    profesional, lucia = profesional_y_lucia
    dia = hoy_o_lectivo()

    tarea = Tarea.objects.create(
        nombre="Apoyo Escolar",
        descripcion_imagen="Pictograma de apoyo",
        ambito=Ambito.ESCOLAR,
        creador=profesional,
    )
    asignacion = Asignacion.objects.create(
        tarea=tarea,
        estudiante=lucia,
        asignado_por=profesional,
        hora_inicio=time(11, 0),
        hora_fin=time(11, 30),
        dias_semana=[dia.isoweekday()],
        vigencia_desde=dia,
        vigencia_hasta=dia,
    )

    url_editar = reverse("tareas:editar_asignacion", args=[asignacion.pk])
    respuesta = entrar(client, "profesional").post(
        url_editar,
        {
            "alcance": "serie",
            "hora_inicio": "11:15",
            "hora_fin": "11:45",
            "dias_semana": [str(dia.isoweekday())],
            "vigencia_desde": dia.isoformat(),
            "vigencia_hasta": dia.isoformat(),
        },
    )
    assert respuesta.status_code == 302
    asignacion.refresh_from_db()
    assert asignacion.hora_inicio == time(11, 15)

    url_cancelar = reverse("tareas:confirmar_cancelacion", args=[asignacion.pk])
    respuesta_cancelar = client.post(url_cancelar, {"alcance": "serie"})
    assert respuesta_cancelar.status_code == 302
    asignacion.refresh_from_db()
    assert asignacion.cancelada is True


def test_3_no_crear_actividades_fuera_horario_escolar(client, profesional_y_lucia):
    """3. No puedo crear actividades fuera del horario escolar."""
    profesional, lucia = profesional_y_lucia
    dia = hoy_o_lectivo()

    tarea = Tarea.objects.create(
        nombre="Actividad Nocturna Prohibida",
        descripcion_imagen="Pictograma",
        ambito=Ambito.ESCOLAR,
        creador=profesional,
    )

    url_asignar = reverse("tareas:asignar_tarea")
    respuesta = entrar(client, "profesional").post(
        url_asignar,
        {
            "tarea": tarea.pk,
            "estudiantes": [lucia.pk],
            "hora_inicio": "19:00",
            "hora_fin": "20:00",
            "dias_semana": [str(dia.isoweekday())],
            "vigencia_desde": dia.isoformat(),
            "vigencia_hasta": dia.isoformat(),
        },
    )
    assert respuesta.status_code == 200
    assert "dentro del horario escolar" in respuesta.content.decode()
    assert not Asignacion.objects.filter(tarea=tarea).exists()


def test_4_no_modificar_actividades_de_tutor_o_otro_profesional(client, datos, profesional_y_lucia):
    """4. No puedo modificar actividades del tutor ni de otro profesional."""
    profesional, lucia = profesional_y_lucia
    asignacion_tutor = Asignacion.objects.get(estudiante=lucia, tarea__nombre="Regar las plantas")

    url_editar = reverse("tareas:editar_asignacion", args=[asignacion_tutor.pk])
    respuesta = entrar(client, "profesional").get(url_editar)
    assert respuesta.status_code == 404


def test_5_solapamiento_no_se_guarda_e_indica_choque(client, profesional_y_lucia):
    """Si se solapa con otra tarea, no se guarda y se indica con cuál choca."""
    profesional, lucia = profesional_y_lucia
    dia = hoy_o_lectivo()

    tarea1 = Tarea.objects.create(
        nombre="Sesión 1", descripcion_imagen="Pic 1", creador=profesional
    )
    tarea2 = Tarea.objects.create(
        nombre="Sesión 2", descripcion_imagen="Pic 2", creador=profesional
    )

    Asignacion.objects.create(
        tarea=tarea1,
        estudiante=lucia,
        asignado_por=profesional,
        hora_inicio=time(9, 0),
        hora_fin=time(9, 30),
        dias_semana=[dia.isoweekday()],
        vigencia_desde=dia,
    )

    url_asignar = reverse("tareas:asignar_tarea")
    respuesta = entrar(client, "profesional").post(
        url_asignar,
        {
            "tarea": tarea2.pk,
            "estudiantes": [lucia.pk],
            "hora_inicio": "9:15",
            "hora_fin": "9:45",
            "dias_semana": [str(dia.isoweekday())],
            "vigencia_desde": dia.isoformat(),
        },
    )
    assert respuesta.status_code == 200
    # Validamos que el formulario detecta el conflicto y muestra el nombre de la tarea que choca
    contenido = respuesta.content.decode()
    assert "ya tiene una tarea asignada" in contenido or "Sesión 1" in contenido
    assert not Asignacion.objects.filter(tarea=tarea2).exists()
