"""Fallos de diseño del acta del 19/11 (prueba en tablet y móviles reales): uno por prueba.

Las comprobaciones generales (axe, sin desplazamiento, nada fuera de su caja, 48 px, letra
del perfil) están en test_encuadre.py; aquí, lo concreto de cada fallo.
Se lanzan con:  pytest -m e2e tests/e2e/test_acta_19_11.py
"""

from datetime import datetime, time, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios
from apps.usuarios.models import Clase, Estudiante, Usuario
from tests.e2e.ayudas import PEOR_PERFIL, RESOLUCIONES, con_sesion, ir_a, revisar

pytestmark = pytest.mark.e2e

GRANDES = ["tablet-horizontal", "tablet-grande", "ordenador"]


def a_las(hora, minuto=0):
    return timezone.make_aware(datetime.combine(timezone.localdate(), time(hora, minuto)))


def tamano(page, nombre):
    ancho, alto = RESOLUCIONES[nombre]
    page.set_viewport_size({"width": ancho, "height": alto})


def caja(localizador):
    return localizador.evaluate(
        "e => { const b = e.getBoundingClientRect(); "
        "return {top: b.top, bottom: b.bottom, left: b.left, right: b.right, "
        "alto: b.height, ancho: b.width, letra: parseFloat(getComputedStyle(e).fontSize), "
        "linea: parseFloat(getComputedStyle(e).lineHeight)}; }"
    )


def letra_del_perfil(page):
    return page.evaluate(
        "() => { const r = getComputedStyle(document.documentElement); "
        "return parseFloat(r.getPropertyValue('--tamano-base')) * parseFloat(r.fontSize); }"
    )


# --- a · Mi horario: con letra y botones al máximo, la barra, la fecha y los días crecen ---


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_a_mi_horario_crece_con_la_letra_del_perfil(live_server, page, client, datos, nombre):
    sofia = Estudiante.objects.get(codigo_estudiante=PEOR_PERFIL)
    con_sesion(page, live_server, client, sofia.usuario)
    tamano(page, nombre)
    page.goto(live_server.url + reverse("horario:mi_horario"))
    base = letra_del_perfil(page)
    assert base == 32
    assert caja(page.locator("#titulo"))["letra"] >= base
    fecha = page.locator(".barra__fecha time span:visible").first
    assert caja(fecha)["letra"] >= base * 0.8
    dia = page.locator(".mi-horario__dia .dia-forma").first
    assert caja(dia)["letra"] >= base * 0.8
    assert caja(page.locator(".mi-horario__dia").first)["alto"] >= 79.5  # botones de 80
    revisar(page, letra=True)


# --- b · Comedor: «Pendiente» en una línea. Perfil visual: la vista previa, en su tarjeta ---


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_b_la_pildora_pendiente_no_se_parte(live_server, page, client, datos, nombre):
    con_sesion(page, live_server, client, Usuario.objects.get(username="admin"))
    tamano(page, nombre)
    page.goto(live_server.url + reverse("centro:comedor"))
    pildoras = page.locator(".centro__pendiente:visible")
    assert pildoras.count() >= 1
    for i in range(pildoras.count()):
        p = caja(pildoras.nth(i))
        assert p["alto"] < p["linea"] * 1.6, "la píldora ocupa más de una línea"


@pytest.mark.parametrize("codigo", ["A01", PEOR_PERFIL])  # Lucía (24/64) y Sofía (32/80)
@pytest.mark.parametrize("panel", ["tamano_botones", "temporizador"])
@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_b_d_el_perfil_visual_se_queda_en_su_tarjeta(
    live_server, page, client, datos, nombre, panel, codigo
):
    con_sesion(page, live_server, client, Usuario.objects.get(username="tutor"))
    tamano(page, nombre)
    page.goto(live_server.url + reverse("perfil:editar", args=[codigo]))
    revisar(page)  # la lista de categorías
    ir_a(page, f'[data-abrir="{panel}"]')
    page.click(f'[data-abrir="{panel}"]')
    revisar(page)  # el panel abierto, con la vista previa a su tamaño


