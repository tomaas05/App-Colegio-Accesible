"""HU-03-06 · Plan B de una tarea (boceto B42): alternativas ordenadas por prioridad.

El plan B ya no se elige al crear la tarea: tiene su pantalla, a la que se llega desde el
catálogo («Plan B»), donde se añaden del catálogo o se crean, se ordenan y se quitan.
"""

import pytest
from django.urls import reverse

from apps.tareas.models import Ambito, PlanB, Tarea
from apps.usuarios.models import Usuario

pytestmark = pytest.mark.django_db


def entrar(client, usuario):
    client.force_login(Usuario.objects.get(username=usuario))
    return client


def tarea(nombre):
    return Tarea.objects.get(nombre=nombre)


def url(t):
    return reverse("tareas:plan_b", args=[t.pk])


def anadir(client, t, alternativa):
    return client.post(url(t), {"accion": "anadir", "alternativa": alternativa.pk})


def nombres(t):
    return [a.nombre for a in t.alternativas]


@pytest.fixture
def regar(datos):
    """Sin el plan B de los datos de prueba, para empezar de cero."""
    t = tarea("Regar las plantas")
    t.planes_b.all().delete()
    return t


def test_los_datos_de_prueba_traen_un_plan_b(datos):
    assert nombres(tarea("Regar las plantas")) == ["Escuchar música", "Leer un cuento"]


def test_una_tarea_sin_plan_b_funciona_normal(client, regar):
    """PA4: sin plan B no pasa nada; el catálogo no dice «Con plan B»."""
    assert regar.alternativas == []
    html = entrar(client, "tutor").get(reverse("tareas:catalogo")).content.decode()
    assert "Con plan B" not in html.split("Regar las plantas", 1)[1].split("</li>", 1)[0]
    assert url(regar) in html  # desde el catálogo se llega a su plan B
    assert entrar(client, "tutor").get(url(regar)).status_code == 200


def test_crear_tarea_ya_no_pide_el_plan_b(client, datos):
    html = entrar(client, "tutor").get(reverse("tareas:crear_tarea")).content.decode()
    assert "planes_b" not in html


def test_anadir_varias_alternativas_en_orden(client, regar):
    """PA1 y PA2: se añaden una o varias, y la tarea muestra que tiene plan B."""
    entrar(client, "tutor")
    respuesta = anadir(client, regar, tarea("Leer un cuento"))
    assert respuesta.status_code == 302
    anadir(client, regar, tarea("Lavarse las manos"))
    assert nombres(regar) == ["Leer un cuento", "Lavarse las manos"]
    assert list(regar.planes_b.values_list("orden", flat=True)) == [1, 2]
    html = client.get(reverse("tareas:catalogo")).content.decode()
    assert "Con plan B (2)" in html


def test_no_se_anade_la_misma_tarea_ni_una_repetida(client, regar):
    entrar(client, "tutor")
    assert anadir(client, regar, regar).status_code == 200
    anadir(client, regar, tarea("Leer un cuento"))
    assert anadir(client, regar, tarea("Leer un cuento")).status_code == 200
    assert nombres(regar) == ["Leer un cuento"]


def test_subir_y_bajar_cambian_la_prioridad(client, regar):
    entrar(client, "tutor")
    cuento, manos, mochila = (
        tarea("Leer un cuento"),
        tarea("Lavarse las manos"),
        tarea("Preparar la mochila"),
    )
    for t in (cuento, manos, mochila):
        anadir(client, regar, t)

    respuesta = client.post(url(regar), {"accion": "subir", "alternativa": mochila.pk})
    assert respuesta.url.endswith(f"?foco=subir-{mochila.pk}")  # el foco vuelve al botón
    assert nombres(regar) == ["Leer un cuento", "Preparar la mochila", "Lavarse las manos"]

    client.post(url(regar), {"accion": "bajar", "alternativa": cuento.pk})
    assert nombres(regar) == ["Preparar la mochila", "Leer un cuento", "Lavarse las manos"]

    # En los extremos no se mueve y se dice por qué.
    seguida = client.post(url(regar), {"accion": "subir", "alternativa": mochila.pk}, follow=True)
    assert "«Preparar la mochila» ya es la primera." in seguida.content.decode()
    assert nombres(regar) == ["Preparar la mochila", "Leer un cuento", "Lavarse las manos"]


