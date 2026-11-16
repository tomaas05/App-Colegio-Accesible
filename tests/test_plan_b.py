from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.tareas.models import Ambito, Tarea
from apps.usuarios.models import Usuario
from tests.arasaac_falso import ArasaacFalso


class PlanBTareaTests(TestCase):
    def setUp(self):
        # ARASAAC de mentira: las pruebas no salen a Internet (decisión 0004).
        self.arasaac = ArasaacFalso()
        parche = mock.patch("apps.comun.pictogramas.requests.get", self.arasaac.get)
        parche.start()
        self.addCleanup(parche.stop)

        self.tutor_user = Usuario(
            username="tutor_plan_b",
            first_name="Úrsula",
            last_name="Tutor",
            rol="tutor",
        )
        self.tutor_user.set_password("despega2026")
        self.tutor_user.save()

    def _crear_imagen_prueba(self, nombre="test_image.jpg"):
        """Genera un archivo de imagen válido en memoria para poder probar el guardado."""
        return SimpleUploadedFile(
            name=nombre,
            content=b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b",
            content_type="image/jpeg",
        )

    def test_anadir_varias_actividades_alternativas(self):
        """Criterio 1: Añado una o varias actividades alternativas a una tarea."""
        tarea_b1 = Tarea.objects.create(nombre="Plan B 1", creador=self.tutor_user, descripcion_imagen="D1")
        tarea_b2 = Tarea.objects.create(nombre="Plan B 2", creador=self.tutor_user, descripcion_imagen="D2")

        self.client.force_login(self.tutor_user)
        response = self.client.post(
            reverse("tareas:crear_tarea"),
            {
                "nombre": "Tarea Principal",
                "descripcion": "Si falla, hay opciones.",
                "ambito": Ambito.CASA,
                "descripcion_imagen": "Principal",
                "imagen": self._crear_imagen_prueba(),
                "planes_b": [str(tarea_b1.id), str(tarea_b2.id)],  # Pasamos los IDs como strings
                "pasos-TOTAL_FORMS": "0",
                "pasos-INITIAL_FORMS": "0",
                "pasos-MIN_NUM_FORMS": "0",
                "pasos-MAX_NUM_FORMS": "1000",
            },
        )

        self.assertEqual(response.status_code, 302)
        tarea_creada = Tarea.objects.get(nombre="Tarea Principal")
        self.assertEqual(tarea_creada.planes_b.count(), 2)
        self.assertIn(tarea_b1, tarea_creada.planes_b.all())
        self.assertIn(tarea_b2, tarea_creada.planes_b.all())

    def test_tarea_muestra_que_tiene_plan_b_en_catalogo(self):
        """Criterio 2: La tarea muestra que tiene plan B."""
        tarea_alt = Tarea.objects.create(nombre="Alternativa", creador=self.tutor_user, descripcion_imagen="Alt")
        tarea_ppal = Tarea.objects.create(nombre="Principal con Plan B", creador=self.tutor_user, descripcion_imagen="Ppal")
        tarea_ppal.planes_b.add(tarea_alt)

        self.client.force_login(self.tutor_user)
        response = self.client.get(reverse("tareas:catalogo"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Principal con Plan B")
        self.assertContains(response, "💡 Tiene plan B")

    def test_eliminar_alternativa_deja_de_aparecer(self):
        """Criterio 3: Elimino una alternativa y deja de aparecer."""
        tarea_alt = Tarea.objects.create(nombre="Alternativa Temporal", creador=self.tutor_user, descripcion_imagen="Temp")
        tarea_ppal = Tarea.objects.create(nombre="Editarme", creador=self.tutor_user, descripcion_imagen="Ppal")
        tarea_ppal.planes_b.add(tarea_alt)

        self.client.force_login(self.tutor_user)

        # 1. Comprobamos que al principio SÍ sale el aviso
        response_antes = self.client.get(reverse("tareas:catalogo"))
        self.assertContains(response_antes, "💡 Tiene plan B")

        # 2. Eliminamos la alternativa directamente en el modelo
        # (ya que la vista de edición no existe todavía en HU-03-06)
        tarea_ppal.planes_b.remove(tarea_alt)

        # 3. Comprobamos que el aviso ya NO aparece en el catálogo
        response_despues = self.client.get(reverse("tareas:catalogo"))
        self.assertNotContains(response_despues, "💡 Tiene plan B", status_code=200)

    def test_tarea_sin_plan_b_funciona_con_normalidad(self):
        """Criterio 4: Una tarea sin plan B sigue funcionando con normalidad."""
        self.client.force_login(self.tutor_user)
        response = self.client.post(
            reverse("tareas:crear_tarea"),
            {
                "nombre": "Tarea Normal",
                "descripcion": "Sin alternativas.",
                "ambito": Ambito.ESCOLAR,
                "descripcion_imagen": "Normal",
                "imagen": self._crear_imagen_prueba(),
                # planes_b se omite por completo del diccionario, como un campo sin marcar
                "pasos-TOTAL_FORMS": "0",
                "pasos-INITIAL_FORMS": "0",
                "pasos-MIN_NUM_FORMS": "0",
                "pasos-MAX_NUM_FORMS": "1000",
            },
        )

        self.assertEqual(response.status_code, 302)
        tarea_creada = Tarea.objects.get(nombre="Tarea Normal")
        self.assertEqual(tarea_creada.planes_b.count(), 0)

        cat_response = self.client.get(reverse("tareas:catalogo"))
        self.assertContains(cat_response, "Tarea Normal")
        self.assertNotContains(cat_response, "💡 Tiene plan B", status_code=200)
