"""Pantallas de usuarios y acceso (Manu).

HU-01-07: entrar como tutor, profesional o familiar (B12) y su pantalla principal (B13).
HU-01-06: entrar como estudiante: clase (B02), avatar (B03) y 3 imágenes o contraseña.
HU-01-08 (Javi): el profesional elige los estudiantes que atiende (B26).
HU-01-01: usuarios (B20), crear cuenta (B21) y cargar una lista de estudiantes (solo admin).
HU-01-04: vínculos de cada estudiante con su tutor y su familiar (B25, solo admin) y
«Tus estudiantes» en el panel de cada adulto.
La portada «¿Quién eres?» (B01) es una plantilla sin lógica: usuarios/portada.html.
Bocetos: docs/iteracion-1/bocetos/despega_mockup_v3.html.
"""

from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_http_methods

from apps.perfil.models import MetodoAcceso

from . import atencion
from .carga import PLANTILLA, cargar_lista
from .forms import (
    CargarListaForm,
    CrearCuentaForm,
    EntrarAdultoForm,
    EntrarConContrasenaForm,
    EntrarConImagenesForm,
    VinculosForm,
)
from .models import Clase, Estudiante, ImagenAcceso, Rol, Usuario
from .permisos import admin_requerido
from .texto import coincide, normalizar
from .vinculos import estudiantes_de, guardar_vinculos

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
        ("Vínculos", "Tutor y familiar de cada estudiante.", "usuarios:vinculos"),
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
        (
            "Mis estudiantes",
            "Elige en la lista del centro los estudiantes que atiendes.",
            "usuarios:mis_estudiantes",
        ),
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
    """HU-01-07. Pantalla principal del adulto, con su nombre (B13).

    HU-01-04: el tutor, el profesional y el familiar ven también a sus estudiantes,
    y solo a los suyos (PA1, PA3 y PA4).
    """
    if request.user.es_estudiante:
        return redirect("agenda:dia")
    estudiantes = None
    if request.user.rol != Rol.ADMINISTRADOR:
        estudiantes = estudiantes_de(request.user)
    return render(
        request,
        "usuarios/panel.html",
        {"opciones": _opciones(request.user.rol), "estudiantes": estudiantes},
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


def _tutor_corto(nombre, apellidos):
    """«Ana», «Martín Ruiz» → «A. Martín», como en el boceto B02."""
    primero = (apellidos or "").split()
    return f"{nombre[:1]}. {primero[0]}" if nombre and primero else nombre


@require_GET
def clases(request):
    """B02 · ¿Cuál es tu clase? Solo las clases con algún estudiante que pueda entrar.

    Debajo de cada clase, su tutor (HU-01-04), para que el estudiante la reconozca.
    Si la clase tiene más de un tutor, no se pone ninguno.
    """
    lista = list(
        Clase.objects.annotate(activos=Count("estudiantes", filter=_estudiantes_activos()))
        .filter(activos__gt=0)
        .order_by("nombre")
    )
    tutores = {}
    for clase_id, nombre, apellidos in (
        Estudiante.objects.filter(usuario__is_active=True, tutor__isnull=False)
        .values_list("clase_id", "tutor__first_name", "tutor__last_name")
        .distinct()
    ):
        tutores.setdefault(clase_id, set()).add(_tutor_corto(nombre, apellidos))
    for clase in lista:
        de_la_clase = tutores.get(clase.pk, set())
        clase.tutor_corto = next(iter(de_la_clase)) if len(de_la_clase) == 1 else ""
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


def _cuenta_coincide(cuenta, texto):
    """Nombre completo o usuario que contiene el texto, o el código exacto del estudiante."""
    if coincide(texto, cuenta.get_full_name(), cuenta.username):
        return True
    return cuenta.es_estudiante and normalizar(texto) == normalizar(
        cuenta.estudiante.codigo_estudiante
    )


@admin_requerido
@require_GET
def lista_usuarios(request):
    """B20 · Usuarios. Todas las cuentas, con filtro por rol, clase y texto."""
    rol = request.GET.get("rol", "")
    clase_id = request.GET.get("clase", "")
    texto = request.GET.get("q", "").strip()

    cuentas = (
        Usuario.objects.select_related(
            "estudiante__clase", "estudiante__tutor", "estudiante__familiar"
        )
        # Columna «Vínculos» de los adultos (HU-01-04): cuántos estudiantes tiene cada uno.
        .annotate(
            n_tutorizados=Count("estudiantes_tutorizados", distinct=True),
            n_familiares=Count("estudiantes_familiares", distinct=True),
            n_atendidos=Count("atenciones", distinct=True),
        )
        .order_by("first_name", "last_name", "pk")  # pk: mismo orden en cada página
    )
    if rol in Rol.values:
        cuentas = cuentas.filter(rol=rol)
    if clase_id.isdigit():
        cuentas = cuentas.filter(estudiante__clase_id=int(clase_id))
    if texto:  # sin mirar tildes: «lucia» encuentra a Lucía (ver texto.py)
        cuentas = [cuenta for cuenta in cuentas if _cuenta_coincide(cuenta, texto)]

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


# --- HU-01-04 · Vínculos con el tutor y el familiar (solo el administrador) -------


def _grupos_por_clase(estudiantes):
    """[(clase, [estudiantes])] en orden de clase, para los <optgroup> del selector."""
    grupos = {}
    for estudiante in estudiantes:
        grupos.setdefault(estudiante.clase, []).append(estudiante)
    return sorted(grupos.items(), key=lambda grupo: grupo[0].nombre)


def _buscar(estudiantes, texto):
    """Por nombre y apellidos o por el código exacto, sin mirar tildes ni mayúsculas."""
    if not texto:
        return list(estudiantes)
    return [
        uno
        for uno in estudiantes
        if coincide(texto, uno.usuario.get_full_name())
        or normalizar(texto) == normalizar(uno.codigo_estudiante)
    ]


@admin_requerido
@require_http_methods(["GET", "POST"])
def vinculos(request):
    """B25 · Vínculos: el tutor y el familiar de cada estudiante (PA1 y PA2).

    Se elige el estudiante con ?estudiante=<código> (y ?q= para buscarlo). «Quitar» y
    «Añadir» cambian el familiar sin guardar; «Guardar vínculos» guarda tutor y familiar.
    """
    texto = request.GET.get("q", "").strip()
    todos = estudiantes_de(request.user)
    encontrados = _buscar(todos, texto)
    codigo = request.GET.get("estudiante", "").upper()
    estudiante = next((uno for uno in encontrados if uno.codigo_estudiante == codigo), None)
    if estudiante is None and encontrados and texto and request.method == "GET":
        estudiante = encontrados[0]  # al buscar sin elegir, el primero que coincide

    form = None
    if estudiante is not None:
        accion = request.POST.get("accion", "guardar")
        if request.method == "POST" and accion in VinculosForm.ACCIONES:
            form = VinculosForm(request.POST, estudiante=estudiante)
            if accion == "guardar" and form.is_valid():
                nombre = estudiante.usuario.get_full_name()
                cambia_tutor = guardar_vinculos(
                    estudiante,
                    tutor=form.cleaned_data["tutor"],
                    familiar=form.cleaned_data["familiar"],
                )
                aviso = f"Vínculos de {nombre} guardados."
                if cambia_tutor and estudiante.tutor:
                    aviso += f" Su tutor ahora es {estudiante.tutor.get_full_name()}."
                messages.success(request, aviso)
                return redirect(
                    reverse("usuarios:vinculos")
                    + "?"
                    + urlencode({"estudiante": estudiante.codigo_estudiante})
                )
            if accion != "guardar":
                datos = form.datos_tras(accion)
                if datos is not None:
                    form = VinculosForm(datos, estudiante=estudiante)
        else:
            form = VinculosForm(estudiante=estudiante)

    return render(
        request,
        "usuarios/vinculos.html",
        {
            "texto": texto,
            "grupos": _grupos_por_clase(encontrados),
            "estudiante": estudiante,
            "form": form,
            "hay_estudiantes": todos.exists(),
        },
    )


# --- HU-01-08 · Elegir los estudiantes que atiendo (Javi) ------------------------


def _solo_profesional(request):
    if request.user.rol != Rol.PROFESIONAL:
        raise PermissionDenied("Solo los profesionales eligen a qué estudiantes atienden.")


@login_required
@require_http_methods(["GET", "POST"])
def mis_estudiantes(request):
    """B26 · Elegir mis estudiantes (PA1, PA2 y PA4).

    A la izquierda, los estudiantes del centro (nombre, clase y avatar; sin fotos) con
    búsqueda y filtro por clase; a la derecha, los ya elegidos. Se guarda al pulsar
    «Guardar». Con un filtro puesto solo cambia lo que se ve: los elegidos que no salen
    en la lista se mantienen (para eso el formulario manda también `mostrados`).
    """
    _solo_profesional(request)
    actuales = {e.codigo_estudiante for e in atencion.mis_estudiantes(request.user)}

    if request.method == "POST":
        if request.POST.get("quitar"):
            # PA4: botón «Quitar» de la lista de la derecha.
            codigos = actuales - {request.POST["quitar"]}
        else:
            mostrados = set(request.POST.getlist("mostrados"))
            codigos = (actuales - mostrados) | set(request.POST.getlist("elegidos"))
        anadidos, quitados = atencion.guardar_mis_estudiantes(request.user, codigos)
        if anadidos or quitados:
            messages.success(request, _texto_cambios(anadidos, quitados))
        else:
            messages.info(request, "No había cambios que guardar.")
        destino = reverse("usuarios:mis_estudiantes")
        consulta = request.POST.get("consulta", "")
        return redirect(f"{destino}?{consulta}" if consulta else destino)

    texto = request.GET.get("q", "").strip()
    clase_id = request.GET.get("clase") or None
    if clase_id and not clase_id.isdigit():
        clase_id = None
    lista = atencion.estudiantes_del_centro(texto, clase_id)
    return render(
        request,
        "usuarios/mis_estudiantes.html",
        {
            "estudiantes": lista,
            "mios": atencion.mis_estudiantes(request.user),
            "actuales": actuales,
            "clases": Clase.objects.filter(estudiantes__usuario__is_active=True)
            .distinct()
            .order_by("nombre"),
            "q": texto,
            "clase_id": int(clase_id) if clase_id else None,
            "consulta": request.GET.urlencode(),
        },
    )


def _texto_cambios(anadidos, quitados):
    partes = []
    if anadidos:
        partes.append(f"{anadidos} añadido{'s' if anadidos != 1 else ''}")
    if quitados:
        partes.append(f"{quitados} quitado{'s' if quitados != 1 else ''}")
    return "Guardado: " + " y ".join(partes) + "."
