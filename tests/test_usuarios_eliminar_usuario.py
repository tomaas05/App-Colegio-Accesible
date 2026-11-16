"""HU-01-03. Eliminar un usuario (AGENDA-129).

Una prueba por cada prueba de aceptación de Jira (PA1 a PA5) y las de qué impide eliminar
una cuenta. Solo el administrador elimina cuentas. Datos de prueba: `admin` / «despega2026».
"""

import pytest
from django.core.files.storage import default_storage
from django.test import Client
from django.urls import reverse

from apps.agenda.models import Ejecucion, EjecucionPaso
from apps.perfil.models import Perfil
from apps.tareas.models import Asignacion
from apps.usuarios.models import Atencion, Estudiante, Usuario

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(client, datos):
    client.force_login(Usuario.objects.get(username="admin"))
    return client


def url_eliminar(cuenta):
    return reverse("usuarios:eliminar", args=[cuenta.pk])


def url_editar(cuenta):
    return reverse("usuarios:editar", args=[cuenta.pk])


def estudiante(codigo="A01"):
    return Estudiante.objects.select_related("usuario").get(codigo_estudiante=codigo)


# --- PA1: elimino la cuenta de un estudiante y ya no puede entrar ni aparece en las listas ---


def test_pa1_el_estudiante_eliminado_no_puede_entrar_ni_aparece(admin):
    lucia = estudiante()
    clase, usuario_pk = lucia.clase_id, lucia.usuario_id
    respuesta = admin.post(url_eliminar(lucia.usuario))
    assert respuesta.status_code == 302 and respuesta["Location"] == reverse("usuarios:lista")
    assert not Usuario.objects.filter(pk=usuario_pk).exists()

    lista = admin.get(reverse("usuarios:lista")).content.decode()
    assert "Cuenta eliminada: Lucía Fernández." in lista
    assert "Código A01" not in lista
    assert "Lucía" not in admin.get(reverse("usuarios:avatares", args=[clase])).content.decode()
    assert admin.get(reverse("usuarios:entrar_estudiante", args=["A01"])).status_code == 404


def test_pa1_si_tenia_la_sesion_abierta_la_pierde(admin):
    lucia = estudiante()
    suya = Client()
    suya.force_login(lucia.usuario)
    assert suya.get(reverse("agenda:dia")).status_code == 200
    admin.post(url_eliminar(lucia.usuario))
    assert suya.get(reverse("agenda:dia")).status_code == 302  # a la portada


def test_pa1_deja_de_salir_al_profesional_y_al_tutor(admin):
    lucia = estudiante()
    admin.post(url_eliminar(lucia.usuario))
    profesional = Client()
    profesional.force_login(Usuario.objects.get(username="profesional"))
    html = profesional.get(reverse("usuarios:mis_estudiantes")).content.decode()
    assert "Lucía" not in html
    tutor = Client()
    tutor.force_login(Usuario.objects.get(username="tutor"))
    assert "Lucía" not in tutor.get(reverse("perfil:lista")).content.decode()


def test_su_avatar_se_borra_del_disco(admin, django_capture_on_commit_callbacks):
    lucia = estudiante()
    avatar = lucia.avatar.name
    assert default_storage.exists(avatar)
    with django_capture_on_commit_callbacks(execute=True):
        admin.post(url_eliminar(lucia.usuario))
    assert not default_storage.exists(avatar)


# --- PA2: antes de eliminar, se pide confirmación ---


def test_pa2_abrir_la_pregunta_no_borra_nada(admin):
    lucia = estudiante()
    respuesta = admin.get(url_eliminar(lucia.usuario))
    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    assert "¿Eliminar la cuenta de Lucía Fernández?" in html and "No se puede deshacer" in html
    assert 'method="post"' in html and "Cancelar" in html
    assert Usuario.objects.filter(pk=lucia.usuario_id).exists()


def test_pa2_editar_cuenta_abre_la_ventana_de_confirmacion(admin):
    lucia = estudiante()
    html = admin.get(url_editar(lucia.usuario)).content.decode()
    # El botón lleva a la pregunta; con JavaScript la abre en la ventana B24.
    assert f'href="{url_eliminar(lucia.usuario)}" data-confirmar="eliminar-ventana"' in html
    ventana = html.split('id="eliminar-ventana"')[1].split("</dialog>")[0]
    assert "¿Eliminar la cuenta de Lucía Fernández?" in ventana
    assert f'action="{url_eliminar(lucia.usuario)}"' in ventana
    # El foco empieza en «Cancelar», que cierra la ventana sin enviar nada.
    assert (
        '<form method="dialog"><button class="boton boton--aux" type="submit" autofocus>Cancelar'
        in ventana
    )


def test_pa2_un_enlace_no_puede_borrar(admin):
    """Solo POST borra: un enlace o una imagen que apunte a la dirección no hace nada."""
    lucia = estudiante()
    admin.get(url_eliminar(lucia.usuario))
    assert Usuario.objects.filter(pk=lucia.usuario_id).exists()


# --- PA3: se borran su agenda, sus marcas, sus comprobaciones y sus emociones ---


