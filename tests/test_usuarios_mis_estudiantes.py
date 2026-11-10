"""HU-01-08. Elegir los estudiantes que atiendo (AGENDA-154).

Una prueba por cada prueba de aceptación de Jira y algunas más de permisos.
Datos de prueba: Luis (profesional) atiende a Lucía (A01) y a Hugo (A04).
La PA3 («solo puedo abrir la agenda de los que he elegido») se comprueba aquí con la
regla `atencion.atiende`; la pantalla de la agenda en modo consulta es HU-01-09.
"""

import pytest
from django.urls import reverse

from apps.usuarios import atencion
from apps.usuarios.models import Atencion, Estudiante, Usuario

pytestmark = pytest.mark.django_db

URL = reverse("usuarios:mis_estudiantes")


@pytest.fixture
def luis(client, datos):
    profesional = Usuario.objects.get(username="profesional")
    client.force_login(profesional)
    return profesional


def codigos_de(profesional):
    return set(
        Atencion.objects.filter(profesional=profesional).values_list(
            "estudiante__codigo_estudiante", flat=True
        )
    )


def guardar(client, elegidos, mostrados=None, consulta=""):
    mostrados = (
        mostrados
        if mostrados is not None
        else list(Estudiante.objects.values_list("codigo_estudiante", flat=True))
    )
    return client.post(URL, {"elegidos": elegidos, "mostrados": mostrados, "consulta": consulta})


# --- PA1: veo la lista de estudiantes del centro con nombre y avatar, sin fotos ---


def test_pa1_veo_todos_los_estudiantes_del_centro_con_nombre_y_avatar(client, luis):
    respuesta = client.get(URL)
    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    for estudiante in Estudiante.objects.select_related("usuario"):
        assert estudiante.usuario.get_full_name() in html
        assert estudiante.avatar.url in html
    # El avatar es decorativo: el nombre ya va escrito al lado.
    assert 'alt=""' in html


def test_pa1_no_salen_los_estudiantes_dados_de_baja(client, luis):
    leo = Usuario.objects.get(username="est-a06")
    leo.is_active = False
    leo.save()
    assert leo.get_full_name() not in client.get(URL).content.decode()


def test_pa1_busco_por_nombre_o_apellidos_y_filtro_por_clase(client, luis):
    html = client.get(URL, {"q": "moreno"}).content.decode()
    assert "Sofía Moreno" in html
    assert "Mateo García" not in html

    ptval2 = Estudiante.objects.get(codigo_estudiante="B01").clase
    html = client.get(URL, {"clase": ptval2.pk}).content.decode()
    assert "Daniela Torres" in html
    assert "Mateo García" not in html


# --- PA2: elijo a dos estudiantes y quedan como míos ---


def test_pa2_elijo_dos_estudiantes_y_quedan_como_mios(client, luis):
    respuesta = guardar(client, ["A01", "A04", "A02", "B01"])
    assert respuesta.status_code == 302
    assert codigos_de(luis) == {"A01", "A04", "A02", "B01"}

    html = client.get(respuesta["Location"]).content.decode()
    assert "Guardado: 2 añadidos." in html
    assert "Quitar a Mateo García" in html
    assert "Quitar a Daniela Torres" in html


def test_pa2_los_marcados_salen_ya_marcados_al_volver(client, luis):
    html = client.get(URL).content.decode()
    assert 'value="A01" checked' in html
    assert 'value="A02">' in html


def test_pa2_guardar_sin_cambios_no_toca_la_fecha_de_alta(client, luis):
    antes = list(Atencion.objects.filter(profesional=luis).values_list("pk", "fecha_alta"))
    guardar(client, ["A01", "A04"])
    despues = list(Atencion.objects.filter(profesional=luis).values_list("pk", "fecha_alta"))
    assert antes == despues


def test_pa2_con_filtro_no_se_pierden_los_elegidos_que_no_se_ven(client, luis):
    # Solo se ve la clase PTVAL 2 y elijo a Daniela: Lucía y Hugo (PTVAL 1) siguen siendo míos.
    mostrados = ["B01", "B02", "B03"]
    guardar(client, ["B01"], mostrados=mostrados)
    assert codigos_de(luis) == {"A01", "A04", "B01"}


def test_pa2_vuelve_a_la_misma_busqueda_tras_guardar(client, luis):
    respuesta = guardar(client, ["A01"], mostrados=["A01"], consulta="q=luc")
    assert respuesta["Location"] == URL + "?q=luc"


def test_pa2_no_se_puede_elegir_un_codigo_que_no_existe(client, luis):
    guardar(client, ["A01", "A04", "Z99"])
    assert codigos_de(luis) == {"A01", "A04"}


# --- PA3: solo puedo abrir la agenda de los estudiantes que he elegido ---


def test_pa3_solo_atiendo_a_los_que_he_elegido(luis):
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    mateo = Estudiante.objects.get(codigo_estudiante="A02")
    assert atencion.atiende(luis, lucia)
    assert not atencion.atiende(luis, mateo)


def test_pa3_el_tutor_no_cuenta_como_profesional_que_atiende(datos):
    tutora = Usuario.objects.get(username="tutor")
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    assert not atencion.atiende(tutora, lucia)


# --- PA4: quito a un estudiante de mi lista y dejo de verlo ---


def test_pa4_quito_a_un_estudiante_con_su_boton(client, luis):
    respuesta = client.post(URL, {"quitar": "A04"})
    assert respuesta.status_code == 302
    assert codigos_de(luis) == {"A01"}
    assert not atencion.atiende(luis, Estudiante.objects.get(codigo_estudiante="A04"))
    html = client.get(URL).content.decode()
    assert "Guardado: 1 quitado." in html
    assert "Quitar a Hugo Romero" not in html


def test_pa4_quito_a_un_estudiante_desmarcandolo(client, luis):
    guardar(client, ["A01"])
    assert codigos_de(luis) == {"A01"}


def test_pa4_quitar_a_uno_no_toca_lo_de_otro_profesional(client, luis):
    otra = Usuario.objects.create_user("otra", password="x", first_name="Eva", rol="profesional")
    hugo = Estudiante.objects.get(codigo_estudiante="A04")
    Atencion.objects.create(profesional=otra, estudiante=hugo)
    client.post(URL, {"quitar": "A04"})
    assert codigos_de(otra) == {"A04"}


# --- Permisos ---


def test_sin_sesion_va_a_la_portada(client, datos):
    respuesta = client.get(URL)
    assert respuesta.status_code == 302
    assert respuesta["Location"].startswith(reverse("inicio"))


@pytest.mark.parametrize("usuario", ["tutor", "familiar", "admin", "est-a01"])
def test_solo_el_profesional_entra(client, datos, usuario):
    client.force_login(Usuario.objects.get(username=usuario))
    assert client.get(URL).status_code == 403
    assert client.post(URL, {"elegidos": ["A01"]}).status_code == 403


def test_el_panel_del_profesional_enlaza_mis_estudiantes(client, luis):
    assert URL in client.get(reverse("usuarios:panel")).content.decode()


def test_el_panel_del_tutor_no_enlaza_mis_estudiantes(client, datos):
    client.force_login(Usuario.objects.get(username="tutor"))
    assert URL not in client.get(reverse("usuarios:panel")).content.decode()