# --- c · Tarea en tablet horizontal: sin hueco y «Podrás empezar a las…» grande ---


@pytest.mark.parametrize("nombre", GRANDES)
def test_c_el_aviso_de_la_tarea_es_grande_y_va_centrado(
    live_server, page, client, datos, monkeypatch, nombre
):
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(10, 32))
    # Sin margen desde la retrospectiva del 19/11; con uno de 15 min sale el aviso.
    monkeypatch.setattr(servicios, "MARGEN_EMPEZAR_ANTES", timedelta(minutes=15))
    hugo = Estudiante.objects.get(codigo_estudiante="A04")
    con_sesion(page, live_server, client, hugo.usuario)
    cuento = hugo.asignaciones.get(tarea__nombre__icontains="cuento")
    tamano(page, nombre)
    page.goto(live_server.url + reverse("agenda:detalle", args=[cuento.pk]))
    aviso = page.get_by_text("Podrás empezar a las 16:45.")
    a = caja(aviso)
    assert a["letra"] >= letra_del_perfil(page) * 1.2
    # A la misma altura que «qué es» (centrado en su columna), no suelto al pie.
    que = caja(page.locator(".col--que .ficha"))
    columna = caja(page.locator(".col--hacer"))
    assert abs((a["top"] + a["bottom"]) / 2 - (columna["top"] + columna["bottom"]) / 2) < 4
    assert a["top"] < que["bottom"] + columna["alto"] / 2
    revisar(page)


# --- f · Alumnos: las tarjetas aprovechan el ancho ---


@pytest.mark.parametrize("nombre", GRANDES)
def test_f_las_tarjetas_de_alumnos_aprovechan_el_ancho(live_server, page, client, datos, nombre):
    con_sesion(page, live_server, client, Usuario.objects.get(username="tutor"))
    tamano(page, nombre)
    page.goto(live_server.url + reverse("perfil:lista"))
    lista = caja(page.locator("#alumnos"))
    tarjetas = page.locator(".perfil-estudiante-card")
    primera, ultima_fila = caja(tarjetas.first), caja(tarjetas.last)
    assert primera["ancho"] >= 250
    # Las columnas llenan el ancho de la lista (auto-fit): no quedan columnas vacías.
    derecha = max(caja(tarjetas.nth(i))["right"] for i in range(tarjetas.count()))
    assert derecha >= lista["right"] - 2
    assert ultima_fila["bottom"] <= lista["bottom"] + 1
    revisar(page)


# --- g · Agenda en el móvil con letra grande: «Salir» con SVG y el pie en su sitio ---


@pytest.mark.parametrize("nombre", ["movil-360", "iphone-15-safari", "android-chrome"])
def test_g_agenda_con_letra_grande_en_el_movil(
    live_server, page, client, datos, monkeypatch, nombre
):
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(10, 32))
    sofia = Estudiante.objects.get(codigo_estudiante=PEOR_PERFIL)
    con_sesion(page, live_server, client, sofia.usuario)
    tamano(page, nombre)
    page.goto(live_server.url + reverse("agenda:dia"))
    salir = page.get_by_role("button", name="Salir", exact=True)
    assert salir.locator("svg.icono").count() == 1  # un dibujo, no un glifo que falte
    antes = salir.evaluate("b => getComputedStyle(b, '::before').content")
    assert antes in ("none", "normal")  # ni «⏻» ni otro glifo en ::before
    for boton in [salir, page.get_by_role("link", name="Mi semana")]:
        b = caja(boton)
        assert b["alto"] >= 79.5 and b["right"] <= RESOLUCIONES[nombre][0]
    semana = caja(page.get_by_role("link", name="Mi semana"))
    horario = caja(page.get_by_role("link", name="Mi horario de clase"))
    assert abs(semana["top"] - horario["top"]) < 1, "«Mi semana» y «Mi horario» en la misma fila"
    revisar(page, letra=True)


# --- h · Horario escolar: un día cada vez, con todas sus franjas ---


