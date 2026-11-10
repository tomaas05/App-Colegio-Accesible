"""HU-01-04. Vincular un estudiante con su tutor y su familiar (AGENDA-135).

Una prueba por cada prueba de aceptación del Plan de Entregas (PA1 a PA4) y algunas más.
Datos de prueba: Ana (`tutor`) tiene PTVAL 1 y Pedro (`tutor2`) PTVAL 2; Carmen
(`familiar`) es la familiar de Lucía y Javier (`familiar2`) la de Daniela; Luis
(`profesional`) atiende a Lucía y a Hugo.
"""

from datetime import timedelta
from urllib.parse import urlencode

import pytest
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from django.utils import timezone

from apps.usuarios.models import Estudiante, Rol, Usuario
from apps.usuarios.vinculos import estudiantes_de

pytestmark = pytest.mark.django_db

PTVAL_1 = {"A01", "A02", "A03", "A04", "A05", "A06"}
PTVAL_2 = {"B01", "B02", "B03"}


@pytest.fixture
def admin(client, datos):
    client.force_login(Usuario.objects.get(username="admin"))
    return client


def adulto(username):
    return Usuario.objects.get(username=username)


def estudiante(codigo):
    return Estudiante.objects.get(codigo_estudiante=codigo)


def url(codigo=None, **extra):
    parametros = {"estudiante": codigo, **extra} if codigo else extra
    return reverse("usuarios:vinculos") + ("?" + urlencode(parametros) if parametros else "")


def enviar(client, codigo, accion, *, tutor, familiar, nuevo_familiar=None):
    """Pulsa «Guardar vínculos», «Añadir» o «Quitar» en el formulario del estudiante."""
    datos = {
        "accion": accion,
        "tutor": tutor.pk if tutor else "",
        "familiar": familiar.pk if familiar else "",
        "nuevo_familiar": nuevo_familiar.pk if nuevo_familiar else "",
    }
    return client.post(url(codigo), datos)


def panel_de(client, username):
    client.force_login(adulto(username))
    return client.get(reverse("usuarios:panel")).content.decode()


def codigos(usuario):
    return set(estudiantes_de(usuario).values_list("codigo_estudiante", flat=True))


# --- PA1: vinculo un estudiante con un tutor y un familiar y los dos lo ven ---


def test_pa1_vinculo_tutor_y_familiar_y_los_dos_lo_ven(admin, client):
    pedro, carmen = adulto("tutor2"), adulto("familiar")
    # Mateo es de Ana y no tiene familiar: «Añadir» a Carmen y cambiar el tutor a Pedro.
    anadido = enviar(admin, "A02", "anadir", tutor=pedro, familiar=None, nuevo_familiar=carmen)
    assert anadido.status_code == 200
    assert "Carmen López Vega" in anadido.content.decode()

    respuesta = enviar(admin, "A02", "guardar", tutor=pedro, familiar=carmen)
    assert respuesta.status_code == 302
    assert respuesta["Location"] == url("A02")
    mateo = estudiante("A02")
    assert (mateo.tutor, mateo.familiar) == (pedro, carmen)
    assert mateo.fecha_alta_tutor == mateo.fecha_alta_familiar == timezone.localdate()

    aviso = admin.get(respuesta["Location"]).content.decode()
    assert "Vínculos de Mateo García guardados. Su tutor ahora es Pedro Gómez Sanz." in aviso
    assert 'role="status"' in aviso

    assert "Mateo García" in panel_de(client, "tutor2")
    familiar = panel_de(client, "familiar")
    assert "Mateo García" in familiar
    assert "Lucía Fernández" in familiar  # un familiar puede tener a más de un estudiante


def test_pa1_anadir_o_quitar_no_guarda_hasta_pulsar_guardar(admin):
    carmen, ana = adulto("familiar"), adulto("tutor")
    respuesta = enviar(admin, "A01", "quitar", tutor=ana, familiar=carmen)
    contenido = respuesta.content.decode()
    assert "Sin familiar vinculado." in contenido
    assert "Hay cambios sin guardar" in contenido
    assert estudiante("A01").familiar == carmen  # todavía no se ha guardado

    enviar(admin, "A01", "guardar", tutor=ana, familiar=None)
    lucia = estudiante("A01")
    assert lucia.familiar is None
    assert lucia.fecha_alta_familiar is None


def test_pa1_guardar_sin_cambios_no_toca_las_fechas_de_alta(admin):
    antes = estudiante("A01")
    enviar(admin, "A01", "guardar", tutor=antes.tutor, familiar=antes.familiar)
    despues = estudiante("A01")
    assert despues.fecha_alta_tutor == antes.fecha_alta_tutor
    assert despues.fecha_alta_familiar == antes.fecha_alta_familiar
    assert despues.fecha_alta_tutor < timezone.localdate() - timedelta(days=1)


