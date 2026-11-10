"""Perfil visual del estudiante (RI4.1.1).

Diseño: docs/iteracion-1/base-datos/diccionario.md. Dueño: Jorge.
Se crea solo, con los valores por defecto, al crear un estudiante (signals.py).
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.usuarios.models import Estudiante


class Tema(models.TextChoices):
    CLARO = "claro", "Claro"
    OSCURO = "oscuro", "Oscuro"


class Paleta(models.TextChoices):
    SUAVE = "suave", "Suave"
    ESTANDAR = "estandar", "Estándar"
    ALTO_CONTRASTE = "alto_contraste", "Alto contraste"


class TipoLetra(models.TextChoices):
    NUNITO = "nunito", "Nunito"
    OPEN_SANS = "open_sans", "Open Sans"
    ATKINSON = "atkinson", "Atkinson Hyperlegible"
    LEXEND = "lexend", "Lexend"


class TamanoLetra(models.IntegerChoices):
    NORMAL = 16, "16 px"
    MEDIANA = 20, "20 px"
    GRANDE = 24, "24 px"
    MUY_GRANDE = 32, "32 px"


class TamanoBotones(models.IntegerChoices):
    NORMAL = 48, "Normal (48 px)"
    GRANDE = 64, "Grande (64 px)"
    MUY_GRANDE = 80, "Muy grande (80 px)"


class PosicionBotones(models.TextChoices):
    ABAJO = "abajo", "Abajo"
    ARRIBA = "arriba", "Arriba"
    IZQUIERDA = "izquierda", "Izquierda"
    DERECHA = "derecha", "Derecha"


class ContenidoBotones(models.TextChoices):
    IMAGEN = "imagen", "Imagen"
    TEXTO = "texto", "Texto"
    AMBOS = "ambos", "Imagen y texto"


class TipoTemporizador(models.TextChoices):
    LINEAL = "lineal", "Lineal"
    RADIAL = "radial", "Radial"
    NUMERICO = "numerico", "Numérico"


class MetodoAcceso(models.TextChoices):
    IMAGENES = "imagenes", "Tres imágenes"
    CONTRASENA = "contrasena", "Contraseña de texto"


class Perfil(models.Model):
    estudiante = models.OneToOneField(
        Estudiante, on_delete=models.CASCADE, primary_key=True, related_name="perfil"
    )
    tema = models.CharField(max_length=10, choices=Tema.choices, default=Tema.CLARO)
    paleta = models.CharField(max_length=20, choices=Paleta.choices, default=Paleta.ESTANDAR)
    tipo_letra = models.CharField(
        max_length=20, choices=TipoLetra.choices, default=TipoLetra.NUNITO
    )
    tamano_letra = models.PositiveSmallIntegerField(
        "tamaño de letra", choices=TamanoLetra.choices, default=TamanoLetra.MEDIANA
    )
    tamano_botones = models.PositiveSmallIntegerField(
        "tamaño de los botones", choices=TamanoBotones.choices, default=TamanoBotones.NORMAL
    )
    posicion_botones = models.CharField(
        "posición de los botones",
        max_length=10,
        choices=PosicionBotones.choices,
        default=PosicionBotones.ABAJO,
    )
    contenido_botones = models.CharField(
        "contenido de los botones",
        max_length=10,
        choices=ContenidoBotones.choices,
        default=ContenidoBotones.AMBOS,
    )
    max_tarjetas = models.PositiveSmallIntegerField(
        "máximo de tarjetas",
        default=6,
        validators=[MinValueValidator(1), MaxValueValidator(6)],
    )
    tipo_temporizador = models.CharField(
        max_length=10, choices=TipoTemporizador.choices, default=TipoTemporizador.LINEAL
    )
    temporizador_visible = models.BooleanField(default=True)
    puede_ocultar_temporizador = models.BooleanField(default=False)
    metodo_acceso = models.CharField(
        "método de acceso",
        max_length=10,
        choices=MetodoAcceso.choices,
        default=MetodoAcceso.IMAGENES,
        help_text="Qué se le pide al estudiante después de pulsar su avatar.",
    )
    usa_lector_pantalla = models.BooleanField(
        "usa lector de pantalla",
        default=False,
        help_text=(
            "El navegador no permite saber si VoiceOver o TalkBack están activos. "
            "Si se marca, la aplicación no reproduce su propia voz para no pisar al lector."
        ),
    )

    class Meta:
        verbose_name = "perfil"
        verbose_name_plural = "perfiles"
        constraints = [
            models.CheckConstraint(
                condition=Q(max_tarjetas__gte=1) & Q(max_tarjetas__lte=6),
                name="perfil_max_tarjetas_1_a_6",
            ),
            models.CheckConstraint(
                condition=Q(tamano_letra__in=TamanoLetra.values),
                name="perfil_tamano_letra_valido",
            ),
            models.CheckConstraint(
                condition=Q(tamano_botones__in=TamanoBotones.values),
                name="perfil_tamano_botones_valido",
            ),
            models.CheckConstraint(
                condition=Q(metodo_acceso__in=MetodoAcceso.values),
                name="perfil_metodo_acceso_valido",
            ),
        ]

    def __str__(self):
        return f"Perfil de {self.estudiante}"
