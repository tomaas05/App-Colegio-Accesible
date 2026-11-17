"""HU-07-04 · Elegir un plan B cuando una tarea no se puede hacer, y HU-02-07 · Confirmar
una acción importante («Terminar» y «No puedo hacerla»).

Datos de prueba de Lucía (A01): mochila 9:00–9:15 (escolar, 4 pasos, sin plan B), manos
10:30–10:45, regar 12:00–12:30 (escolar, plan B: «Escuchar música» y «Leer un cuento»),
cuento 17:00–17:30 (ocio) y «Poner la mesa» 20:00–20:20 (casa, de su familiar).
"""

from datetime import datetime, time

import pytest
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios
from apps.agenda.models import Ejecucion, EstadoEjecucion
from apps.comun.models import Notificacion, TipoAviso, avisar
from apps.tareas.models import PlanB, Tarea
from apps.usuarios.models import Estudiante, Usuario

pytestmark = pytest.mark.django_db


def a_las(hora, minuto=0):
    return timezone.make_aware(datetime.combine(timezone.localdate(), time(hora, minuto)))


@pytest.fixture
def hora(monkeypatch):
    def fijar(h, m=0):
        monkeypatch.setattr(servicios, "ahora", lambda: a_las(h, m))

    return fijar


@pytest.fixture
def lucia(datos, client):
    estudiante = Estudiante.objects.get(codigo_estudiante="A01")
    client.force_login(estudiante.usuario)
    return estudiante


def de(estudiante, nombre):
    return estudiante.asignaciones.get(tarea__nombre=nombre)


def url(nombre_url, asignacion):
    return reverse(f"agenda:{nombre_url}", args=[asignacion.pk])


def ejecucion_de(asignacion):
    return Ejecucion.objects.get(asignacion=asignacion, fecha=timezone.localdate())


def avisos(usuario, tipo=None):
    avisos = Notificacion.objects.filter(destinatario=usuario)
    return avisos.filter(tipo=tipo) if tipo else avisos


def entrar(client, usuario):
    client.force_login(Usuario.objects.get(username=usuario))
    return client


# --- «No puedo hacerla» y su confirmación (HU-02-07) ---------------------------------


def test_no_puedo_hacerla_sale_en_las_escolares_con_su_confirmacion(client, lucia, hora):
    hora(11, 50)
    html = client.get(url("detalle", de(lucia, "Regar las plantas"))).content.decode()
    assert ">No puedo hacerla<" in html and 'data-confirmar="confirmar-no-puedo"' in html
    # La ventana: pictograma de la tarea, una frase corta y el foco empieza en «No».
    ventana = html.split('id="confirmar-no-puedo"', 1)[1].split("</dialog>", 1)[0]
    assert "¿No puedes hacerla?" in ventana and "<img" in ventana
    assert "autofocus>No<" in ventana


@pytest.mark.parametrize("nombre", ["Leer un cuento", "Poner la mesa"])
def test_ni_las_de_ocio_ni_las_de_casa_tienen_no_puedo(client, lucia, hora, nombre):
    """RF2.15.1: solo las del horario escolar (B07: las de casa no lo tienen)."""
    hora(16, 50)
    html = client.get(url("detalle", de(lucia, nombre))).content.decode()
    assert "No puedo hacerla" not in html


def test_sin_confirmar_no_cambia_nada(client, lucia, hora):
    """PA3: la pregunta en una página (sin JavaScript); hasta decir «Sí», nada cambia."""
    hora(11, 50)
    regar = de(lucia, "Regar las plantas")
    html = client.get(url("no_puedo", regar)).content.decode()
    assert "¿No puedes hacerla?" in html and regar.tarea.imagen.url in html
    assert url("detalle", regar) in html  # «No» vuelve a la tarea
    assert not Ejecucion.objects.filter(asignacion=regar, fecha=timezone.localdate()).exists()


def test_terminar_tambien_pide_confirmacion_con_pictograma(client, lucia, hora):
    hora(10, 35)
    manos = de(lucia, "Lavarse las manos")
    client.post(url("empezar", manos))
    for paso in manos.tarea.pasos.all():
        client.post(reverse("agenda:paso_hecho", args=[manos.pk, paso.pk]))
    html = client.get(url("terminar", manos)).content.decode()
    assert "¿Has terminado?" in html and manos.tarea.imagen.url in html
    assert ejecucion_de(manos).estado == EstadoEjecucion.EN_CURSO  # hasta pulsar «Sí»


