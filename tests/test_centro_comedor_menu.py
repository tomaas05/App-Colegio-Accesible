"""HU-05-03. Asignar el comedor y el reparto del menú (AGENDA-270).

Una o más pruebas por cada prueba de aceptación de Jira, el menú del mes (para HU-06-03)
y los permisos. Datos de prueba: Lucía (A01) tiene cada día «Preparar la mochila» de 9:00
a 9:15, «Lavarse las manos» de 10:30 a 10:45, «Regar las plantas» de 12:00 a 12:30 y
«Leer un cuento» de 17:00 a 17:30, y «Poner la mesa» (casa) a las 20:00.

La fecha se fija en un miércoles (el próximo) para que las pruebas no dependan del día en
que se pasan: el comedor solo es de lunes a viernes.
"""

from datetime import datetime, time, timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios as agenda
from apps.agenda.models import Ejecucion
from apps.centro import servicios
from apps.centro.models import ComedorDelDia, RepartoMenu, TareaDelCentro, TipoTareaCentro
from apps.tareas.models import Asignacion
from apps.usuarios import bajas
from apps.usuarios.models import Estudiante, Usuario

pytestmark = pytest.mark.django_db

URL = reverse("centro:comedor")
# «○ Pendiente de asignar» (en el móvil se lee y se ve solo «Pendiente»).
PENDIENTE = 'Pendiente<span class="centro__largo"> de asignar</span>'


def proximo_miercoles():
    hoy = timezone.localdate()
    return hoy + timedelta(days=(2 - hoy.weekday()) % 7)


MIERCOLES = proximo_miercoles()
JUEVES = MIERCOLES + timedelta(days=1)
MES = MIERCOLES.replace(day=1)


@pytest.fixture(autouse=True)
def hoy_es_miercoles(monkeypatch):
    """Hoy es el miércoles MIERCOLES a las 10:00 (para el centro y para la agenda)."""
    monkeypatch.setattr(servicios, "hoy", lambda: MIERCOLES)
    monkeypatch.setattr(agenda, "ahora", lambda: a_las(MIERCOLES, 10))


def a_las(dia, hora, minuto=0):
    return timezone.make_aware(datetime.combine(dia, time(hora, minuto)))


@pytest.fixture
def admin(client, datos):
    usuario = Usuario.objects.get(username="admin")
    client.force_login(usuario)
    return usuario


def est(codigo):
    return Estudiante.objects.select_related("usuario").get(codigo_estudiante=codigo)


@pytest.fixture
def lucia(datos):
    return est("A01")


@pytest.fixture
def mateo(datos):
    return est("A02")


def url_mes(mes=MES):
    return f"{URL}?mes={mes:%Y-%m}"


def asignar_comedor(client, dia, estudiante, inicio="13:00", fin="14:00"):
    return client.post(
        URL,
        {
            "mes": f"{dia:%Y-%m}",
            "accion": "comedor",
            "comedor-dia": dia.isoformat(),
            "comedor-estudiante": estudiante.pk,
            "comedor-hora_inicio": inicio,
            "comedor-hora_fin": fin,
        },
    )


def asignar_reparto(
    client, estudiante, dias=(1, 2, 3, 4, 5), inicio="11:00", fin="11:30", mes=MES, **kwargs
):
    return client.post(
        URL,
        {
            "mes": f"{mes:%Y-%m}",
            "accion": "reparto",
            "reparto-estudiante": estudiante.pk,
            "reparto-dias": list(dias),
            "reparto-hora_inicio": inicio,
            "reparto-hora_fin": fin,
        },
        **kwargs,
    )


def tareas_del_dia(estudiante, dia):
    """Nombres de las tareas de la agenda del estudiante ese día, en orden."""
    return [t.tarea.nombre for t in agenda.agenda_del_dia(estudiante, a_las(dia, 8)).tareas]


def html(respuesta):
    return respuesta.content.decode()


# --- PA1: asigno el comedor de un día con hora de inicio y fin, y sale en su agenda -------


