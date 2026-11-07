"""Ejecución de tareas: realización de una asignación en un día concreto.

Diseño: docs/iteracion-1/base-datos/ (relacional.md y diccionario.md).
Dueño: Tomás.

La tarea y el estudiante se obtienen a través de la asignación
(ejecucion.asignacion.tarea / .estudiante) para no guardar el dato dos veces.
Las transiciones de estado de RF2.3.1 se implementan en las HU, no aquí.
"""

from django.db import models
from django.db.models import F, Q

from apps.tareas.models import Asignacion, Paso


class EstadoEjecucion(models.TextChoices):
    PENDIENTE = "pendiente", "Pendiente"
    EN_CURSO = "en_curso", "En curso"
    TIEMPO_AGOTADO = "tiempo_agotado", "Tiempo agotado"
    HECHA = "hecha", "Hecha"
    VENCIDA = "vencida", "Vencida"
    CANCELADA = "cancelada", "Cancelada"
    NO_REALIZABLE = "no_realizable", "No realizable"


class EstadoPaso(models.TextChoices):
    PENDIENTE = "pendiente", "Pendiente"
    HECHO = "hecho", "Hecho"


class Ejecucion(models.Model):
    """RI2.1.1. Una por asignación y día."""

    asignacion = models.ForeignKey(Asignacion, on_delete=models.CASCADE, related_name="ejecuciones")
    fecha = models.DateField()
    inicio_real = models.DateTimeField(null=True, blank=True)
    fin_real = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(
        max_length=20, choices=EstadoEjecucion.choices, default=EstadoEjecucion.PENDIENTE
    )

    class Meta:
        verbose_name = "ejecución"
        verbose_name_plural = "ejecuciones"
        ordering = ["-fecha", "asignacion__hora_inicio"]
        constraints = [
            models.UniqueConstraint(fields=["asignacion", "fecha"], name="ejecucion_una_por_dia"),
            models.CheckConstraint(
                condition=Q(fin_real__isnull=True)
                | Q(inicio_real__isnull=True)
                | Q(fin_real__gte=F("inicio_real")),
                name="ejecucion_fin_posterior_inicio",
            ),
            models.CheckConstraint(
                condition=Q(estado__in=EstadoEjecucion.values), name="ejecucion_estado_valido"
            ),
        ]

    def __str__(self):
        return f"{self.asignacion.tarea} · {self.asignacion.estudiante} · {self.fecha}"


class EjecucionPaso(models.Model):
    """Relación «avanza» (RI2.1.2): estado de cada paso en una ejecución."""

    ejecucion = models.ForeignKey(Ejecucion, on_delete=models.CASCADE, related_name="pasos")
    paso = models.ForeignKey(Paso, on_delete=models.CASCADE, related_name="ejecuciones")
    estado = models.CharField(
        max_length=10, choices=EstadoPaso.choices, default=EstadoPaso.PENDIENTE
    )

    class Meta:
        verbose_name = "avance de paso"
        verbose_name_plural = "avance de pasos"
        ordering = ["ejecucion", "paso__orden"]
        constraints = [
            models.UniqueConstraint(fields=["ejecucion", "paso"], name="ejecucion_paso_unico"),
        ]

    def __str__(self):
        return f"{self.paso} · {self.get_estado_display()}"
