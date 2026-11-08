"""HU-01-06. Entrar como estudiante (AGENDA-144).

Una prueba por cada prueba de aceptación de Jira (PA1 a PA7) y algunas más de seguridad.
Datos de prueba: PTVAL 1 (Lucía A01, Mateo A02, Sofía, Hugo, Martina, Leo) y PTVAL 2
(Daniela, Pablo, Vega). Todos entran con las imágenes perro, sol y flor, salvo Mateo,
que usa la contraseña «mateo2026».
"""

import pytest
from django.urls import reverse

from apps.usuarios.models import Clase, Estudiante, ImagenAcceso, Usuario

pytestmark = pytest.mark.django_db

NO_ES_CORRECTO = "No es correcto. Vuelve a intentarlo."


def ids(*palabras):
    return [ImagenAcceso.objects.get(descripcion_imagen=p).pk for p in palabras]


def url_entrar(codigo):
    return reverse("usuarios:entrar_estudiante", args=[codigo])


def url_clase(nombre):
    return reverse("usuarios:avatares", args=[Clase.objects.get(nombre=nombre).pk])


def sesion_de(client):
    return client.session.get("_auth_user_id")


def lucia():
    return Estudiante.objects.get(codigo_estudiante="A01").usuario


# --- Portada «¿Quién eres?» (B01) y LOGIN_URL ---


def test_la_portada_lleva_a_estudiante_y_a_adulto(client, datos):
    contenido = client.get(reverse("inicio")).content.decode()
    assert "¿Quién eres?" in contenido
    assert f'href="{reverse("usuarios:clases")}"' in contenido
    assert f'href="{reverse("usuarios:entrar")}"' in contenido


def test_quien_no_ha_entrado_va_a_la_portada_y_no_pierde_la_pantalla_pedida(client, datos):
    respuesta = client.get(reverse("agenda:dia"))
    assert respuesta.status_code == 302
    assert respuesta["Location"] == reverse("inicio") + "?next=" + reverse("agenda:dia")

    portada = client.get(respuesta["Location"]).content.decode()
    assert reverse("usuarios:clases") + "?next=/agenda/" in portada


def test_la_lista_de_clases_ensena_las_clases_con_estudiantes(client, datos):
    contenido = client.get(reverse("usuarios:clases")).content.decode()
    assert "PTVAL 1" in contenido
    assert "PTVAL 2" in contenido
    assert url_clase("PTVAL 1") in contenido


# --- PA1: la lista de la clase muestra el avatar y el nombre de cada compañero, sin fotos ---


def test_pa1_la_clase_muestra_avatar_y_nombre_de_cada_companero(client, datos):
    contenido = client.get(url_clase("PTVAL 1")).content.decode()
    for nombre in ["Lucía", "Mateo", "Sofía", "Hugo", "Martina", "Leo"]:
        assert f'<span class="loseta__nombre">{nombre}</span>' in contenido
    # Las imágenes son los avatares (dibujos), no fotos: solo se usa Estudiante.avatar.
    assert contenido.count('class="loseta__imagen loseta__imagen--avatar"') == 6
    assert contenido.count("/media/avatares/") == 6


# --- PA2: un estudiante de otra clase no aparece en la lista ---


def test_pa2_no_aparecen_estudiantes_de_otra_clase(client, datos):
    contenido = client.get(url_clase("PTVAL 1")).content.decode()
    for nombre in ["Daniela", "Pablo", "Vega"]:
        assert nombre not in contenido


def test_pa2_un_estudiante_dado_de_baja_no_aparece_ni_puede_entrar(client, datos):
    Usuario.objects.filter(pk=lucia().pk).update(is_active=False)
    assert "Lucía" not in client.get(url_clase("PTVAL 1")).content.decode()
    assert client.get(url_entrar("A01")).status_code == 404


# --- PA3: con acceso con imágenes, veo la rejilla y entro con mis 3 imágenes en cualquier orden ---


