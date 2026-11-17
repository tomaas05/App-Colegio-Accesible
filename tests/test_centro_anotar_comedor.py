"""HU-05-04. Anotar quién come cada día (AGENDA-276).

Una o más pruebas por cada prueba de aceptación de Jira, el acceso (solo el encargado de
hoy) y `comedor_de` para el familiar (HU-06-03, Manu). Datos de prueba: en PTVAL 1 están
Lucía, Mateo, Sofía, Hugo, Martina y Leo; en PTVAL 2, Daniela, Pablo y Vega. Hoy es el
próximo miércoles y el encargado del comedor es Hugo (A04).
"""

from datetime import datetime, time, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios as agenda
from apps.agenda.models import Ejecucion, EstadoEjecucion
from apps.centro import comedor, servicios
from apps.centro.models import AsistenciaComedor, ClaseComedorTerminada, ComedorDelDia
from apps.usuarios.models import Clase, Estudiante, Usuario

pytestmark = pytest.mark.django_db

HOY = timezone.localdate() + timedelta(days=(2 - timezone.localdate().weekday()) % 7)
URL = reverse("centro:comedor_hoy")


@pytest.fixture(autouse=True)
def hoy_es_miercoles(monkeypatch):
    monkeypatch.setattr(servicios, "hoy", lambda: HOY)
    monkeypatch.setattr(
        agenda, "ahora", lambda: timezone.make_aware(datetime.combine(HOY, time(13, 5)))
    )


def est(codigo):
    return Estudiante.objects.select_related("usuario", "clase").get(codigo_estudiante=codigo)


@pytest.fixture
def hugo(datos):
    """El encargado del comedor de hoy, con la sesión abierta."""
    admin = Usuario.objects.get(username="admin")
    hugo = est("A04")
    servicios.asignar_comedor(HOY, hugo, time(13), time(14), admin)
    return hugo


@pytest.fixture
def entra(client, hugo):
    client.force_login(hugo.usuario)
    return client


def ptval(n):
    return Clase.objects.get(nombre=f"PTVAL {n}")


def url_clase(clase):
    return reverse("centro:comedor_clase", args=[clase.pk])


def tocar(client, codigo, clase=None, **extra):
    clase = clase or est(codigo).clase
    return client.post(reverse("centro:comedor_marcar", args=[clase.pk, codigo]), **extra)


def terminar(client, clase):
    return client.post(reverse("centro:comedor_terminar", args=[clase.pk]))


def marcar_todos(encargado, clase, come=True):
    for e in Estudiante.objects.filter(clase=clase, usuario__is_active=True):
        comedor.marcar(encargado, e, come)


def html(respuesta):
    return respuesta.content.decode()


# --- PA1: veo los estudiantes de cada clase con su avatar -------------------------------


def test_pa1_veo_las_clases_del_centro(entra):
    pagina = html(entra.get(URL))

    assert "PTVAL 1" in pagina and "PTVAL 2" in pagina
    assert "0 de 6" in pagina and "0 de 3" in pagina
    assert "Comen hoy: <strong>0</strong>" in pagina


def test_pa1_veo_los_companeros_de_una_clase_con_su_avatar(entra):
    pagina = html(entra.get(url_clase(ptval(1))))

    for codigo in ("A01", "A02", "A03", "A04", "A05", "A06"):
        e = est(codigo)
        assert e.usuario.first_name in pagina
        assert e.avatar.url in pagina
    assert pagina.count("Sin marcar") == 6
    assert "Daniela" not in pagina


def test_pa1_un_estudiante_dado_de_baja_no_sale(entra):
    Usuario.objects.filter(estudiante__codigo_estudiante="A06").update(is_active=False)

    pagina = html(entra.get(url_clase(ptval(1))))
    assert "Leo" not in pagina
    assert "0 de 5" in html(entra.get(URL))


