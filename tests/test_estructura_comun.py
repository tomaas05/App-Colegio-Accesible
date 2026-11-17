"""Estructura común de las pantallas (decisión 0003): logotipo, panel lateral y «Salir».

El logotipo lleva a la pantalla principal de cada uno; los adultos tienen un panel
lateral con las mismas opciones que su pantalla principal; el estudiante no lo tiene.
"""

import re

import pytest
from django.urls import reverse

from apps.usuarios.models import Rol, Usuario
from apps.usuarios.navegacion import OPCIONES_POR_ROL, navegacion_de, opciones_de

pytestmark = pytest.mark.django_db

ADULTOS = ["admin", "tutor", "profesional", "familiar"]


def pagina(client, usuario, ruta):
    client.force_login(Usuario.objects.get(username=usuario))
    return client.get(ruta).content.decode()


def enlace_del_logotipo(html):
    return re.search(r'<a class="cabecera__logo" href="([^"]*)"', html).group(1)


def lateral(html):
    """El HTML del panel lateral, o "" si la página no lo tiene."""
    encontrado = re.search(r"<aside.*?</aside>", html, re.S)
    return encontrado.group(0) if encontrado else ""


# --- Logotipo ---------------------------------------------------------------------


def test_la_portada_ensena_el_logotipo_junto_al_titulo_en_su_barra(client, db):
    """B01 + B02: sin barra del adulto ni panel; el logotipo va en la barra de título, junto
    a «¿Cuál es tu clase?», con la fecha de hoy (revisión con la profesora)."""
    html = client.get(reverse("inicio")).content.decode()
    assert lateral(html) == "" and "data-menu" not in html and "<footer" not in html
    barra = re.search(r'<header class="barra">.*?</header>', html, re.S).group(0)
    assert re.search(r'<img class="barra__logo" src="[^"]*logo-despega[^"]*" alt="Despega"', barra)
    assert '<h1 id="titulo">¿Cuál es tu clase?</h1>' in barra and "barra__fecha" in barra


@pytest.mark.parametrize("usuario", ADULTOS)
def test_el_logotipo_del_adulto_lleva_a_su_panel(client, datos, usuario):
    assert enlace_del_logotipo(pagina(client, usuario, reverse("usuarios:panel"))) == reverse(
        "usuarios:panel"
    )


def test_el_logotipo_del_adulto_tiene_tamano_para_no_mover_la_pagina(client, datos):
    html = pagina(client, "tutor", reverse("usuarios:panel"))
    assert re.search(
        r'<img src="[^"]*logo-despega[^"]*" alt="[^"]+" width="\d+" height="\d+">', html
    )


# --- Panel lateral de los adultos -------------------------------------------------


@pytest.mark.parametrize("usuario", ADULTOS)
def test_el_lateral_tiene_inicio_las_opciones_del_rol_y_salir(client, datos, usuario):
    html = lateral(pagina(client, usuario, reverse("usuarios:panel")))
    assert '<nav aria-label="Principal">' in html
    rol = Usuario.objects.get(username=usuario).rol
    textos = re.findall(r'<a class="lateral__enlace[^>]*>([^<]+)</a>', html)
    assert textos == ["Inicio", *[opcion["texto"] for opcion in opciones_de(rol)]]
    # «Salir» va al final, con POST y con CSRF.
    assert html.index("lateral__salir") > html.rindex("lateral__enlace")
    assert f'method="post" action="{reverse("usuarios:salir")}"' in html
    assert "csrfmiddlewaretoken" in html


def test_el_lateral_y_el_panel_ensenan_las_mismas_opciones(client, datos):
    html = pagina(client, "tutor", reverse("usuarios:panel"))
    del_panel = re.findall(r'<a class="panel__opcion" href="([^"]+)"', html)
    del_lateral = re.findall(r'<a class="lateral__enlace[^"]*" href="([^"]+)"', lateral(html))
    assert del_lateral == [reverse("usuarios:panel"), *del_panel]


def test_la_pagina_actual_lleva_aria_current(client, datos):
    html = lateral(pagina(client, "admin", reverse("usuarios:lista")))
    assert html.count('aria-current="page"') == 1
    assert re.search(r'href="/usuarios/" aria-current="page">Usuarios<', html)


def test_en_una_pantalla_interior_se_marca_la_seccion_sin_aria_current(client, datos):
    html = lateral(pagina(client, "admin", reverse("usuarios:crear")))
    assert 'aria-current="page"' not in html
    assert re.search(r'lateral__enlace--seccion" href="/usuarios/">Usuarios<', html)


