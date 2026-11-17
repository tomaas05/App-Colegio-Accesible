"""HU-03-05 · Cancelar una tarea planificada, y el aviso que recibe el estudiante.

Datos de prueba: Lucía (A01) tiene todos los días mochila 9:00–9:15, manos 10:30–10:45,
regar 12:00–12:30 y cuento 17:00–17:30 (de su tutora Ana) y «Poner la mesa» 20:00–20:20
(de su familiar Carmen).
"""

from datetime import datetime, time, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios
from apps.agenda.models import Ejecucion, EstadoEjecucion
from apps.comun.models import Notificacion, TipoAviso, avisar
from apps.tareas import planificacion
from apps.tareas.models import ExcepcionAsignacion, TipoExcepcion
from apps.usuarios.models import Estudiante, Usuario

pytestmark = pytest.mark.django_db


@pytest.fixture
def lucia(datos):
    return Estudiante.objects.get(codigo_estudiante="A01")


def entrar(client, usuario):
    client.force_login(Usuario.objects.get(username=usuario))
    return client


def de(estudiante, nombre):
    return estudiante.asignaciones.get(tarea__nombre=nombre)


def url_cancelar(asignacion, **parametros):
    url = reverse("tareas:confirmar_cancelacion", args=[asignacion.pk])
    if parametros:
        url += "?" + "&".join(f"{k}={v}" for k, v in parametros.items())
    return url


def a_las(hora, minuto=0, dia=None):
    dia = dia or timezone.localdate()
    return timezone.make_aware(datetime.combine(dia, time(hora, minuto)))


def manana():
    return timezone.localdate() + timedelta(days=1)


def avisos_de(estudiante):
    return Notificacion.objects.filter(destinatario=estudiante.usuario)


# --- Confirmación (PA3) ---------------------------------------------------------------


def test_antes_de_cancelar_se_pide_confirmacion_y_no_cambia_nada(client, lucia):
    regar = de(lucia, "Regar las plantas")
    respuesta = entrar(client, "tutor").get(url_cancelar(regar))
    html = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert "¿Cancelar «Regar las plantas» de Lucía" in html
    assert "Sí, cancelar" in html and ">No<" in html
    regar.refresh_from_db()
    assert not regar.cancelada and not avisos_de(lucia).exists()


def test_la_pantalla_de_confirmar_no_anida_otro_main(client, lucia):
    html = entrar(client, "tutor").get(url_cancelar(de(lucia, "Regar las plantas"))).content
    assert html.count(b"<main") == 1


# --- Toda la serie --------------------------------------------------------------------


def test_cancelar_la_serie(client, lucia):
    regar = de(lucia, "Regar las plantas")
    respuesta = entrar(client, "tutor").post(url_cancelar(regar), {"alcance": "serie"})
    assert respuesta.status_code == 302
    regar.refresh_from_db()
    assert regar.cancelada and regar.cancelada_el == timezone.localdate()

    aviso = avisos_de(lucia).get()
    assert aviso.tipo == TipoAviso.CANCELACION and aviso.tarea == regar.tarea
    assert aviso.mensaje == "«Regar las plantas» se ha cancelado. Ya no la tienes que hacer."


def test_la_serie_cancelada_sale_como_cancelada_en_la_agenda(client, lucia):
    """PA1: el estudiante la ve tachada, «Cancelada», y no la puede empezar."""
    regar = de(lucia, "Regar las plantas")
    entrar(client, "tutor").post(url_cancelar(regar), {"alcance": "serie"})

    agenda = servicios.agenda_del_dia(lucia, a_las(12, 5))
    tarea = next(t for t in agenda.tareas if t.asignacion == regar)
    assert tarea.estado == EstadoEjecucion.CANCELADA and tarea.etiqueta == "Cancelada"
    # No cuenta como la de ahora ni como siguiente.
    assert agenda.actual is None or agenda.actual.asignacion != regar
    assert agenda.siguiente.tarea.nombre == "Leer un cuento"
    assert not tarea.puede_empezar
    with pytest.raises(servicios.ErrorDeAgenda):
        servicios.empezar(lucia, regar.pk, a_las(12, 5))