def test_pa3_se_borra_todo_lo_suyo_y_nada_de_los_demas(admin):
    lucia = estudiante()
    asignaciones = list(lucia.asignaciones.values_list("pk", flat=True))
    ejecuciones = list(
        Ejecucion.objects.filter(asignacion__estudiante=lucia).values_list("pk", flat=True)
    )
    assert asignaciones and ejecuciones  # los datos de prueba le dan agenda e historial
    otras = Asignacion.objects.exclude(estudiante=lucia).count()

    # La pregunta dice qué se va a borrar.
    html = admin.get(url_eliminar(lucia.usuario)).content.decode()
    assert f"su agenda: {len(asignaciones)} tareas puestas" in html
    assert "lo que ha hecho:" in html and "profesional deja de atenderle" in html

    admin.post(url_eliminar(lucia.usuario))
    assert not Asignacion.objects.filter(pk__in=asignaciones).exists()
    assert not Ejecucion.objects.filter(pk__in=ejecuciones).exists()
    assert not EjecucionPaso.objects.filter(ejecucion_id__in=ejecuciones).exists()
    assert not Perfil.objects.filter(estudiante_id=lucia.pk).exists()
    assert not Atencion.objects.filter(estudiante_id=lucia.pk).exists()
    # Las tareas siguen existiendo (las usan otros) y la agenda de los demás no cambia.
    assert Asignacion.objects.count() == otras


# --- PA4: si es un tutor con estudiantes vinculados, se avisa ---


def test_pa4_un_tutor_con_estudiantes_no_se_elimina_y_se_dice_por_que(admin):
    tutor = Usuario.objects.get(username="tutor")
    html = admin.get(url_editar(tutor)).content.decode()
    assert "No se puede eliminar todavía" in html
    assert "Tiene 6 estudiantes a su cargo como tutor" in html and "Ir a Vínculos" in html
    assert url_eliminar(tutor) not in html and 'id="eliminar-ventana"' not in html

    html = admin.get(url_eliminar(tutor)).content.decode()
    assert "No se puede eliminar la cuenta de Ana Martín Ruiz" in html
    assert "desactívala" in html and 'method="post"' not in html.split("<main")[1]

    # Aunque llegue un POST (otra pestaña abierta), no se borra.
    assert admin.post(url_eliminar(tutor)).status_code == 409
    assert Usuario.objects.filter(pk=tutor.pk).exists()


def test_pa4_cuando_ya_no_tiene_estudiantes_ni_tareas_se_puede(admin):
    tutor2 = Usuario.objects.get(username="tutor2")
    Estudiante.objects.filter(tutor=tutor2).update(tutor=None, fecha_alta_tutor=None)
    tutor2.asignaciones_hechas.all().delete()
    tutor2.tareas_creadas.all().delete()
    assert admin.post(url_eliminar(tutor2)).status_code == 302
    assert not Usuario.objects.filter(username="tutor2").exists()


def test_un_familiar_con_estudiante_tampoco(admin):
    familiar = Usuario.objects.get(username="familiar")
    html = admin.get(url_eliminar(familiar)).content.decode()
    assert "Figura como familiar de 1 estudiante" in html
    assert admin.post(url_eliminar(familiar)).status_code == 409


def test_quien_ha_creado_o_puesto_tareas_tampoco(admin):
    """Si se borrara, sus tareas desaparecerían de las agendas de los estudiantes."""
    familiar = Usuario.objects.get(username="familiar")
    Estudiante.objects.filter(familiar=familiar).update(familiar=None, fecha_alta_familiar=None)
    if not (familiar.tareas_creadas.exists() or familiar.asignaciones_hechas.exists()):
        pytest.skip("Los datos de prueba no le dan tareas a la familiar")
    html = admin.get(url_eliminar(familiar)).content.decode()
    assert "desaparecerían de las agendas" in html
    assert admin.post(url_eliminar(familiar)).status_code == 409


def test_un_profesional_sin_tareas_si_y_deja_de_atender(admin):
    profesional = Usuario.objects.get(username="profesional")
    profesional.asignaciones_hechas.all().delete()
    profesional.tareas_creadas.all().delete()
    html = admin.get(url_eliminar(profesional)).content.decode()
    assert "deja de atender a 2 estudiantes" in html
    admin.post(url_eliminar(profesional))
    assert not Usuario.objects.filter(pk=profesional.pk).exists()
    # Los estudiantes siguen ahí.
    assert Estudiante.objects.filter(codigo_estudiante__in=["A01", "A04"]).count() == 2


def test_nadie_elimina_su_propia_cuenta(admin):
    yo = Usuario.objects.get(username="admin")
    assert "Eliminar la cuenta" not in admin.get(url_editar(yo)).content.decode()
    assert admin.post(url_eliminar(yo)).status_code == 409
    assert Usuario.objects.filter(pk=yo.pk).exists()


def test_otro_administrador_si(admin):
    otro = Usuario.objects.create_user(
        "admin2", password="Colegio-2026", first_name="Otra", rol="administrador"
    )
    assert admin.post(url_eliminar(otro)).status_code == 302
    assert not Usuario.objects.filter(pk=otro.pk).exists()


# --- PA5: un usuario que no es administrador no puede eliminar cuentas ---


@pytest.mark.parametrize("quien", ["tutor", "profesional", "familiar"])
def test_pa5_quien_no_es_administrador_no_puede(client, datos, quien):
    lucia = estudiante()
    client.force_login(Usuario.objects.get(username=quien))
    assert client.get(url_eliminar(lucia.usuario)).status_code == 403
    assert client.post(url_eliminar(lucia.usuario)).status_code == 403
    assert Usuario.objects.filter(pk=lucia.usuario_id).exists()


def test_pa5_un_estudiante_y_quien_no_ha_entrado_tampoco(client, datos):
    lucia = estudiante()
    mateo = estudiante("A02")
    assert client.post(url_eliminar(mateo.usuario)).status_code == 302  # a la portada
    client.force_login(lucia.usuario)
    assert client.post(url_eliminar(mateo.usuario)).status_code == 403
    assert Usuario.objects.filter(pk=mateo.usuario_id).exists()


def test_una_cuenta_que_no_existe_da_404(admin):
    assert admin.post(reverse("usuarios:eliminar", args=[999999])).status_code == 404
