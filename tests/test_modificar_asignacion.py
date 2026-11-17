from datetime import date, time

from django.test import TestCase
from django.urls import reverse

from apps.comun.models import Notificacion
from apps.horario.models import Clase
from apps.tareas.models import Ambito, Asignacion, DiaSemana, Tarea
from apps.usuarios.models import Estudiante, Rol, Usuario


class ModificarAsignacionTestCase(TestCase):
    def setUp(self):
        # Obtenemos o creamos una clase para el estudiante
        self.clase_1, _ = Clase.objects.get_or_create(nombre="Aula 1A")

        # Crear tutor y estudiante
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
        self.estudiante = Estudiante.objects.create(
            usuario=self.user_estudiante,
            codigo_estudiante="EST001",
            clase=self.clase_1,
        )

        # Crear tarea y asignación inicial cumpliendo los constraints del modelo
        self.tarea = Tarea.objects.create(
            nombre="Preparar la mochila",
            descripcion_imagen="Icono de una mochila escolar",
            creador=self.user_tutor,
            ambito=Ambito.ESCOLAR,
        )
        self.asignacion = Asignacion.objects.create(
            tarea=self.tarea,
            estudiante=self.estudiante,
            asignado_por=self.user_tutor,
            hora_inicio=time(9, 0),
            hora_fin=time(9, 15),
            dias_semana=[DiaSemana.LUNES],
            vigencia_desde=date(2026, 1, 1),
        )

        self.client.login(username="tutor1", password="password123")
        self.url_editar = reverse(
            "tareas:editar_asignacion",
            args=[self.asignacion.id],
        )

    def test_cambio_hora_actualiza_agenda(self):
        """Prueba 1: Cambio la hora de una tarea y se actualiza."""
        datos_post = {
            "hora_inicio": "10:00",
            "hora_fin": "10:30",
            "dias_semana": [str(DiaSemana.LUNES)],
            "vigencia_desde": "2026-01-01",
        }
        response = self.client.post(self.url_editar, data=datos_post)
        self.assertRedirects(response, reverse("tareas:tareas_planificadas"))

        self.asignacion.refresh_from_db()
        self.assertEqual(self.asignacion.hora_inicio, time(10, 0))
        self.assertEqual(self.asignacion.hora_fin, time(10, 30))

    def test_cambio_genera_solapamiento_se_rechaza(self):
        """Prueba 2: Un cambio que genera solapamiento se rechaza."""
        Asignacion.objects.create(
            tarea=self.tarea,
            estudiante=self.estudiante,
            asignado_por=self.user_tutor,
            hora_inicio=time(11, 0),
            hora_fin=time(12, 0),
            dias_semana=[DiaSemana.LUNES],
            vigencia_desde=date(2026, 1, 1),
        )

        datos_post = {
            "hora_inicio": "11:30",
            "hora_fin": "12:30",
            "dias_semana": [str(DiaSemana.LUNES)],
            "vigencia_desde": "2026-01-01",
        }
        response = self.client.post(self.url_editar, data=datos_post)

        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertTrue(form.errors)

    def test_estudiante_recibe_aviso_del_cambio(self):
        """Prueba 3: Se genera la notificación en BD tras modificar la tarea."""
        datos_post = {
            "hora_inicio": "09:30",
            "hora_fin": "09:45",
            "dias_semana": [str(DiaSemana.LUNES)],
            "vigencia_desde": "2026-01-01",
        }
        response = self.client.post(self.url_editar, data=datos_post)
        self.assertRedirects(response, reverse("tareas:tareas_planificadas"))

        notif = Notificacion.objects.filter(destinatario=self.user_estudiante).first()
        self.assertIsNotNone(notif)
        self.assertIn("actualizado", notif.mensaje.lower())

    def test_horario_invalido_fin_anterior_inicio(self):
        """Prueba adicional: Horario con fin anterior al inicio."""
        datos_post = {
            "hora_inicio": "10:30",
            "hora_fin": "10:00",
            "dias_semana": [str(DiaSemana.LUNES)],
            "vigencia_desde": "2026-01-01",
        }
        response = self.client.post(self.url_editar, data=datos_post)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    def test_vigencia_incoherente_se_rechaza(self):
        """Prueba adicional: Vigencia hasta anterior a desde."""
        datos_post = {
            "hora_inicio": "10:00",
            "hora_fin": "10:30",
            "dias_semana": [str(DiaSemana.LUNES)],
            "vigencia_desde": "2026-06-01",
            "vigencia_hasta": "2026-01-01",
        }
        response = self.client.post(self.url_editar, data=datos_post)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
