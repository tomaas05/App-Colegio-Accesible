"""Pantallas de usuarios y acceso (Manu).

HU-01-07: entrar como tutor, profesional o familiar (B12) y su pantalla principal (B13).
HU-01-06: entrar como estudiante: portada con las clases (B01 + B02), avatar (B03) y
3 imágenes o contraseña.
HU-01-08 (Javi): el profesional elige los estudiantes que atiende (B26).
HU-01-09 (Javi): el profesional consulta la agenda de los estudiantes que atiende (B27).
HU-01-01: usuarios (B20), crear cuenta (B21) y cargar una lista de estudiantes (solo admin).
HU-01-04: vínculos de cada estudiante con su tutor y su familiar (B25, solo admin) y
«Tus estudiantes» en el panel de cada adulto.
HU-01-03: eliminar una cuenta, con confirmación (B24, solo admin).
HU-01-02: editar una cuenta (B23, solo admin): nombre, clase, avatar, usuario, correo,
activar o desactivar y restablecer la contraseña; y cambiar la contraseña temporal (B15).
Bocetos: docs/iteracion-1/bocetos/despega_mockup_v3.html.
"""

from datetime import date, timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.comun.models import Notificacion, pendientes
from apps.perfil.models import MetodoAcceso

from . import atencion, bajas, consulta, edicion
from .carga import PLANTILLA, cargar_lista
from .forms import (
    CambiarContrasenaForm,
    CargarListaForm,
    CrearCuentaForm,
    EditarCuentaForm,
    EntrarAdultoForm,
    EntrarConContrasenaForm,
    EntrarConImagenesForm,
    VinculosForm,
)
from .models import Clase, Estudiante, ImagenAcceso, Rol, Usuario
from .navegacion import (  # noqa: F401 (OPCIONES_POR_ROL se importaba de aquí)
    OPCIONES_POR_ROL,
    lista_estudiantes_en_el_panel,
    opciones_de,
)
from .permisos import admin_requerido
from .texto import coincide, normalizar
from .vinculos import estudiantes_de, guardar_vinculos

# login() necesita saber con qué backend se ha comprobado al usuario. El estudiante
# no pasa por authenticate() (no tiene usuario y contraseña), así que se indica aquí.
BACKEND_ESTUDIANTE = "django.contrib.auth.backends.ModelBackend"


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


@login_required
@require_GET
def panel(request):
    """HU-01-07. Pantalla principal del adulto, con su nombre (B13).

    HU-01-04: cada adulto ve a sus estudiantes, y solo a los suyos (PA1, PA3 y PA4). El
    tutor en «Alumnos» y el profesional en «Mis estudiantes»; el familiar, que no tiene una
    opción así, aquí mismo. Así el panel cabe sin desplazarse (decisión 0005).
    """
    if request.user.es_estudiante:
        return redirect("agenda:dia")
    estudiantes = None
    if lista_estudiantes_en_el_panel(request.user.rol):
        estudiantes = estudiantes_de(request.user)
    # HU-07-04 (PA5): los avisos sin ver, de uno en uno (el más antiguo primero).
    avisos = pendientes(request.user)
    return render(
        request,
        "usuarios/panel.html",
        {
            "opciones": opciones_de(request.user.rol),
            "estudiantes": estudiantes,
            "aviso": avisos.first(),
            "avisos_mas": max(avisos.count() - 1, 0),
        },
    )


