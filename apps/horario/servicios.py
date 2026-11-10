"""HU-03-11. Cargar el horario escolar de una clase (AGENDA-222). Dueño: Javi.

- El administrador pone en cada casilla (día y franja) de una clase una asignatura o
  taller del catálogo, o la quita (PA1). Las franjas son las mismas para todo el centro
  y todos los días (PA2): salen de la tabla Franja.
- Una casilla ocupada no se pisa: hay que quitarla antes (PA3). La base de datos lo
  impide además con la clave única (clase, día, franja).
- `choca_con_horario_escolar` dice si unas horas caen dentro del horario escolar: el
  familiar solo pone tareas para casa fuera de él (PA5).
"""

from dataclasses import dataclass

from django.db import IntegrityError, transaction

from .models import DiaLectivo, Franja, HorarioClase


class ErrorDeHorario(Exception):
    """Algo que no se puede guardar. El mensaje se enseña tal cual."""


@dataclass
class FilaHorario:
    franja: Franja
    casillas: list  # una por día lectivo: HorarioClase o None


def dias():
    return DiaLectivo.choices


def _texto_casilla(dia, franja):
    nombre_dia = DiaLectivo(dia).label.lower()
    return f"el {nombre_dia} de {franja.hora_inicio:%H:%M} a {franja.hora_fin:%H:%M}"


def rejilla(clase):
    """El horario de la clase: una fila por franja, una columna por día (lunes a viernes)."""
    casillas = {
        (c.dia_semana, c.franja_id): c
        for c in HorarioClase.objects.filter(clase=clase).select_related("asignatura")
    }
    return [
        FilaHorario(franja, [casillas.get((dia, franja.pk)) for dia, _ in dias()])
        for franja in Franja.objects.order_by("orden")
    ]


def del_dia(clase, dia):
    """Las casillas de un día de la clase, por orden de franja."""
    return (
        HorarioClase.objects.filter(clase=clase, dia_semana=dia)
        .select_related("franja", "asignatura")
        .order_by("franja__orden")
    )


def poner(clase, dia, franja, asignatura):
    """PA1 y PA3: pone la asignatura en la casilla; si ya hay otra, no guarda y lo dice."""
    ocupada = (
        HorarioClase.objects.filter(clase=clase, dia_semana=dia, franja=franja)
        .select_related("asignatura")
        .first()
    )
    if ocupada:
        raise ErrorDeHorario(
            f"No se ha guardado: {_texto_casilla(dia, franja)} {clase.nombre} ya tiene "
            f"«{ocupada.asignatura.nombre}». Quítala antes de poner otra."
        )
    try:
        with transaction.atomic():
            return HorarioClase.objects.create(
                clase=clase, dia_semana=dia, franja=franja, asignatura=asignatura
            )
    except IntegrityError:
        # Otra persona la ha ocupado a la vez: la clave única lo para.
        raise ErrorDeHorario(
            f"No se ha guardado: {_texto_casilla(dia, franja)} ya está ocupada."
        ) from None


def quitar(clase, dia, franja):
    """Deja libre la casilla. Devuelve la asignatura que había (o None)."""
    casilla = (
        HorarioClase.objects.filter(clase=clase, dia_semana=dia, franja=franja)
        .select_related("asignatura")
        .first()
    )
    if casilla is None:
        return None
    casilla.delete()
    return casilla.asignatura


def choca_con_horario_escolar(dias_semana, hora_inicio, hora_fin):
    """PA5: ¿se solapan esas horas, algún día lectivo, con alguna franja del centro?

    Las franjas son iguales para todo el centro, así que no depende de la clase.
    """
    if not any(1 <= int(d) <= 5 for d in dias_semana):
        return False
    return Franja.objects.filter(hora_inicio__lt=hora_fin, hora_fin__gt=hora_inicio).exists()


def texto_de(casilla):
    return f"{casilla.asignatura.nombre} {_texto_casilla(casilla.dia_semana, casilla.franja)}"