# --- Con plan B (B11) -------------------------------------------------------------------


def test_no_puedo_con_plan_b_lleva_a_elegir_otra_cosa(client, lucia, hora):
    hora(11, 50)
    regar = de(lucia, "Regar las plantas")
    respuesta = client.post(url("no_puedo", regar))
    assert respuesta.status_code == 302 and respuesta.url == url("plan_b", regar)
    ejecucion = ejecucion_de(regar)
    assert ejecucion.estado == EstadoEjecucion.NO_REALIZABLE
    assert ejecucion.no_realizable_por == lucia.usuario and ejecucion.no_realizable_el
    # El tutor se entera cuando elige (así sabe también qué ha elegido).
    assert not avisos(lucia.tutor).exists()

    html = client.get(url("plan_b", regar)).content.decode()
    assert "Puedes hacer esto" in html and "En lugar de «Regar las plantas»" in html
    assert html.index("Escuchar música") < html.index("Leer un cuento")  # por prioridad


def test_elegir_una_alternativa_la_pone_en_la_agenda_y_avisa_al_tutor(client, lucia, hora):
    hora(11, 50)
    regar, musica = de(lucia, "Regar las plantas"), Tarea.objects.get(nombre="Escuchar música")
    client.post(url("no_puedo", regar))
    respuesta = client.post(url("plan_b", regar), {"alternativa": musica.pk})
    assert respuesta.url == reverse("agenda:dia")

    ejecucion = ejecucion_de(regar)
    assert ejecucion.plan_b == musica and ejecucion.estado == EstadoEjecucion.PENDIENTE

    # PA3: sustituye a la tarea en su agenda, a la misma hora.
    agenda = servicios.agenda_del_dia(lucia, a_las(11, 50))
    t = next(t for t in agenda.tareas if t.asignacion == regar)
    assert t.tarea == musica and t.es_plan_b and t.inicio == a_las(12)
    html = client.get(reverse("agenda:dia")).content.decode()
    assert "Escuchar música (plan B)" in html

    # PA5: el tutor ve qué ha elegido.
    aviso = avisos(lucia.tutor).get()
    assert aviso.tipo == TipoAviso.PLAN_B and aviso.tarea == musica
    assert (
        aviso.mensaje
        == "Lucía no ha podido hacer «Regar las plantas» y ha elegido «Escuchar música»."
    )


def test_la_alternativa_se_hace_como_cualquier_tarea(client, lucia, hora):
    hora(11, 50)
    regar, musica = de(lucia, "Regar las plantas"), Tarea.objects.get(nombre="Escuchar música")
    client.post(url("no_puedo", regar))
    client.post(url("plan_b", regar), {"alternativa": musica.pk})

    html = client.get(url("detalle", regar)).content.decode()
    assert "<h1" in html and "Escuchar música" in html
    assert "Plan B, en lugar de «Regar las plantas»" in html

    hora(12, 0)
    client.post(url("empezar", regar))
    client.post(url("terminar", regar))
    assert ejecucion_de(regar).estado == EstadoEjecucion.HECHA


def test_los_pasos_son_los_de_la_alternativa(client, lucia, hora):
    regar, mochila = de(lucia, "Regar las plantas"), Tarea.objects.get(nombre="Preparar la mochila")
    regar.tarea.planes_b.all().delete()
    PlanB.objects.create(tarea=regar.tarea, alternativa=mochila, orden=1)
    hora(11, 50)
    client.post(url("no_puedo", regar))
    client.post(url("plan_b", regar), {"alternativa": mochila.pk})
    hora(12, 0)
    client.post(url("empezar", regar))
    pasos = list(mochila.pasos.all())
    assert [p.paso for p in ejecucion_de(regar).pasos.all()] == pasos
    client.post(reverse("agenda:paso_hecho", args=[regar.pk, pasos[0].pk]))
    assert ejecucion_de(regar).pasos.filter(estado="hecho").count() == 1
    assert "Paso 2 de 4" in client.get(url("detalle", regar)).content.decode()


