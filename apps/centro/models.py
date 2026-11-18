"""Tareas del centro (Objetivo 5). Dueño: Javi.

HU-05-03 (AGENDA-270): el administrador asigna a un estudiante el comedor de un día o el
reparto del menú de un mes.
HU-05-04 (AGENDA-276): el estudiante encargado del comedor anota quién come cada día
(AsistenciaComedor) y da por terminada cada clase (ClaseComedorTerminada).
HU-05-01 (AGENDA-260): el tutor o el administrador crea en la agenda de un estudiante una
tarea de reprografía con sus datos (TrabajoReprografia).

- TareaDelCentro: la tarea del catálogo (apps.tareas.Tarea) que corresponde a cada tipo
  de tarea del centro («Comedor», «Reparto del menú», «Reprografía»). Se crea sola la
  primera vez.
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
from apps.usuarios.models import Clase, Estudiante, Usuario

# Formatos del menú del mes: PDF o imagen.
EXTENSIONES_MENU = ["pdf", "png", "jpg", "jpeg", "webp"]


class TipoTareaCentro(models.TextChoices):
    COMEDOR = "comedor", "Comedor"
    REPARTO_MENU = "reparto_menu", "Reparto del menú"
    REPROGRAFIA = "reprografia", "Reprografía"


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


class AsistenciaComedor(models.Model):
    """Si un estudiante come o no come un día (RF5.2.4). La anota el encargado del comedor.

    Sin dietas ni tipos de comida (decisión del equipo, 20/10). Mientras su clase no esté
    terminada, la marca se puede cambiar (RF5.2.5).
    """

    fecha = models.DateField()
    estudiante = models.ForeignKey(
        Estudiante, on_delete=models.CASCADE, related_name="asistencias_comedor"
    )
    come = models.BooleanField()
    # Quién la anotó. Si se borra su cuenta, la marca se queda.
    anotada_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    anotada_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "asistencia al comedor"
        verbose_name_plural = "asistencias al comedor"
        ordering = ["-fecha", "estudiante"]
        constraints = [
            models.UniqueConstraint(
                fields=["fecha", "estudiante"], name="asistencia_comedor_una_por_dia"
            ),
        ]

    def __str__(self):
        return f"{self.estudiante} · {self.fecha:%d/%m/%Y} · {'come' if self.come else 'no come'}"


class ClaseComedorTerminada(models.Model):
    """Una clase que el encargado ha dado por terminada un día (RF5.2.6)."""

    fecha = models.DateField()
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name="+")
    terminada_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    terminada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "clase terminada en el comedor"
        verbose_name_plural = "clases terminadas en el comedor"
        ordering = ["-fecha", "clase"]
        constraints = [
            models.UniqueConstraint(fields=["fecha", "clase"], name="clase_comedor_una_por_dia"),
        ]

    def __str__(self):
        return f"{self.clase} · {self.fecha:%d/%m/%Y} · terminada"


COPIAS_MAXIMO = 99
AULA_MAXIMO = 50


class TrabajoReprografia(models.Model):
    """Los datos de una tarea de reprografía (RI5.1.2): copias, tipo de trabajo, color y aula.

    Apunta a la Asignacion (Úrsula) que pone la tarea «Reprografía» en la agenda del
    estudiante un día, con su horario. El estudiante, el día y las horas se leen de ella.
    `color`: True color, False blanco y negro, vacío = no aplica (solo plastificar, RF5.1.2).
    """

    asignacion = models.OneToOneField(
        Asignacion, on_delete=models.CASCADE, related_name="reprografia"
    )
    copias = models.PositiveSmallIntegerField("número de copias")
    imprimir = models.BooleanField(default=False)
    fotocopiar = models.BooleanField(default=False)
    plastificar = models.BooleanField(default=False)
    color = models.BooleanField(null=True, blank=True)
    aula = models.CharField("aula de recogida y entrega", max_length=AULA_MAXIMO)

    class Meta:
        verbose_name = "trabajo de reprografía"
        verbose_name_plural = "trabajos de reprografía"
        constraints = [
            models.CheckConstraint(
                condition=Q(copias__gte=1, copias__lte=COPIAS_MAXIMO),
                name="reprografia_copias_1_a_99",
            ),
            models.CheckConstraint(
                condition=Q(imprimir=True) | Q(fotocopiar=True) | Q(plastificar=True),
                name="reprografia_algun_trabajo",
            ),
            # Color solo si se imprime o se fotocopia; si no, «no aplica».
            models.CheckConstraint(
                condition=((Q(imprimir=True) | Q(fotocopiar=True)) & Q(color__isnull=False))
                | (Q(imprimir=False, fotocopiar=False) & Q(color__isnull=True)),
                name="reprografia_color_coherente",
            ),
            models.CheckConstraint(condition=~Q(aula=""), name="reprografia_aula_no_vacia"),
        ]

    def __str__(self):
        return f"Reprografía: {self.texto_trabajo} · {self.copias} · {self.aula}"

    @property
    def trabajos(self):
        """Los tipos de trabajo, en orden: ["imprimir", "plastificar"]."""
        return [
            nombre
            for nombre, si in (
                ("imprimir", self.imprimir),
                ("fotocopiar", self.fotocopiar),
                ("plastificar", self.plastificar),
            )
            if si
        ]

    @property
    def texto_trabajo(self):
        """«Imprimir y plastificar»."""
        t = self.trabajos
        texto = t[0] if len(t) == 1 else ", ".join(t[:-1]) + " y " + t[-1]
        return texto.capitalize()

    @property
    def texto_color(self):
        """«En color», «En blanco y negro» o "" (no aplica)."""
        if self.color is None:
            return ""
        return "En color" if self.color else "En blanco y negro"

    @property
    def texto_copias(self):
        return "1 copia" if self.copias == 1 else f"{self.copias} copias"