def test_la_serie_cancelada_se_ve_unos_dias_y_luego_desaparece(client, lucia):
    regar = de(lucia, "Regar las plantas")
    entrar(client, "tutor").post(url_cancelar(regar), {"alcance": "serie"})
    hoy = timezone.localdate()

    def tiene(dia):
        return regar in [o.asignacion for o in planificacion.ocurrencias_del_dia(lucia, dia)]

    assert tiene(hoy + timedelta(days=planificacion.DIAS_VISIBLE_CANCELADA - 1))
    assert not tiene(hoy + timedelta(days=planificacion.DIAS_VISIBLE_CANCELADA))
    # Antes de cancelarse, en los días pasados, sigue como era.
    ayer = [o for o in planificacion.ocurrencias_del_dia(lucia, hoy - timedelta(days=1))]
    assert regar in [o.asignacion for o in ayer if not o.cancelada]


def test_si_hoy_ya_la_ha_empezado_la_serie_se_cancela_desde_manana(client, lucia):
    """PA2: lo empezado no se cancela; lo de hoy sigue y se cancela lo que viene."""
    regar, hoy = de(lucia, "Regar las plantas"), timezone.localdate()
    Ejecucion.objects.create(
        asignacion=regar, fecha=hoy, estado=EstadoEjecucion.EN_CURSO, inicio_real=timezone.now()
    )
    entrar(client, "tutor").post(url_cancelar(regar), {"alcance": "serie"})
    regar.refresh_from_db()
    assert regar.cancelada_el == hoy + timedelta(days=1)
    hoy_ = {o.asignacion: o for o in planificacion.ocurrencias_del_dia(lucia, hoy)}
    assert not hoy_[regar].cancelada
    manana_ = {o.asignacion: o for o in planificacion.ocurrencias_del_dia(lucia, manana())}
    assert manana_[regar].cancelada


def test_una_serie_cancelada_no_se_vuelve_a_cancelar_ni_a_cambiar(client, lucia):
    regar = de(lucia, "Regar las plantas")
    entrar(client, "tutor").post(url_cancelar(regar), {"alcance": "serie"})
    otra = client.post(url_cancelar(regar), {"alcance": "serie"}, follow=True)
    assert "ya estaba cancelada" in otra.content.decode()
    cambio = client.get(reverse("tareas:editar_asignacion", args=[regar.pk]), follow=True)
    assert "está cancelada: ya no se puede cambiar" in cambio.content.decode()
    assert avisos_de(lucia).count() == 1


def test_la_serie_cancelada_ya_no_sale_en_planificadas(client, lucia):
    regar = de(lucia, "Regar las plantas")
    entrar(client, "tutor").post(url_cancelar(regar), {"alcance": "serie"}, follow=True)
    url = reverse("tareas:tareas_planificadas")
    html = client.get(url, {"estudiante": lucia.pk}).content.decode()
    assert "Regar las plantas" not in html
    html = client.get(url, {"estudiante": lucia.pk, "fecha": manana().isoformat()})
    assert "Regar las plantas" not in html.content.decode()


# --- Solo este día ------------------------------------------------------------------


def test_cancelar_solo_un_dia(client, lucia):
    regar, dia = de(lucia, "Regar las plantas"), manana()
    entrar(client, "tutor").post(url_cancelar(regar), {"alcance": "dia", "fecha": dia.isoformat()})
    regar.refresh_from_db()
    assert not regar.cancelada
    assert ExcepcionAsignacion.objects.get(asignacion=regar, fecha=dia).tipo == (
        TipoExcepcion.CANCELADA
    )
    ese = {o.asignacion: o for o in planificacion.ocurrencias_del_dia(lucia, dia)}
    otro = {
        o.asignacion: o for o in planificacion.ocurrencias_del_dia(lucia, dia + timedelta(days=1))
    }
    assert ese[regar].cancelada and not otro[regar].cancelada
    assert avisos_de(lucia).get().mensaje == (
        f"«Regar las plantas» del {planificacion.fecha_en_texto(dia)} se ha cancelado."
    )