def test_quitar_una_alternativa(client, regar):
    """PA3: al quitarla deja de estar en el plan B; las demás se renumeran."""
    entrar(client, "tutor")
    cuento, manos = tarea("Leer un cuento"), tarea("Lavarse las manos")
    anadir(client, regar, cuento)
    anadir(client, regar, manos)
    client.post(url(regar), {"accion": "quitar", "alternativa": cuento.pk})
    assert nombres(regar) == ["Lavarse las manos"]
    assert list(regar.planes_b.values_list("orden", flat=True)) == [1]
    assert Tarea.objects.filter(pk=cuento.pk).exists()  # la tarea sigue en el catálogo


def test_crear_una_alternativa_nueva_con_pictograma(client, regar, arasaac):
    entrar(client, "tutor")
    anadir(client, regar, tarea("Leer un cuento"))
    respuesta = client.post(
        url(regar), {"accion": "crear", "nombre": "Barrer el patio", "arasaac_id_alternativa": "7"}
    )
    assert respuesta.status_code == 302
    nueva = tarea("Barrer el patio")
    assert nueva.imagen and nueva.ambito == Ambito.ESCOLAR
    assert nombres(regar) == ["Leer un cuento", "Barrer el patio"]  # va la última


def test_crear_una_alternativa_necesita_nombre_y_pictograma(client, regar, arasaac):
    entrar(client, "tutor")
    respuesta = client.post(
        url(regar), {"accion": "crear", "nombre": "", "arasaac_id_alternativa": ""}
    )
    assert respuesta.status_code == 200
    assert not PlanB.objects.exists()


def test_si_arasaac_no_responde_no_se_crea_nada(client, regar, arasaac):
    arasaac.lento()
    entrar(client, "tutor")
    respuesta = client.post(
        url(regar), {"accion": "crear", "nombre": "Barrer el patio", "arasaac_id_alternativa": "7"}
    )
    assert respuesta.status_code == 200
    assert not Tarea.objects.filter(nombre="Barrer el patio").exists()


@pytest.mark.parametrize(
    ("usuario", "nombre", "puede"),
    [
        ("tutor", "Regar las plantas", True),
        ("tutor2", "Regar las plantas", True),  # el catálogo es del centro
        ("profesional", "Regar las plantas", True),
        ("familiar", "Poner la mesa", True),  # la suya
        ("familiar", "Regar las plantas", False),
    ],
)
def test_quien_edita_el_plan_b(client, datos, usuario, nombre, puede):
    t = tarea(nombre)
    entrar(client, usuario)
    assert client.get(url(t)).status_code == (200 if puede else 404)
    respuesta = anadir(client, t, tarea("Lavarse las manos"))
    assert respuesta.status_code == (302 if puede else 404)


def test_un_estudiante_no_entra(client, regar):
    assert entrar(client, "est-a01").get(url(regar)).status_code == 403


def test_una_tarea_que_no_existe_da_404(client, datos):
    assert entrar(client, "tutor").get(reverse("tareas:plan_b", args=[999999])).status_code == 404


def test_borrar_una_alternativa_del_catalogo_la_quita_del_plan_b(regar):
    suelta = Tarea.objects.create(
        nombre="Dibujar",
        imagen="tareas/dibujar.png",
        descripcion_imagen="Dibujar",
        ambito=Ambito.ESCOLAR,
        creador=regar.creador,
    )
    PlanB.objects.create(tarea=regar, alternativa=suelta, orden=1)
    suelta.delete()
    assert regar.alternativas == []