def test_pa1_se_llega_desde_la_tarea_comedor_ya_empezada(entra, hugo):
    asignacion = ComedorDelDia.objects.get(fecha=HOY).asignacion
    tarea = reverse("agenda:detalle", args=[asignacion.pk])
    assert "Anotar quién come" not in html(entra.get(tarea))  # sin empezar

    Ejecucion.objects.create(asignacion=asignacion, fecha=HOY, estado=EstadoEjecucion.EN_CURSO)
    pagina = html(entra.get(tarea))
    assert f'href="{URL}"' in pagina and "Anotar quién come" in pagina
    # Y desde las clases se vuelve a la tarea.
    assert f'href="{tarea}"' in html(entra.get(URL))


# --- PA2: marco si cada compañero come o no come ----------------------------------------


def test_pa2_un_toque_marca_que_come_y_otro_que_no(entra, hugo):
    lucia = est("A01")

    assert tocar(entra, "A01").status_code == 302
    assert AsistenciaComedor.objects.get(fecha=HOY, estudiante=lucia).come is True
    tocar(entra, "A01")
    marca = AsistenciaComedor.objects.get(fecha=HOY, estudiante=lucia)
    assert marca.come is False and marca.anotada_por == hugo.usuario

    pagina = html(entra.get(url_clase(ptval(1))))
    assert "No come" in pagina and "Marcados 1 de 6" in pagina


def test_pa2_con_htmx_solo_cambia_la_marca_y_el_recuento(entra):
    respuesta = tocar(entra, "A02", HTTP_HX_REQUEST="true")

    assert respuesta.status_code == 200
    pagina = html(respuesta)
    assert 'id="marca-A02"' in pagina and 'comedor__marca--come" id="marca-A02"' in pagina
    assert "Mateo: come." in pagina  # lo que oye el lector de pantalla
    assert 'Marcados 1 de 6<span class="comedor__solo-ancho"> · Comen hoy: 1' in pagina


def test_pa2_el_total_del_centro_cuenta_los_que_comen(entra, hugo):
    comedor.marcar(hugo, est("A01"), True)
    comedor.marcar(hugo, est("A02"), False)
    comedor.marcar(hugo, est("B01"), True)

    assert comedor.resumen(HOY).comen == 2
    assert "Comen hoy: <strong>2</strong>" in html(entra.get(URL))


# --- PA3: puedo corregir una marca mientras la clase no esté terminada -------------------


def test_pa3_corrijo_una_marca(entra, hugo):
    comedor.marcar(hugo, est("A03"), False)
    tocar(entra, "A03")

    assert AsistenciaComedor.objects.get(fecha=HOY, estudiante=est("A03")).come is True


def test_pa3_con_la_clase_terminada_no_se_puede_cambiar(entra, hugo):
    marcar_todos(hugo, ptval(2))
    comedor.terminar_clase(hugo, ptval(2))

    respuesta = tocar(entra, "B01")
    assert respuesta.status_code == 400
    assert "ya está terminada" in html(respuesta)
    assert AsistenciaComedor.objects.get(fecha=HOY, estudiante=est("B01")).come is True
    # Y la pantalla ya no ofrece tocar a nadie.
    pagina = html(entra.get(url_clase(ptval(2))))
    assert "data-marcar" not in pagina and "Clase terminada" in pagina


# --- PA4: marco la clase como terminada y veo qué clases me faltan -----------------------


def test_pa4_termino_una_clase_y_veo_las_que_faltan(entra, hugo):
    marcar_todos(hugo, ptval(2))

    respuesta = terminar(entra, ptval(2))
    assert respuesta.status_code == 302 and respuesta.url == URL
    assert ClaseComedorTerminada.objects.filter(fecha=HOY, clase=ptval(2)).exists()

    pagina = html(entra.get(URL))
    assert "PTVAL 2 terminada." in pagina and "Te falta PTVAL 1." in pagina
    assert "Terminada" in pagina and "0 de 6" in pagina


def test_pa4_con_todas_terminadas_lo_dice(entra, hugo):
    for clase in comedor.clases_del_centro():
        marcar_todos(hugo, clase)
        comedor.terminar_clase(hugo, clase)

    assert comedor.resumen(HOY).texto_faltan == "Has terminado todas las clases."


