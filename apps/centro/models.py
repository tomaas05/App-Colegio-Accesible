"""Tareas del centro (Objetivo 5). Dueño: Javi.

HU-05-03 (AGENDA-270): el administrador asigna a un estudiante el comedor de un día o el
reparto del menú de un mes.

- TareaDelCentro: la tarea del catálogo (apps.tareas.Tarea) que corresponde a cada tipo
  de tarea del centro («Comedor», «Reparto del menú»). Se crea sola la primera vez.
- ComedorDelDia y RepartoMenu: quién se encarga de cada día y de cada mes. Apuntan a la
  Asignacion (Úrsula) que pone la tarea en la agenda del estudiante con su horario; así
  sale en su agenda como cualquier otra tarea, sin tocar la agenda de Tomás. El
  estudiante y las horas se leen de la asignación, para no guardarlos dos veces.

Si se borra la asignación (por ejemplo, al eliminar al estudiante, HU-01-03), el día o
el mes vuelve a quedar «pendiente de asignar».
"""

from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Q

from apps.tareas.models import Asignacion, Tarea

# Formatos del menú del mes: PDF o imagen.
EXTENSIONES_MENU = ["pdf", "png", "jpg", "jpeg", "webp"]


class TipoTareaCentro(models.TextChoices):
    COMEDOR = "comedor", "Comedor"
    REPARTO_MENU = "reparto_menu", "Reparto del menú"


class TareaDelCentro(models.Model):
    """La tarea del catálogo de cada tipo de tarea del centro (una por tipo)."""

    tipo = models.CharField(max_length=20, choices=TipoTareaCentro.choices, unique=True)
    tarea = models.OneToOneField(Tarea, on_delete=models.CASCADE, related_name="del_centro")

    class Meta:
        verbose_name = "tarea del centro"
        verbose_name_plural = "tareas del centro"
        constraints = [
            models.CheckConstraint(
                condition=Q(tipo__in=TipoTareaCentro.values), name="tarea_centro_tipo_valido"
            ),
        ]

    def __str__(self):
        return self.get_tipo_display()


class ComedorDelDia(models.Model):
    """El estudiante encargado del comedor un día (RF5.2.1). Uno por día."""

    fecha = models.DateField(unique=True)
    asignacion = models.OneToOneField(
        Asignacion, on_delete=models.CASCADE, related_name="comedor_del_dia"
    )

    class Meta:
        verbose_name = "comedor del día"
        verbose_name_plural = "comedor de cada día"
        ordering = ["fecha"]
        constraints = [
            # Solo de lunes a viernes (en PostgreSQL, «week_day» va de 1 = domingo a 7 = sábado).
            models.CheckConstraint(
                condition=Q(fecha__week_day__range=(2, 6)), name="comedor_dia_lectivo"
            ),
        ]

    def __str__(self):
        return f"Comedor del {self.fecha:%d/%m/%Y}: {self.asignacion.estudiante}"


class RepartoMenu(models.Model):
    """El reparto del menú de un mes (RF5.3.1): quién lo reparte y el menú. Uno por mes.

    `asignacion` vacía = pendiente de asignar. Así el menú del mes se puede subir antes
    de elegir al estudiante y no se pierde al cambiarlo. El familiar ve el menú en el
    día del estudiante (HU-06-03, Manu): ver `menu_del_mes` en servicios.py.
    """

    mes = models.DateField(unique=True, help_text="Siempre el día 1 del mes")
    asignacion = models.OneToOneField(
        Asignacion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reparto_menu",
    )
    menu = models.FileField(
        "menú del mes",
        upload_to="menus/",
        blank=True,
        validators=[FileExtensionValidator(EXTENSIONES_MENU)],
        help_text="PDF o imagen con el menú del comedor de ese mes (opcional).",
    )

    class Meta:
        verbose_name = "reparto del menú"
        verbose_name_plural = "reparto del menú de cada mes"
        ordering = ["mes"]
        constraints = [
            models.CheckConstraint(condition=Q(mes__day=1), name="reparto_menu_dia_1"),
        ]

    def __str__(self):
        quien = self.asignacion.estudiante if self.asignacion else "pendiente de asignar"
        return f"Reparto del menú de {self.mes:%m/%Y}: {quien}"