def test_un_dia_cancelado_deja_el_hueco_libre(client, lucia):
    regar, dia = de(lucia, "Regar las plantas"), manana()
    entrar(client, "tutor").post(url_cancelar(regar), {"alcance": "dia", "fecha": dia.isoformat()})
    assert planificacion.choque_en_fecha(lucia, dia, time(12, 0), time(12, 30)) is None


def test_un_dia_cancelado_se_ve_tachado_en_planificadas_y_no_se_vuelve_a_cancelar(client, lucia):
    regar, dia = de(lucia, "Regar las plantas"), manana()
    entrar(client, "tutor").post(url_cancelar(regar), {"alcance": "dia", "fecha": dia.isoformat()})
    html = client.get(
        reverse("tareas:tareas_planificadas"), {"fecha": dia.isoformat()}
    ).content.decode()
    assert "Cancelada ese día" in html
    otra = client.post(
        url_cancelar(regar), {"alcance": "dia", "fecha": dia.isoformat()}, follow=True
    )
    assert "Ese día no se puede cancelar." in otra.content.decode()
    assert avisos_de(lucia).count() == 1


def test_no_se_cancela_un_dia_ya_empezado(client, lucia):
    regar, hoy = de(lucia, "Regar las plantas"), timezone.localdate()
    Ejecucion.objects.create(
        asignacion=regar, fecha=hoy, estado=EstadoEjecucion.EN_CURSO, inicio_real=timezone.now()
    )
    respuesta = entrar(client, "tutor").post(
        url_cancelar(regar), {"alcance": "dia", "fecha": hoy.isoformat()}, follow=True
    )
    assert "ya ha empezado «Regar las plantas» ese día" in respuesta.content.decode()
    assert not ExcepcionAsignacion.objects.exists() and not avisos_de(lucia).exists()


def test_una_tarea_empezada_y_luego_cancelada_ese_dia_sigue_en_marcha(lucia):
    """Si se cancela el día después de empezarla (no debería pasar, pero por si acaso),
    la agenda la sigue mostrando en marcha: no se pierde lo hecho."""
    regar, hoy = de(lucia, "Regar las plantas"), timezone.localdate()
    Ejecucion.objects.create(
        asignacion=regar, fecha=hoy, estado=EstadoEjecucion.EN_CURSO, inicio_real=a_las(12)
    )
    ExcepcionAsignacion.objects.create(
        asignacion=regar,
        fecha=hoy,
        tipo=TipoExcepcion.CANCELADA,
        creada_por=Usuario.objects.get(username="tutor"),
    )
    tarea = servicios.tarea_del_dia(lucia, regar.pk, a_las(12, 10))
    assert tarea.estado == EstadoEjecucion.EN_CURSO


@pytest.mark.parametrize(
    ("usuario", "tarea"),
    [
        ("tutor", "Poner la mesa"),
        ("tutor2", "Regar las plantas"),
        ("profesional", "Regar las plantas"),
        ("familiar", "Regar las plantas"),
    ],
)
def test_quien_no_puede_cancelar(client, lucia, usuario, tarea):
    asignacion = de(lucia, tarea)
    entrar(client, usuario)
    assert client.get(url_cancelar(asignacion)).status_code == 404
    assert client.post(url_cancelar(asignacion), {"alcance": "serie"}).status_code == 404
    asignacion.refresh_from_db()
    assert not asignacion.cancelada


def test_el_familiar_cancela_su_tarea_de_casa(client, lucia):
    mesa = de(lucia, "Poner la mesa")
    entrar(client, "familiar").post(url_cancelar(mesa), {"alcance": "serie"})
    mesa.refresh_from_db()
    assert mesa.cancelada


# --- Lo que ve el estudiante -----------------------------------------------------------