def test_no_se_elige_algo_que_no_esta_en_su_plan_b(client, lucia, hora):
    hora(11, 50)
    regar = de(lucia, "Regar las plantas")
    client.post(url("no_puedo", regar))
    otra = Tarea.objects.get(nombre="Preparar la mochila")
    assert client.post(url("plan_b", regar), {"alternativa": otra.pk}).status_code == 404
    assert client.post(url("plan_b", regar), {"alternativa": "x"}).status_code == 404
    assert ejecucion_de(regar).plan_b is None


def test_solo_se_elige_una_vez(client, lucia, hora):
    hora(11, 50)
    regar = de(lucia, "Regar las plantas")
    musica, cuento = (
        Tarea.objects.get(nombre="Escuchar música"),
        Tarea.objects.get(nombre="Leer un cuento"),
    )
    client.post(url("no_puedo", regar))
    client.post(url("plan_b", regar), {"alternativa": musica.pk})
    client.post(url("plan_b", regar), {"alternativa": cuento.pk})
    assert ejecucion_de(regar).plan_b == musica
    assert client.get(url("plan_b", regar)).url == url("detalle", regar)


def test_si_tampoco_puede_la_alternativa_se_queda_asi_y_lo_sabe_el_tutor(client, lucia, hora):
    hora(11, 50)
    regar, musica = de(lucia, "Regar las plantas"), Tarea.objects.get(nombre="Escuchar música")
    client.post(url("no_puedo", regar))
    client.post(url("plan_b", regar), {"alternativa": musica.pk})
    respuesta = client.post(url("no_puedo", regar))
    assert respuesta.url == url("detalle", regar)  # no se ofrece otra alternativa
    ejecucion = ejecucion_de(regar)
    assert ejecucion.estado == EstadoEjecucion.NO_REALIZABLE and ejecucion.plan_b == musica
    assert avisos(lucia.tutor).last().mensaje == (
        "Lucía tampoco ha podido hacer «Escuchar música», del plan B de «Regar las plantas»."
    )
    html = client.get(reverse("agenda:dia")).content.decode()
    assert "Escuchar música (plan B)" in html and "No se ha podido" in html


def test_si_se_sale_sin_elegir_puede_volver_a_elegir(client, lucia, hora):
    hora(11, 50)
    regar = de(lucia, "Regar las plantas")
    client.post(url("no_puedo", regar))
    html = client.get(url("detalle", regar)).content.decode()
    assert "Elegir otra cosa" in html and url("plan_b", regar) in html


def test_pasada_la_hora_ya_no_se_elige(client, lucia, hora):
    hora(11, 50)
    regar = de(lucia, "Regar las plantas")
    client.post(url("no_puedo", regar))
    hora(12, 40)
    assert client.get(url("plan_b", regar)).url == url("detalle", regar)
    assert "No se ha podido hacer." in client.get(url("detalle", regar)).content.decode()


# --- Sin plan B ----------------------------------------------------------------------


def test_sin_plan_b_se_queda_como_no_se_ha_podido_y_se_avisa_al_tutor(client, lucia, hora):
    """PA4: si no hay plan B, se dice; el tutor lo sabe."""
    hora(9, 5)
    mochila = de(lucia, "Preparar la mochila")
    client.post(url("empezar", mochila))
    respuesta = client.post(url("no_puedo", mochila), follow=True)
    html = respuesta.content.decode()
    assert respuesta.redirect_chain[-1][0] == url("detalle", mochila)
    assert "No se ha podido hacer." in html and "No puedo hacerla" not in html
    assert ejecucion_de(mochila).estado == EstadoEjecucion.NO_REALIZABLE
    assert avisos(lucia.tutor).get().mensaje == (
        "Lucía no ha podido hacer «Preparar la mochila» y no tiene plan B."
    )


def test_lo_hecho_no_se_marca(client, lucia, hora):
    hora(10, 35)
    manos = de(lucia, "Lavarse las manos")
    client.post(url("empezar", manos))
    for paso in manos.tarea.pasos.all():
        client.post(reverse("agenda:paso_hecho", args=[manos.pk, paso.pk]))
    client.post(url("terminar", manos))
    respuesta = client.post(url("no_puedo", manos), follow=True)
    assert "Esta tarea ya no se puede marcar." in respuesta.content.decode()
    assert ejecucion_de(manos).estado == EstadoEjecucion.HECHA


