"""Pruebas de las reglas del diccionario de datos que garantiza la base de datos.

No prueban ninguna HU: comprueban que las restricciones de
docs/iteracion-1/base-datos/diccionario.md están de verdad en PostgreSQL.
"""

from datetime import time, timedelta

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.agenda.models import Ejecucion
from apps.horario.models import Asignatura, Franja, HorarioClase
from apps.perfil.models import Perfil
from apps.tareas.models import Asignacion, Paso, Tarea
from apps.usuarios.models import Atencion, Clase, Estudiante, Rol, Usuario


def falla_en_bd(funcion):
    """True si la base de datos rechaza la operación."""
    try:
        with transaction.atomic():
            funcion()
    except IntegrityError:
        return True
    return False


# --------------------------------------------------------------- datos de prueba
def test_datos_de_prueba_cargan_y_no_se_duplican(datos):
    from apps.usuarios.models import ImagenAcceso

    assert Usuario.objects.filter(rol=Rol.ESTUDIANTE).count() == 9
    assert ImagenAcceso.objects.count() == 12
    assert Tarea.objects.count() == 5
    call_command("cargar_datos_prueba", verbosity=0)  # segunda vez: no hace nada
    assert Tarea.objects.count() == 5


def test_reiniciar_vuelve_a_cargar(datos):
    Tarea.objects.filter(nombre="Leer un cuento").delete()
    call_command("cargar_datos_prueba", reiniciar=True, verbosity=0)
    assert Tarea.objects.filter(nombre="Leer un cuento").exists()


# --------------------------------------------------------------------- usuarios
def test_cada_estudiante_tiene_perfil_por_defecto(datos):
    assert Perfil.objects.count() == Estudiante.objects.count()
    martina = Estudiante.objects.get(codigo_estudiante="A05").perfil
    assert (martina.tema, martina.max_tarjetas, martina.tamano_botones) == ("claro", 6, 48)


def test_contrasena_de_imagenes_sin_orden(datos):
    from apps.usuarios.acceso import comprobar_contrasena_imagenes
    from apps.usuarios.models import ImagenAcceso

    lucia = Estudiante.objects.get(codigo_estudiante="A01").usuario
    ids = {i.descripcion_imagen: i.pk for i in ImagenAcceso.objects.all()}
    assert comprobar_contrasena_imagenes(lucia, [ids["flor"], ids["perro"], ids["sol"]])
    assert comprobar_contrasena_imagenes(lucia, [ids["sol"], ids["flor"], ids["perro"]])
    assert not comprobar_contrasena_imagenes(lucia, [ids["gato"], ids["perro"], ids["sol"]])
    assert not comprobar_contrasena_imagenes(lucia, [ids["perro"], ids["sol"]])  # solo 2
    assert "imagenes:" not in lucia.password  # la combinación nunca se guarda en claro


def test_mateo_entra_con_contrasena_de_texto(datos):
    mateo = Estudiante.objects.get(codigo_estudiante="A02")
    assert mateo.perfil.metodo_acceso == "contrasena"
    assert mateo.usuario.check_password("mateo2026")


def test_metodo_de_acceso_por_defecto_imagenes(datos):
    assert Estudiante.objects.get(codigo_estudiante="A05").perfil.metodo_acceso == "imagenes"


@pytest.mark.parametrize(
    "modelo",
    ["apps.tareas.models.Tarea", "apps.tareas.models.Paso", "apps.horario.models.Asignatura"],
)
def test_imagen_sin_descripcion_rechazada(datos, modelo):
    """Lector de pantalla: toda imagen tiene que tener su descripción."""
    from django.utils.module_loading import import_string

    objeto = import_string(modelo).objects.first()
    objeto.descripcion_imagen = ""
    assert falla_en_bd(objeto.save)


def test_clase_con_imagen_sin_descripcion_rechazada(datos):
    clase = Clase.objects.first()
    clase.descripcion_imagen = ""
    assert falla_en_bd(clase.save)


def test_rol_invalido_rechazado(db):
    assert falla_en_bd(lambda: Usuario.objects.create(username="x", first_name="X", rol="otro"))


def test_tutor_sin_fecha_de_alta_rechazado(datos):
    estudiante = Estudiante.objects.get(codigo_estudiante="A02")
    estudiante.fecha_alta_tutor = None
    assert falla_en_bd(estudiante.save)