def test_pa1_asigno_el_comedor_de_un_dia_y_sale_en_su_agenda(client, admin, lucia):
    respuesta = asignar_comedor(client, JUEVES, lucia)

    assert respuesta.status_code == 302
    comedor = ComedorDelDia.objects.get(fecha=JUEVES)
    assert comedor.asignacion.estudiante == lucia
    assert comedor.asignacion.hora_inicio == time(13, 0)
    assert comedor.asignacion.hora_fin == time(14, 0)
    assert tareas_del_dia(lucia, JUEVES) == [
        "Preparar la mochila",
        "Lavarse las manos",
        "Regar las plantas",
        "Comedor",
        "Leer un cuento",
        "Poner la mesa",
    ]
    # Solo ese día.
    assert "Comedor" not in tareas_del_dia(lucia, MIERCOLES)
    assert "Comedor" not in tareas_del_dia(lucia, JUEVES + timedelta(days=7))
    pagina = html(client.get(respuesta["Location"]))
    assert f"Comedor del {servicios.texto_fecha(JUEVES)}: Lucía" in pagina
    assert "de 13:00 a 14:00" in pagina


def test_pa1_el_estudiante_ve_el_comedor_en_su_agenda(client, admin, lucia):
    asignar_comedor(client, MIERCOLES, lucia)

    client.force_login(lucia.usuario)
    respuesta = client.get(reverse("agenda:dia"))
    assert respuesta.status_code == 200
    assert "Comedor" in html(respuesta)
    pk = ComedorDelDia.objects.get(fecha=MIERCOLES).asignacion.pk
    assert client.get(reverse("agenda:detalle", args=[pk])).status_code == 200


def test_pa1_la_tarea_comedor_del_catalogo_se_crea_una_sola_vez(client, admin, lucia, mateo):
    asignar_comedor(client, MIERCOLES, lucia)
    asignar_comedor(client, JUEVES, mateo)

    centro = TareaDelCentro.objects.get(tipo=TipoTareaCentro.COMEDOR)
    assert centro.tarea.nombre == "Comedor"
    assert centro.tarea.descripcion_imagen == "Comedor"
    assert centro.tarea.imagen
    assert set(ComedorDelDia.objects.values_list("asignacion__tarea", flat=True)) == {
        centro.tarea.pk
    }


def test_pa1_solo_de_lunes_a_viernes(admin, lucia):
    sabado = MIERCOLES + timedelta(days=3)
    with pytest.raises(servicios.ErrorDeCentro, match="de lunes a viernes"):
        servicios.asignar_comedor(sabado, lucia, time(13), time(14), admin)
    assert not ComedorDelDia.objects.exists()


def test_pa1_un_dia_que_ya_ha_pasado_no_se_asigna(client, admin, lucia):
    lunes = MIERCOLES - timedelta(days=2)
    with pytest.raises(servicios.ErrorDeCentro, match="ya ha pasado"):
        servicios.asignar_comedor(lunes, lucia, time(13), time(14), admin)
    # Y en la pantalla, ese día ni se ofrece.
    respuesta = asignar_comedor(client, lunes, lucia)
    assert respuesta.status_code == 400
    assert "Elige un día de la lista." in html(respuesta)


def test_pa1_no_se_guarda_si_choca_con_otra_tarea(client, admin, lucia):
    respuesta = asignar_comedor(client, JUEVES, lucia, "12:15", "13:00")

    assert respuesta.status_code == 400
    assert "Lucía ya tiene «Regar las plantas» de 12:00 a 12:30" in html(respuesta)
    assert not ComedorDelDia.objects.exists()


# --- PA2: asigno el reparto del menú de un mes con su horario, y sale en su agenda --------


def test_pa2_asigno_el_reparto_del_menu_y_sale_en_su_agenda(client, admin, lucia):
    respuesta = asignar_reparto(client, lucia, dias=(3, 4))  # miércoles y jueves

    assert respuesta.status_code == 302
    reparto = RepartoMenu.objects.get(mes=MES)
    asignacion = reparto.asignacion
    assert asignacion.estudiante == lucia
    assert asignacion.dias_semana == [3, 4]
    assert asignacion.vigencia_desde == MIERCOLES  # el mes ya ha empezado: desde hoy
    assert asignacion.vigencia_hasta == servicios.ultimo_dia(MES)
    assert "Reparto del menú" in tareas_del_dia(lucia, MIERCOLES)
    viernes = MIERCOLES + timedelta(days=2)
    assert "Reparto del menú" not in tareas_del_dia(lucia, viernes)
    siguiente = servicios.mes_siguiente(MES)
    assert "Reparto del menú" not in tareas_del_dia(lucia, siguiente + timedelta(days=7))
    pagina = html(client.get(respuesta["Location"]))
    assert "Lucía Fernández</b>" in pagina
    assert "(PTVAL 1), miércoles y jueves, de 11:00 a 11:30" in pagina


