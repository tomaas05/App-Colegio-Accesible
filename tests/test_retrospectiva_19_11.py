"""Retrospectiva de la profesora del 19/11 (iteración 2): lo que se comprueba sin navegador.

Cada prueba lleva el número del punto de la retrospectiva. Lo que necesita navegador (la
flecha «Ahora» que avanza, el sello de hecha / no hecha, los tamaños) está en
tests/e2e/test_retrospectiva_19_11.py.
"""

from datetime import date, datetime, time

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.agenda import servicios
from apps.tareas.models import PlanB, Tarea
from apps.usuarios import avatares
from apps.usuarios.models import Estudiante, Usuario

pytestmark = pytest.mark.django_db


def a_las(hora, minuto=0):
    return timezone.make_aware(datetime.combine(timezone.localdate(), time(hora, minuto)))


def entrar(client, usuario):
    client.force_login(Usuario.objects.get(username=usuario))
    return client


@pytest.fixture
def lucia(datos, client):
    est = Estudiante.objects.get(codigo_estudiante="A01")
    client.force_login(est.usuario)
    return est


@pytest.fixture
def hora(monkeypatch):
    def fijar(h, m=0):
        monkeypatch.setattr(servicios, "ahora", lambda: a_las(h, m))

    return fijar


# --- 1 y 2 · Contraseña del estudiante: recuadro que destaca y el error abajo ---


def test_2_el_error_de_la_contrasena_va_debajo_del_campo(client, datos):
    url = reverse("usuarios:entrar_estudiante", args=["A02"])
    html = client.post(url, {"password": "mal"}).content.decode()
    campo = html.index('type="password"')
    error = html.index('class="aviso-error aviso-error--estudiante"')
    entrar_boton = html.index(">Entrar</button>")
    assert campo < error < entrar_boton


# --- 3 · Avatares de su propia galería, distintos de las imágenes de la contraseña ---


def test_3_la_galeria_no_repite_las_imagenes_de_la_contrasena(datos):
    from apps.usuarios.models import ImagenAcceso

    palabras = {i.descripcion_imagen.lower() for i in ImagenAcceso.objects.all()}
    nombres = {n.lower() for _, n in avatares.galeria()}
    assert len(avatares.galeria()) >= 12
    assert not palabras & nombres


def test_3_los_estudiantes_de_prueba_tienen_avatares_de_la_galeria_y_distintos(datos):
    clase = Estudiante.objects.get(codigo_estudiante="A01").clase
    claves = [avatares.clave_de(e) for e in clase.estudiantes.all()]
    assert None not in claves and len(set(claves)) == len(claves)


def test_3_al_crear_un_estudiante_se_elige_un_avatar_de_la_galeria(client, datos):
    from apps.perfil.models import MetodoAcceso
    from apps.usuarios.models import Clase, ImagenAcceso

    entrar(client, "admin")
    html = client.get(reverse("usuarios:crear")).content.decode()
    assert 'name="avatar_galeria" value="miel"' in html
    imagenes = list(ImagenAcceso.objects.values_list("pk", flat=True)[:3])
    client.post(
        reverse("usuarios:crear"),
        {
            "rol": "estudiante",
            "nombre": "Noa",
            "apellidos": "Prueba",
            "clase": Clase.objects.first().pk,
            "metodo_acceso": MetodoAcceso.IMAGENES,
            "imagenes": imagenes,
            "avatar_galeria": "fresa",
        },
    )
    noa = Estudiante.objects.get(usuario__first_name="Noa")
    assert avatares.clave_de(noa) == "fresa"


def test_3_el_administrador_cambia_el_avatar_por_otro_de_la_galeria(client, datos):
    entrar(client, "admin")
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    url = reverse("usuarios:editar", args=[lucia.usuario.pk])
    html = client.get(url).content.decode()
    assert f'value="{avatares.clave_de(lucia)}" checked' in html
    datos_form = {
        "nombre": lucia.usuario.first_name,
        "apellidos": lucia.usuario.last_name,
        "clase": lucia.clase_id,
        "estado": "activa",
        "avatar_galeria": "cereza",
    }
    client.post(url, datos_form)
    lucia.refresh_from_db()
    assert avatares.clave_de(lucia) == "cereza"


# --- 4 · Flecha «Ahora» en la línea de tiempo ---


def test_4_la_linea_de_hoy_lleva_la_hora_y_cada_tarea_sus_horas(client, lucia, hora):
    hora(10, 32)
    html = client.get(reverse("agenda:dia")).content.decode()
    assert 'data-ahora="10:32"' in html
    assert 'data-inicio="10:30" data-fin="10:45"' in html


