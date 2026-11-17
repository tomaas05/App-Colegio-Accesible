from datetime import date, time

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.comun.models import Notificacion
from apps.horario.models import Clase
from apps.tareas.models import Ambito, Asignacion, DiaSemana, Tarea
from apps.usuarios.models import Estudiante, Rol, Usuario


class CancelarAsignacionTestCase(TestCase):
    def setUp(self):
        self.clase_1, _ = Clase.objects.get_or_create(nombre="Aula 1A")
        self.user_tutor = Usuario.objects.create_user(
            username="tutor1",
            password="password123",
            rol=Rol.TUTOR,
            first_name="Ana",
            last_name="Martín",
        )
        self.user_estudiante = Usuario.objects.create_user(
            username="estudiante1",
            password="password123",
            rol=Rol.ESTUDIANTE,
            first_name="Lucía",
            last_name="Fernández",
        )

        # Archivo dummy para evitar errores de ficheros nulos en plantillas
        archivo_ficticio = SimpleUploadedFile(
            "imagen.png", b"\x47\x49\x46\x38\x39\x61\x01\x00", content_type="image/png"
        )

        self.estudiante = Estudiante.objects.create(
            usuario=self.user_estudiante,
            codigo_estudiante="EST001",
            clase=self.clase_1,
            avatar=archivo_ficticio,
        )
        self.tarea = Tarea.objects.create(
            nombre="Imprimir apuntes de reprografía",
            descripcion_imagen="Icono de reprografía",
            creador=self.user_tutor,
            ambito=Ambito.ESCOLAR,
            imagen=archivo_ficticio,
        )
        self.asignacion = Asignacion.objects.create(
            tarea=self.tarea,
            estudiante=self.estudiante,
            asignado_por=self.user_tutor,
            hora_inicio=time(9, 0),
            hora_fin=time(9, 15),
            dias_semana=[DiaSemana.LUNES, DiaSemana.MARTES],
            vigencia_desde=date(2026, 1, 1),
        )
        self.client.login(username="tutor1", password="password123")
        self.url_cancelar = reverse(
            "tareas:confirmar_cancelacion",
            args=[self.asignacion.id],
        )

    def test_pide_confirmacion_en_get(self):
        """Prueba: Antes de cancelar, se pide confirmación."""
        response = self.client.get(self.url_cancelar)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tareas/confirmar_cancelacion.html")

    def test_cancela_tarea_toda_la_serie(self):
        """Prueba: Cancelo una tarea (toda la serie) y aparece como cancelada."""
        response = self.client.post(
            self.url_cancelar,
            data={"alcance": "serie"},
        )
        self.assertRedirects(response, reverse("tareas:tareas_planificadas"))

        self.asignacion.refresh_from_db()
        self.assertTrue(self.asignacion.cancelada)

    def test_cancela_solo_un_dia_de_la_tarea(self):
        """Prueba: Cancelo una tarea de
        reprografía que el estudiante aún
        no ha empezado (solo un día)."""
        response = self.client.post(
            self.url_cancelar,
            data={"alcance": "dia", "dia": str(DiaSemana.LUNES)},
        )
        self.assertRedirects(response, reverse("tareas:tareas_planificadas"))

        self.asignacion.refresh_from_db()
        # El lunes debe haberse eliminado, pero el martes debe seguir
        self.assertNotIn(DiaSemana.LUNES, self.asignacion.dias_semana)
        self.assertIn(DiaSemana.MARTES, self.asignacion.dias_semana)

    def test_aviso_al_estudiante_en_cancelacion(self):
        """Prueba: Se genera una notificación en BD para el estudiante al cancelar."""
        self.client.post(self.url_cancelar, data={"alcance": "serie"})

        notif = Notificacion.objects.filter(destinatario=self.user_estudiante).first()
        self.assertIsNotNone(notif)
        self.assertIn("cancelado", notif.mensaje.lower())

    def test_estudiante_ve_aviso_en_agenda_y_se_marca_leido(self):
        """Prueba: El estudiante ve el aviso en su agenda y al reentrar ya no sale."""
        Notificacion.objects.create(
            destinatario=self.user_estudiante, mensaje="Aviso de prueba por cancelación."
        )

        self.client.logout()
        self.client.login(username="estudiante1", password="password123")

        url_agenda = reverse("agenda:dia")
        response = self.client.get(url_agenda)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["aviso_reciente"])
        self.assertEqual(
            response.context["aviso_reciente"].mensaje, "Aviso de prueba por cancelación."
        )

        response_segunda = self.client.get(url_agenda)
        self.assertEqual(response_segunda.status_code, 200)
        self.assertIsNone(response_segunda.context["aviso_reciente"])