def test_pa2_el_reparto_de_un_mes_futuro_empieza_el_dia_1(client, admin, lucia):
    siguiente = servicios.mes_siguiente(MES)
    respuesta = asignar_reparto(client, lucia, mes=siguiente)

    assert respuesta.status_code == 302
    asignacion = RepartoMenu.objects.get(mes=siguiente).asignacion
    assert asignacion.vigencia_desde == siguiente
    assert asignacion.dias_semana == [1, 2, 3, 4, 5]


def test_pa2_un_mes_que_ya_ha_pasado_no_se_asigna(admin, lucia):
    with pytest.raises(servicios.ErrorDeCentro, match="ese mes ya ha pasado"):
        servicios.asignar_reparto(
            servicios.mes_anterior(MES), lucia, time(11), time(11, 30), [1], admin
        )


def test_pa2_sin_dias_de_la_semana_no_se_guarda(client, admin, lucia):
    respuesta = asignar_reparto(client, lucia, dias=())

    assert respuesta.status_code == 400
    assert "Elige al menos un día." in html(respuesta)
    assert not RepartoMenu.objects.exists()


# --- PA3: sin horario no se guarda --------------------------------------------------------


def test_pa3_comedor_sin_horario_no_se_guarda(client, admin, lucia):
    respuesta = asignar_comedor(client, JUEVES, lucia, "", "")

    assert respuesta.status_code == 400
    pagina = html(respuesta)
    assert "Pon la hora de inicio." in pagina
    assert "Pon la hora de fin." in pagina
    assert not ComedorDelDia.objects.exists()
    assert not Asignacion.objects.filter(tarea__nombre="Comedor").exists()


def test_pa3_reparto_sin_horario_no_se_guarda(client, admin, lucia):
    respuesta = asignar_reparto(client, lucia, inicio="", fin="")

    assert respuesta.status_code == 400
    assert "Pon la hora de inicio." in html(respuesta)
    assert not RepartoMenu.objects.exists()


def test_pa3_la_hora_de_fin_tiene_que_ser_despues(client, admin, lucia):
    respuesta = asignar_comedor(client, JUEVES, lucia, "14:00", "13:00")

    assert respuesta.status_code == 400
    assert "La hora de fin tiene que ser después de la de inicio." in html(respuesta)
    assert not ComedorDelDia.objects.exists()


def test_pa3_tambien_en_el_servicio(admin, lucia):
    with pytest.raises(servicios.ErrorDeCentro, match="pon la hora de inicio y la de fin"):
        servicios.asignar_comedor(JUEVES, lucia, None, time(14), admin)


# --- PA4: sustituyo al estudiante asignado por otro ---------------------------------------


def test_pa4_sustituyo_al_estudiante_del_comedor(client, admin, lucia, mateo):
    asignar_comedor(client, JUEVES, lucia)
    respuesta = asignar_comedor(client, JUEVES, mateo, "13:30", "14:15")

    assert respuesta.status_code == 302
    comedor = ComedorDelDia.objects.get(fecha=JUEVES)
    assert comedor.asignacion.estudiante == mateo
    assert ComedorDelDia.objects.count() == 1
    assert "Comedor" not in tareas_del_dia(lucia, JUEVES)
    assert "Comedor" in tareas_del_dia(mateo, JUEVES)
    assert "Sustituye a Lucía Fernández." in html(client.get(respuesta["Location"]))


def test_pa4_mismo_estudiante_solo_cambia_la_hora(client, admin, lucia):
    asignar_comedor(client, JUEVES, lucia)
    antes = ComedorDelDia.objects.get(fecha=JUEVES).asignacion.pk
    asignar_comedor(client, JUEVES, lucia, "13:15", "14:00")

    comedor = ComedorDelDia.objects.get(fecha=JUEVES)
    assert comedor.asignacion.pk == antes
    assert comedor.asignacion.hora_inicio == time(13, 15)