def test_pa3_con_imagenes_veo_la_rejilla(client, datos):
    contenido = client.get(url_entrar("A01")).content.decode()
    assert "Elige tus 3 imágenes" in contenido
    assert contenido.count('type="checkbox" name="imagenes"') == ImagenAcceso.objects.count()
    assert 'type="password"' not in contenido


@pytest.mark.parametrize(
    "orden", [("perro", "sol", "flor"), ("flor", "perro", "sol"), ("sol", "flor", "perro")]
)
def test_pa3_entro_con_mis_3_imagenes_en_cualquier_orden(client, datos, orden):
    respuesta = client.post(url_entrar("A01"), {"imagenes": ids(*orden)})
    assert respuesta.status_code == 302
    assert respuesta["Location"] == reverse("agenda:dia")
    assert sesion_de(client) == str(lucia().pk)


def test_pa3_una_imagen_desactivada_no_sale_en_la_rejilla(client, datos):
    ImagenAcceso.objects.filter(descripcion_imagen="gato").update(activa=False)
    contenido = client.get(url_entrar("A01")).content.decode()
    assert 'alt="gato"' not in contenido


# --- PA4: con acceso con contraseña, escribo mi contraseña y entro ---


def test_pa4_con_contrasena_veo_el_campo_y_no_la_rejilla(client, datos):
    contenido = client.get(url_entrar("A02")).content.decode()
    assert "Escribe tu contraseña" in contenido
    assert 'type="password"' in contenido
    assert 'name="imagenes"' not in contenido


def test_pa4_entro_con_mi_contrasena(client, datos):
    respuesta = client.post(url_entrar("A02"), {"password": "mateo2026"})
    assert respuesta.status_code == 302
    assert respuesta["Location"] == reverse("agenda:dia")
    assert sesion_de(client) == str(Estudiante.objects.get(codigo_estudiante="A02").usuario.pk)


# --- PA5: si me equivoco no entro y un mensaje con pictograma me dice que lo intente otra vez ---


def test_pa5_imagenes_equivocadas_no_entro(client, datos):
    respuesta = client.post(url_entrar("A01"), {"imagenes": ids("perro", "sol", "gato")})
    assert respuesta.status_code == 200
    assert sesion_de(client) is None
    contenido = respuesta.content.decode()
    assert NO_ES_CORRECTO in contenido
    assert 'role="alert"' in contenido
    assert 'class="aviso-error__picto"' in contenido  # el pictograma
    # No dice cuáles ha acertado: la rejilla vuelve sin ninguna marcada.
    assert "checked" not in contenido


def test_pa5_contrasena_equivocada_no_entro(client, datos):
    respuesta = client.post(url_entrar("A02"), {"password": "otra"})
    assert respuesta.status_code == 200
    assert sesion_de(client) is None
    assert NO_ES_CORRECTO in respuesta.content.decode()


@pytest.mark.parametrize(
    "palabras", [(), ("perro",), ("perro", "sol"), ("perro", "sol", "flor", "gato")]
)
def test_pa5_hay_que_elegir_justo_3_imagenes(client, datos, palabras):
    respuesta = client.post(url_entrar("A01"), {"imagenes": ids(*palabras)})
    assert respuesta.status_code == 200
    assert sesion_de(client) is None
    assert "Elige 3 imágenes." in respuesta.content.decode()


def test_pa5_una_imagen_que_no_existe_no_rompe_nada(client, datos):
    respuesta = client.post(url_entrar("A01"), {"imagenes": ["99999", "abc", ids("sol")[0]]})
    assert respuesta.status_code == 200
    assert sesion_de(client) is None


def test_pa5_sin_bloqueo_tras_varios_fallos(client, datos, settings):
    """Decisión 0002: un niño no se queda fuera de su agenda por equivocarse."""
    settings.AXES_ENABLED = True
    for _ in range(10):
        client.post(url_entrar("A01"), {"imagenes": ids("gato", "luna", "pez")})
    respuesta = client.post(url_entrar("A01"), {"imagenes": ids("perro", "sol", "flor")})
    assert respuesta.status_code == 302
    assert sesion_de(client) == str(lucia().pk)