def test_la_tarea_de_otro_estudiante_da_404(client, lucia, hora):
    hora(11, 50)
    otra = Estudiante.objects.get(codigo_estudiante="A02").asignaciones.get(
        tarea__nombre="Regar las plantas"
    )
    assert client.post(url("no_puedo", otra)).status_code == 404
    assert client.get(url("plan_b", otra)).status_code == 404


def test_un_plan_b_sin_haber_dicho_no_puedo_no_se_elige(client, lucia, hora):
    hora(11, 50)
    regar, musica = de(lucia, "Regar las plantas"), Tarea.objects.get(nombre="Escuchar música")
    client.post(url("plan_b", regar), {"alternativa": musica.pk})
    assert not Ejecucion.objects.filter(asignacion=regar, plan_b__isnull=False).exists()


def test_la_base_de_datos_no_guarda_un_plan_b_sin_no_realizable(lucia):
    with pytest.raises(IntegrityError):
        Ejecucion.objects.create(
            asignacion=de(lucia, "Regar las plantas"),
            fecha=timezone.localdate(),
            plan_b=Tarea.objects.get(nombre="Escuchar música"),
        )


# --- Lo marca un adulto (RF2.15.1: dice el motivo) --------------------------------------


def url_no_se_puede(asignacion):
    return reverse("tareas:no_se_puede", args=[asignacion.pk])


def test_el_tutor_marca_que_hoy_no_se_puede_y_el_estudiante_elige(client, lucia, hora):
    hora(11, 0)
    regar = de(lucia, "Regar las plantas")
    entrar(client, "tutor")
    html = client.get(url_no_se_puede(regar)).content.decode()
    assert "¿Lucía no puede hacer hoy «Regar las plantas»?" in html
    assert "elegirá otra cosa de su plan B" in html

    # El motivo es obligatorio.
    assert client.post(url_no_se_puede(regar), {"motivo": ""}).status_code == 200
    assert not Ejecucion.objects.filter(asignacion=regar, fecha=timezone.localdate()).exists()

    respuesta = client.post(url_no_se_puede(regar), {"motivo": "Llueve y el huerto está cerrado."})
    assert respuesta.status_code == 302
    ejecucion = ejecucion_de(regar)
    assert ejecucion.estado == EstadoEjecucion.NO_REALIZABLE
    assert ejecucion.motivo == "Llueve y el huerto está cerrado"
    assert ejecucion.no_realizable_por.username == "tutor"
    aviso = avisos(lucia.usuario).get()
    assert aviso.tipo == TipoAviso.NO_SE_PUEDE and aviso.tarea == regar.tarea
    assert aviso.mensaje == (
        "Hoy no se puede hacer «Regar las plantas»: Llueve y el huerto está cerrado. "
        "Elige otra cosa."
    )

    # Lucía ve el aviso y, al pulsar «Entendido», va directa a elegir.
    entrar(client, "est-a01")
    html = client.get(reverse("agenda:dia")).content.decode()
    assert "Hoy no se puede" in html and "Llueve y el huerto está cerrado" in html
    respuesta = client.post(reverse("agenda:aviso_visto", args=[aviso.pk]))
    assert respuesta.url == url("plan_b", regar)


def test_si_lo_marca_otro_adulto_el_tutor_tambien_se_entera(client, lucia, hora):
    hora(11, 0)
    profesional = Usuario.objects.get(username="profesional")
    regar = de(lucia, "Regar las plantas")
    regar.asignado_por = profesional
    regar.save()
    entrar(client, "profesional").post(url_no_se_puede(regar), {"motivo": "Estoy de baja"})
    aviso = avisos(lucia.tutor).get()
    assert aviso.mensaje == (
        "Luis Navarro Gil ha marcado que Lucía no puede hacer «Regar las plantas» hoy: "
        "Estoy de baja."
    )


@pytest.mark.parametrize("usuario", ["tutor2", "profesional", "familiar"])
def test_quien_no_puede_marcarla(client, lucia, hora, usuario):
    hora(11, 0)
    regar = de(lucia, "Regar las plantas")
    entrar(client, usuario)
    assert client.get(url_no_se_puede(regar)).status_code == 404
    assert client.post(url_no_se_puede(regar), {"motivo": "x"}).status_code == 404
    assert not Ejecucion.objects.filter(asignacion=regar, fecha=timezone.localdate()).exists()