def test_pa4_terminar_dos_veces_no_falla(entra, hugo):
    marcar_todos(hugo, ptval(2))
    terminar(entra, ptval(2))

    assert terminar(entra, ptval(2)).status_code == 302
    assert ClaseComedorTerminada.objects.filter(fecha=HOY).count() == 1


# --- PA5: no puedo terminar una clase con compañeros sin marcar ---------------------------


def test_pa5_no_termino_con_companeros_sin_marcar(entra, hugo):
    comedor.marcar(hugo, est("B01"), True)

    respuesta = terminar(entra, ptval(2))
    assert respuesta.status_code == 400
    assert "Te faltan 2 compañeros por marcar." in html(respuesta)
    assert not ClaseComedorTerminada.objects.exists()


def test_pa5_el_boton_se_ve_apagado_mientras_falta_alguien(entra, hugo):
    pagina = html(entra.get(url_clase(ptval(2))))
    assert 'aria-disabled="true" aria-describedby="comedor-faltan"' in pagina
    assert "Faltan 3 compañeros por marcar." in pagina

    marcar_todos(hugo, ptval(2))
    assert 'aria-disabled="true"' not in html(entra.get(url_clase(ptval(2))))


def test_pa5_con_uno_solo_lo_dice_en_singular(hugo):
    marcar_todos(hugo, ptval(2))
    AsistenciaComedor.objects.filter(estudiante=est("B03")).delete()

    with pytest.raises(servicios.ErrorDeCentro, match="Te falta 1 compañero por marcar."):
        comedor.terminar_clase(hugo, ptval(2))


# --- Acceso: solo el encargado del comedor de hoy ----------------------------------------


@pytest.mark.parametrize("codigo", ["A01", "B01"])
def test_otro_estudiante_no_entra(client, hugo, codigo):
    client.force_login(est(codigo).usuario)

    assert client.get(URL).status_code == 403
    assert tocar(client, "A02").status_code == 403
    assert not AsistenciaComedor.objects.exists()


def test_el_encargado_de_otro_dia_no_entra(client, datos):
    admin = Usuario.objects.get(username="admin")
    servicios.asignar_comedor(HOY + timedelta(days=1), est("A04"), time(13), time(14), admin)
    client.force_login(est("A04").usuario)

    assert client.get(URL).status_code == 403


@pytest.mark.parametrize("usuario", ["admin", "tutor", "familiar"])
def test_un_adulto_no_entra(client, hugo, usuario):
    client.force_login(Usuario.objects.get(username=usuario))
    assert client.get(URL).status_code == 403


def test_sin_sesion_va_a_entrar(client, hugo):
    assert client.get(URL).status_code == 302


def test_el_codigo_tiene_que_ser_de_esa_clase(entra):
    assert tocar(entra, "B01", clase=ptval(1)).status_code == 404
    assert not AsistenciaComedor.objects.exists()


def test_marcar_solo_con_post(entra):
    url = reverse("centro:comedor_marcar", args=[ptval(1).pk, "A01"])
    assert entra.get(url).status_code == 405


# --- Para el familiar (HU-06-03, Manu) ---------------------------------------------------


def test_comedor_de_no_se_sabe_hasta_que_la_clase_esta_terminada(hugo):
    daniela, pablo = est("B01"), est("B02")
    marcar_todos(hugo, ptval(2))
    comedor.marcar(hugo, pablo, False)

    assert comedor.comedor_de(daniela, HOY) is None  # aún se puede cambiar
    comedor.terminar_clase(hugo, ptval(2))
    assert comedor.comedor_de(daniela, HOY) == comedor.COME
    assert comedor.comedor_de(pablo, HOY) == comedor.NO_COME
    assert comedor.comedor_de(daniela, HOY + timedelta(days=1)) is None


def test_la_base_de_datos_no_deja_dos_marcas_del_mismo_dia(hugo):
    from django.db import IntegrityError

    comedor.marcar(hugo, est("A01"), True)
    with pytest.raises(IntegrityError):
        AsistenciaComedor.objects.create(fecha=HOY, estudiante=est("A01"), come=False)
