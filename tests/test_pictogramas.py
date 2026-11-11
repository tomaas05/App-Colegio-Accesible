"""Pictogramas de ARASAAC desde el servidor (decisión 0004) y permisos de tareas.

La red está simulada (fixture `arasaac`): ninguna prueba sale a Internet.
"""

import pytest
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.urls import reverse

from apps.comun import pictogramas
from apps.tareas.models import Tarea
from apps.usuarios.models import Usuario

from .arasaac_falso import Respuesta, png

pytestmark = pytest.mark.django_db

BUSCAR = reverse("pictogramas:buscar")


def entrar(client, usuario):
    client.force_login(Usuario.objects.get(username=usuario))
    return client


# --- Buscador: solo adultos, validado, con caché y con límite ------------------------


def test_buscar_devuelve_un_parcial_con_botones_de_opcion(client, datos, arasaac):
    html = entrar(client, "tutor").get(BUSCAR, {"q": "perro"}).content.decode()
    assert "<html" not in html  # es un parcial para HTMX
    assert html.count('type="radio"') == 3  # «Ninguno» y los dos resultados
    assert 'name="arasaac_id_tarea" value="2349"' in html
    assert reverse("pictogramas:vista_previa", args=[2349]) in html
    assert "arasaac.org/" not in html  # las imágenes salen de nuestro servidor
    assert ">perro guía</span>" in html
    assert "2 pictogramas de «perro»" in html
    assert 'hx-swap-oob="innerHTML"' in html  # el número va a la región role="status"


def test_a_arasaac_solo_sale_la_palabra_y_con_tiempo_maximo(client, datos, arasaac):
    entrar(client, "tutor").get(BUSCAR, {"q": "lavarse las manos"})
    (pedida,) = arasaac.pedidas
    assert pedida["url"].endswith("/es/search/lavarse%20las%20manos")
    assert pedida["timeout"] == (3, 5)
    assert "tutor" not in pedida["url"] and "Ana" not in pedida["url"]


def test_la_misma_busqueda_no_vuelve_a_salir_a_arasaac(client, datos, arasaac):
    entrar(client, "tutor")
    client.get(BUSCAR, {"q": "perro"})
    client.get(BUSCAR, {"q": "Perro"})  # la caché no mira mayúsculas ni tildes
    assert len(arasaac.pedidas) == 1


def test_el_campo_del_paso_se_respeta_y_uno_inventado_no(client, datos, arasaac):
    entrar(client, "tutor")
    html = client.get(BUSCAR, {"q": "perro", "campo": "pasos-3-arasaac_id_paso"}).content.decode()
    assert 'name="pasos-3-arasaac_id_paso"' in html
    html = client.get(BUSCAR, {"q": "perro", "campo": '"><script>'}).content.decode()
    assert "<script>" not in html and 'name="arasaac_id_tarea"' in html


@pytest.mark.parametrize("texto", ["", "a", "x" * 41, "../../etc", "perro<script>", "?q=1"])
def test_una_busqueda_no_valida_no_sale_a_arasaac(client, datos, arasaac, texto):
    html = entrar(client, "tutor").get(BUSCAR, {"q": texto}).content.decode()
    assert "Escribe una palabra" in html
    assert arasaac.pedidas == []


def test_sin_resultados_lo_dice(client, datos, arasaac):
    arasaac.resultados = None  # ARASAAC responde 404
    html = entrar(client, "tutor").get(BUSCAR, {"q": "xyzzy"}).content.decode()
    assert "No hay pictogramas de «xyzzy»" in html and 'type="radio"' not in html


def test_si_arasaac_tarda_hay_mensaje_y_se_puede_subir_un_archivo(client, datos, arasaac):
    arasaac.lento()
    respuesta = entrar(client, "tutor").get(BUSCAR, {"q": "perro"})
    assert respuesta.status_code == 200
    assert "Ahora no se puede buscar en ARASAAC" in respuesta.content.decode()
    assert "subir una imagen" in respuesta.content.decode()


def test_un_fallo_de_arasaac_no_se_guarda_en_la_cache(client, datos, arasaac):
    arasaac.lento()
    entrar(client, "tutor").get(BUSCAR, {"q": "perro"})
    arasaac.error = None
    assert "2 pictogramas" in client.get(BUSCAR, {"q": "perro"}).content.decode()