def test_tutor_con_rol_equivocado_no_valida(datos):
    estudiante = Estudiante.objects.get(codigo_estudiante="A02")
    estudiante.tutor = Usuario.objects.get(username="familiar")
    with pytest.raises(ValidationError):
        estudiante.full_clean()


def test_atencion_repetida_rechazada(datos):
    atencion = Atencion.objects.first()
    assert falla_en_bd(
        lambda: Atencion.objects.create(
            profesional=atencion.profesional, estudiante=atencion.estudiante
        )
    )


def test_clase_repetida_en_el_mismo_curso_rechazada(datos):
    assert falla_en_bd(lambda: Clase.objects.create(nombre="PTVAL 1", curso_escolar="2026-2027"))


def test_borrar_estudiante_borra_sus_datos(datos):
    """RNF1.1.5: al eliminar un estudiante se borran su agenda y sus ejecuciones."""
    lucia = Estudiante.objects.get(codigo_estudiante="A01")
    lucia.usuario.delete()
    assert not Asignacion.objects.filter(estudiante_id=lucia.pk).exists()
    assert not Ejecucion.objects.filter(asignacion__estudiante_id=lucia.pk).exists()
    assert not Perfil.objects.filter(estudiante_id=lucia.pk).exists()


def test_no_se_borra_tutor_con_estudiantes(datos):
    from django.db.models import ProtectedError

    with pytest.raises(ProtectedError):
        Usuario.objects.get(username="tutor").delete()


# ---------------------------------------------------------------------- horario
def test_dos_asignaturas_en_la_misma_franja_rechazadas(datos):
    casilla = HorarioClase.objects.first()
    otra = Asignatura.objects.exclude(pk=casilla.asignatura_id).first()
    assert falla_en_bd(
        lambda: HorarioClase.objects.create(
            clase=casilla.clase,
            dia_semana=casilla.dia_semana,
            franja=casilla.franja,
            asignatura=otra,
        )
    )


def test_horario_solo_dias_lectivos(datos):
    casilla = HorarioClase.objects.first()
    casilla.dia_semana = 6
    assert falla_en_bd(casilla.save)


def test_franja_que_termina_antes_de_empezar_rechazada(db):
    assert falla_en_bd(
        lambda: Franja.objects.create(orden=9, hora_inicio=time(10), hora_fin=time(9))
    )


def test_franja_solapada_no_valida(datos):
    franja = Franja(orden=9, hora_inicio=time(9, 30), hora_fin=time(10, 30))
    with pytest.raises(ValidationError):
        franja.full_clean()


# ----------------------------------------------------------------------- tareas
def test_orden_de_paso_repetido_rechazado(datos):
    paso = Paso.objects.first()
    assert falla_en_bd(
        lambda: Paso.objects.create(tarea=paso.tarea, orden=paso.orden, imagen="x.png")
    )


@pytest.mark.parametrize(
    "cambios",
    [
        {"hora_inicio": time(10), "hora_fin": time(9)},  # fin antes del inicio
        {"dias_semana": []},  # sin días
        {"dias_semana": [1, 8]},  # día inexistente
        {"vigencia_hasta": timezone.localdate() - timedelta(days=30)},  # hasta antes de desde
    ],
)
def test_asignacion_incoherente_rechazada(datos, cambios):
    asignacion = Asignacion.objects.first()
    for campo, valor in cambios.items():
        setattr(asignacion, campo, valor)
    assert falla_en_bd(asignacion.save)


def test_asignacion_aplica_segun_dia_y_vigencia(datos):
    asignacion = Asignacion.objects.first()
    hoy = timezone.localdate()
    assert asignacion.aplica_el(hoy)
    asignacion.vigencia_hasta = hoy - timedelta(days=1)
    assert not asignacion.aplica_el(hoy)


# ----------------------------------------------------------------------- agenda
def test_una_ejecucion_por_asignacion_y_dia(datos):
    ejecucion = Ejecucion.objects.first()
    assert falla_en_bd(
        lambda: Ejecucion.objects.create(asignacion=ejecucion.asignacion, fecha=ejecucion.fecha)
    )


def test_ejecucion_que_termina_antes_de_empezar_rechazada(datos):
    ejecucion = Ejecucion.objects.exclude(inicio_real=None).first()
    ejecucion.fin_real = ejecucion.inicio_real - timedelta(minutes=5)
    assert falla_en_bd(ejecucion.save)