@login_required
@require_POST
def aviso_visto(request, pk):
    """«Visto» en un aviso del panel: queda la hora en que lo vio y sale el siguiente."""
    aviso = get_object_or_404(Notificacion, pk=pk, destinatario=request.user)
    aviso.marcar_vista()
    return redirect("usuarios:panel")


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
def portada(request):
    """B01 + B02 · Primera pantalla: «¿Cuál es tu clase?» y, en pequeño, la entrada de adultos.

    Revisión con la profesora (noviembre de 2026): el estudiante elige su clase nada más
    abrir la aplicación, sin pasar antes por «Estudiante o Adulto». Solo salen las clases
    con algún estudiante que pueda entrar. Debajo de cada clase, su tutor (HU-01-04), para
    que el estudiante la reconozca; si la clase tiene más de un tutor, no se pone ninguno.
    Aquí llega también quien no ha entrado (LOGIN_URL), con la pantalla que pedía en ?next=.
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
    return render(request, "usuarios/portada.html", {"clases": lista, "next": _siguiente(request)})


@require_GET
def clases(request):
    """Dirección antigua de «¿Cuál es tu clase?» (B02): ahora es la portada."""
    destino = reverse("inicio")
    siguiente = _siguiente(request)
    return redirect(f"{destino}?{urlencode({'next': siguiente})}" if siguiente else destino)


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


# --- HU-01-02 · Modificar un usuario (solo el administrador) ----------------------

# Dónde se guarda, hasta que se enseña una vez, la contraseña temporal recién creada.
# La sesión está en la base de datos del servidor: no viaja al navegador en una cookie.
CLAVE_TEMPORAL = "contrasena_temporal"

TEXTO_CAMBIOS = {
    "nombre": "el nombre",
    "clase": "la clase",
    "avatar": "el avatar",
    "usuario": "el usuario",
    "correo": "el correo",
    "estado": "el estado",
}


def _lista_en_texto(partes):
    """«el nombre», «el nombre y la clase», «el nombre, la clase y el avatar»."""
    if len(partes) <= 1:
        return "".join(partes)
    return ", ".join(partes[:-1]) + " y " + partes[-1]


def _mensaje_cambios(cuenta, cambios):
    nombre = cuenta.get_full_name()
    if not cambios:
        return f"No has cambiado nada en la cuenta de {nombre}."
    texto = f"Cambios guardados en la cuenta de {nombre}: "
    texto += _lista_en_texto([TEXTO_CAMBIOS[c] for c in cambios]) + "."
    if "clase" in cambios:
        estudiante = cuenta.estudiante
        texto += f" Ahora está en {estudiante.clase.nombre}"
        if estudiante.tutor_id:
            texto += (
                f" y sigue con su tutor, {estudiante.tutor.get_full_name()}"
                " (se cambia en «Vínculos»)"
            )
        texto += "."
    if "estado" in cambios:
        texto += (
            " Ya puede entrar."
            if cuenta.is_active
            else " Ya no puede entrar; conserva sus datos y sus vínculos."
        )
    return texto


@admin_requerido
@require_http_methods(["GET", "POST"])
def editar_cuenta(request, pk):
    """B23 · Editar cuenta (PA1 a PA5), activar o desactivar y restablecer la contraseña."""
    cuenta = get_object_or_404(
        Usuario.objects.select_related("estudiante__clase", "estudiante__tutor"), pk=pk
    )
    aqui = reverse("usuarios:editar", args=[cuenta.pk])
    puede_restablecer = edicion.puede_restablecer(cuenta, request.user)

    if request.method == "POST" and request.POST.get("accion") == "restablecer":
        if not puede_restablecer:
            raise PermissionDenied
        request.session[CLAVE_TEMPORAL] = {
            "pk": cuenta.pk,
            "valor": edicion.restablecer_contrasena(cuenta),
        }
        return redirect(aqui)

    if request.method == "POST":
        form = EditarCuentaForm(request.POST, request.FILES, cuenta=cuenta, quien=request.user)
    else:
        form = EditarCuentaForm(cuenta=cuenta, quien=request.user)
    if form.is_bound and form.is_valid():
        messages.success(request, _mensaje_cambios(cuenta, form.guardar()))
        return redirect("usuarios:lista")

    # HU-01-03: lo que se borraría con la cuenta o por qué no se puede (B24).
    baja = bajas.baja_de(cuenta, request.user)
    # La contraseña temporal se enseña una sola vez, justo después de crearla.
    guardada = request.session.pop(CLAVE_TEMPORAL, None)
    temporal = guardada["valor"] if guardada and guardada.get("pk") == cuenta.pk else ""
    return render(
        request,
        "usuarios/editar_cuenta.html",
        {
            "cuenta": cuenta,
            "form": form,
            "puede_restablecer": puede_restablecer,
            "temporal": temporal,
            "es_propia": cuenta.pk == request.user.pk,
            "baja": baja,
        },
    )


# --- HU-01-03 · Eliminar un usuario (solo el administrador) -----------------------


@admin_requerido
@require_http_methods(["GET", "POST"])
def eliminar_cuenta(request, pk):
    """B24 · ¿Eliminar la cuenta? (PA1 a PA5).

    Con JavaScript la pregunta es una ventana dentro de «Editar cuenta»; esta página es la
    misma pregunta sin él. El borrado solo se hace con POST y después de confirmar.
    """
    cuenta = get_object_or_404(Usuario.objects.select_related("estudiante"), pk=pk)
    baja = bajas.baja_de(cuenta, request.user)
    if request.method == "POST" and baja.se_puede:
        nombre = cuenta.get_full_name() or cuenta.username
        es_estudiante = cuenta.es_estudiante
        bajas.eliminar(cuenta)
        texto = f"Cuenta eliminada: {nombre}."
        if es_estudiante:
            texto += " Se han borrado también su agenda y todo lo que había hecho."
        messages.success(request, texto)
        return redirect("usuarios:lista")
    # Un POST que no se puede hacer (otra pestaña, otro administrador…) vuelve a explicar
    # por qué, sin borrar nada.
    estado = 409 if request.method == "POST" else 200
    return render(
        request, "usuarios/eliminar_cuenta.html", {"cuenta": cuenta, "baja": baja}, status=estado
    )


@login_required
@require_http_methods(["GET", "POST"])
def cambiar_contrasena(request):
    """B15 · Quien entra con una contraseña temporal elige la suya antes de seguir."""
    usuario = request.user
    if usuario.es_estudiante or not usuario.debe_cambiar_contrasena:
        return redirect(destino_tras_entrar(usuario))
    form = CambiarContrasenaForm(usuario, request.POST or None)
    if form.is_valid():
        form.save()
        # Al cambiar la contraseña Django cierra las sesiones de ese usuario: esta no.
        update_session_auth_hash(request, usuario)
        messages.success(request, "Contraseña cambiada. Úsala la próxima vez que entres.")
        return redirect(destino_tras_entrar(usuario))
    return render(request, "usuarios/cambiar_contrasena.html", {"form": form})


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


# --- HU-01-09 · Consultar la agenda de mis estudiantes (Javi) --------------------


DIAS_CONSULTABLES = 366


def _fecha_pedida(request):
    """La fecha de ?dia=AAAA-MM-DD, o hoy si no viene o no es válida."""
    hoy = timezone.localdate()
    try:
        fecha = date.fromisoformat(request.GET.get("dia", ""))
    except ValueError:
        return hoy, hoy
    # Como mucho un año antes o después: fuera de ahí no hay agenda que consultar, y con
    # 9999-12-31 sumar un día desbordaba y la página daba un error 500.
    if abs((fecha - hoy).days) > DIAS_CONSULTABLES:
        return hoy, hoy
    return fecha, hoy


@login_required
@require_GET
def agenda_estudiante(request, codigo):
    """B27 · Agenda de un estudiante, solo consulta (PA1, PA2 y PA3).

    Solo para el profesional que lo atiende: si no lo atiende, 404 (no se dice si el
    estudiante existe). Se pasa de un día a otro con ?dia=AAAA-MM-DD.
    """
    _solo_profesional(request)
    estudiante = get_object_or_404(
        Estudiante.objects.select_related("usuario", "clase"),
        codigo_estudiante=codigo.upper(),
        usuario__is_active=True,
    )
    if not atencion.atiende(request.user, estudiante):
        raise Http404("No atiendes a este estudiante.")
    fecha, hoy = _fecha_pedida(request)
    return render(
        request,
        "usuarios/agenda_estudiante.html",
        {
            "estudiante": estudiante,
            "fecha": fecha,
            "fecha_texto": consulta.fecha_en_texto(fecha),
            "es_hoy": fecha == hoy,
            "anterior": fecha - timedelta(days=1),
            "siguiente": fecha + timedelta(days=1),
            "tareas": consulta.tareas_del_dia(estudiante, fecha, request.user),
            "horario": consulta.horario_del_dia(estudiante, fecha),
        },
    )