def test_limite_de_busquedas_por_usuario(client, datos, arasaac, monkeypatch):
    monkeypatch.setattr("apps.comun.views.BUSQUEDAS_POR_MINUTO", 2)
    entrar(client, "tutor")
    for palabra in ("perro", "gato"):
        assert "pictograma" in client.get(BUSCAR, {"q": palabra}).content.decode()
    assert "Espera un minuto" in client.get(BUSCAR, {"q": "pez"}).content.decode()
    assert len(arasaac.pedidas) == 2
    # El límite es de cada usuario: otro adulto sigue buscando.
    entrar(client, "profesional")
    assert "pictograma" in client.get(BUSCAR, {"q": "pez"}).content.decode()


@pytest.mark.parametrize("nombre_url, args", [("buscar", []), ("vista_previa", [2349])])
def test_un_estudiante_no_puede_usar_los_pictogramas(client, datos, arasaac, nombre_url, args):
    respuesta = entrar(client, "est-a01").get(reverse(f"pictogramas:{nombre_url}", args=args))
    assert respuesta.status_code == 403
    assert arasaac.pedidas == []


def test_sin_sesion_va_a_la_portada(client, db, arasaac):
    respuesta = client.get(BUSCAR, {"q": "perro"})
    assert respuesta.status_code == 302 and respuesta["Location"].startswith("/?next=")


def test_buscar_es_solo_lectura(client, datos, arasaac):
    assert entrar(client, "tutor").post(BUSCAR, {"q": "perro"}).status_code == 405


# --- Imágenes: siempre la copia local ---------------------------------------------


def test_la_vista_previa_descarga_una_vez_y_sirve_la_copia_local(client, datos, arasaac):
    entrar(client, "tutor")
    url = reverse("pictogramas:vista_previa", args=[2349])
    primera = client.get(url)
    assert primera.status_code == 200 and primera["Content-Type"] == "image/png"
    assert "max-age=31536000" in primera["Cache-Control"]
    assert b"".join(primera.streaming_content) == png()
    assert default_storage.exists("pictogramas/2349.png")
    client.get(url)
    assert len(arasaac.pedidas) == 1  # la segunda vez no se sale a ARASAAC
    assert arasaac.pedidas[0]["url"].endswith("/pictograms/2349/2349_300.png")
    assert arasaac.pedidas[0]["timeout"] == (3, 5)


@pytest.mark.parametrize("valor", ["abc", "12a", "-1", "0", "1/../2", "12345678", " ", "1.5"])
def test_identificador_no_numerico(valor, arasaac):
    with pytest.raises(pictogramas.IdentificadorNoValido):
        pictogramas.obtener(valor)
    assert arasaac.pedidas == []


def test_respuesta_lenta(arasaac):
    arasaac.lento()
    with pytest.raises(pictogramas.ErrorArasaac):
        pictogramas.obtener(2349)
    assert not default_storage.exists("pictogramas/2349.png")


@pytest.mark.parametrize(
    "contenido", [b"<html>no soy una imagen</html>", b"", b"GIF89a" + b"\0" * 40], ids=str
)
def test_respuesta_que_no_es_imagen(arasaac, contenido):
    arasaac.imagen = Respuesta(contenido=contenido, cabeceras={"Content-Type": "image/png"})
    with pytest.raises(pictogramas.ErrorArasaac):
        pictogramas.obtener(2349)
    assert not default_storage.exists("pictogramas/2349.png")


def test_un_jpeg_no_vale_aunque_diga_que_es_png(arasaac):
    import io

    from PIL import Image

    salida = io.BytesIO()
    Image.new("RGB", (10, 10)).save(salida, "JPEG")
    arasaac.imagen = Respuesta(contenido=salida.getvalue(), cabeceras={"Content-Type": "image/png"})
    with pytest.raises(pictogramas.ErrorArasaac):
        pictogramas.obtener(2349)


def test_imagen_que_pesa_demasiado(arasaac, monkeypatch):
    monkeypatch.setattr(pictogramas, "TAMANO_MAXIMO", 1000)
    arasaac.imagen = Respuesta(
        contenido=png() + b"\0" * 2000
    )  # sin Content-Length: se corta al leer
    with pytest.raises(pictogramas.ErrorArasaac, match="pesa demasiado"):
        pictogramas.obtener(2349)
    arasaac.imagen = Respuesta(contenido=b"", cabeceras={"Content-Length": "999999999"})
    with pytest.raises(pictogramas.ErrorArasaac, match="pesa demasiado"):
        pictogramas.obtener(2350)


