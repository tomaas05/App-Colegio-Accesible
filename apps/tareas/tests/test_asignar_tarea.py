from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.tareas.models import Asignacion, Tarea
from apps.usuarios.models import Clase, Estudiante

Usuario = get_user_model()


class AsignacionTareaTests(TestCase):
    def setUp(self):
        # Creamos un usuario tutor compatible con el modelo del proyecto
        self.tutor_user = Usuario(
            username="tutor_test",
            first_name="Tutor",
            last_name="Prueba",
            rol="tutor",
        )
        self.tutor_user.set_password("despega2026")
        self.tutor_user.save()

        self.clase = Clase.objects.create(nombre="PTVAL 1", curso_escolar="2026-2027")

        self.usuario_estudiante1 = Usuario.objects.create_user(
            username="est_1",
            first_name="Lucía",
            last_name="Prueba",
            rol="estudiante",
            password="password",
        )
        self.estudiante1 = Estudiante.objects.create(
            usuario=self.usuario_estudiante1,
            codigo_estudiante="est_1",
            clase=self.clase,
            avatar="perro.png",
        )

        self.usuario_estudiante2 = Usuario.objects.create_user(
            username="est_2",
            first_name="Mateo",
            last_name="Prueba",
            rol="estudiante",
            password="password",
        )
        self.estudiante2 = Estudiante.objects.create(
            usuario=self.usuario_estudiante2,
            codigo_estudiante="est_2",
            clase=self.clase,
            avatar="sol.png",
        )

        self.tarea = Tarea.objects.create(
            nombre="Matemáticas Básicas",
            descripcion="Hacer sumas",
            ambito="escolar",
            creador=self.tutor_user,
            descripcion_imagen="Libro de matemáticas",
            imagen="matematicas.png",
        )

    def test_asignacion_correcta_individual(self):
        """Asigno una tarea a un estudiante en un día y horario correcto."""
        self.client.force_login(self.tutor_user)
        response = self.client.post(
            reverse("tareas:asignar_tarea"),
            {
                "tarea": self.tarea.id,
                "estudiantes": [self.estudiante1.pk],
                "hora_inicio": "09:00",
                "hora_fin": "10:00",
                "dias_semana": ["1"],  # 1 = Lunes
                "vigencia_desde": date.today().isoformat(),
                "vigencia_hasta": date.today().isoformat(),
            },
        )
        self.assertEqual(response.status_code, 302)  # Redirección tras éxito
        self.assertTrue(
            Asignacion.objects.filter(estudiante=self.estudiante1, tarea=self.tarea).exists()
        )

    def test_asignacion_masiva_grupo(self):
        """Asigno la misma tarea a un grupo de estudiantes a la vez."""
        self.client.force_login(self.tutor_user)
        response = self.client.post(
            reverse("tareas:asignar_tarea"),
            {
                "tarea": self.tarea.id,
                "estudiantes": [self.estudiante1.pk, self.estudiante2.pk],
                "hora_inicio": "10:00",
                "hora_fin": "11:00",
                "dias_semana": ["2"],  # 2 = Martes
                "vigencia_desde": date.today().isoformat(),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Asignacion.objects.filter(tarea=self.tarea).count(), 2)

    def test_error_hora_fin_anterior(self):
        """Una tarea cuya hora de fin es anterior o igual a la de inicio no se guarda."""
        self.client.force_login(self.tutor_user)
        response = self.client.post(
            reverse("tareas:asignar_tarea"),
            {
                "tarea": self.tarea.id,
                "estudiantes": [self.estudiante1.pk],
                "hora_inicio": "11:00",
                "hora_fin": "10:00",  # Anterior
                "dias_semana": ["3"],  # 3 = Miércoles
                "vigencia_desde": date.today().isoformat(),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "La hora de fin no puede ser anterior o igual a la hora de inicio."
        )

    def test_error_sin_estudiantes_seleccionados(self):
        """Intentar asignar una tarea sin marcar ningún estudiante muestra error de validación."""
        self.client.force_login(self.tutor_user)
        response = self.client.post(
            reverse("tareas:asignar_tarea"),
            {
                "tarea": self.tarea.id,
                "estudiantes": [],  # Vacío (incorrecto)
                "hora_inicio": "09:00",
                "hora_fin": "10:00",
                "dias_semana": ["1"],
                "vigencia_desde": date.today().isoformat(),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Asignacion.objects.filter(tarea=self.tarea).exists())

    def test_error_vigencia_hasta_anterior(self):
        """Una fecha de fin de vigencia anterior a la fecha de inicio no se guarda."""
        self.client.force_login(self.tutor_user)
        hoy = date.today()
        ayer = hoy.replace(day=hoy.day - 1) if hoy.day > 1 else hoy

        response = self.client.post(
            reverse("tareas:asignar_tarea"),
            {
                "tarea": self.tarea.id,
                "estudiantes": [self.estudiante1.pk],
                "hora_inicio": "09:00",
                "hora_fin": "10:00",
                "dias_semana": ["1"],
                "vigencia_desde": hoy.isoformat(),
                "vigencia_hasta": ayer.isoformat(),  # Anterior a vigencia_desde
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Asignacion.objects.filter(estudiante=self.estudiante1, tarea=self.tarea).exists()
        )

    def test_error_solape_horario(self):
        """Si la tarea se solapa con otra existente, no se guarda y se indica el error."""
        # Creamos una primera asignación previa
        Asignacion.objects.create(
            tarea=self.tarea,
            estudiante=self.estudiante1,
            asignado_por=self.tutor_user,
            hora_inicio=time(9, 0),
            hora_fin=time(10, 0),
            dias_semana=[1],  # 1 = Lunes
            vigencia_desde=date.today(),
        )

        self.client.force_login(self.tutor_user)
        # Intentamos asignar otra tarea cruzando el horario (09:30 a 10:30) el mismo día
        response = self.client.post(
            reverse("tareas:asignar_tarea"),
            {
                "tarea": self.tarea.id,
                "estudiantes": [self.estudiante1.pk],
                "hora_inicio": "09:30",
                "hora_fin": "10:30",
                "dias_semana": ["1"],  # 1 = Lunes
                "vigencia_desde": date.today().isoformat(),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f"El estudiante {self.estudiante1} ya tiene una tarea asignada "
            f"en ese horario y día ({self.tarea.nombre}).",
        )

    def test_asignacion_sin_solape_diferente_dia(self):
        """Un solape de horas pero en días distintos de la semana SÍ se permite correctamente."""
        # Asignación previa el Lunes (día 1)
        Asignacion.objects.create(
            tarea=self.tarea,
            estudiante=self.estudiante1,
            asignado_por=self.tutor_user,
            hora_inicio=time(9, 0),
            hora_fin=time(10, 0),
            dias_semana=[1],
            vigencia_desde=date.today(),
        )

        self.client.force_login(self.tutor_user)
        # Intentamos asignar el mismo horario pero el Martes (día 2)
        response = self.client.post(
            reverse("tareas:asignar_tarea"),
            {
                "tarea": self.tarea.id,
                "estudiantes": [self.estudiante1.pk],
                "hora_inicio": "09:00",
                "hora_fin": "10:00",
                "dias_semana": ["2"],  # Martes (no choca con el lunes)
                "vigencia_desde": date.today().isoformat(),
            },
        )
        self.assertEqual(response.status_code, 302)  # Debe guardarse con éxito
        self.assertEqual(Asignacion.objects.filter(estudiante=self.estudiante1).count(), 2)
