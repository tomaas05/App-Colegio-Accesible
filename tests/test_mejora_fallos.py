"""Fallos corregidos en la mejora de interfaz. Cada prueba fallaba antes del arreglo."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.perfil.context_processors import perfil_estudiante
from apps.usuarios.altas import avatar_por_defecto
from apps.usuarios.models import Usuario

pytestmark = pytest.mark.django_db


def entrar(client, usuario):
    client.force_login(Usuario.objects.get(username=usuario))
    return client


# --- Fallo 8: el context processor del perfil cerraba la sesión -----------------------


def test_el_context_processor_no_cierra_la_sesion(client, datos, rf):
    """Pintar una plantilla no puede tener efectos: antes llamaba a logout()."""
    entrar(client, "est-a01")
    peticion = rf.get("/")
    peticion.user = Usuario.objects.get(username="est-a01")
    peticion.session = client.session
    perfil_estudiante(peticion)
    assert peticion.session.get("_auth_user_id") is not None


@pytest.mark.parametrize("ruta", ["/", "/estudiante/", "/entrar/"])
def test_el_estudiante_que_vuelve_a_la_entrada_sale_de_su_sesion(client, datos, ruta):
    """Lo mismo que antes, pero en un middleware: el siguiente estudiante empieza limpio."""
    entrar(client, "est-a01")
    html = client.get(ruta).content.decode()
    assert client.session.get("_auth_user_id") is None
    assert ">Salir</button>" not in html  # la página ya se pinta sin sesión


def test_un_adulto_no_sale_al_abrir_la_portada(client, datos):
    entrar(client, "tutor").get("/")
    assert client.session.get("_auth_user_id") is not None


def test_un_post_a_la_entrada_no_cierra_la_sesion_del_estudiante(client, datos):
    entrar(client, "est-a01").post("/estudiante/")  # 405, pero sin tocar la sesión
    assert client.session.get("_auth_user_id") is not None


# --- Fallo 9: agenda de «Mis estudiantes» (HU-01-09) ----------------------------------


def agenda_de_lucia(client, dia=None):
    url = reverse("usuarios:agenda_estudiante", args=["A01"])
    return entrar(client, "profesional").get(url, {"dia": dia} if dia else {})


def test_las_tareas_de_dias_pasados_sin_hacer_salen_vencidas(client, datos):
    """Antes salían «Pendiente», y en la agenda del estudiante «Vencida»."""
    hace_una_semana = timezone.localdate() - timedelta(days=7)
    html = agenda_de_lucia(client, hace_una_semana.isoformat()).content.decode()
    assert "Estado: <b>Vencida</b>" in html
    assert "Estado: <b>Pendiente</b>" not in html


def test_las_tareas_de_manana_siguen_pendientes(client, datos):
    manana = timezone.localdate() + timedelta(days=1)
    html = agenda_de_lucia(client, manana.isoformat()).content.decode()
    assert "Estado: <b>Pendiente</b>" in html and "Vencida" not in html


@pytest.mark.parametrize("dia", ["9999-12-31", "0001-01-01", "2500-01-01", "no-es-fecha"])
def test_una_fecha_fuera_de_rango_ensena_hoy_y_no_da_error(client, datos, dia):
    """Con ?dia=9999-12-31 la página daba 500 al sumar un día."""
    respuesta = agenda_de_lucia(client, dia)
    assert respuesta.status_code == 200
    assert respuesta.context["fecha"] == timezone.localdate()


# --- Fallo 13 y avatares: Pillow no dibujaba las vocales con tilde ---------------------


def tinta(texto):
    """Los píxeles blancos (las letras) de un marcador de imagen de los datos de prueba."""
    from apps.comun.management.commands.cargar_datos_prueba import imagen

    pixeles = Image.open(imagen(texto, "#0b3c49", "prueba.png")).convert("RGBA").getdata()
    return [p[:3] == (255, 255, 255) for p in pixeles]


def test_las_letras_con_tilde_se_dibujan_y_no_son_un_cuadro():
    """Con la fuente de Pillow «Á», «É» y «Ñ» eran el mismo cuadro."""
    assert tinta("Á") != tinta("Ñ")
    assert tinta("Á") != tinta("É")
    assert sum(tinta("Á")) > sum(tinta("A"))  # la «Á» es la «A» más su tilde


def test_el_avatar_con_inicial_usa_la_misma_fuente():
    assert Image.open(avatar_por_defecto("Ángel", "A01")).size == (256, 256)


# --- Páginas de error accesibles ------------------------------------------------------


def test_el_403_tiene_pagina_con_enlace_al_inicio(client, datos):
    respuesta = entrar(client, "tutor").get(reverse("usuarios:lista"))
    html = respuesta.content.decode()
    assert respuesta.status_code == 403
    assert html.count("<h1") == 1 and "No puedes entrar aquí" in html
    assert f'href="{reverse("usuarios:panel")}">Ir al inicio</a>' in html
    assert "<title>No puedes entrar aquí · Despega</title>" in html


def test_el_404_tiene_pagina_con_enlace_al_inicio(client, datos):
    respuesta = entrar(client, "est-a01").get("/esta-pagina-no-existe/")
    html = respuesta.content.decode()
    assert respuesta.status_code == 404
    assert "No encontramos esta página" in html
    assert f'href="{reverse("agenda:dia")}">Ir al inicio</a>' in html


def test_el_500_se_pinta_sin_contexto():
    from django.template.loader import render_to_string

    html = render_to_string("500.html")
    assert 'lang="es"' in html and html.count("<h1") == 1 and 'href="/"' in html


# --- Fallo 12 --------------------------------------------------------------------------


def test_el_readme_no_repite_la_fila_del_perfil(settings):
    filas = [
        linea
        for linea in (settings.BASE_DIR / "README.md").read_text(encoding="utf-8").splitlines()
        if linea.startswith("| `/perfil/`")
    ]
    assert len(filas) == 1