# --- 5 · Al entrar, el horario de clase; las tareas, a un botón ---


def test_5_el_estudiante_entra_a_su_horario_de_clase(client, datos):
    from apps.usuarios.models import ImagenAcceso

    ids = [ImagenAcceso.objects.get(descripcion_imagen=p).pk for p in ("perro", "sol", "flor")]
    respuesta = client.post(reverse("usuarios:entrar_estudiante", args=["A01"]), {"imagenes": ids})
    assert respuesta["Location"] == reverse("horario:mi_horario")
    html = client.get(respuesta["Location"]).content.decode()
    assert f'href="{reverse("agenda:dia")}"' in html and "Tareas de hoy" in html
    assert 'class="salir-est"' in html


# --- 6 · La forma del día en la barra de título ---


def test_6_la_barra_lleva_la_forma_del_dia(client, lucia):
    html = client.get(reverse("agenda:dia")).content.decode()
    barra = html.split('class="barra__fecha"', 1)[1].split("</p>", 1)[0]
    assert f"dia-forma--{timezone.localdate().isoweekday()}" in barra


# --- 7 · Empezar cuando quiera (sin otra en marcha) ---


def test_7_se_empieza_una_tarea_de_la_tarde_por_la_manana(lucia):
    cuento = lucia.asignaciones.get(tarea__nombre="Leer un cuento")  # 17:00
    assert servicios.empezar(lucia, cuento.pk, a_las(9, 30)).inicio_real == a_las(9, 30)


def test_7_no_se_empiezan_dos_a_la_vez(lucia):
    cuento = lucia.asignaciones.get(tarea__nombre="Leer un cuento")
    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas")
    servicios.empezar(lucia, regar.pk, a_las(12, 5))
    with pytest.raises(servicios.ErrorDeAgenda, match="Primero termina"):
        servicios.empezar(lucia, cuento.pk, a_las(12, 10))


# --- 8 · Plan B: tocar para añadir o quitar, «Primera» y buscador arriba ---


@pytest.fixture
def regar(datos):
    t = Tarea.objects.get(nombre="Regar las plantas")
    t.planes_b.all().delete()
    return t


def test_8_tocar_una_tarjeta_la_anade_y_otra_vez_la_quita(client, regar):
    entrar(client, "tutor")
    url = reverse("tareas:plan_b", args=[regar.pk])
    musica = Tarea.objects.get(nombre="Escuchar música")
    cuento = Tarea.objects.get(nombre="Leer un cuento")
    client.post(url, {"accion": "alternar", "alternativa": musica.pk})
    client.post(url, {"accion": "alternar", "alternativa": cuento.pk})
    assert [a.nombre for a in regar.alternativas] == ["Escuchar música", "Leer un cuento"]
    html = client.get(url).content.decode()
    assert html.count('aria-pressed="true"') == 2
    client.post(url, {"accion": "alternar", "alternativa": musica.pk})
    assert [a.nombre for a in regar.alternativas] == ["Leer un cuento"]
    assert list(regar.planes_b.values_list("orden", flat=True)) == [1]


def test_8_primera_cambia_el_orden(client, regar):
    entrar(client, "tutor")
    url = reverse("tareas:plan_b", args=[regar.pk])
    musica = Tarea.objects.get(nombre="Escuchar música")
    cuento = Tarea.objects.get(nombre="Leer un cuento")
    for t in (musica, cuento):
        client.post(url, {"accion": "alternar", "alternativa": t.pk})
    respuesta = client.post(url, {"accion": "primera", "alternativa": cuento.pk}, follow=True)
    assert "«Leer un cuento» es ahora la primera." in respuesta.content.decode()
    assert [a.nombre for a in regar.alternativas] == ["Leer un cuento", "Escuchar música"]


def test_8_no_se_puede_poner_la_misma_tarea_en_su_plan_b(client, regar):
    entrar(client, "tutor")
    url = reverse("tareas:plan_b", args=[regar.pk])
    assert client.post(url, {"accion": "alternar", "alternativa": regar.pk}).status_code == 404
    assert not PlanB.objects.filter(tarea=regar).exists()


def test_8_el_buscador_va_arriba_y_filtra_las_tarjetas(client, regar):
    entrar(client, "tutor")
    url = reverse("tareas:plan_b", args=[regar.pk])
    html = client.get(url, {"q": "cuento"}).content.decode()
    assert html.index('role="search"') < html.index('id="biblioteca-plan-b"')
    tarjetas = html.split('id="biblioteca-plan-b"', 1)[1]
    assert "Leer un cuento" in tarjetas and "Escuchar música" not in tarjetas
    assert "Nueva" in tarjetas  # «+ Nueva» siempre está


