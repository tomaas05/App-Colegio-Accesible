"""Alta de cuentas (HU-01-01, Manu).

Lo usan la pantalla «Crear cuenta» (B21) y la carga de una lista de estudiantes,
para que las dos creen las cuentas exactamente igual.
"""

import io
import re
import unicodedata

from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image, ImageDraw, ImageFont

from apps.perfil.models import MetodoAcceso, Perfil

from .acceso import establecer_contrasena_imagenes
from .models import Estudiante, Rol, Usuario

# Usuario interno del estudiante: «est-» + su código («est-a07»). No entra con él:
# entra con su avatar (HU-01-06). Ningún adulto puede tener un usuario así.
PREFIJO_ESTUDIANTE = "est-"

# Colores oscuros: la inicial en blanco encima cumple el contraste AA.
COLORES_AVATAR = [
    "#0B3C49",
    "#1F6F6B",
    "#7A3E9D",
    "#B54708",
    "#1D4ED8",
    "#9F1239",
    "#3F6212",
    "#5B21B6",
]


def siguiente_codigo():
    """Siguiente código de estudiante libre: A01, A02… (se asigna solo, B21)."""
    numeros = [
        int(m.group(1))
        for codigo in Estudiante.objects.values_list("codigo_estudiante", flat=True)
        if (m := re.fullmatch(r"A(\d+)", codigo))
    ]
    return f"A{max(numeros, default=0) + 1:02d}"


def _inicial(nombre):
    """Primera letra sin tilde: la fuente de Pillow no tiene «Á» ni «É»."""
    letra = unicodedata.normalize("NFD", nombre.strip()[:1] or "?")[0]
    return letra.upper()


def avatar_por_defecto(nombre, codigo):
    """Avatar dibujado: círculo de color con la inicial (nunca una foto, RNF de privacidad)."""
    lado = 256
    lienzo = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(lienzo)
    numero = int(re.sub(r"\D", "", codigo) or 0)
    dibujo.ellipse((0, 0, lado - 1, lado - 1), fill=COLORES_AVATAR[numero % len(COLORES_AVATAR)])
    fuente = ImageFont.load_default(size=120)
    texto = _inicial(nombre)
    caja = dibujo.textbbox((0, 0), texto, font=fuente)
    x = (lado - (caja[2] - caja[0])) / 2 - caja[0]
    y = (lado - (caja[3] - caja[1])) / 2 - caja[1]
    dibujo.text((x, y), texto, font=fuente, fill="white")
    salida = io.BytesIO()
    lienzo.save(salida, format="PNG")
    return ContentFile(salida.getvalue(), name=f"{codigo.lower()}.png")


@transaction.atomic
def crear_adulto(*, rol, nombre, apellidos, usuario, contrasena, correo=""):
    """Tutor, profesional, familiar o administrador con usuario y contraseña inicial.

    El administrador queda igual que el de `createsuperuser` (is_staff e is_superuser):
    la opción «Clases» de su panel es la administración de Django y sin eso no entraría.
    """
    es_admin = rol == Rol.ADMINISTRADOR
    adulto = Usuario(
        username=usuario,
        first_name=nombre,
        last_name=apellidos,
        email=correo,
        rol=rol,
        is_staff=es_admin,
        is_superuser=es_admin,
    )
    adulto.set_password(contrasena)
    adulto.save()
    return adulto


@transaction.atomic
def crear_estudiante(
    *,
    nombre,
    apellidos,
    clase,
    metodo_acceso,
    imagenes=None,
    contrasena="",
    usa_lector_pantalla=False,
    avatar=None,
):
    """Estudiante con su código, su avatar, su clase y su forma de entrar.

    `imagenes`: las 3 ImagenAcceso elegidas, si entra con imágenes.
    `contrasena`: su contraseña de texto, si entra con contraseña.
    El perfil lo crea la señal de apps/perfil; aquí se rellena el método de acceso.
    """
    codigo = siguiente_codigo()
    usuario = Usuario(
        username=f"{PREFIJO_ESTUDIANTE}{codigo.lower()}",
        first_name=nombre,
        last_name=apellidos,
        rol=Rol.ESTUDIANTE,
    )
    if metodo_acceso == MetodoAcceso.IMAGENES:
        establecer_contrasena_imagenes(usuario, [i.pk for i in imagenes], guardar=False)
    else:
        usuario.set_password(contrasena)
    usuario.save()

    estudiante = Estudiante(usuario=usuario, codigo_estudiante=codigo, clase=clase)
    if avatar:
        estudiante.avatar.save(f"{codigo.lower()}-{avatar.name}", avatar, save=False)
    else:
        estudiante.avatar.save(
            f"{codigo.lower()}.png", avatar_por_defecto(nombre, codigo), save=False
        )
    estudiante.save()

    Perfil.objects.update_or_create(
        estudiante=estudiante,
        defaults={"metodo_acceso": metodo_acceso, "usa_lector_pantalla": usa_lector_pantalla},
    )
    return estudiante
