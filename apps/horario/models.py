"""Horario escolar: franjas, asignaturas y talleres, y horario de cada clase (RI3.4).

Diseño: docs/iteracion-1/base-datos/relacional.md. Dueño: Javi.

- Franja: rejilla de horas común a todo el centro, igual de lunes a viernes.
- Asignatura: catálogo de asignaturas y talleres.
- HorarioClase: qué asignatura o taller tiene cada clase, cada día, en cada franja.
  La clave única (clase, día, franja) impide los solapes.
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from apps.usuarios.models import Clase


class DiaLectivo(models.IntegerChoices):
    LUNES = 1, "Lunes"
    MARTES = 2, "Martes"
    MIERCOLES = 3, "Miércoles"
    JUEVES = 4, "Jueves"
    VIERNES = 5, "Viernes"


class Franja(models.Model):
    orden = models.PositiveSmallIntegerField(unique=True)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    class Meta:
        verbose_name = "franja horaria"
        verbose_name_plural = "franjas horarias"
        ordering = ["orden"]
        constraints = [
            models.CheckConstraint(
                condition=Q(hora_fin__gt=F("hora_inicio")),
                name="franja_fin_posterior_inicio",
            ),
            models.CheckConstraint(condition=Q(orden__gt=0), name="franja_orden_positivo"),
        ]

    def __str__(self):
        return f"{self.orden}.ª ({self.hora_inicio:%H:%M}–{self.hora_fin:%H:%M})"

    def clean(self):
        if self.hora_inicio and self.hora_fin:
            solapadas = Franja.objects.filter(
                hora_inicio__lt=self.hora_fin, hora_fin__gt=self.hora_inicio
            ).exclude(pk=self.pk)
            if solapadas.exists():
                raise ValidationError(f"Se solapa con la franja {solapadas.first()}.")


class TipoAsignatura(models.TextChoices):
    ASIGNATURA = "asignatura", "Asignatura"
    TALLER = "taller", "Taller"


class Asignatura(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    tipo = models.CharField(
        max_length=15, choices=TipoAsignatura.choices, default=TipoAsignatura.ASIGNATURA
    )
    imagen = models.ImageField(upload_to="asignaturas/")
    descripcion_imagen = models.CharField("descripción de la imagen", max_length=150)

    class Meta:
        verbose_name = "asignatura o taller"
        verbose_name_plural = "asignaturas y talleres"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class HorarioClase(models.Model):
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name="horario")
    dia_semana = models.PositiveSmallIntegerField("día", choices=DiaLectivo.choices)
    franja = models.ForeignKey(Franja, on_delete=models.PROTECT, related_name="sesiones")
    asignatura = models.ForeignKey(Asignatura, on_delete=models.PROTECT, related_name="sesiones")

    class Meta:
        verbose_name = "casilla del horario"
        verbose_name_plural = "horario de las clases"
        ordering = ["clase", "dia_semana", "franja__orden"]
        constraints = [
            models.UniqueConstraint(
                fields=["clase", "dia_semana", "franja"], name="horario_una_cosa_por_franja"
            ),
            models.CheckConstraint(
                condition=Q(dia_semana__gte=1) & Q(dia_semana__lte=5),
                name="horario_dia_lectivo",
            ),
        ]

    def __str__(self):
        return f"{self.clase} · {self.get_dia_semana_display()} · {self.franja}: {self.asignatura}"
