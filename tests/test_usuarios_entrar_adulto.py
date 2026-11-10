"""HU-01-07. Entrar como tutor, profesional o familiar (AGENDA-149).

Una prueba por cada prueba de aceptación de Jira (PA1 a PA5) y algunas más de seguridad.
Usa los datos de prueba: todos los adultos tienen la contraseña «despega2026».
"""

import pytest
from django.urls import reverse

from apps.usuarios.models import Usuario

pytestmark = pytest.mark.django_db

CONTRASENA = "despega2026"
NO_COINCIDEN = "Los datos no coinciden con una cuenta existente"


def entrar(client, usuario, contrasena, **extra):
    return client.post(
        reverse("usuarios:entrar"), {"username": usuario, "password": contrasena}, **extra
    )


def sesion_de(client):
    """Id del usuario con sesión en el cliente, o None."""
    return client.session.get("_auth_user_id")


# --- PA1: con mi usuario y mi contraseña entro y veo la pantalla principal con mi nombre ---


@pytest.mark.parametrize(
    "usuario, nombre",
    [("tutor", "Ana"), ("profesional", "Luis"), ("familiar", "Carmen"), ("admin", None)],
)
def test_pa1_entro_y_veo_mi_pantalla_principal_con_mi_nombre(client, datos, usuario, nombre):
    respuesta = entrar(client, usuario, CONTRASENA)
    assert respuesta.status_code == 302
    assert respuesta["Location"] == reverse("usuarios:panel")

    adulto = Usuario.objects.get(username=usuario)
    assert sesion_de(client) == str(adulto.pk)

    panel = client.get(respuesta["Location"])
    assert panel.status_code == 200
    assert f"Hola, {nombre or adulto.first_name}" in panel.content.decode()
    assert adulto.get_rol_display() in panel.content.decode()


def test_pa1_vuelve_a_la_pantalla_que_pedia_antes_de_entrar(client, datos):
    # Sin sesión se va a la portada «¿Quién eres?» (LOGIN_URL, HU-01-06), que pasa el ?next=.
    pedida = client.get(reverse("usuarios:panel"))
    assert pedida.status_code == 302
    assert pedida["Location"] == reverse("inicio") + "?next=/panel/"

    respuesta = client.post(
        reverse("usuarios:entrar") + "?next=/panel/",
        {"username": "tutor", "password": CONTRASENA, "next": "/panel/"},
    )
    assert respuesta["Location"] == "/panel/"


def test_pa1_el_panel_ensena_las_opciones_de_cada_rol(client, datos):
    client.force_login(Usuario.objects.get(username="tutor"))
    assert "Crear una tarea" in client.get(reverse("usuarios:panel")).content.decode()

    client.force_login(Usuario.objects.get(username="admin"))
    contenido = client.get(reverse("usuarios:panel")).content.decode()
    assert reverse("admin:index") in contenido
    assert "Crear una tarea" not in contenido  # el administrador no crea tareas


# --- PA2: con usuario o contraseña incorrectos no entro y un mensaje dice que no coinciden ---


@pytest.mark.parametrize("usuario, contrasena", [("tutor", "otra-cosa"), ("no-existe", CONTRASENA)])
def test_pa2_datos_incorrectos_no_entro_y_veo_el_mensaje(client, datos, usuario, contrasena):
    respuesta = entrar(client, usuario, contrasena)
    assert respuesta.status_code == 200
    assert sesion_de(client) is None
    contenido = respuesta.content.decode()
    assert NO_COINCIDEN in contenido
    assert 'role="alert"' in contenido


def test_pa2_el_mensaje_no_dice_que_dato_ha_fallado(client, datos):
    """El mismo texto si falla el usuario o la contraseña: no da pistas a quien prueba."""
    mal_usuario = entrar(client, "no-existe", CONTRASENA).content.decode()
    mala_contrasena = entrar(client, "tutor", "otra-cosa").content.decode()
    assert NO_COINCIDEN in mal_usuario
    assert NO_COINCIDEN in mala_contrasena


# --- PA3: con un campo vacío no se envía el formulario y se indica qué falta ---


def test_pa3_campos_vacios_indican_que_falta(client, datos):
    respuesta = entrar(client, "", "")
    assert respuesta.status_code == 200
    assert sesion_de(client) is None
    contenido = respuesta.content.decode()
    assert "Escribe tu usuario." in contenido
    assert "Escribe tu contraseña." in contenido
    # El campo queda marcado y enlazado con su mensaje para el lector de pantalla.
    assert 'aria-invalid="true"' in contenido
    assert 'id="id_username_error"' in contenido


def test_pa3_solo_falta_la_contrasena(client, datos):
    contenido = entrar(client, "tutor", "").content.decode()
    assert "Escribe tu contraseña." in contenido
    assert "Escribe tu usuario." not in contenido


