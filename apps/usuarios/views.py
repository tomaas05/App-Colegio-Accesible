"""Pantallas de usuarios y acceso (Manu).

HU-01-07: entrar como tutor, profesional o familiar (B12) y su pantalla principal (B13).
Bocetos: docs/iteracion-1/bocetos/despega_mockup_v3.html.
"""

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import NoReverseMatch, reverse
from django.views.decorators.http import require_GET

from .forms import EntrarAdultoForm
from .models import Rol

# Opciones de la pantalla principal de cada rol (B13): (texto, descripción, nombre de la URL).
# Cada dueño añade aquí la entrada de su pantalla cuando la tenga. Si la URL todavía no
# existe, la opción no se enseña (así nadie rompe el panel de otro).
OPCIONES_POR_ROL = {
    Rol.ADMINISTRADOR: [
        (
            "Usuarios, clases y vínculos",
            "Mientras no estén sus pantallas, desde la administración de Django.",
            "admin:index",
        ),
    ],
    Rol.TUTOR: [
        ("Crear una tarea", "Con su imagen y sus pasos.", "tareas:crear_tarea"),
        ("Tareas creadas", "Las tareas que ya existen.", "tareas:catalogo"),
    ],
    Rol.PROFESIONAL: [
        ("Crear una tarea", "Con su imagen y sus pasos.", "tareas:crear_tarea"),
        ("Tareas creadas", "Las tareas que ya existen.", "tareas:catalogo"),
    ],
    Rol.FAMILIAR: [
        ("Crear una tarea", "Con su imagen y sus pasos.", "tareas:crear_tarea"),
        ("Tareas creadas", "Las tareas que ya existen.", "tareas:catalogo"),
    ],
}


def destino_tras_entrar(usuario):
    """A dónde va cada usuario al entrar: el estudiante a su agenda, el adulto a su panel."""
    if usuario.es_estudiante:
        return reverse("agenda:dia")
    return reverse("usuarios:panel")


class EntrarAdultoView(LoginView):
    """HU-01-07. Entrar con usuario y contraseña (B12).

    Los 5 intentos fallidos y los 5 minutos de bloqueo los cuenta django-axes
    (RNF1.2.3, config/settings/base.py); al bloquear enseña usuarios/bloqueado.html.
    """

    form_class = EntrarAdultoForm
    template_name = "usuarios/entrar.html"
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        # Sin ?next=, cada rol a su pantalla (LOGIN_REDIRECT_URL solo admite una).
        return destino_tras_entrar(self.request.user)


def _opciones(rol):
    opciones = []
    for texto, descripcion, nombre_url in OPCIONES_POR_ROL.get(rol, []):
        try:
            opciones.append(
                {"texto": texto, "descripcion": descripcion, "url": reverse(nombre_url)}
            )
        except NoReverseMatch:
            continue
    return opciones


@login_required
@require_GET
def panel(request):
    """HU-01-07. Pantalla principal del adulto, con su nombre (B13)."""
    if request.user.es_estudiante:
        return redirect("agenda:dia")
    return render(
        request,
        "usuarios/panel.html",
        {"opciones": _opciones(request.user.rol)},
    )