def test_planificadas_ofrece_hoy_no_se_puede_solo_hoy_y_en_las_escolares(client, lucia, hora):
    hora(11, 0)
    entrar(client, "tutor")
    planificadas = reverse("tareas:tareas_planificadas")
    hoy = client.get(
        planificadas, {"estudiante": lucia.pk, "fecha": timezone.localdate().isoformat()}
    ).content.decode()
    assert url_no_se_puede(de(lucia, "Regar las plantas")) in hoy
    assert url_no_se_puede(de(lucia, "Leer un cuento")) not in hoy  # ocio
    assert url_no_se_puede(de(lucia, "Preparar la mochila")) not in hoy  # ya ha pasado
    sin_dia = client.get(planificadas, {"estudiante": lucia.pk}).content.decode()
    assert "Hoy no se puede" not in sin_dia


def test_una_tarea_ya_pasada_no_se_marca(client, lucia, hora):
    hora(13, 0)
    regar = de(lucia, "Regar las plantas")
    respuesta = entrar(client, "tutor").get(url_no_se_puede(regar), follow=True)
    assert "ya no se puede marcar hoy" in respuesta.content.decode()


# --- Avisos en el panel del adulto (PA5) -----------------------------------------------


def test_el_tutor_ve_el_aviso_en_su_panel_y_lo_marca_como_visto(client, lucia, hora):
    hora(11, 50)
    regar, musica = de(lucia, "Regar las plantas"), Tarea.objects.get(nombre="Escuchar música")
    client.post(url("no_puedo", regar))
    client.post(url("plan_b", regar), {"alternativa": musica.pk})
    avisar(lucia.tutor, "Otro aviso.")

    entrar(client, "tutor")
    html = client.get(reverse("usuarios:panel")).content.decode()
    assert "Lucía no ha podido hacer «Regar las plantas» y ha elegido «Escuchar música»." in html
    assert "(1 aviso más)" in html and musica.imagen.url in html
    aviso = avisos(lucia.tutor).first()
    client.post(reverse("usuarios:aviso_visto", args=[aviso.pk]))
    aviso.refresh_from_db()
    assert aviso.leida and aviso.vista_el
    html = client.get(reverse("usuarios:panel")).content.decode()
    assert "Otro aviso." in html and "aviso más" not in html


def test_un_adulto_no_marca_los_avisos_de_otro(client, lucia):
    aviso = avisar(lucia.tutor, "De Ana.")
    respuesta = entrar(client, "tutor2").post(reverse("usuarios:aviso_visto", args=[aviso.pk]))
    assert respuesta.status_code == 404


def test_sin_avisos_el_panel_no_tiene_el_bloque(client, datos):
    html = entrar(client, "tutor").get(reverse("usuarios:panel")).content.decode()
    assert "panel__aviso" not in html


def test_el_profesional_ve_el_plan_b_elegido_en_la_consulta(client, lucia, hora):
    hora(11, 50)
    regar, musica = de(lucia, "Regar las plantas"), Tarea.objects.get(nombre="Escuchar música")
    client.post(url("no_puedo", regar))
    client.post(url("plan_b", regar), {"alternativa": musica.pk})
    html = (
        entrar(client, "profesional")
        .get(reverse("usuarios:agenda_estudiante", args=["A01"]))
        .content.decode()
    )
    assert "Plan B: <b>Escuchar música</b>" in html


def test_si_ya_hacia_el_plan_b_el_adulto_lo_ve_y_el_aviso_nombra_esa(client, lucia, hora):
    hora(11, 50)
    regar, musica = de(lucia, "Regar las plantas"), Tarea.objects.get(nombre="Escuchar música")
    client.post(url("no_puedo", regar))
    client.post(url("plan_b", regar), {"alternativa": musica.pk})
    entrar(client, "tutor")
    html = client.get(url_no_se_puede(regar)).content.decode()
    assert "Ya la había cambiado por «Escuchar música»" in html
    assert "No se le ofrecerá otra cosa." in html
    client.post(url_no_se_puede(regar), {"motivo": "Se ha roto el altavoz"})
    aviso = avisos(lucia.usuario).get()
    assert aviso.mensaje == "Hoy no se puede hacer «Escuchar música»: Se ha roto el altavoz."
    assert ejecucion_de(regar).plan_b == musica