def test_la_tarjeta_cancelada_no_se_abre(client, lucia, monkeypatch):
    regar = de(lucia, "Regar las plantas")
    entrar(client, "tutor").post(url_cancelar(regar), {"alcance": "serie"})
    Notificacion.objects.all().delete()  # el aviso se prueba aparte
    monkeypatch.setattr(servicios, "ahora", lambda: a_las(8))
    html = entrar(client, "est-a01").get(reverse("agenda:dia")).content.decode()
    assert "tarjeta--cancelada" in html and "Cancelada" in html
    assert reverse("agenda:detalle", args=[regar.pk]) not in html
    # Si se llega por la dirección, dice que se ha cancelado y no ofrece empezar.
    detalle = client.get(reverse("agenda:detalle", args=[regar.pk])).content.decode()
    assert "Se ha cancelado. No la tienes que hacer." in detalle
    assert reverse("agenda:empezar", args=[regar.pk]) not in detalle


def test_el_estudiante_ve_el_aviso_antes_que_la_agenda(client, lucia):
    regar = de(lucia, "Regar las plantas")
    entrar(client, "tutor").post(url_cancelar(regar), {"alcance": "serie"})
    entrar(client, "est-a01")

    html = client.get(reverse("agenda:dia")).content.decode()
    aviso = avisos_de(lucia).get()
    assert "Tarea cancelada" in html
    assert "«Regar las plantas» se ha cancelado. Ya no la tienes que hacer." in html
    assert regar.tarea.imagen.url in html and "Entendido" in html
    # Verlo no basta: el aviso sigue sin ver hasta que pulsa «Entendido».
    aviso.refresh_from_db()
    assert not aviso.leida

    respuesta = client.post(reverse("agenda:aviso_visto", args=[aviso.pk]))
    assert respuesta.status_code == 302 and respuesta.url == reverse("agenda:dia")
    aviso.refresh_from_db()
    assert aviso.leida and aviso.vista_el is not None
    assert "Tareas de hoy" in client.get(reverse("agenda:dia")).content.decode()


def test_varios_avisos_salen_de_uno_en_uno_del_mas_antiguo_al_mas_nuevo(client, lucia):
    primero = avisar(lucia.usuario, "Primero.")
    avisar(lucia.usuario, "Segundo.")
    html = entrar(client, "est-a01").get(reverse("agenda:dia")).content.decode()
    assert "Primero." in html and "Segundo." not in html and "Tienes otro aviso." in html
    client.post(reverse("agenda:aviso_visto", args=[primero.pk]))
    html = client.get(reverse("agenda:dia")).content.decode()
    assert "Segundo." in html and "Tienes otro aviso." not in html


def test_un_aviso_de_otro_no_se_puede_marcar(client, lucia):
    aviso = avisar(Usuario.objects.get(username="est-a02"), "De otra persona.")
    respuesta = entrar(client, "est-a01").post(reverse("agenda:aviso_visto", args=[aviso.pk]))
    assert respuesta.status_code == 404
    aviso.refresh_from_db()
    assert not aviso.leida


def test_entendido_solo_por_post(client, lucia):
    aviso = avisar(lucia.usuario, "Algo.")
    respuesta = entrar(client, "est-a01").get(reverse("agenda:aviso_visto", args=[aviso.pk]))
    assert respuesta.status_code == 405


def test_avisar_sin_destinatario_no_hace_nada():
    assert avisar(None, "Nada.") is None


def test_el_profesional_ve_la_tarea_cancelada_en_la_consulta(client, lucia):
    regar = de(lucia, "Regar las plantas")
    entrar(client, "tutor").post(url_cancelar(regar), {"alcance": "dia", "fecha": manana()})
    html = (
        entrar(client, "profesional")
        .get(reverse("usuarios:agenda_estudiante", args=["A01"]), {"dia": manana().isoformat()})
        .content.decode()
    )
    assert "Estado: <b>Cancelada</b>" in html


def test_si_llega_un_aviso_con_la_agenda_abierta_se_recarga(client, lucia):
    entrar(client, "est-a01")
    url = reverse("agenda:aviso")
    assert "HX-Redirect" not in client.get(url, {"mostrado": "0"}).headers
    avisar(lucia.usuario, "Algo ha cambiado.")
    respuesta = client.get(url, {"mostrado": "0"})
    assert respuesta.headers["HX-Redirect"] == reverse("agenda:dia")
