"""HU-06-03 · Consultar el día del estudiante (AGENDA-69).

Una prueba por cada prueba de aceptación de Jira (PA1 a PA5) y las de cada caso del
comedor y del menú. Carmen (`familiar`) es la familiar de Lucía (A01, PTVAL 1); Javier
(`familiar2`), de Daniela (B01, PTVAL 2).
"""

import io
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.centro.models import AsistenciaComedor, ClaseComedorTerminada, RepartoMenu
from apps.usuarios.models import Estudiante, Usuario

pytestmark = pytest.mark.django_db


def url(codigo="A01", dia=None):
    base = reverse("seguimiento:dia", args=[codigo])
    return f"{base}?dia={dia.isoformat()}" if dia else base


def como(client, usuario):
    client.force_login(Usuario.objects.get(username=usuario))
    return client


def lucia():
    return Estudiante.objects.select_related("usuario", "clase").get(codigo_estudiante="A01")


def dia_lectivo(atras=0):
    """Un día de lunes a viernes: hoy si lo es, o el último antes de hoy, menos `atras`."""
    dia = timezone.localdate() - timedelta(days=atras)
    while dia.isoweekday() > 5:
        dia -= timedelta(days=1)
    return dia


def anotar(estudiante, fecha, come, terminada=True):
    AsistenciaComedor.objects.create(fecha=fecha, estudiante=estudiante, come=come)
    if terminada:
        ClaseComedorTerminada.objects.create(fecha=fecha, clase=estudiante.clase)


def subir_menu(fecha, nombre="menu.png"):
    if nombre.endswith(".pdf"):
        contenido, tipo = b"%PDF-1.4 menu", "application/pdf"
    else:
        salida = io.BytesIO()
        Image.new("RGB", (8, 8), "#1F6F6B").save(salida, format="PNG")
        contenido, tipo = salida.getvalue(), "image/png"
    return RepartoMenu.objects.create(
        mes=fecha.replace(day=1), menu=SimpleUploadedFile(nombre, contenido, content_type=tipo)
    )


# --- PA1: veo la agenda del día del estudiante en modo solo lectura ---


def test_pa1_el_familiar_ve_las_tareas_del_dia(client, datos):
    dia = dia_lectivo()
    html = como(client, "familiar").get(url(dia=dia)).content.decode()
    assert "Día de Lucía" in html and "Solo consulta" in html
    # Las tareas de ese día, como en la agenda del profesional (B27).
    assert "Regar las plantas" in html and "Preparar la mochila" in html
    assert 'class="consulta__tareas"' in html


def test_pa1_se_pasa_de_un_dia_a_otro(client, datos):
    dia = dia_lectivo(atras=7)
    respuesta = como(client, "familiar").get(url(dia=dia))
    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    assert f"?dia={(dia - timedelta(days=1)).isoformat()}" in html
    assert ">Hoy<" in html  # para volver a hoy


# --- PA2: no puedo modificar la planificación ---


def test_pa2_sin_nada_que_cambiar(client, datos):
    html = como(client, "familiar").get(url(dia=dia_lectivo())).content.decode()
    principal = html.split('id="contenido"', 1)[1]
    assert "<form" not in principal and 'method="post"' not in principal
    assert reverse("tareas:tareas_planificadas") not in principal
    assert como(client, "familiar").post(url()).status_code == 405


# --- PA3: veo si el estudiante ha acudido al comedor ---


def test_pa3_ha_ido_al_comedor(client, datos):
    dia = dia_lectivo()
    anotar(lucia(), dia, come=True)
    html = como(client, "familiar").get(url(dia=dia)).content.decode()
    assert "Lucía ha ido al comedor." in html
    assert "dia-comedor__estado--come" in html and "✓" in html


def test_pa3_no_ha_ido_al_comedor(client, datos):
    dia = dia_lectivo()
    anotar(lucia(), dia, come=False)
    html = como(client, "familiar").get(url(dia=dia)).content.decode()
    assert "Lucía no ha ido al comedor." in html and "✕" in html


def test_pa3_mientras_la_clase_no_esta_terminada_no_se_sabe(client, datos):
    """La marca se puede cambiar hasta terminar la clase (HU-05-04): todavía no cuenta."""
    hoy = timezone.localdate()
    if hoy.isoweekday() > 5:
        pytest.skip("Hoy no hay comedor")
    anotar(lucia(), hoy, come=True, terminada=False)
    html = como(client, "familiar").get(url()).content.decode()
    assert "Todavía no se sabe: aún no se ha anotado." in html
    assert "ha ido al comedor" not in html


