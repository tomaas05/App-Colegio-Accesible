"""Ejecución de tareas: realización de una asignación en un día concreto.

Diseño: docs/iteracion-1/base-datos/ (relacional.md y diccionario.md).
Dueño: Tomás.

La tarea y el estudiante se obtienen a través de la asignación
(ejecucion.asignacion.tarea / .estudiante) para no guardar el dato dos veces.
Las transiciones de estado de RF2.3.1 se implementan en las HU, no aquí.
"""

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from apps.tareas.models import Asignacion, Paso, Tarea


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
    # HU-07-04 (RF2.15.1, RF2.15.2): la tarea no se pudo hacer. Quién y cuándo lo dijo, por
    # qué (solo si lo marca un adulto) y, si eligió una, la actividad del plan B que la
    # sustituye ese día. Con plan B la ejecución vuelve a «pendiente», ahora de la otra.
    no_realizable_el = models.DateTimeField("no se pudo hacer desde", null=True, blank=True)
    no_realizable_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="lo marcó",
    )
    motivo = models.CharField(max_length=200, blank=True)
    plan_b = models.ForeignKey(
        Tarea,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="actividad del plan B",
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
            models.CheckConstraint(
                condition=Q(plan_b__isnull=True) | Q(no_realizable_el__isnull=False),
                name="ejecucion_plan_b_tras_no_realizable",
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
