"""Tareas: catálogo de tareas, sus pasos y sus asignaciones a estudiantes.

Diseño: docs/iteracion-1/base-datos/ (relacional.md y diccionario.md).
Dueña: Úrsula.

Los solapamientos entre asignaciones de un mismo estudiante dependen de varias
filas, así que no son una restricción de la base de datos: se comprueban en
planificacion.py (HU-03-03 y HU-03-04).
"""

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import F, Q

from apps.usuarios.models import Estudiante, Usuario


class Ambito(models.TextChoices):
    ESCOLAR = "escolar", "Escolar"
    OCIO = "ocio", "Ocio"
    CASA = "casa", "Casa"


class DiaSemana(models.IntegerChoices):
    LUNES = 1, "Lunes"
    MARTES = 2, "Martes"
    MIERCOLES = 3, "Miércoles"
    JUEVES = 4, "Jueves"
    VIERNES = 5, "Viernes"
    SABADO = 6, "Sábado"
    DOMINGO = 7, "Domingo"


class Tarea(models.Model):
    """Tarea del catálogo del centro (RI3.1.1). Sin fecha de creación ni estado."""

    nombre = models.CharField(max_length=80)
    descripcion = models.TextField("descripción", blank=True)
    imagen = models.ImageField(upload_to="tareas/")
    descripcion_imagen = models.CharField("descripción de la imagen", max_length=150)
    ambito = models.CharField(
        "ámbito", max_length=10, choices=Ambito.choices, default=Ambito.ESCOLAR
    )
    creador = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name="tareas_creadas")

    class Meta:
        verbose_name = "tarea"
        verbose_name_plural = "tareas"
        ordering = ["nombre"]
        constraints = [
            models.CheckConstraint(condition=~Q(nombre=""), name="tarea_nombre_no_vacio"),
            models.CheckConstraint(
                condition=~Q(descripcion_imagen=""), name="tarea_imagen_con_descripcion"
            ),
        ]

    def __str__(self):
        return self.nombre

    @property
    def alternativas(self):
        """Las actividades del plan B, en el orden en que se ofrecen (HU-03-06)."""
        return [p.alternativa for p in self.planes_b.select_related("alternativa")]


class PlanB(models.Model):
    """Una actividad alternativa de una tarea, con su prioridad (RI3.3.1, RF3.4.3).

    La primera (orden más bajo) es la que se ofrece antes al estudiante (HU-07-04).
    """

    tarea = models.ForeignKey(Tarea, on_delete=models.CASCADE, related_name="planes_b")
    alternativa = models.ForeignKey(
        Tarea, on_delete=models.CASCADE, related_name="es_plan_b_de", verbose_name="alternativa"
    )
    orden = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name = "plan B"
        verbose_name_plural = "planes B"
        ordering = ["tarea", "orden", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["tarea", "alternativa"], name="plan_b_sin_repetir"),
            models.CheckConstraint(
                condition=~Q(tarea=F("alternativa")), name="plan_b_no_es_la_misma"
            ),
            models.CheckConstraint(condition=Q(orden__gt=0), name="plan_b_orden_positivo"),
        ]

    def __str__(self):
        return f"{self.tarea} → {self.alternativa} ({self.orden})"


class Paso(models.Model):
    """Paso de una tarea (RI3.1.3). Entidad débil: orden único dentro de la tarea."""

    tarea = models.ForeignKey(Tarea, on_delete=models.CASCADE, related_name="pasos")
    orden = models.PositiveSmallIntegerField()
    imagen = models.ImageField(upload_to="pasos/")
    descripcion_imagen = models.CharField("descripción de la imagen", max_length=150)
    descripcion = models.TextField("descripción", blank=True)

    class Meta:
        verbose_name = "paso"
        verbose_name_plural = "pasos"
        ordering = ["tarea", "orden"]
        constraints = [
            models.UniqueConstraint(fields=["tarea", "orden"], name="paso_orden_unico"),
            models.CheckConstraint(condition=Q(orden__gt=0), name="paso_orden_positivo"),
            models.CheckConstraint(
                condition=~Q(descripcion_imagen=""), name="paso_imagen_con_descripcion"
            ),
        ]

    def __str__(self):
        return f"{self.tarea} · paso {self.orden}"