def test_imagen_de_demasiados_pixeles(arasaac):
    arasaac.imagen = Respuesta(contenido=png(lado=1200))
    with pytest.raises(pictogramas.ErrorArasaac, match="demasiado grande"):
        pictogramas.obtener(2349)


def test_si_la_imagen_falla_la_vista_previa_da_404(client, datos, arasaac):
    arasaac.imagen = Respuesta(status_code=500)
    url = reverse("pictogramas:vista_previa", args=[2349])
    assert entrar(client, "tutor").get(url).status_code == 404


# --- Crear tarea con pictograma -----------------------------------------------------

DATOS_TAREA = {
    "nombre": "Pasear al perro",
    "descripcion": "",
    "ambito": "casa",
    "descripcion_imagen": "perro",
    "pasos-TOTAL_FORMS": "0",
    "pasos-INITIAL_FORMS": "0",
}


def test_dos_tareas_con_el_mismo_pictograma_comparten_la_copia(client, datos, arasaac):
    entrar(client, "tutor")
    for nombre in ("Pasear al perro", "Dar de comer al perro"):
        respuesta = client.post(
            reverse("tareas:crear_tarea"),
            {**DATOS_TAREA, "nombre": nombre, "arasaac_id_tarea": "2349"},
        )
        assert respuesta.status_code == 302
    imagenes = set(Tarea.objects.filter(nombre__contains="perro").values_list("imagen", flat=True))
    assert imagenes == {"pictogramas/2349.png"}
    assert len(arasaac.pedidas) == 1


def test_identificador_no_numerico_en_el_formulario(client, datos, arasaac):
    entrar(client, "tutor")
    respuesta = client.post(
        reverse("tareas:crear_tarea"), {**DATOS_TAREA, "arasaac_id_tarea": "../../secreto"}
    )
    assert respuesta.status_code == 200
    assert "Ese pictograma no existe" in respuesta.content.decode()
    assert arasaac.pedidas == [] and not Tarea.objects.filter(nombre="Pasear al perro").exists()


def test_si_arasaac_falla_al_guardar_se_avisa_y_no_se_guarda_a_medias(client, datos, arasaac):
    arasaac.lento()
    entrar(client, "tutor")
    respuesta = client.post(
        reverse("tareas:crear_tarea"), {**DATOS_TAREA, "arasaac_id_tarea": "2349"}
    )
    html = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert "No se ha podido traer el pictograma de ARASAAC" in html
    assert 'role="alert"' in html
    assert not Tarea.objects.filter(nombre="Pasear al perro").exists()
    # El pictograma elegido no se pierde: sigue marcado para volver a intentarlo.
    assert 'name="arasaac_id_tarea" value="2349" checked' in html


def test_sin_imagen_ni_pictograma_no_se_guarda(client, datos, arasaac):
    respuesta = entrar(client, "tutor").post(reverse("tareas:crear_tarea"), DATOS_TAREA)
    assert respuesta.status_code == 200
    assert "Sube una imagen o elige un pictograma" in respuesta.content.decode()


def test_los_pasos_no_se_pierden_si_el_formulario_vuelve_con_errores(client, datos, arasaac):
    """Antes, al fallar la validación, la página volvía sin los pasos escritos."""
    entrar(client, "tutor")
    respuesta = client.post(
        reverse("tareas:crear_tarea"),
        {
            **DATOS_TAREA,
            "nombre": "",
            "arasaac_id_tarea": "2349",
            "pasos-TOTAL_FORMS": "1",
            "pasos-0-orden": "1",
            "pasos-0-descripcion": "Coger la correa",
            "pasos-0-descripcion_imagen": "correa",
            "pasos-0-arasaac_id_paso": "7202",
        },
    )
    html = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert (
        "Coger la correa" in html and 'name="pasos-0-arasaac_id_paso" value="7202" checked' in html
    )


def test_el_formulario_no_lleva_estilos_ni_eventos_en_linea(client, datos, arasaac):
    entrar(client, "tutor")
    paginas = [
        client.get(reverse("tareas:crear_tarea")),
        client.get(reverse("tareas:anadir_paso"), {"total_forms": "0"}),
        client.get(reverse("tareas:asignar_tarea")),
        client.get(reverse("tareas:catalogo")),
        client.get(BUSCAR, {"q": "perro"}),
    ]
    for pagina in paginas:
        html = pagina.content.decode()
        assert pagina.status_code == 200
        assert " style=" not in html and "onclick=" not in html and "<script>" not in html
        assert "arasaac.org/" not in html.replace("(arasaac.org)", "")


