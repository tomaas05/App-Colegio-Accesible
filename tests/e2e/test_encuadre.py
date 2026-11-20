"""Encuadre de las pantallas (decisión 0007, acta del 19/11): accesibilidad en navegador.

Cada pantalla, en los 6 tamaños de revisión (ayudas.RESOLUCIONES), con el perfil por defecto
y con el peor perfil (Sofía: letra 32, botones 80, alto contraste):
  - axe sin fallos (WCAG 2.2 AA);
  - sin desplazamiento: ni la página ni <main> (el estudiante nunca hace scroll);
  - nada fuera de la pantalla ni de su caja, y los elementos de una lista no se montan;
  - objetivos de 48 px o más;
  - con el peor perfil, ningún texto por debajo del 80 % de la letra del perfil.
Se lanzan con:  pytest -m e2e tests/e2e/test_encuadre.py
"""

from datetime import datetime, time

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios
from apps.usuarios.models import Clase, Estudiante, Usuario
from tests.e2e.ayudas import PEOR_PERFIL, RESOLUCIONES, con_sesion, revisar

pytestmark = pytest.mark.e2e

# Hugo tiene el perfil por defecto; Sofía, el peor.
ESTUDIANTES = {"defecto": "A04", "peor": PEOR_PERFIL}
PANTALLAS_ESTUDIANTE = [
    "agenda",
    "tarea-en-curso",
    "tarea-antes-de-la-hora",
    "semana",
    "mi-horario",
]
# Pendiente de decidir con el dueño de la pantalla (Tomás): con letra 32 y botones de 80, la
# parte «Hacerla» de una tarea en marcha (pasos, el paso con «Hecho», el aviso y «No puedo
# hacerla») mide ella sola más que un móvil pequeño. Hoy se desplaza <main>, el último recurso
# de la decisión 0005. Para quitarlo hay que partir «Hacerla» en más pantallas.
PENDIENTES = {
    ("peor", "movil-360", "tarea-en-curso"),
    ("peor", "iphone-15-safari", "tarea-en-curso"),
    ("peor", "android-chrome", "tarea-en-curso"),
}


def a_las(hora, minuto=0):
    return timezone.make_aware(datetime.combine(timezone.localdate(), time(hora, minuto)))


@pytest.fixture
def estudiante(request, datos, page, live_server, client, monkeypatch):
    """El estudiante del perfil pedido, a las 10:32, con «Lavarse las manos» empezada."""
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(10, 32))
    est = Estudiante.objects.get(codigo_estudiante=ESTUDIANTES[request.param])
    con_sesion(page, live_server, client, est.usuario)
    manos = est.asignaciones.get(tarea__nombre__icontains="manos")
    servicios.empezar(est, manos.pk, a_las(10, 30))
    return est


def url_estudiante(est, pantalla):
    manos = est.asignaciones.get(tarea__nombre__icontains="manos")
    cuento = est.asignaciones.get(tarea__nombre__icontains="cuento")
    return {
        "agenda": reverse("agenda:dia"),
        "tarea-en-curso": reverse("agenda:detalle", args=[manos.pk]),
        "tarea-antes-de-la-hora": reverse("agenda:detalle", args=[cuento.pk]),
        "semana": reverse("agenda:semana"),
        "mi-horario": reverse("horario:mi_horario"),
    }[pantalla]


@pytest.mark.parametrize("pantalla", PANTALLAS_ESTUDIANTE)
@pytest.mark.parametrize("tamano", RESOLUCIONES)
@pytest.mark.parametrize("estudiante", ESTUDIANTES, indirect=True)
def test_pantallas_del_estudiante(request, live_server, page, estudiante, tamano, pantalla):
    perfil = "peor" if estudiante.codigo_estudiante == PEOR_PERFIL else "defecto"
    if (perfil, tamano, pantalla) in PENDIENTES:
        request.applymarker(
            pytest.mark.xfail(strict=True, reason="«Hacerla» no cabe en un móvil pequeño")
        )
    ancho, alto = RESOLUCIONES[tamano]
    page.set_viewport_size({"width": ancho, "height": alto})
    page.goto(live_server.url + url_estudiante(estudiante, pantalla))
    revisar(page, letra=estudiante.codigo_estudiante == PEOR_PERFIL)


def rutas_de_entrada():
    clase = Clase.objects.order_by("pk").first()
    return {
        "portada": "/",
        "clases": reverse("usuarios:clases"),
        "avatares": reverse("usuarios:avatares", args=[clase.pk]),
        "entrar-imagenes": reverse("usuarios:entrar_estudiante", args=["A04"]),
        "entrar-contrasena": reverse("usuarios:entrar_estudiante", args=["A02"]),
        "entrar-adulto": reverse("usuarios:entrar"),
    }


@pytest.mark.parametrize(
    "pantalla",
    ["portada", "clases", "avatares", "entrar-imagenes", "entrar-contrasena", "entrar-adulto"],
)
@pytest.mark.parametrize("tamano", RESOLUCIONES)
def test_pantallas_de_entrada(live_server, page, datos, tamano, pantalla):
    ancho, alto = RESOLUCIONES[tamano]
    page.set_viewport_size({"width": ancho, "height": alto})
    page.goto(live_server.url + rutas_de_entrada()[pantalla])
    revisar(page)


def rutas_de_adulto():
    clase = Clase.objects.order_by("pk").first()
    return {
        "comedor": ("admin", reverse("centro:comedor")),
        "horario-escolar": ("admin", reverse("horario:cargar") + f"?clase={clase.pk}"),
        "alumnos": ("tutor", reverse("perfil:lista")),
        "perfil-visual": ("tutor", reverse("perfil:editar", args=[PEOR_PERFIL])),
    }


@pytest.mark.parametrize("pantalla", ["comedor", "horario-escolar", "alumnos", "perfil-visual"])
@pytest.mark.parametrize("tamano", RESOLUCIONES)
def test_pantallas_del_acta_de_adultos(live_server, page, client, datos, tamano, pantalla):
    usuario, ruta = rutas_de_adulto()[pantalla]
    con_sesion(page, live_server, client, Usuario.objects.get(username=usuario))
    ancho, alto = RESOLUCIONES[tamano]
    page.set_viewport_size({"width": ancho, "height": alto})
    page.goto(live_server.url + ruta)
    revisar(page)