def test_pa1_las_listas_solo_tienen_tutores_y_familiares_activos(admin):
    Usuario.objects.filter(username="tutor2").update(is_active=False)
    contenido = admin.get(url("A02")).content.decode()
    tutor_select = contenido.split('name="tutor"')[1].split("</select>")[0]
    assert "Ana Martín Ruiz (actual)" in tutor_select
    assert "Pedro" not in tutor_select  # desactivado
    assert "Luis" not in tutor_select and "Carmen" not in tutor_select
    familiar_select = contenido.split('name="nuevo_familiar"')[1].split("</select>")[0]
    assert "Carmen López Vega" in familiar_select and "Javier Ortega Ramos" in familiar_select
    assert "Ana" not in familiar_select


def test_pa1_el_tutor_actual_desactivado_sigue_en_la_lista(admin):
    """Si no, guardar sin tocar nada le quitaría el tutor a Daniela sin avisar."""
    Usuario.objects.filter(username="tutor2").update(is_active=False)
    contenido = admin.get(url("B01")).content.decode()
    assert "Pedro Gómez Sanz (actual)" in contenido


@pytest.mark.parametrize(
    "campo, username, mensaje",
    [
        ("tutor", "profesional", "Elige un tutor de la lista."),
        ("tutor", "familiar", "Elige un tutor de la lista."),
        ("familiar", "tutor", "Elige un familiar de la lista."),
    ],
)
def test_pa1_no_se_puede_poner_otro_rol(admin, campo, username, mensaje):
    antes = estudiante("A02")
    datos = {"accion": "guardar", "tutor": antes.tutor_id, "familiar": ""}
    datos[campo] = adulto(username).pk
    respuesta = admin.post(url("A02"), datos)
    assert respuesta.status_code == 200
    assert mensaje in respuesta.content.decode()
    despues = estudiante("A02")
    assert (despues.tutor_id, despues.familiar_id) == (antes.tutor_id, antes.familiar_id)


# --- PA2: un segundo familiar para el mismo estudiante se rechaza con un mensaje ---


def test_pa2_un_segundo_familiar_se_rechaza_con_un_mensaje(admin):
    ana, carmen, javier = adulto("tutor"), adulto("familiar"), adulto("familiar2")
    respuesta = enviar(admin, "A01", "anadir", tutor=ana, familiar=carmen, nuevo_familiar=javier)
    assert respuesta.status_code == 200
    contenido = respuesta.content.decode()
    assert (
        "Lucía Fernández ya tiene un familiar vinculado (Carmen López Vega). "
        "Solo puede tener uno: quita el vínculo actual para añadir otro."
    ) in contenido
    assert 'role="alert"' in contenido
    assert 'href="#id_nuevo_familiar"' in contenido  # el resumen lleva al campo
    assert estudiante("A01").familiar == carmen


def test_pa2_quitando_el_actual_si_se_puede_cambiar_de_familiar(admin):
    ana, carmen, javier = adulto("tutor"), adulto("familiar"), adulto("familiar2")
    enviar(admin, "A01", "quitar", tutor=ana, familiar=carmen)
    respuesta = enviar(admin, "A01", "anadir", tutor=ana, familiar=None, nuevo_familiar=javier)
    assert "ya tiene un familiar" not in respuesta.content.decode()
    enviar(admin, "A01", "guardar", tutor=ana, familiar=javier)
    assert estudiante("A01").familiar == javier


def test_pa2_anadir_sin_elegir_familiar_avisa(admin):
    respuesta = enviar(admin, "A02", "anadir", tutor=adulto("tutor"), familiar=None)
    assert "Elige el familiar que quieres añadir." in respuesta.content.decode()


# --- PA3: un tutor no ve a los estudiantes de otro tutor ---


def test_pa3_un_tutor_no_ve_a_los_estudiantes_de_otro_tutor(client, datos):
    assert codigos(adulto("tutor")) == PTVAL_1
    assert codigos(adulto("tutor2")) == PTVAL_2

    ana = panel_de(client, "tutor")
    assert "Tus estudiantes" in ana
    assert "Mateo García" in ana
    assert "Daniela Torres" not in ana and "Pablo Díaz" not in ana

    pedro = panel_de(client, "tutor2")
    assert "Daniela Torres" in pedro
    assert "Mateo García" not in pedro


def test_pa3_al_cambiar_de_tutor_el_anterior_deja_de_verlo(admin, client):
    enviar(admin, "A02", "guardar", tutor=adulto("tutor2"), familiar=None)
    assert "A02" not in codigos(adulto("tutor"))
    assert "Mateo García" not in panel_de(client, "tutor")


# --- PA4: un familiar no ve a ningún estudiante distinto del suyo ---


def test_pa4_un_familiar_solo_ve_a_su_estudiante(client, datos):
    assert codigos(adulto("familiar")) == {"A01"}
    assert codigos(adulto("familiar2")) == {"B01"}

    carmen = panel_de(client, "familiar")
    assert "Lucía Fernández" in carmen
    assert "Mateo García" not in carmen and "Daniela Torres" not in carmen