# --- PA4: con una cuenta eliminada o desactivada no puedo entrar ---


def test_pa4_cuenta_desactivada_no_entra(client, datos):
    Usuario.objects.filter(username="tutor").update(is_active=False)
    respuesta = entrar(client, "tutor", CONTRASENA)
    assert respuesta.status_code == 200
    assert sesion_de(client) is None


def test_pa4_cuenta_eliminada_no_entra(client, datos):
    familiar = Usuario.objects.get(username="familiar2")
    familiar.estudiantes_familiares.update(familiar=None, fecha_alta_familiar=None)
    familiar.delete()
    respuesta = entrar(client, "familiar2", CONTRASENA)
    assert NO_COINCIDEN in respuesta.content.decode()
    assert sesion_de(client) is None


# --- PA5: tras 5 intentos fallidos seguidos no puedo volver a intentarlo en 5 minutos ---


@pytest.fixture
def con_axes(settings):
    """En config/settings/test.py axes está apagado; aquí se enciende."""
    settings.AXES_ENABLED = True


def test_pa5_tras_5_fallos_queda_bloqueado(client, datos, con_axes):
    for _ in range(4):
        assert entrar(client, "tutor", "mal").status_code == 200
    bloqueo = entrar(client, "tutor", "mal")  # 5.º fallo
    assert bloqueo.status_code == 429
    assert "Espera 5 minutos" in bloqueo.content.decode()

    # Ni con la contraseña buena entra mientras dura el bloqueo.
    otra_vez = entrar(client, "tutor", CONTRASENA)
    assert otra_vez.status_code == 429
    assert sesion_de(client) is None


def test_pa5_el_bloqueo_no_deja_fuera_a_otros_adultos_del_mismo_colegio(client, datos, con_axes):
    """Todas las tabletas del centro salen por la misma IP: se bloquea usuario + IP."""
    for _ in range(5):
        entrar(client, "tutor", "mal")
    assert entrar(client, "profesional", CONTRASENA).status_code == 302


def test_pa5_acertar_reinicia_la_cuenta_de_fallos(client, datos, con_axes):
    for _ in range(4):
        entrar(client, "tutor", "mal")
    assert entrar(client, "tutor", CONTRASENA).status_code == 302
    client.post(reverse("usuarios:salir"))
    for _ in range(4):
        assert entrar(client, "tutor", "mal").status_code == 200  # no bloquea: empezó de cero


# --- Seguridad y recorrido ---


def test_un_estudiante_no_entra_por_la_pantalla_de_adultos(client, datos):
    """Mateo tiene contraseña de texto, pero los estudiantes entran con su avatar (HU-01-06)."""
    respuesta = entrar(client, "est-a02", "mateo2026")
    assert respuesta.status_code == 200
    assert sesion_de(client) is None
    assert "Esta entrada es para adultos" in respuesta.content.decode()


def test_un_estudiante_con_sesion_que_abre_el_panel_va_a_su_agenda(client, datos):
    estudiante = Usuario.objects.filter(rol="estudiante").first()
    client.force_login(estudiante)
    respuesta = client.get(reverse("usuarios:panel"))
    assert respuesta.status_code == 302
    assert respuesta["Location"] == reverse("agenda:dia")


def test_quien_ya_ha_entrado_no_ve_otra_vez_el_formulario(client, datos):
    client.force_login(Usuario.objects.get(username="tutor"))
    respuesta = client.get(reverse("usuarios:entrar"))
    assert respuesta.status_code == 302
    assert respuesta["Location"] == reverse("usuarios:panel")


def test_no_redirige_a_otra_web_tras_entrar(client, datos):
    respuesta = client.post(
        reverse("usuarios:entrar"),
        {"username": "tutor", "password": CONTRASENA, "next": "https://otra-web.example/"},
    )
    assert respuesta["Location"] == reverse("usuarios:panel")


def test_salir_cierra_la_sesion(client, datos):
    client.force_login(Usuario.objects.get(username="tutor"))
    respuesta = client.post(reverse("usuarios:salir"))
    assert respuesta.status_code == 302
    assert respuesta["Location"] == reverse("inicio")
    assert sesion_de(client) is None


def test_salir_con_un_enlace_no_cierra_la_sesion(client, datos):
    client.force_login(Usuario.objects.get(username="tutor"))
    assert client.get(reverse("usuarios:salir")).status_code == 405
    assert sesion_de(client) is not None


def test_la_pantalla_de_entrar_tiene_los_campos_del_boceto(client, db):
    contenido = client.get(reverse("usuarios:entrar")).content.decode()
    assert '<label for="id_username">Usuario</label>' in contenido
    assert '<label for="id_password">Contraseña</label>' in contenido
    assert 'autocomplete="current-password"' in contenido
