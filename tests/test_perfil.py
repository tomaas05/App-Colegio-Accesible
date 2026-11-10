"""HU-04-01. Elegir tema, colores, letra y tamaño de botones (AGENDA-227).

Una prueba por cada prueba de aceptación de Jira (PA1 a PA6) y comprobaciones de permisos.
"""

import re
from datetime import datetime, time
from pathlib import Path

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios
from apps.perfil.models import (
    Paleta,
    Perfil,
    TamanoBotones,
    TamanoLetra,
    Tema,
    TipoLetra,
)
from apps.usuarios.models import Estudiante, ImagenAcceso, Usuario

pytestmark = pytest.mark.django_db


def url_editar(codigo="A01"):
    return reverse("perfil:editar", args=[codigo])


def datos_form(**cambios):
    base = {
        "tema": Tema.CLARO,
        "paleta": Paleta.ESTANDAR,
        "tipo_letra": TipoLetra.NUNITO,
        "tamano_letra": TamanoLetra.MEDIANA,
        "tamano_botones": TamanoBotones.NORMAL,
        "usa_lector_pantalla": False,
    }
    base.update(cambios)
    return base


# --- PA1: cambio el tema y la paleta de un estudiante y solo se aplican a ese estudiante ---


def test_pa1_cambio_tema_y_paleta_solo_se_aplican_a_ese_estudiante(client, datos):
    tutor = Usuario.objects.get(username="tutor")
    client.force_login(tutor)

    respuesta = client.post(
        url_editar("A01"),
        datos_form(tema=Tema.OSCURO, paleta=Paleta.SUAVE),
    )
    assert respuesta.status_code == 302

    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    hugo = Estudiante.objects.get(codigo_estudiante="A04")

    # Al entrar como Lucía ve su tema oscuro y paleta suave.
    client.force_login(lucia.usuario)
    html_lucia = client.get(reverse("agenda:dia")).content.decode()
    assert 'data-tema="oscuro"' in html_lucia
    assert 'data-paleta="suave"' in html_lucia

    # Hugo conserva su tema claro y paleta estándar.
    client.force_login(hugo.usuario)
    html_hugo = client.get(reverse("agenda:dia")).content.decode()
    assert 'data-tema="claro"' in html_hugo
    assert 'data-paleta="estandar"' in html_hugo

    # Un adulto no tiene atributos de perfil de estudiante en su panel.
    client.force_login(tutor)
    html_tutor = client.get(reverse("usuarios:panel")).content.decode()
    assert "data-tema=" not in html_tutor


# --- PA2: cambio el tipo y el tamaño de letra (16, 20, 24 o 32 px) y se ve en la pantalla ---


@pytest.mark.parametrize("fuente", TipoLetra.values)
@pytest.mark.parametrize("tamano", TamanoLetra.values)
def test_pa2_cambio_tipo_y_tamano_de_letra_se_ve_en_la_pantalla(client, datos, fuente, tamano):
    client.force_login(Usuario.objects.get(username="tutor"))
    client.post(url_editar("A01"), datos_form(tipo_letra=fuente, tamano_letra=tamano))

    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    client.force_login(lucia.usuario)
    html = client.get(reverse("agenda:dia")).content.decode()
    assert f'data-fuente="{fuente}"' in html
    assert f'data-letra="{tamano}"' in html


# --- PA3: cambio el tamaño de los botones (48, 64 u 80 px) y se ve en la pantalla ---


@pytest.mark.parametrize("botones", TamanoBotones.values)
def test_pa3_cambio_tamano_de_botones_se_ve_en_la_pantalla(client, datos, botones):
    client.force_login(Usuario.objects.get(username="tutor"))
    client.post(url_editar("A01"), datos_form(tamano_botones=botones))

    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    client.force_login(lucia.usuario)
    html = client.get(reverse("agenda:dia")).content.decode()
    assert f'data-botones="{botones}"' in html


# --- PA4: con cualquier paleta, el texto tiene un contraste mínimo de 4,5:1 ---


def _luminancia(hex_color):
    hex_color = hex_color.lstrip("#")
    canales = [int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canales]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contraste(c1, c2):
    l1, l2 = _luminancia(c1), _luminancia(c2)
    mayor, menor = max(l1, l2), min(l1, l2)
    return (mayor + 0.05) / (menor + 0.05)


def _extraer_bloque(css, selector):
    patron = re.escape(selector) + r"\s*\{([^}]+)\}"
    m = re.search(patron, css)
    assert m, f"No se encontró el bloque {selector} en tokens.css"
    return dict(re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{6})", m.group(1)))