def test_pa4_sustituyo_al_estudiante_del_reparto_y_se_conserva_lo_hecho(admin, lucia, mateo):
    # Lucía reparte desde el día 1; el miércoles se cambia por Mateo.
    servicios.asignar_reparto(MES, lucia, time(11), time(11, 30), [1, 2, 3, 4, 5], admin)
    vieja = RepartoMenu.objects.get(mes=MES).asignacion
    vieja.vigencia_desde = MIERCOLES - timedelta(days=7)  # como si se hubiera asignado antes
    vieja.save()

    resultado = servicios.asignar_reparto(
        MES, mateo, time(11), time(11, 30), [1, 2, 3, 4, 5], admin
    )

    assert resultado.sustituido == lucia
    assert RepartoMenu.objects.get(mes=MES).asignacion.estudiante == mateo
    vieja.refresh_from_db()
    assert vieja.vigencia_hasta == MIERCOLES - timedelta(days=1)  # lo de antes se queda
    assert "Reparto del menú" not in tareas_del_dia(lucia, MIERCOLES)
    assert "Reparto del menú" in tareas_del_dia(mateo, MIERCOLES)


def test_pa4_sustituyo_el_reparto_desde_la_pantalla(client, admin, lucia, mateo):
    asignar_reparto(client, lucia)
    respuesta = asignar_reparto(client, mateo, follow=True)

    assert "Sustituye a Lucía Fernández" in html(respuesta)
    assert RepartoMenu.objects.get(mes=MES).asignacion.estudiante == mateo
    assert "Reparto del menú" not in tareas_del_dia(lucia, JUEVES)
    assert "Reparto del menú" in tareas_del_dia(mateo, JUEVES)


# Lo que el estudiante ya ha hecho no se pierde al cambiar o quitar su tarea.


def hecha(asignacion, dia=MIERCOLES):
    return Ejecucion.objects.create(asignacion=asignacion, fecha=dia, estado="hecha")


def test_pa4_sustituir_el_comedor_de_hoy_conserva_lo_que_ya_ha_hecho(admin, lucia, mateo):
    servicios.asignar_comedor(MIERCOLES, lucia, time(13), time(14), admin)
    vieja = ComedorDelDia.objects.get(fecha=MIERCOLES).asignacion
    ejecucion = hecha(vieja)

    servicios.asignar_comedor(MIERCOLES, mateo, time(13), time(14), admin)

    assert Ejecucion.objects.filter(pk=ejecucion.pk).exists()
    assert ComedorDelDia.objects.get(fecha=MIERCOLES).asignacion.estudiante == mateo
    assert "Comedor" in tareas_del_dia(lucia, MIERCOLES)  # con su «Hecha»


def test_pa4_sustituir_el_comedor_sin_empezar_lo_quita_de_su_agenda(admin, lucia, mateo):
    servicios.asignar_comedor(MIERCOLES, lucia, time(13), time(14), admin)
    servicios.asignar_comedor(MIERCOLES, mateo, time(13), time(14), admin)

    assert "Comedor" not in tareas_del_dia(lucia, MIERCOLES)
    assert Asignacion.objects.filter(tarea__del_centro__tipo="comedor").count() == 1


def test_quitar_el_comedor_de_hoy_conserva_lo_que_ya_ha_hecho(admin, lucia):
    servicios.asignar_comedor(MIERCOLES, lucia, time(13), time(14), admin)
    ejecucion = hecha(ComedorDelDia.objects.get(fecha=MIERCOLES).asignacion)

    assert servicios.quitar_comedor(MIERCOLES) == lucia

    assert not ComedorDelDia.objects.exists()
    assert Ejecucion.objects.filter(pk=ejecucion.pk).exists()


def test_pa4_el_mismo_estudiante_del_reparto_cambia_la_hora_sin_perder_lo_de_hoy(admin, lucia):
    servicios.asignar_reparto(MES, lucia, time(11), time(11, 30), [1, 2, 3, 4, 5], admin)
    asignacion = RepartoMenu.objects.get(mes=MES).asignacion
    Asignacion.objects.filter(pk=asignacion.pk).update(vigencia_desde=MIERCOLES - timedelta(days=7))
    ejecucion = hecha(asignacion)

    servicios.asignar_reparto(MES, lucia, time(11, 30), time(11, 45), [1, 3, 5], admin)

    asignacion.refresh_from_db()
    assert RepartoMenu.objects.get(mes=MES).asignacion == asignacion
    assert (asignacion.hora_inicio, asignacion.dias_semana) == (time(11, 30), [1, 3, 5])
    assert Ejecucion.objects.filter(pk=ejecucion.pk).exists()