def test_8_sin_desplegables_ni_subir_bajar(client, regar):
    entrar(client, "tutor")
    html = client.get(reverse("tareas:plan_b", args=[regar.pk])).content.decode()
    principal = html.split("<main", 1)[1]
    assert "<select" not in principal
    assert 'value="subir"' not in principal and 'value="bajar"' not in principal


# --- 9 · Asignar: «Desde» con la fecha de hoy ---


def test_9_asignar_propone_la_fecha_de_hoy(client, datos):
    entrar(client, "tutor")
    html = client.get(reverse("tareas:asignar_tarea")).content.decode()
    assert f'name="vigencia_desde" value="{date.today():%Y-%m-%d}"' in html or (
        f'value="{timezone.localdate():%Y-%m-%d}"' in html
    )


# --- 11 y 12 · Pasos a toda la pantalla y «¡Bravo!» ---


def test_11_con_la_tarea_en_marcha_los_pasos_se_quedan_la_pantalla(client, lucia, hora):
    hora(9, 1)
    mochila = lucia.asignaciones.get(tarea__nombre="Preparar la mochila")
    html = client.get(reverse("agenda:detalle", args=[mochila.pk])).content.decode()
    assert "ejec--pasos" not in html and "col--que" in html
    client.post(reverse("agenda:empezar", args=[mochila.pk]))
    html = client.get(reverse("agenda:detalle", args=[mochila.pk])).content.decode()
    assert "ejec--pasos" in html and "col col--que" not in html
    assert "data-temporizador" in html  # el tiempo sigue a la vista


def test_12_al_terminar_sale_bravo(client, lucia, hora):
    hora(10, 31)
    manos = lucia.asignaciones.get(tarea__nombre="Lavarse las manos")
    servicios.empezar(lucia, manos.pk, a_las(10, 30))
    t = servicios.tarea_del_dia(lucia, manos.pk, a_las(10, 31))
    for p in t.pasos:
        servicios.marcar_paso_hecho(lucia, manos.pk, p.paso.pk, a_las(10, 31))
    respuesta = client.post(reverse("agenda:terminar", args=[manos.pk]))
    assert respuesta["Location"] == reverse("agenda:bravo", args=[manos.pk])
    html = client.get(respuesta["Location"]).content.decode()
    assert "¡Bravo!" in html and "Has terminado «Lavarse las manos»" in html
    assert "Siguiente" in html  # luego toca «Regar las plantas»


def test_12_bravo_de_una_tarea_sin_terminar_vuelve_a_la_tarea(client, lucia, hora):
    hora(10, 31)
    manos = lucia.asignaciones.get(tarea__nombre="Lavarse las manos")
    respuesta = client.get(reverse("agenda:bravo", args=[manos.pk]))
    assert respuesta["Location"] == reverse("agenda:detalle", args=[manos.pk])


# --- 13 · Hecha y no hecha se distinguen ---


def test_13_hecha_y_no_hecha_llevan_su_sello(client, lucia, hora):
    hora(10, 31)
    manos = lucia.asignaciones.get(tarea__nombre="Lavarse las manos")
    servicios.empezar(lucia, manos.pk, a_las(10, 30))
    t = servicios.tarea_del_dia(lucia, manos.pk, a_las(10, 31))
    for p in t.pasos:
        servicios.marcar_paso_hecho(lucia, manos.pk, p.paso.pk, a_las(10, 31))
    servicios.terminar(lucia, manos.pk, a_las(10, 31))
    html = client.get(reverse("agenda:dia")).content.decode()
    assert "tarjeta--hecha" in html and "tarjeta__sello--hecha" in html
    assert "tarjeta--no-hecha" in html and "tarjeta__sello--no-hecha" in html  # la mochila


# --- 14 y 16 · Biblioteca de tareas con buscador ---


def test_16_tareas_creadas_ahora_es_biblioteca_de_tareas(client, datos):
    entrar(client, "tutor")
    html = client.get(reverse("usuarios:panel")).content.decode()
    assert "Biblioteca de tareas" in html and "Tareas creadas" not in html