@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_h_horario_escolar_por_dias(live_server, page, client, datos, nombre):
    con_sesion(page, live_server, client, Usuario.objects.get(username="admin"))
    clase = Clase.objects.get(nombre="PTVAL 1")
    tamano(page, nombre)
    page.goto(live_server.url + reverse("horario:cargar") + f"?clase={clase.pk}&dia=1")
    dias = page.get_by_role("navigation", name="Elegir día").get_by_role("link")
    assert dias.count() == 5
    assert page.locator('.mi-horario__dia[aria-current="page"]').count() == 1
    page.locator(".mi-horario__dia").nth(2).click()  # miércoles
    assert page.get_by_role("heading", name="Miércoles · PTVAL 1").is_visible()
    revisar(page)


# --- i · Entrar y contraseña: centradas también en tableta y ordenador ---


@pytest.mark.parametrize("pantalla", ["adulto", "contrasena"])
@pytest.mark.parametrize("nombre", RESOLUCIONES)
def test_i_la_entrada_va_centrada(live_server, page, datos, nombre, pantalla):
    tamano(page, nombre)
    if pantalla == "adulto":
        page.goto(live_server.url + reverse("usuarios:entrar"))
        bloque = page.locator(".acceso > form")
    else:
        page.goto(live_server.url + reverse("usuarios:entrar_estudiante", args=["A02"]))
        bloque = page.locator(".formulario--estudiante")
    barra = caja(page.locator("header.barra"))
    cuerpo = caja(bloque)
    hueco_arriba = cuerpo["top"] - barra["bottom"]
    alto = RESOLUCIONES[nombre][1]
    # El contenido (campos y «Entrar») queda en el centro del sitio que deja la barra.
    contenido = page.locator(
        ".acceso > form > :not([type=hidden]), .formulario--estudiante > :not([type=hidden])"
    )
    abajo = max(caja(contenido.nth(i))["bottom"] for i in range(contenido.count()))
    arriba = min(caja(contenido.nth(i))["top"] for i in range(contenido.count()))
    assert abs((arriba - barra["bottom"]) - (alto - abajo)) < 40, (hueco_arriba, arriba, abajo)
    revisar(page)


# --- j · «Quitar» es una papelera roja de 48 px con nombre accesible ---


def test_j_las_papeleras_del_horario(live_server, page, client, datos):
    con_sesion(page, live_server, client, Usuario.objects.get(username="admin"))
    clase = Clase.objects.get(nombre="PTVAL 1")
    tamano(page, "tablet-grande")
    page.goto(live_server.url + reverse("horario:cargar") + f"?clase={clase.pk}&dia=1")
    papeleras = page.locator(".boton--papelera:visible")
    assert papeleras.count() >= 1
    primera = papeleras.first
    assert primera.get_attribute("aria-label") is None  # el nombre sale del texto oculto
    nombre = primera.evaluate("b => b.textContent.trim()")
    assert nombre.startswith("Quitar ") and " del lunes a las " in nombre
    b = caja(primera)
    assert b["ancho"] >= 48 and b["alto"] >= 48
    colores = primera.evaluate(
        "b => [getComputedStyle(b).color, getComputedStyle(b).borderTopColor,"
        " getComputedStyle(b).backgroundColor]"
    )
    assert colores[0] == colores[1] == "rgb(181, 71, 8)"  # --error: 5,43:1 sobre blanco
    assert colores[2] == "rgb(255, 255, 255)"
    revisar(page)


def test_j_quitar_con_la_papelera_sigue_funcionando(live_server, page, client, datos):
    con_sesion(page, live_server, client, Usuario.objects.get(username="admin"))
    clase = Clase.objects.get(nombre="PTVAL 1")
    tamano(page, "tablet-grande")
    page.goto(live_server.url + reverse("horario:cargar") + f"?clase={clase.pk}&dia=2")
    antes = page.locator(".boton--papelera").count()
    page.locator(".boton--papelera").first.click()
    page.wait_for_load_state()
    assert page.get_by_role("status").get_by_text("Quitada").is_visible()
    assert page.locator(".boton--papelera").count() == antes - 1
    assert "dia=2" in page.url  # vuelve al mismo día