def test_pa4_un_reparto_que_empezo_hoy_y_ya_esta_hecho_no_se_borra(admin, lucia, mateo):
    servicios.asignar_reparto(MES, lucia, time(11), time(11, 30), [1, 2, 3, 4, 5], admin)
    vieja = RepartoMenu.objects.get(mes=MES).asignacion
    Asignacion.objects.filter(pk=vieja.pk).update(vigencia_desde=MIERCOLES)
    ejecucion = hecha(vieja)

    servicios.asignar_reparto(MES, mateo, time(11), time(11, 30), [1, 2, 3, 4, 5], admin)

    vieja.refresh_from_db()
    assert vieja.vigencia_hasta == MIERCOLES  # se queda hoy, que ya lo ha hecho
    assert Ejecucion.objects.filter(pk=ejecucion.pk).exists()
    assert "Reparto del menú" not in tareas_del_dia(lucia, JUEVES)


def test_dos_administradores_a_la_vez_no_dan_error_500(client, admin, lucia, monkeypatch):
    """El segundo que crea el mismo día choca con la restricción de la base de datos."""

    def ya_existe(**kwargs):
        raise IntegrityError("comedordeldia_fecha_key")

    monkeypatch.setattr(ComedorDelDia.objects, "create", ya_existe)
    respuesta = asignar_comedor(client, JUEVES, lucia)

    assert respuesta.status_code == 400
    assert "otra persona lo estaba cambiando" in html(respuesta)
    assert not Asignacion.objects.filter(estudiante=lucia, tarea__del_centro__isnull=False).exists()


def test_pa4_se_puede_quitar_y_vuelve_a_quedar_pendiente(client, admin, lucia):
    asignar_comedor(client, JUEVES, lucia)
    respuesta = client.post(
        URL, {"mes": f"{MES:%Y-%m}", "accion": "quitar_comedor", "dia": JUEVES.isoformat()}
    )

    assert respuesta.status_code == 302
    assert not ComedorDelDia.objects.exists()
    assert "Comedor" not in tareas_del_dia(lucia, JUEVES)


# --- PA5: un día o un mes sin estudiante se muestra como pendiente de asignar --------------


def test_pa5_los_dias_y_el_mes_sin_estudiante_salen_pendientes(client, admin, lucia):
    lectivos = servicios.dias_lectivos(MES)
    quedan = [d for d in lectivos if d >= MIERCOLES]

    pagina = html(client.get(url_mes()))
    assert pagina.count(PENDIENTE) == len(quedan) + 1  # los días + el reparto

    asignar_comedor(client, JUEVES, lucia)
    asignar_reparto(client, lucia, dias=(5,))
    pagina = html(client.get(url_mes()))
    assert pagina.count(PENDIENTE) == len(quedan) - 1
    # Los días que ya han pasado no se pueden asignar.
    assert pagina.count("Sin asignar") == len(lectivos) - len(quedan)


def test_pa5_al_eliminar_al_estudiante_el_dia_vuelve_a_estar_pendiente(client, admin, lucia):
    asignar_comedor(client, JUEVES, lucia)
    bajas.eliminar(lucia.usuario)

    assert not ComedorDelDia.objects.exists()
    dia = next(d for d in servicios.comedor_del_mes(MES) if d.fecha == JUEVES)
    assert dia.pendiente


def test_pa5_cada_mes_tiene_su_lista(client, admin):
    siguiente = servicios.mes_siguiente(MES)
    pagina = html(client.get(url_mes(siguiente)))
    assert servicios.nombre_mes(siguiente).capitalize() in pagina
    assert pagina.count(PENDIENTE) == len(servicios.dias_lectivos(siguiente)) + 1


# --- Menú del mes (lo ve el familiar en HU-06-03) -----------------------------------------


def subir(client, nombre="menu.pdf", contenido=b"%PDF-1.4 menu", mes=MES):
    return client.post(
        URL,
        {
            "mes": f"{mes:%Y-%m}",
            "accion": "menu",
            "menu-archivo": SimpleUploadedFile(nombre, contenido),
        },
    )


