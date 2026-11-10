"""Pantallas de usuarios y acceso (Manu).

HU-01-07: entrar como tutor, profesional o familiar (B12) y su pantalla principal (B13).
HU-01-06: entrar como estudiante: clase (B02), avatar (B03) y 3 imágenes o contraseña.
HU-01-01: usuarios (B20), crear cuenta (B21) y cargar una lista de estudiantes (solo admin).
La portada «¿Quién eres?» (B01) es una plantilla sin lógica: usuarios/portada.html.
Bocetos: docs/iteracion-1/bocetos/despega_mockup_v3.html.
"""

from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_http_methods

from apps.perfil.models import MetodoAcceso

from .carga import PLANTILLA, cargar_lista
from .forms import (
    CargarListaForm,
    CrearCuentaForm,
    EntrarAdultoForm,
    EntrarConContrasenaForm,
    EntrarConImagenesForm,
)
from .models import Clase, Estudiante, ImagenAcceso, Rol, Usuario
from .permisos import admin_requerido

# login() necesita saber con qué backend se ha comprobado al usuario. El estudiante
# no pasa por authenticate() (no tiene usuario y contraseña), así que se indica aquí.
BACKEND_ESTUDIANTE = "django.contrib.auth.backends.ModelBackend"

# Opciones de la pantalla principal de cada rol (B13): (texto, descripción, nombre de la URL).
# Cada dueño añade aquí la entrada de su pantalla cuando la tenga. Si la URL todavía no
# existe, la opción no se enseña (así nadie rompe el panel de otro).
OPCIONES_POR_ROL = {
    Rol.ADMINISTRADOR: [
        (
            "Usuarios",
            "Ver las cuentas, crear una o cargar una lista de estudiantes.",
            "usuarios:lista",
        ),
        (
            "Clases",
            "Crear y editar clases, desde la administración de Django.",
            "admin:usuarios_clase_changelist",
        ),
    ],
    Rol.TUTOR: [
        ("Crear una tarea", "Con su imagen y sus pasos.", "tareas:crear_tarea"),
        ("Tareas creadas", "Las tareas que ya existen.", "tareas:catalogo"),
        (
            "Perfil visual",
            "Tema, colores, letra, botones y lector de pantalla de tus estudiantes.",
            "perfil:lista",
        ),
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


# --- HU-01-01 · Crear un usuario (solo el administrador) -------------------------

CUENTAS_POR_PAGINA = 25


@admin_requerido
@require_GET
def lista_usuarios(request):
    """B20 · Usuarios. Todas las cuentas, con filtro por rol, clase y texto."""
    rol = request.GET.get("rol", "")
    clase_id = request.GET.get("clase", "")
    texto = request.GET.get("q", "").strip()

    cuentas = Usuario.objects.select_related(
        "estudiante__clase", "estudiante__tutor", "estudiante__familiar"
    ).order_by("first_name", "last_name", "pk")  # pk: mismo orden en cada página
    if rol in Rol.values:
        cuentas = cuentas.filter(rol=rol)
    if clase_id.isdigit():
        cuentas = cuentas.filter(estudiante__clase_id=int(clase_id))
    if texto:
        cuentas = cuentas.filter(
            Q(first_name__icontains=texto)
            | Q(last_name__icontains=texto)
            | Q(username__icontains=texto)
            | Q(estudiante__codigo_estudiante__iexact=texto)
        )

    pagina = Paginator(cuentas, CUENTAS_POR_PAGINA).get_page(request.GET.get("pagina"))
    filtros = {k: v for k, v in {"rol": rol, "clase": clase_id, "q": texto}.items() if v}
    return render(
        request,
        "usuarios/lista.html",
        {
            "pagina": pagina,
            "roles": Rol.choices,
            "clases": Clase.objects.all(),
            "rol": rol,
            "clase_id": clase_id,
            "texto": texto,
            "filtros_url": urlencode(filtros),
        },
    )


@admin_requerido
@require_http_methods(["GET", "POST"])
def crear_cuenta(request):
    """B21 · Crear cuenta (PA1, PA2, PA3)."""
    if request.method == "POST":
        form = CrearCuentaForm(request.POST, request.FILES)
    else:
        form = CrearCuentaForm()
    if form.is_bound and form.is_valid():
        usuario = form.crear()
        if usuario.es_estudiante:
            estudiante = usuario.estudiante
            como = (
                "con sus 3 imágenes"
                if estudiante.perfil.metodo_acceso == MetodoAcceso.IMAGENES
                else "con su contraseña"
            )
            messages.success(
                request,
                f"Cuenta creada: {usuario.get_full_name()}, código {estudiante.codigo_estudiante}. "
                f"Entra desde «Estudiante» → {estudiante.clase.nombre} → su avatar, {como}.",
            )
            destino = {"clase": estudiante.clase_id}
        else:
            messages.success(
                request,
                f"Cuenta creada: {usuario.get_full_name()} ({usuario.get_rol_display()}). "
                f"Entra en «Adulto» con el usuario «{usuario.username}».",
            )
            destino = {"rol": usuario.rol}
        return redirect(reverse("usuarios:lista") + "?" + urlencode(destino))

    return render(request, "usuarios/crear_cuenta.html", {"form": form})


@admin_requerido
@require_http_methods(["GET", "POST"])
def cargar_estudiantes(request):
    """Cargar una lista de estudiantes en una clase (PA4)."""
    if request.method == "POST":
        form = CargarListaForm(request.POST, request.FILES)
    else:
        form = CargarListaForm()
    resultado = None
    if form.is_bound and form.is_valid():
        resultado = cargar_lista(form.cleaned_data["archivo"], form.cleaned_data["clase"])
    return render(
        request,
        "usuarios/cargar_lista.html",
        {
            "form": form,
            "resultado": resultado,
            "imagenes": ImagenAcceso.objects.filter(activa=True),
        },
    )


@admin_requerido
@require_GET
def plantilla_csv(request):
    """Plantilla para rellenar en Excel o LibreOffice (con BOM para que respete las tildes)."""
    respuesta = HttpResponse("\ufeff" + PLANTILLA, content_type="text/csv; charset=utf-8")
    respuesta["Content-Disposition"] = 'attachment; filename="plantilla_estudiantes.csv"'
    return respuesta
