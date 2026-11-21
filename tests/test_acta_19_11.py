"""Acta del 19/11: lo que se puede comprobar sin navegador (marcado y CSS).

Las pruebas en navegador están en tests/e2e/test_acta_19_11.py y test_encuadre.py.
"""

import re
from pathlib import Path

import pytest
from django.urls import reverse

from apps.usuarios.models import Usuario

pytestmark = pytest.mark.django_db

RAIZ = Path(__file__).resolve().parent.parent
CSS = RAIZ / "static" / "css"


# --- Decisión 0007: la letra sale del perfil ---


def test_ningun_componente_pone_la_letra_en_px_ni_en_rem():
    """Un font-size en rem o px no crece con la letra del perfil (data-letra)."""
    malos = []
    for archivo in CSS.glob("*.css"):
        for n, linea in enumerate(archivo.read_text("utf-8").splitlines(), 1):
            m = re.search(r"font-size:\s*([^;]+);", linea)
            if m and re.search(r"\d(px|rem)\b", m.group(1)) and "clamp(" not in m.group(1):
                malos.append(f"{archivo.name}:{n}: {m.group(1)}")
    assert not malos, "\n".join(malos)


def test_la_escala_de_letra_se_recalcula_donde_cambia_el_perfil():
    tokens = (CSS / "tokens.css").read_text("utf-8")
    assert (
        ":root,\n[data-letra] {\n  --letra-xs: max(1rem, calc(var(--tamano-base) * 0.8));" in tokens
    )


def test_sin_order_ni_lazy_load():
    for archivo in CSS.glob("*.css"):
        assert not re.search(r"(^|[\s;{])order:", archivo.read_text("utf-8")), archivo.name
    for plantilla in RAIZ.glob("**/templates/**/*.html"):
        assert 'loading="lazy"' not in plantilla.read_text("utf-8"), plantilla


def test_el_alto_de_pantalla_es_dvh_con_respaldo_vh():
    base = (CSS / "base.css").read_text("utf-8")
    assert "height: 100vh; /* respaldo */\n  height: 100dvh;" in base


# --- d · Temporizador del perfil visual en tres grupos con título ---


def test_d_el_temporizador_va_en_tres_grupos_con_legend(client, datos):
    client.force_login(Usuario.objects.get(username="tutor"))
    html = client.get(reverse("perfil:editar", args=["A01"])).content.decode()
    panel = html[html.index('data-panel="temporizador"') :]
    panel = panel[: panel.index('data-panel="lector"')]
    legends = re.findall(r'<fieldset class="perfil-subgrupo">\s*<legend>([^<]+)</legend>', panel)
    assert legends == ["Tipo de temporizador", "Avisos", "Qué ve el estudiante"]
    tipo, avisos, que_ve = panel.split('<fieldset class="perfil-subgrupo">')[1:]
    assert tipo.count('type="radio"') == 3
    for campo in ["aviso_5_min", "aviso_1_min", "sonidos_activos", "baja_sobrecarga_sensorial"]:
        assert f'name="{campo}"' in avisos
    for campo in ["temporizador_visible", "puede_ocultar_temporizador"]:
        assert f'name="{campo}"' in que_ve
    assert 'role="radiogroup"' not in panel  # el fieldset ya agrupa los radios


# --- g · «Salir» del estudiante con un SVG, no con un glifo que en Android no existe ---


def test_g_salir_lleva_un_svg_y_no_un_glifo(client, datos):
    from apps.usuarios.models import Estudiante

    client.force_login(Estudiante.objects.get(codigo_estudiante="A03").usuario)
    html = client.get(reverse("agenda:dia")).content.decode()
    salir = html[html.index('<form class="salir-est"') :]
    salir = salir[: salir.index("</form>")]
    assert '<svg class="icono"' in salir and "Salir</button>" in salir
    assert "⏻" not in (CSS / "tokens.css").read_text("utf-8")


# --- j · Todos los «Quitar» son papeleras con su nombre accesible ---

PLANTILLAS_QUITAR = [
    "apps/centro/templates/centro/comedor.html",
    "apps/centro/templates/centro/reprografia_form.html",
    "apps/horario/templates/horario/cargar.html",
    "apps/tareas/templates/tareas/_paso.html",
    "apps/usuarios/templates/usuarios/mis_estudiantes.html",
    "apps/usuarios/templates/usuarios/vinculos.html",
]


@pytest.mark.parametrize("ruta", PLANTILLAS_QUITAR)
def test_j_quitar_es_una_papelera_con_nombre(ruta):
    html = (RAIZ / ruta).read_text("utf-8")
    botones = re.findall(r"<button[^>]*boton--papelera[^>]*>.*?</button>", html, re.S)
    assert botones, ruta
    for boton in botones:
        assert 'nombre="papelera"' in boton
        assert '<span class="visualmente-oculto">Quitar ' in boton  # nombre: «Quitar …»
        assert ">Quitar<" not in boton and ">Quitar " not in boton.split("visualmente-oculto")[0]
    # Ningún «Quitar» de texto queda suelto (salvo «Quitar filtros», que no borra nada).
    assert not re.search(r'(?<!"visualmente-oculto")>\s*Quitar\b', html)


def test_j_la_papelera_usa_el_rojo_de_la_paleta_y_mide_48():
    base = (CSS / "base.css").read_text("utf-8")
    regla = base[base.index(".boton--papelera {") :]
    regla = regla[: regla.index("}")]
    assert "min-width: var(--toque);" in regla and "min-height: var(--toque);" in regla
    assert "color: var(--error);" in regla and "border: 2px solid var(--error);" in regla