def test_pa3_dias_sin_anotar_fin_de_semana_y_futuro(client, datos):
    familiar = como(client, "familiar")
    pasado = dia_lectivo(atras=7)
    assert "Ese día no se anotó." in familiar.get(url(dia=pasado)).content.decode()
    sabado = timezone.localdate() + timedelta(days=(6 - timezone.localdate().isoweekday()) % 7)
    assert "no hay comedor" in familiar.get(url(dia=sabado)).content.decode()
    futuro = timezone.localdate() + timedelta(days=1)
    while futuro.isoweekday() > 5:
        futuro += timedelta(days=1)
    assert "todavía no ha llegado" in familiar.get(url(dia=futuro)).content.decode()


# --- PA4: veo el menú del día ---


def test_pa4_el_menu_del_mes_en_imagen(client, datos):
    dia = dia_lectivo()
    reparto = subir_menu(dia)
    html = como(client, "familiar").get(url(dia=dia)).content.decode()
    assert reparto.menu.url in html
    assert 'alt="Menú del comedor de ' in html and "Ver el menú en grande" in html


def test_pa4_el_menu_del_mes_en_pdf(client, datos):
    dia = dia_lectivo()
    reparto = subir_menu(dia, "menu.pdf")
    html = como(client, "familiar").get(url(dia=dia)).content.decode()
    assert reparto.menu.url in html and "Ver el menú (PDF)" in html
    assert "<img" not in html.split('id="dia-comedor-t"')[1].split("</section>")[0]


def test_pa4_sin_menu_lo_dice(client, datos):
    html = como(client, "familiar").get(url(dia=dia_lectivo())).content.decode()
    assert "El colegio todavía no ha subido el menú de" in html


def test_pa4_es_el_menu_del_mes_de_ese_dia(client, datos):
    dia = dia_lectivo()
    otro_mes = (dia.replace(day=1) - timedelta(days=1)).replace(day=1)
    reparto = subir_menu(otro_mes)
    html = como(client, "familiar").get(url(dia=dia)).content.decode()
    assert reparto.menu.url not in html


# --- PA5: solo veo al estudiante con el que estoy vinculado ---


def test_pa5_otro_estudiante_da_404(client, datos):
    assert como(client, "familiar").get(url("B01")).status_code == 404
    assert como(client, "familiar2").get(url("A01")).status_code == 404
    assert como(client, "familiar").get(url("Z99")).status_code == 404


@pytest.mark.parametrize("quien", ["tutor", "profesional", "admin", "est-a01"])
def test_pa5_solo_el_familiar_usa_esta_pantalla(client, datos, quien):
    assert como(client, quien).get(url()).status_code == 403
    assert como(client, quien).get(reverse("seguimiento:familiar")).status_code == 403


def test_sin_sesion_va_a_la_portada(client, datos):
    respuesta = client.get(url())
    assert respuesta.status_code == 302 and respuesta["Location"].startswith(reverse("inicio"))


# --- Cómo se llega ---


def test_con_un_estudiante_va_directo_a_su_dia(client, datos):
    respuesta = como(client, "familiar").get(reverse("seguimiento:familiar"))
    assert respuesta.status_code == 302 and respuesta["Location"] == url()


def test_con_varios_elige_de_quien(client, datos):
    carmen = Usuario.objects.get(username="familiar")
    Estudiante.objects.filter(codigo_estudiante="A04").update(
        familiar=carmen, fecha_alta_familiar=timezone.localdate()
    )
    html = como(client, "familiar").get(reverse("seguimiento:familiar")).content.decode()
    assert f'href="{url("A01")}"' in html and f'href="{url("A04")}"' in html
    # En su día, «volver» lleva a elegir otra vez.
    html = client.get(url("A04")).content.decode()
    assert reverse("seguimiento:familiar") in html and "Día de Hugo" in html


def test_en_el_menu_y_en_el_panel_del_familiar(client, datos):
    html = como(client, "familiar").get(reverse("usuarios:panel")).content.decode()
    assert "Día en el colegio" in html and reverse("seguimiento:familiar") in html
    # Cada estudiante del panel lleva a su día.
    assert f'href="{url("A01")}"' in html
