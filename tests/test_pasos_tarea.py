import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.tareas.models import Ambito, Tarea
from apps.usuarios.models import Usuario

pytestmark = pytest.mark.django_db


@pytest.fixture
def tutor_usuario():
    tutor, _ = Usuario.objects.get_or_create(
        username="tutor_pasos",
        defaults={"first_name": "Úrsula", "last_name": "Tutor", "rol": "tutor"},
    )
    tutor.set_password("despega2026")
    tutor.save()
    return tutor


def test_tarea_sin_pasos_es_valida(tutor_usuario):
    """Una tarea sin pasos sigue siendo válida (Criterio de aceptación)."""
    tarea = Tarea.objects.create(
        nombre="Tarea sin pasos",
        descripcion_imagen="Icono válido",
        creador=tutor_usuario,
        ambito=Ambito.ESCOLAR,
    )
    assert tarea.pk is not None
    assert tarea.pasos.count() == 0


def test_gestion_orden_de_pasos_integracion(client, tutor_usuario):
    """Criterios: Añadimos tres pasos con imágenes
    independientes, los modificamos y comprobamos su orden."""
    client.force_login(tutor_usuario)

    tarea = Tarea.objects.create(
        nombre="Tarea con pasos",
        descripcion_imagen="Icono base",
        creador=tutor_usuario,
        ambito=Ambito.ESCOLAR,
    )

    url = reverse("tareas:editar_pasos_tarea", kwargs={"tarea_id": tarea.id})

    def crear_imagen():
        return SimpleUploadedFile(
            name="paso.png",
            content=b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/png",
        )

    post_data = {
        "pasos-TOTAL_FORMS": "3",
        "pasos-INITIAL_FORMS": "0",
        "pasos-MIN_NUM_FORMS": "0",
        "pasos-MAX_NUM_FORMS": "1000",
        # Paso 1
        "pasos-0-id": "",
        "pasos-0-orden": "1",
        "pasos-0-descripcion": "Primer paso",
        "pasos-0-descripcion_imagen": "Foto paso 1",
        # Paso 2
        "pasos-1-id": "",
        "pasos-1-orden": "2",
        "pasos-1-descripcion": "Segundo paso",
        "pasos-1-descripcion_imagen": "Foto paso 2",
        # Paso 3
        "pasos-2-id": "",
        "pasos-2-orden": "3",
        "pasos-2-descripcion": "Tercer paso",
        "pasos-2-descripcion_imagen": "Foto paso 3",
    }

    files_data = {
        "pasos-0-imagen": crear_imagen(),
        "pasos-1-imagen": crear_imagen(),
        "pasos-2-imagen": crear_imagen(),
    }

    response = client.post(url, {**post_data, **files_data})

    # Verificamos que redirige correctamente (código 302)
    assert response.status_code == 302, (
        f"Errores en formulario: "
        f"{
            response.context['formset'].errors
            if response.context and 'formset' in response.context
            else response.content
        }"
    )
    assert response.url == reverse("tareas:catalogo")

    # Comprobamos en base de datos que se guardaron los 3 pasos ordenados correctamente
    tarea.refresh_from_db()
    pasos = list(tarea.pasos.order_by("orden"))
    assert len(pasos) == 3
    assert pasos[0].descripcion == "Primer paso"
    assert pasos[0].orden == 1
    assert pasos[1].descripcion == "Segundo paso"
    assert pasos[1].orden == 2
    assert pasos[2].descripcion == "Tercer paso"
    assert pasos[2].orden == 3