def test_la_seccion_es_la_opcion_mas_concreta():
    """/usuarios/vinculos/ está dentro de «Vínculos», no de «Usuarios»."""
    admin = Usuario(rol=Rol.ADMINISTRADOR)
    marcadas = [e["texto"] for e in navegacion_de(admin, "/usuarios/vinculos/") if e["seccion"]]
    assert marcadas == ["Vínculos"]


def test_una_opcion_cuya_url_no_existe_no_se_ensena(monkeypatch):
    monkeypatch.setitem(OPCIONES_POR_ROL, Rol.FAMILIAR, [("Fantasma", "No existe.", "no:existe")])
    assert opciones_de(Rol.FAMILIAR) == []
    assert [e["texto"] for e in navegacion_de(Usuario(rol=Rol.FAMILIAR), "/panel/")] == ["Inicio"]


def test_el_boton_menu_dice_que_controla_y_si_esta_abierto(client, datos):
    html = pagina(client, "tutor", reverse("usuarios:panel"))
    assert re.search(
        r'<button[^>]*data-menu aria-expanded="false" aria-controls="lateral">Menú</button>',
        html,
    )
    assert '<aside class="lateral" id="lateral">' in html


# --- El estudiante: sin panel lateral y con «Salir» a la vista ----------------------


@pytest.mark.parametrize("nombre_url", ["agenda:dia", "horario:mi_horario"])
def test_el_estudiante_no_tiene_lateral_y_si_barra_de_titulo(client, datos, nombre_url):
    """Sin la barra del adulto ni panel lateral, pero con su barra de título: dónde está, la
    fecha de hoy, su nombre y la hora (revisión con la profesora)."""
    html = pagina(client, "est-a01", reverse(nombre_url))
    assert lateral(html) == "" and "data-menu" not in html and 'class="cabecera"' not in html
    barra = re.search(r'<header class="barra">.*?</header>', html, re.S).group(0)
    assert "<h1" in barra and "barra__fecha" in barra and "Lucía" in barra and "data-reloj" in barra


def test_el_estudiante_tiene_salir_en_su_agenda(client, datos):
    html = pagina(client, "est-a01", reverse("agenda:dia"))
    fila = re.search(r'<header class="barra">.*?</header>', html, re.S).group(0)
    assert f'method="post" action="{reverse("usuarios:salir")}"' in fila
    assert ">Salir</button>" in fila and fila.index("Salir") < fila.index("<h1")


def test_sin_sesion_no_hay_lateral_ni_salir(client, db):
    html = client.get(reverse("inicio")).content.decode()
    assert lateral(html) == "" and ">Salir</button>" not in html


# --- Regiones y pie ---------------------------------------------------------------


def test_el_adulto_tiene_sus_regiones_una_sola_vez(client, datos):
    html = pagina(client, "tutor", "/panel/")
    for etiqueta in ('<header class="cabecera"', '<header class="barra"', "<aside", "<main", "<h1"):
        assert html.count(etiqueta) == 1, etiqueta
    # La barra del logotipo, el panel y el contenido, con su barra de título dentro de <main>.
    assert html.index('class="saltar"') < html.index('class="cabecera"') < html.index("<main")
    assert html.index("<main") < html.index('<header class="barra"')
    assert "<footer" not in html  # sin pie: la atribución va en el panel lateral


def test_la_atribucion_de_arasaac_esta_en_el_lateral_y_no_la_ve_el_estudiante(client, datos):
    assert "Origen: ARASAAC" in lateral(pagina(client, "tutor", "/panel/"))
    assert "ARASAAC" not in pagina(client, "est-a01", "/agenda/")


def test_la_portada_ensena_la_imagen_de_cada_clase_y_si_no_tiene_un_dibujo(client, datos):
    from apps.usuarios.models import Clase

    clase = Clase.objects.get(nombre="PTVAL 1")
    html = client.get(reverse("inicio")).content.decode()
    assert f'src="{clase.imagen.url}" alt=""' in html
    Clase.objects.filter(pk=clase.pk).update(imagen="")
    html = client.get(reverse("inicio")).content.decode()
    assert '<span class="loseta__dibujo" aria-hidden="true">🏫</span>' in html


def test_la_navegacion_no_consulta_la_base_de_datos(datos, rf, django_assert_num_queries):
    """El context processor solo lee request.user y resuelve direcciones."""
    from apps.usuarios.context_processors import navegacion

    peticion = rf.get(reverse("usuarios:lista"))
    peticion.user = Usuario.objects.get(username="admin")
    with django_assert_num_queries(0):
        contexto = navegacion(peticion)
    assert contexto["inicio_url"] == reverse("usuarios:panel")
    assert len(contexto["nav_principal"]) == 6  # Inicio y las 5 opciones del administrador
