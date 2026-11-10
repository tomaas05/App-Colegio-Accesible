"""Pantallas de usuarios y acceso (Manu).

HU-01-07: entrar como tutor, profesional o familiar (B12) y su pantalla principal (B13).
HU-01-06: entrar como estudiante: clase (B02), avatar (B03) y 3 imágenes o contraseña.
La portada «¿Quién eres?» (B01) es una plantilla sin lógica: usuarios/portada.html.
Bocetos: docs/iteracion-1/bocetos/despega_mockup_v3.html.
"""

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_http_methods

from apps.perfil.models import MetodoAcceso

from .forms import EntrarAdultoForm, EntrarConContrasenaForm, EntrarConImagenesForm
from .models import Clase, Estudiante, Rol

# login() necesita saber con qué backend se ha comprobado al usuario. El estudiante
# no pasa por authenticate() (no tiene usuario y contraseña), así que se indica aquí.
BACKEND_ESTUDIANTE = "django.contrib.auth.backends.ModelBackend"

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
        (
            "Horario escolar",
            "Qué asignatura o taller tiene cada clase en cada franja.",
            "horario:cargar",
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


# --- HU-01-06 · Entrar como estudiante -------------------------------------------


def _siguiente(request):
    """La pantalla que se pedía antes de entrar (?next=), solo si es de esta web."""
    destino = request.POST.get("next") or request.GET.get("next") or ""
    if url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return destino
    return ""


def _estudiantes_activos():
    return Q(estudiantes__usuario__is_active=True)


@require_GET
def clases(request):
    """B02 · ¿Cuál es tu clase? Solo las clases con algún estudiante que pueda entrar."""
    lista = (
        Clase.objects.annotate(activos=Count("estudiantes", filter=_estudiantes_activos()))
        .filter(activos__gt=0)
        .order_by("nombre")
    )
    return render(request, "usuarios/clases.html", {"clases": lista, "next": _siguiente(request)})


@require_GET
def avatares(request, pk):
    """B03 · ¿Quién eres? Los avatares de una clase, con el nombre de cada uno (PA1, PA2)."""
    clase = get_object_or_404(Clase, pk=pk)
    estudiantes = clase.estudiantes.filter(usuario__is_active=True).select_related("usuario")
    return render(
        request,
        "usuarios/avatares.html",
        {"clase": clase, "estudiantes": estudiantes, "next": _siguiente(request)},
    )


@require_http_methods(["GET", "POST"])
def entrar_estudiante(request, codigo):
    """Tras pulsar su avatar: 3 imágenes o contraseña, según su perfil (PA3, PA4, PA5).

    Sin bloqueo tras varios fallos: un niño no puede quedarse fuera de su agenda
    (ver docs/decisiones/0002-entrada-y-sesion.md).
    """
    estudiante = get_object_or_404(
        Estudiante.objects.select_related("usuario", "clase"),
        codigo_estudiante=codigo.upper(),
        usuario__is_active=True,
    )
    perfil = getattr(estudiante, "perfil", None)
    con_imagenes = perfil is None or perfil.metodo_acceso == MetodoAcceso.IMAGENES
    Formulario = EntrarConImagenesForm if con_imagenes else EntrarConContrasenaForm

    if request.method == "POST":
        form = Formulario(request.POST, usuario=estudiante.usuario)
        if form.is_valid():
            login(request, estudiante.usuario, backend=BACKEND_ESTUDIANTE)
            # PA7: entra en su propia agenda; la agenda solo enseña la del usuario con sesión.
            return redirect(_siguiente(request) or "agenda:dia")
    else:
        form = Formulario(usuario=estudiante.usuario)

    return render(
        request,
        "usuarios/entrar_estudiante.html",
        {
            "estudiante": estudiante,
            "form": form,
            "con_imagenes": con_imagenes,
            "next": _siguiente(request),
        },
    )