@pytest.mark.parametrize(
    "selectores",
    [
        [":root"],
        [":root", 'html[data-paleta="suave"]'],
        [":root", 'html[data-paleta="alto_contraste"]'],
        [":root", 'html[data-tema="oscuro"]'],
        [":root", 'html[data-tema="oscuro"]', 'html[data-tema="oscuro"][data-paleta="suave"]'],
        [
            ":root",
            'html[data-tema="oscuro"]',
            'html[data-tema="oscuro"][data-paleta="alto_contraste"]',
        ],
    ],
)
def test_pa4_contraste_minimo_4_5_en_todas_las_paletas_y_temas(selectores):
    css = Path("static/css/tokens.css").read_text(encoding="utf-8")
    colores = {}
    for sel in selectores:
        colores.update(_extraer_bloque(css, sel))

    for fondo in ("--blanco", "--menta"):
        for texto in ("--texto", "--petroleo", "--verde-oscuro", "--gris"):
            ratio = _contraste(colores[texto], colores[fondo])
            assert ratio >= 4.5, f"{selectores}: {texto} sobre {fondo} tiene {ratio:.2f}:1 (< 4.5)"

    # Botón principal: texto --blanco sobre fondo --petroleo
    assert _contraste(colores["--blanco"], colores["--petroleo"]) >= 4.5


# --- PA5: la configuración se mantiene cuando el estudiante vuelve a entrar ---


def test_pa5_la_configuracion_se_mantiene_cuando_vuelve_a_entrar(client, datos):
    client.force_login(Usuario.objects.get(username="tutor"))
    client.post(
        url_editar("A01"),
        datos_form(
            tema=Tema.OSCURO,
            paleta=Paleta.ALTO_CONTRASTE,
            tipo_letra=TipoLetra.LEXEND,
            tamano_letra=TamanoLetra.MUY_GRANDE,
            tamano_botones=TamanoBotones.MUY_GRANDE,
        ),
    )
    client.post(reverse("usuarios:salir"))

    # Lucía entra con sus 3 imágenes, vuelve a la portada (cierra sesión) y vuelve a entrar.
    ids = [ImagenAcceso.objects.get(descripcion_imagen=p).pk for p in ("perro", "sol", "flor")]
    entrar_lucia = reverse("usuarios:entrar_estudiante", args=["A01"])
    client.post(entrar_lucia, {"imagenes": ids})
    client.get(reverse("inicio"))  # volver a la portada limpia la sesión activa
    client.post(entrar_lucia, {"imagenes": ids})

    html = client.get(reverse("agenda:dia")).content.decode()
    assert 'data-tema="oscuro"' in html
    assert 'data-paleta="alto_contraste"' in html
    assert 'data-fuente="lexend"' in html
    assert 'data-letra="32"' in html
    assert 'data-botones="80"' in html


# --- PA6: marco que usa lector de pantalla y deja de reproducir su propia voz ---


def test_pa6_marcar_lector_de_pantalla_desactiva_la_voz_propia(client, datos, monkeypatch):
    ahora = timezone.make_aware(datetime.combine(timezone.localdate(), time(12, 5)))
    monkeypatch.setattr(servicios, "ahora", lambda: ahora)

    tutor = Usuario.objects.get(username="tutor")
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    regar_pk = lucia.asignaciones.get(tarea__nombre="Regar las plantas").pk
    url_tarea = reverse("agenda:detalle", args=[regar_pk])

    # El tutor marca que Lucía usa lector de pantalla.
    client.force_login(tutor)
    client.post(url_editar("A01"), datos_form(usa_lector_pantalla=True))
    assert Perfil.objects.get(estudiante=lucia).usa_lector_pantalla is True

    # En la pantalla de la tarea no se ofrece el botón de voz propia.
    client.force_login(lucia.usuario)
    assert "data-escuchar" not in client.get(url_tarea).content.decode()


# --- Seguridad y permisos ---


def test_sin_sesion_redirige_a_la_portada(client, datos):
    respuesta = client.get(reverse("perfil:lista"))
    assert respuesta.status_code == 302
    assert reverse("inicio") in respuesta["Location"]


@pytest.mark.parametrize("username", ["profesional", "familiar", "admin"])
def test_otros_roles_adultos_no_pueden_editar_perfiles(client, datos, username):
    client.force_login(Usuario.objects.get(username=username))
    assert client.get(reverse("perfil:lista")).status_code == 403
    assert client.get(url_editar("A01")).status_code == 403


def test_un_estudiante_no_puede_entrar_a_configurar_perfiles(client, datos):
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    client.force_login(lucia.usuario)
    assert client.get(reverse("perfil:lista")).status_code == 403
    assert client.get(url_editar("A01")).status_code == 403


def test_un_tutor_no_puede_editar_el_perfil_de_un_estudiante_de_otro_tutor(client, datos):
    # B01 (Daniela) pertenece a PTVAL 2 (tutor2), no a tutor.
    client.force_login(Usuario.objects.get(username="tutor"))
    assert client.get(url_editar("B01")).status_code == 404
    assert client.post(url_editar("B01"), datos_form()).status_code == 404
