from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.tareas.models import Ambito, Tarea
from apps.usuarios.models import Usuario
from tests.arasaac_falso import ArasaacFalso


class CrearTareaTests(TestCase):
    def setUp(self):
        # ARASAAC de mentira: las pruebas no salen a Internet (decisión 0004).
        self.arasaac = ArasaacFalso()
        parche = mock.patch("apps.comun.pictogramas.requests.get", self.arasaac.get)
        parche.start()
        self.addCleanup(parche.stop)
        # Creamos un usuario con rol 'tutor' usando el modelo de la app usuarios
        self.tutor_user = Usuario(
            username="tutor_creador",
            first_name="Úrsula",
            last_name="Tutor",
            rol="tutor",
        )
        self.tutor_user.set_password("despega2026")
        self.tutor_user.save()

    def _crear_imagen_prueba(self, nombre="test_image.jpg"):
        """Función auxiliar para generar un archivo de imagen fresco en cada petición."""
        return SimpleUploadedFile(
            name=nombre,
            content=b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b",
            content_type="image/jpeg",
        )

    def test_creacion_tarea_valida_en_catalogo(self):
        """Creo una tarea con nombre, descripción, ámbito e imagen y aparece en el catálogo."""
        self.client.force_login(self.tutor_user)

        response = self.client.post(
            reverse("tareas:crear_tarea"),
            {
                "nombre": "Lavarse los dientes",
                "descripcion": "Cepillar los dientes con pasta fluorada",
                "ambito": Ambito.CASA,
                "descripcion_imagen": "Cepillo de dientes",
                "imagen": self._crear_imagen_prueba(),
                "pasos-TOTAL_FORMS": "0",
                "pasos-INITIAL_FORMS": "0",
                "pasos-MIN_NUM_FORMS": "0",
                "pasos-MAX_NUM_FORMS": "1000",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Tarea.objects.filter(nombre="Lavarse los dientes").exists())
        tarea = Tarea.objects.get(nombre="Lavarse los dientes")
        self.assertEqual(tarea.ambito, Ambito.CASA)
        self.assertEqual(tarea.creador, self.tutor_user)

    def test_creacion_tarea_valida_con_arasaac(self):
        """Una tarea sin archivo de imagen físico pero con arasaac_id_tarea se guarda bien."""
        self.client.force_login(self.tutor_user)

        response = self.client.post(
            reverse("tareas:crear_tarea"),
            {
                "nombre": "Beber agua",
                "descripcion": "Beber un vaso de agua",
                "ambito": Ambito.CASA,
                "descripcion_imagen": "Vaso de agua",
                "arasaac_id_tarea": "12345",
                "pasos-TOTAL_FORMS": "0",
                "pasos-INITIAL_FORMS": "0",
                "pasos-MIN_NUM_FORMS": "0",
                "pasos-MAX_NUM_FORMS": "1000",
            },
        )
        self.assertEqual(response.status_code, 302)
        tarea = Tarea.objects.get(nombre="Beber agua")
        # La imagen es la copia local compartida del pictograma, no una dirección de ARASAAC.
        self.assertEqual(tarea.imagen.name, "pictogramas/12345.png")

    def test_error_tarea_sin_nombre(self):
        """Una tarea sin nombre no se guarda y muestra errores de formulario."""
        self.client.force_login(self.tutor_user)

        response = self.client.post(
            reverse("tareas:crear_tarea"),
            {
                "nombre": "",  # Vacío (incorrecto)
                "descripcion": "Sin nombre",
                "ambito": Ambito.ESCOLAR,
                "descripcion_imagen": "Imagen de prueba",
                "imagen": self._crear_imagen_prueba(),
                "pasos-TOTAL_FORMS": "0",
                "pasos-INITIAL_FORMS": "0",
                "pasos-MIN_NUM_FORMS": "0",
                "pasos-MAX_NUM_FORMS": "1000",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Este campo es requerido.")
        self.assertFalse(Tarea.objects.filter(descripcion="Sin nombre").exists())

    def test_error_tarea_sin_imagen_principal(self):
        """Una tarea sin imagen principal o sin campos obligatorios asociados no se guarda."""
        self.client.force_login(self.tutor_user)

        response = self.client.post(
            reverse("tareas:crear_tarea"),
            {
                "nombre": "Tarea sin imagen",
                "descripcion": "Falta la imagen principal",
                "ambito": Ambito.CASA,
                "descripcion_imagen": "",
                "pasos-TOTAL_FORMS": "0",
                "pasos-INITIAL_FORMS": "0",
                "pasos-MIN_NUM_FORMS": "0",
                "pasos-MAX_NUM_FORMS": "1000",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Tarea.objects.filter(nombre="Tarea sin imagen").exists())

    def test_error_pasos_incompletos(self):
        """Añadir un paso con campos obligatorios vacíos frena el guardado."""
        self.client.force_login(self.tutor_user)

        response = self.client.post(
            reverse("tareas:crear_tarea"),
            {
                "nombre": "Tarea con paso defectuoso",
                "descripcion": "Descripción válida",
                "ambito": Ambito.CASA,
                "descripcion_imagen": "Imagen ok",
                "imagen": self._crear_imagen_prueba("principal.jpg"),
                "pasos-TOTAL_FORMS": "1",
                "pasos-INITIAL_FORMS": "0",
                "pasos-MIN_NUM_FORMS": "0",
                "pasos-MAX_NUM_FORMS": "1000",
                "pasos-0-orden": "1",
                "pasos-0-descripcion": "",  # Vacío (incorrecto)
                "pasos-0-descripcion_imagen": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Tarea.objects.filter(nombre="Tarea con paso defectuoso").exists())

    def test_creacion_tarea_con_pasos_ordenados(self):
        """Añado pasos a la tarea, cada uno con su imagen y descripción, manteniendo el orden."""
        self.client.force_login(self.tutor_user)

        response = self.client.post(
            reverse("tareas:crear_tarea"),
            {
                "nombre": "Hacer la cama",
                "descripcion": "Estirar bien las sábanas",
                "ambito": Ambito.CASA,
                "descripcion_imagen": "Cama hecha",
                "imagen": self._crear_imagen_prueba("principal.jpg"),
                "pasos-TOTAL_FORMS": "2",
                "pasos-INITIAL_FORMS": "0",
                "pasos-MIN_NUM_FORMS": "0",
                "pasos-MAX_NUM_FORMS": "1000",
                "pasos-0-orden": "1",
                "pasos-0-descripcion": "Estirar sábana bajera",
                "pasos-0-descripcion_imagen": "Sábana bajera",
                "pasos-0-imagen": self._crear_imagen_prueba("paso1.jpg"),
                "pasos-1-orden": "2",
                "pasos-1-descripcion": "Colocar la almohada",
                "pasos-1-descripcion_imagen": "Almohada colocada",
                "pasos-1-imagen": self._crear_imagen_prueba("paso2.jpg"),
            },
        )

        self.assertEqual(response.status_code, 302)
        tarea = Tarea.objects.get(nombre="Hacer la cama")

        pasos = tarea.pasos.all()
        self.assertEqual(pasos.count(), 2)
        self.assertEqual(pasos[0].orden, 1)
        self.assertEqual(pasos[0].descripcion, "Estirar sábana bajera")
        self.assertEqual(pasos[1].orden, 2)
        self.assertEqual(pasos[1].descripcion, "Colocar la almohada")

    def test_creacion_paso_con_arasaac(self):
        """Un paso con un pictograma de ARASAAC en lugar de imagen física se guarda con éxito."""
        self.client.force_login(self.tutor_user)

        response = self.client.post(
            reverse("tareas:crear_tarea"),
            {
                "nombre": "Lavarse las manos",
                "descripcion": "Usar jabón",
                "ambito": Ambito.CASA,
                "descripcion_imagen": "Lavado",
                "imagen": self._crear_imagen_prueba("principal.jpg"),
                "pasos-TOTAL_FORMS": "1",
                "pasos-INITIAL_FORMS": "0",
                "pasos-MIN_NUM_FORMS": "0",
                "pasos-MAX_NUM_FORMS": "1000",
                "pasos-0-orden": "1",
                "pasos-0-descripcion": "Enjabonar las manos",
                "pasos-0-descripcion_imagen": "Manos con jabón",
                "pasos-0-arasaac_id_paso": "67890",
            },
        )
        self.assertEqual(response.status_code, 302)
        tarea = Tarea.objects.get(nombre="Lavarse las manos")
        self.assertEqual(tarea.pasos.count(), 1)
        self.assertEqual(tarea.pasos.first().descripcion, "Enjabonar las manos")
        self.assertEqual(tarea.pasos.first().imagen.name, "pictogramas/67890.png")

    def test_clasificacion_por_ambito(self):
        """Comprobamos que se puede clasificar la tarea por su ámbito (escolar, ocio, casa)."""
        self.client.force_login(self.tutor_user)

        for ambito_val, _ in Ambito.choices:
            response = self.client.post(
                reverse("tareas:crear_tarea"),
                {
                    "nombre": f"Tarea de {ambito_val}",
                    "descripcion": "Prueba de ámbito",
                    "ambito": ambito_val,
                    "descripcion_imagen": "Pictograma",
                    "imagen": self._crear_imagen_prueba(f"{ambito_val}.jpg"),
                    "pasos-TOTAL_FORMS": "0",
                    "pasos-INITIAL_FORMS": "0",
                    "pasos-MIN_NUM_FORMS": "0",
                    "pasos-MAX_NUM_FORMS": "1000",
                },
            )
            self.assertEqual(response.status_code, 302)
            self.assertTrue(
                Tarea.objects.filter(nombre=f"Tarea de {ambito_val}", ambito=ambito_val).exists()
            )