def test_pa5_cada_uno_entra_solo_de_su_forma(client, datos):
    """Mateo usa contraseña: sus imágenes no sirven. Lucía usa imágenes: una contraseña no sirve."""
    mateo = Estudiante.objects.get(codigo_estudiante="A02").usuario
    con_imagenes = client.post(url_entrar("A02"), {"imagenes": ids("perro", "sol", "flor")})
    assert con_imagenes.status_code == 200
    assert client.post(url_entrar("A01"), {"password": "despega2026"}).status_code == 200
    assert sesion_de(client) is None
    assert mateo.check_password("mateo2026")


# --- PA6: con lector de pantalla, cada avatar se lee con su nombre ---
# ---      y cada imagen de la rejilla con su descripción ---


def test_pa6_cada_avatar_se_lee_con_el_nombre(client, datos):
    contenido = client.get(url_clase("PTVAL 1")).content.decode()
    # El enlace tiene el nombre como texto y el avatar es decorativo (alt vacío): se lee «Lucía».
    assert 'alt=""' in contenido
    assert '<span class="loseta__nombre">Lucía</span>' in contenido


def test_pa6_cada_imagen_de_la_rejilla_se_lee_con_su_descripcion(client, datos):
    contenido = client.get(url_entrar("A01")).content.decode()
    for imagen in ImagenAcceso.objects.filter(activa=True):
        assert f'alt="{imagen.descripcion_imagen}"' in contenido
    assert '<legend class="visualmente-oculto">' in contenido


# --- PA7: entrando como estudiante solo veo mi propia agenda ---


def test_pa7_entrando_como_estudiante_veo_mi_agenda(client, datos):
    client.post(url_entrar("A01"), {"imagenes": ids("perro", "sol", "flor")})
    contenido = client.get(reverse("agenda:dia")).content.decode()
    assert "Lucía" in contenido
    assert "Mateo" not in contenido


def test_pa7_un_estudiante_no_entra_en_el_panel_de_los_adultos(client, datos):
    client.post(url_entrar("A01"), {"imagenes": ids("perro", "sol", "flor")})
    respuesta = client.get(reverse("usuarios:panel"))
    assert respuesta["Location"] == reverse("agenda:dia")


# --- Recorrido y seguridad ---


def test_vuelve_a_la_pantalla_que_pedia(client, datos):
    destino = reverse("agenda:dia") + "?vista=manana"
    respuesta = client.post(
        url_entrar("A01"), {"imagenes": ids("perro", "sol", "flor"), "next": destino}
    )
    assert respuesta["Location"] == destino


def test_no_redirige_a_otra_web(client, datos):
    respuesta = client.post(
        url_entrar("A01"),
        {"imagenes": ids("perro", "sol", "flor"), "next": "https://otra-web.example/"},
    )
    assert respuesta["Location"] == reverse("agenda:dia")


def test_un_codigo_que_no_existe_da_404(client, datos):
    assert client.get(url_entrar("Z99")).status_code == 404


def test_el_codigo_vale_en_minusculas(client, datos):
    assert client.get(url_entrar("a01")).status_code == 200


def test_entrar_cambia_la_sesion(client, datos):
    """Al entrar se crea una sesión nueva (evita la fijación de sesión)."""
    client.get(url_entrar("A01"))
    antes = client.session.session_key
    client.post(url_entrar("A01"), {"imagenes": ids("perro", "sol", "flor")})
    assert client.session.session_key != antes


def test_salir_devuelve_a_la_portada(client, datos):
    client.post(url_entrar("A01"), {"imagenes": ids("perro", "sol", "flor")})
    respuesta = client.post(reverse("usuarios:salir"))
    assert respuesta["Location"] == reverse("inicio")
    assert sesion_de(client) is None