def test_14_el_buscador_de_la_biblioteca_filtra_por_nombre_y_ambito(client, datos):
    entrar(client, "tutor")
    url = reverse("tareas:catalogo")
    html = client.get(url, {"q": "mochila"}).content.decode()
    lista = html.split('id="catalogo"', 1)[1]
    assert "Preparar la mochila" in lista and "Leer un cuento" not in lista
    html = client.get(url, {"ambito": "ocio"}).content.decode()
    lista = html.split('id="catalogo"', 1)[1]
    assert "Leer un cuento" in lista and "Preparar la mochila" not in lista
    html = client.get(url, {"q": "zzzz"}).content.decode()
    assert "No hay ninguna tarea" in html


# --- 15 · Tareas planificadas: de quién es cada una ---


def test_15_cada_tarea_planificada_lleva_avatar_y_nombre_del_alumno(client, datos):
    entrar(client, "tutor")
    html = client.get(reverse("tareas:tareas_planificadas")).content.decode()
    assert html.count('class="planificada__quien"') >= 1
    quien = html.split('class="planificada__quien"', 1)[1].split("</p>", 1)[0]
    assert "<img" in quien and "avatares/" in quien


# --- 17 · Buscador de alumnos del tutor ---


def test_17_el_tutor_busca_entre_sus_alumnos(client, datos):
    entrar(client, "tutor")
    html = client.get(reverse("perfil:lista"), {"q": "sof"}).content.decode()
    lista = html.split('id="alumnos"', 1)[1]
    assert "Sofía" in lista and "Hugo" not in lista
    html = client.get(reverse("perfil:lista"), {"q": "nadie"}).content.decode()
    assert "Ningún alumno coincide" in html


# --- 4 (cont.) · Mi horario dice por dónde vamos ---


def un_lunes(hora, minuto=0):
    from datetime import timedelta

    hoy = timezone.localdate()
    lunes = hoy - timedelta(days=hoy.weekday())
    return timezone.make_aware(datetime.combine(lunes, time(hora, minuto)))


def test_4_hoy_cada_clase_dice_si_ha_pasado_si_es_ahora_o_si_viene(client, lucia, monkeypatch):
    from apps.horario import servicios as horario

    monkeypatch.setattr(horario, "ahora", lambda: un_lunes(10, 30))
    html = client.get(reverse("horario:mi_horario")).content.decode()
    assert html.count("Ya ha pasado") == 1  # Matemáticas, de 9 a 10
    assert "▶</span> Ahora" in html and "Después" in html
    assert 'data-ahora="10:30"' in html and 'mi-horario__donde"' not in html


def test_4_otro_dia_lo_dice_en_una_frase(client, lucia, monkeypatch):
    from apps.horario import servicios as horario

    monkeypatch.setattr(horario, "ahora", lambda: un_lunes(10, 30))
    html = client.get(reverse("horario:mi_horario"), {"dia": 3}).content.decode()
    assert "Aún no ha llegado. Hoy es lunes." in html and "data-ahora" not in html
    monkeypatch.setattr(horario, "ahora", lambda: un_lunes(10, 30) + timedelta_dias(5))
    html = client.get(reverse("horario:mi_horario")).content.decode()
    assert "Hoy es sábado: no hay clase." in html


def timedelta_dias(n):
    from datetime import timedelta

    return timedelta(days=n)


def test_7_si_se_empieza_antes_tiene_lo_que_dura_la_tarea(client, lucia, hora):
    """Captura del 21/11: «Leer un cuento» (17:00-17:30) empezada a las 12:22 decía «Quedan
    308 min». Tiene 30 minutos desde que empieza: hasta las 12:52."""
    cuento = lucia.asignaciones.get(tarea__nombre="Leer un cuento")
    servicios.empezar(lucia, cuento.pk, a_las(12, 22))
    t = servicios.tarea_del_dia(lucia, cuento.pk, a_las(12, 30))
    assert t.fin_tarea == a_las(12, 52) and t.estado == "en_curso"
    hora(12, 30)
    html = client.get(reverse("agenda:detalle", args=[cuento.pk])).content.decode()
    assert 'data-restante-seg="1320"' in html  # 22 minutos
    assert "tienes hasta las 12:52" in html
    t = servicios.tarea_del_dia(lucia, cuento.pk, a_las(12, 53))
    assert t.estado == "tiempo_agotado"


def test_7_si_se_empieza_a_su_hora_o_tarde_el_final_no_se_mueve(lucia):
    regar = lucia.asignaciones.get(tarea__nombre="Regar las plantas")  # 12:00-12:30
    servicios.empezar(lucia, regar.pk, a_las(12, 10))
    assert servicios.tarea_del_dia(lucia, regar.pk, a_las(12, 15)).fin_tarea == a_las(12, 30)