def test_pa4_un_familiar_sin_estudiantes_lo_ve_dicho(client, datos):
    nuevo = Usuario.objects.create_user("abuela", password="x", first_name="Rosa", rol=Rol.FAMILIAR)
    client.force_login(nuevo)
    contenido = client.get(reverse("usuarios:panel")).content.decode()
    assert "Todavía no tienes ningún estudiante vinculado." in contenido


def test_cada_clase_ensena_a_su_tutor_para_reconocerla(client, datos):
    """B02: «PTVAL 1 · A. Martín». Al cambiar el tutor de todos, cambia también aquí."""
    contenido = client.get(reverse("usuarios:clases")).content.decode()
    assert '<span class="loseta__sub">A. Martín</span>' in contenido
    assert '<span class="loseta__sub">P. Gómez</span>' in contenido
    # Con dos tutores en la misma clase no se pone ninguno, para no confundir.
    Estudiante.objects.filter(codigo_estudiante="A02").update(tutor=adulto("tutor2"))
    contenido = client.get(reverse("usuarios:clases")).content.decode()
    assert "A. Martín" not in contenido


# --- La regla de quién ve a quién (apps/usuarios/vinculos.py) ---


def test_el_profesional_ve_a_los_que_atiende_y_el_administrador_a_todos(datos):
    assert codigos(adulto("profesional")) == {"A01", "A04"}
    assert codigos(adulto("admin")) == PTVAL_1 | PTVAL_2
    assert codigos(Usuario.objects.get(username="est-a01")) == {"A01"}


def test_un_estudiante_desactivado_no_lo_ve_nadie(admin, client):
    Usuario.objects.filter(username="est-a01").update(is_active=False)
    assert "A01" not in codigos(adulto("tutor"))
    assert "A01" not in codigos(adulto("familiar"))
    assert 'value="A01"' not in admin.get(url()).content.decode()


def test_sin_sesion_no_ve_a_nadie(datos):
    assert not estudiantes_de(AnonymousUser()).exists()


def test_el_panel_del_administrador_no_lista_estudiantes(admin):
    contenido = admin.get(reverse("usuarios:panel")).content.decode()
    assert "Tus estudiantes" not in contenido
    assert reverse("usuarios:vinculos") in contenido  # su opción «Vínculos»


# --- B25 · Elegir el estudiante ---


@pytest.mark.parametrize(
    "texto, nombre",
    [("mateo", "Mateo García"), ("b02", "Pablo Díaz"), ("lucia fernandez", "Lucía Fernández")],
)
def test_buscar_elige_el_primero_que_coincide(admin, texto, nombre):
    contenido = admin.get(url(q=texto)).content.decode()
    assert f"<h2>{nombre}</h2>" in contenido


def test_buscar_sin_resultados(admin):
    contenido = admin.get(url(q="nadie-se-llama-asi")).content.decode()
    assert "Ningún estudiante coincide" in contenido
    assert 'name="accion"' not in contenido


def test_sin_elegir_estudiante_solo_sale_el_selector(admin):
    contenido = admin.get(url()).content.decode()
    assert "Elige un estudiante para ver" in contenido
    assert 'optgroup label="PTVAL 2"' in contenido


def test_guardar_con_una_busqueda_no_cambia_a_otro_estudiante(admin):
    """Al guardar manda el código de la dirección; nunca «el primero que coincide»."""
    pedro = adulto("tutor2")
    admin.post(url("A02", q="pablo"), {"accion": "guardar", "tutor": pedro.pk, "familiar": ""})
    assert estudiante("B02").tutor == pedro  # Pablo ya era de Pedro: sin cambios
    assert estudiante("A02").tutor == adulto("tutor")


def test_la_lista_de_usuarios_dice_los_vinculos_de_cada_adulto(admin):
    contenido = " ".join(admin.get(reverse("usuarios:lista")).content.decode().split())
    assert "6 estudiantes a su cargo" in contenido  # Ana
    assert "3 estudiantes a su cargo" in contenido  # Pedro
    assert "Familiar de 1 estudiante" in contenido  # Carmen y Javier
    assert "Atiende a 2 estudiantes" in contenido  # Luis


def test_la_lista_de_usuarios_enlaza_a_los_vinculos(admin):
    contenido = admin.get(reverse("usuarios:lista") + "?clase=").content.decode()
    assert f'href="{url("A01")}"' in contenido
    assert "los vínculos de Lucía Fernández" in contenido


# --- Solo el administrador ---


@pytest.mark.parametrize("username", ["tutor", "profesional", "familiar", "est-a01"])
def test_otros_roles_reciben_403(client, datos, username):
    client.force_login(adulto(username))
    assert client.get(url("A01")).status_code == 403
    respuesta = client.post(url("A01"), {"accion": "guardar", "tutor": "", "familiar": ""})
    assert respuesta.status_code == 403
    assert estudiante("A01").tutor is not None


def test_sin_sesion_va_a_la_portada(client, datos):
    respuesta = client.get(url("A01"))
    assert respuesta.status_code == 302
    assert respuesta["Location"].startswith(reverse("inicio"))