def test_subo_el_menu_del_mes_y_se_puede_consultar(client, admin):
    respuesta = subir(client)

    assert respuesta.status_code == 302
    menu = servicios.menu_del_mes(JUEVES)
    assert menu and menu.name.endswith(".pdf")
    assert servicios.menu_del_mes(servicios.mes_siguiente(MES)) is None
    assert "✓</span> Subido" in html(client.get(url_mes()))
    assert "Ver el menú de" in html(client.get(url_mes() + "&abrir=menu"))


def test_el_menu_no_pide_estudiante_y_no_se_pierde_al_asignar(client, admin, lucia):
    subir(client, "menu.png", b"png")
    asignar_reparto(client, lucia)

    reparto = RepartoMenu.objects.get(mes=MES)
    assert reparto.menu and reparto.asignacion.estudiante == lucia


def test_el_menu_solo_pdf_o_imagen(client, admin):
    respuesta = subir(client, "menu.exe", b"MZ")

    assert respuesta.status_code == 400
    assert servicios.menu_del_mes(MIERCOLES) is None


def test_quito_el_menu_del_mes(client, admin):
    subir(client)
    client.post(URL, {"mes": f"{MES:%Y-%m}", "accion": "quitar_menu"})

    assert servicios.menu_del_mes(MIERCOLES) is None


def test_un_mes_pasado_no_deja_quitar_el_menu(admin):
    pasado = servicios.mes_anterior(MES)
    RepartoMenu.objects.create(mes=pasado, menu="menus/menu-viejo.pdf")

    with pytest.raises(servicios.ErrorDeCentro):
        servicios.quitar_menu(pasado)
    assert RepartoMenu.objects.get(mes=pasado).menu


def test_subir_el_menu_solo_guarda_el_menu(client, admin, lucia):
    """Si otro administrador asigna el reparto a la vez, subir el menú no lo pisa."""
    asignar_reparto(client, lucia)
    with CaptureQueriesContext(connection) as consultas:
        subir(client)

    cambios = [c["sql"] for c in consultas.captured_queries if c["sql"].startswith("UPDATE")]
    assert cambios and all("asignacion_id" not in c for c in cambios)
    assert RepartoMenu.objects.get(mes=MES).asignacion.estudiante == lucia


# --- Permisos y navegación ---------------------------------------------------------------


@pytest.mark.parametrize("usuario", ["tutor", "profesional", "familiar"])
def test_solo_el_administrador(client, datos, usuario):
    client.force_login(Usuario.objects.get(username=usuario))
    assert client.get(URL).status_code == 403


def test_un_estudiante_no_entra(client, lucia):
    client.force_login(lucia.usuario)
    assert client.get(URL).status_code == 403


def test_sin_sesion_va_a_la_portada(client, datos):
    respuesta = client.get(URL)
    assert respuesta.status_code == 302
    assert respuesta["Location"].startswith(reverse("inicio"))


def test_el_administrador_lo_tiene_en_su_panel(client, admin):
    pagina = html(client.get(reverse("usuarios:panel")))
    assert "Comedor y menú" in pagina
    assert URL in pagina


def test_un_mes_que_no_existe_enseña_el_de_hoy(client, admin):
    pagina = html(client.get(f"{URL}?mes=2026-13"))
    assert servicios.nombre_mes(MES).capitalize() in pagina


# --- Restricciones de la base de datos ---------------------------------------------------


def test_la_base_de_datos_no_deja_comedor_en_fin_de_semana_ni_reparto_sin_dia_1(admin, lucia):
    from django.db import IntegrityError, transaction

    asignacion = Asignacion.objects.filter(estudiante=lucia).first()
    sabado = MIERCOLES + timedelta(days=3)
    with pytest.raises(IntegrityError), transaction.atomic():
        ComedorDelDia.objects.create(fecha=sabado, asignacion=asignacion)
    with pytest.raises(IntegrityError), transaction.atomic():
        RepartoMenu.objects.create(mes=MES.replace(day=2))


def test_cambiar_un_dia_trae_sus_datos_y_deja_quitarlo(client, admin, lucia):
    asignar_comedor(client, JUEVES, lucia, "13:15", "14:00")

    pagina = html(client.get(f"{url_mes()}&abrir=comedor&dia={JUEVES.isoformat()}"))
    assert "Ahora lo tiene Lucía Fernández" in pagina
    assert 'value="13:15"' in pagina
    assert f'<option value="{lucia.pk}" selected>' in pagina
    assert 'form="quitar" name="accion" value="quitar_comedor"' in pagina
