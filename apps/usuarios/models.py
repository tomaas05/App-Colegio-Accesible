"""Usuarios y acceso: usuario, clase, estudiante y atención.

Diseño: docs/iteracion-1/base-datos/ (relacional.md y diccionario.md).
Dueño: Manu.
"""

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models import Q


class Rol(models.TextChoices):
    ADMINISTRADOR = "administrador", "Administrador"
    TUTOR = "tutor", "Tutor"
    PROFESIONAL = "profesional", "Profesional"
    FAMILIAR = "familiar", "Familiar"
    ESTUDIANTE = "estudiante", "Estudiante"


class UsuarioManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # createsuperuser crea siempre un administrador.
        extra_fields.setdefault("rol", Rol.ADMINISTRADOR)
        return super().create_superuser(username, email, password, **extra_fields)


class Usuario(AbstractUser):
    """Usuario de la aplicación (RI1.1.1, RI1.3.1).

    Tutor, profesional, familiar y administrador no tienen tabla propia:
    se distinguen por `rol`. El estudiante tiene además una fila en Estudiante.

    Correspondencia con el diccionario: username = usuario_acceso,
    first_name = nombre, last_name = apellidos, email = correo,
    password = hash_contrasena, is_active = activo, date_joined = fecha_creacion.
    """

    first_name = models.CharField("nombre", max_length=150)
    last_name = models.CharField("apellidos", max_length=150, blank=True)
    rol = models.CharField(max_length=20, choices=Rol.choices)

    objects = UsuarioManager()

    REQUIRED_FIELDS = ["first_name"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["first_name", "last_name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(rol__in=Rol.values),
                name="usuario_rol_valido",
            ),
        ]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_rol_display()})"

    @property
    def es_adulto(self):
        return self.rol != Rol.ESTUDIANTE

    @property
    def es_estudiante(self):
        return self.rol == Rol.ESTUDIANTE


class Clase(models.Model):
    """Grupo al que pertenece un estudiante: A, B, PTVAL 1… (RI1.1.2)."""

    nombre = models.CharField(max_length=50)
    curso_escolar = models.CharField(max_length=9, help_text="Formato 2026-2027")
    imagen = models.ImageField(upload_to="clases/", blank=True)
    descripcion_imagen = models.CharField("descripción de la imagen", max_length=150, blank=True)

    class Meta:
        verbose_name = "clase"
        verbose_name_plural = "clases"
        ordering = ["curso_escolar", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["nombre", "curso_escolar"], name="clase_unica_por_curso"
            ),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.curso_escolar})"


class Estudiante(models.Model):
    """Datos propios del estudiante (RI1.1.1, RI1.2.1).

    Un estudiante tiene como mucho un tutor y un familiar: son claves ajenas.
    Que el usuario apuntado tenga el rol correcto se comprueba en clean().
    """

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="estudiante",
        limit_choices_to={"rol": Rol.ESTUDIANTE},
    )
    codigo_estudiante = models.CharField("código de estudiante", max_length=20, unique=True)
    avatar = models.ImageField(upload_to="avatares/")
    clase = models.ForeignKey(Clase, on_delete=models.PROTECT, related_name="estudiantes")
    tutor = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="estudiantes_tutorizados",
        limit_choices_to={"rol": Rol.TUTOR},
    )
    fecha_alta_tutor = models.DateField("fecha de alta del tutor", null=True, blank=True)
    familiar = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="estudiantes_familiares",
        limit_choices_to={"rol": Rol.FAMILIAR},
    )
    fecha_alta_familiar = models.DateField("fecha de alta del familiar", null=True, blank=True)

    class Meta:
        verbose_name = "estudiante"
        verbose_name_plural = "estudiantes"
        ordering = ["usuario__first_name", "usuario__last_name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(tutor__isnull=True) | Q(fecha_alta_tutor__isnull=False),
                name="estudiante_tutor_con_fecha",
            ),
            models.CheckConstraint(
                condition=Q(familiar__isnull=True) | Q(fecha_alta_familiar__isnull=False),
                name="estudiante_familiar_con_fecha",
            ),
        ]

    def __str__(self):
        return self.usuario.get_full_name() or self.codigo_estudiante

    def clean(self):
        from django.core.exceptions import ValidationError

        errores = {}
        if self.usuario_id and self.usuario.rol != Rol.ESTUDIANTE:
            errores["usuario"] = "El usuario debe tener el rol de estudiante."
        if self.tutor_id and self.tutor.rol != Rol.TUTOR:
            errores["tutor"] = "El tutor debe tener el rol de tutor."
        if self.familiar_id and self.familiar.rol != Rol.FAMILIAR:
            errores["familiar"] = "El familiar debe tener el rol de familiar."
        if errores:
            raise ValidationError(errores)


class Atencion(models.Model):
    """Estudiantes que atiende un profesional (RI1.2.2). La rellena HU-01-08."""

    profesional = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="atenciones",
        limit_choices_to={"rol": Rol.PROFESIONAL},
    )
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name="atenciones")
    fecha_alta = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "atención"
        verbose_name_plural = "atenciones"
        constraints = [
            models.UniqueConstraint(fields=["profesional", "estudiante"], name="atencion_unica"),
        ]

    def __str__(self):
        return f"{self.profesional} atiende a {self.estudiante}"