class Asignacion(models.Model):
    """Una tarea en la agenda de un estudiante, con su horario (RI3.2.1, RI3.2.2).

    Incluye los atributos de la antigua PROGRAMACIÓN.
    """

    tarea = models.ForeignKey(Tarea, on_delete=models.CASCADE, related_name="asignaciones")
    estudiante = models.ForeignKey(
        Estudiante, on_delete=models.CASCADE, related_name="asignaciones"
    )
    asignado_por = models.ForeignKey(
        Usuario, on_delete=models.PROTECT, related_name="asignaciones_hechas"
    )
    fecha_asignacion = models.DateTimeField("fecha de asignación", auto_now_add=True)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    dias_semana = ArrayField(
        models.PositiveSmallIntegerField(choices=DiaSemana.choices),
        verbose_name="días de la semana",
        help_text="1 = lunes … 7 = domingo",
    )
    vigencia_desde = models.DateField()
    vigencia_hasta = models.DateField(null=True, blank=True, help_text="Vacío = sin fecha de fin")
    # HU-03-05: cancelar toda la serie. Desde `cancelada_el` ya no se hace; esa semana el
    # estudiante la sigue viendo en su agenda, tachada como «Cancelada» (planificacion.py).
    cancelada = models.BooleanField(default=False, verbose_name="cancelada")
    cancelada_el = models.DateField("cancelada desde", null=True, blank=True)

    class Meta:
        verbose_name = "asignación"
        verbose_name_plural = "asignaciones"
        ordering = ["estudiante", "hora_inicio"]
        constraints = [
            models.CheckConstraint(
                condition=Q(hora_fin__gt=F("hora_inicio")),
                name="asignacion_fin_posterior_inicio",
            ),
            models.CheckConstraint(
                condition=Q(dias_semana__len__gt=0), name="asignacion_al_menos_un_dia"
            ),
            models.CheckConstraint(
                condition=Q(dias_semana__contained_by=DiaSemana.values),
                name="asignacion_dias_validos",
            ),
            models.CheckConstraint(
                condition=Q(vigencia_hasta__isnull=True)
                | Q(vigencia_hasta__gte=F("vigencia_desde")),
                name="asignacion_vigencia_coherente",
            ),
            models.CheckConstraint(
                condition=Q(cancelada=False) | Q(cancelada_el__isnull=False),
                name="asignacion_cancelada_con_fecha",
            ),
        ]

    def __str__(self):
        return f"{self.tarea} → {self.estudiante} ({self.hora_inicio:%H:%M}–{self.hora_fin:%H:%M})"

    def aplica_el(self, fecha):
        """True si la asignación toca en esa fecha (día de la semana y vigencia)."""
        if fecha.isoweekday() not in self.dias_semana:
            return False
        if fecha < self.vigencia_desde:
            return False
        return self.vigencia_hasta is None or fecha <= self.vigencia_hasta


class TipoExcepcion(models.TextChoices):
    MODIFICADA = "modificada", "Modificada"
    CANCELADA = "cancelada", "Cancelada"


class ExcepcionAsignacion(models.Model):
    """Un cambio de una asignación en una sola fecha (RI3.2.3, RF3.5.2).

    «Solo este día» en HU-03-04 (otras horas ese día) y HU-03-05 (ese día no se hace).
    El resto de la serie sigue igual.
    """

    asignacion = models.ForeignKey(Asignacion, on_delete=models.CASCADE, related_name="excepciones")
    fecha = models.DateField()
    tipo = models.CharField(max_length=10, choices=TipoExcepcion.choices)
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    creada_por = models.ForeignKey(
        Usuario, on_delete=models.PROTECT, related_name="excepciones_hechas"
    )
    creada_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "excepción de una asignación"
        verbose_name_plural = "excepciones de asignaciones"
        ordering = ["asignacion", "fecha"]
        constraints = [
            models.UniqueConstraint(fields=["asignacion", "fecha"], name="excepcion_una_por_dia"),
            models.CheckConstraint(
                condition=Q(tipo__in=TipoExcepcion.values), name="excepcion_tipo_valido"
            ),
            # Modificada: con sus horas nuevas y coherentes. Cancelada: sin horas.
            models.CheckConstraint(
                condition=(
                    Q(
                        tipo=TipoExcepcion.MODIFICADA,
                        hora_inicio__isnull=False,
                        hora_fin__gt=F("hora_inicio"),
                    )
                    | Q(
                        tipo=TipoExcepcion.CANCELADA,
                        hora_inicio__isnull=True,
                        hora_fin__isnull=True,
                    )
                ),
                name="excepcion_horas_coherentes",
            ),
        ]

    def __str__(self):
        return f"{self.asignacion} · {self.fecha:%d/%m/%Y} · {self.get_tipo_display()}"