@pytest.mark.parametrize("total", ["abc", "-1", "30", "9999"])
def test_anadir_paso_valida_el_numero(client, datos, total):
    respuesta = entrar(client, "tutor").get(reverse("tareas:anadir_paso"), {"total_forms": total})
    assert respuesta.status_code == 400


def test_anadir_paso_numera_los_campos(client, datos):
    html = (
        entrar(client, "tutor")
        .get(reverse("tareas:anadir_paso"), {"total_forms": "2"})
        .content.decode()
    )
    assert 'name="pasos-2-descripcion"' in html and "__prefix__" not in html
    assert "Paso 3" in html


# --- Permisos de las pantallas de tareas (fallo 7) ----------------------------------

PANTALLAS_DE_TAREAS = ["crear_tarea", "catalogo", "asignar_tarea", "anadir_paso"]


@pytest.mark.parametrize("nombre_url", PANTALLAS_DE_TAREAS)
def test_un_estudiante_no_entra_en_las_pantallas_de_tareas(client, datos, nombre_url):
    assert entrar(client, "est-a01").get(reverse(f"tareas:{nombre_url}")).status_code == 403


def test_un_estudiante_no_puede_crear_ni_asignar_con_post(client, datos, arasaac):
    entrar(client, "est-a01")
    crear = client.post(reverse("tareas:crear_tarea"), {**DATOS_TAREA, "arasaac_id_tarea": "1"})
    asignar = client.post(reverse("tareas:asignar_tarea"), {})
    assert crear.status_code == 403 and asignar.status_code == 403
    assert not Tarea.objects.filter(nombre="Pasear al perro").exists()


@pytest.mark.parametrize("usuario", ["tutor", "profesional", "familiar"])
@pytest.mark.parametrize("nombre_url", PANTALLAS_DE_TAREAS[:3])
def test_tutor_profesional_y_familiar_si_entran(client, datos, usuario, nombre_url):
    assert entrar(client, usuario).get(reverse(f"tareas:{nombre_url}")).status_code == 200


def test_el_administrador_no_gestiona_tareas(client, datos):
    assert entrar(client, "admin").get(reverse("tareas:crear_tarea")).status_code == 403


@pytest.mark.parametrize(
    "usuario, esperados",
    [
        ("tutor", {"Lucía", "Mateo", "Sofía", "Hugo", "Martina", "Leo"}),
        ("tutor2", {"Daniela", "Pablo", "Vega"}),
        ("profesional", {"Lucía", "Hugo"}),
        ("familiar", {"Lucía"}),
    ],
)
def test_al_asignar_solo_salen_mis_estudiantes(client, datos, usuario, esperados):
    respuesta = entrar(client, usuario).get(reverse("tareas:asignar_tarea"))
    visibles = {
        e.usuario.first_name for e in respuesta.context["form"].fields["estudiantes"].queryset
    }
    assert visibles == esperados


def test_no_puedo_asignar_a_un_estudiante_que_no_es_mio(client, datos):
    from apps.tareas.models import Asignacion
    from apps.usuarios.models import Estudiante

    ajeno = Estudiante.objects.get(usuario__first_name="Daniela")
    antes = Asignacion.objects.count()
    respuesta = entrar(client, "tutor").post(
        reverse("tareas:asignar_tarea"),
        {
            "tarea": Tarea.objects.first().pk,
            "estudiantes": [ajeno.pk],
            "hora_inicio": "22:00",
            "hora_fin": "22:30",
            "dias_semana": ["1"],
            "vigencia_desde": "2026-11-11",
        },
    )
    assert respuesta.status_code == 200 and Asignacion.objects.count() == antes


def test_las_vistas_de_tareas_no_escriben_en_la_consola(client, datos, capsys):
    """Antes había print() de depuración cuando el formulario tenía errores."""
    entrar(client, "tutor")
    client.post(reverse("tareas:crear_tarea"), {**DATOS_TAREA, "nombre": ""})
    client.post(reverse("tareas:asignar_tarea"), {})
    assert capsys.readouterr().out == ""


def test_el_catalogo_no_hace_una_consulta_por_tarea(client, datos, django_assert_max_num_queries):
    entrar(client, "tutor")
    with django_assert_max_num_queries(4):  # sesión, usuario y las tareas con sus pasos contados
        client.get(reverse("tareas:catalogo"))


def test_la_cache_de_cada_prueba_empieza_vacia():
    assert cache.get("picto:buscar:cualquiera") is None
