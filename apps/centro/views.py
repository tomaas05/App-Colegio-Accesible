"""Pantallas de las tareas del centro (Objetivo 5, Javi).

HU-05-03 · Comedor y menú (administrador): de un mes, quién reparte el menú, el menú del
mes y quién se encarga del comedor cada día (boceto B67, «Tareas del centro»).
HU-05-04 · Anotar quién come (el estudiante encargado del comedor de hoy): las clases (B60)
y los compañeros de cada clase (B61).
HU-05-01 · Reprografía (tutor y administrador, boceto B66): los trabajos de hoy en adelante,
crear uno, cambiarlo mientras el estudiante no lo empiece y ver sus fases. Se entra desde
«Tareas del centro», la opción del menú lateral que reúne las tareas del centro.
"""

import re
from datetime import date
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.agenda.acceso import estudiante_requerido
from apps.usuarios.models import Clase, Estudiante, Rol
from apps.usuarios.permisos import admin_requerido

from . import comedor as quien_come
from . import reprografia, servicios
from .forms import FormComedor, FormMenu, FormReparto, FormReprografia
from .models import ComedorDelDia

MES = re.compile(r"(\d{4})-(\d{2})")


def _mes_pedido(valor):
    """«2026-11» → 1/11/2026. Si no es un mes válido, el mes de hoy."""
    encontrado = MES.fullmatch(valor or "")
    if encontrado:
        anio, mes = int(encontrado[1]), int(encontrado[2])
        if 2000 <= anio <= 2100 and 1 <= mes <= 12:
            return date(anio, mes, 1)
    return servicios.primer_dia(servicios.hoy())


def _fecha(valor):
    try:
        return date.fromisoformat(valor)
    except ValueError:
        return None


def reparto_actual(mes):
    """La asignación del reparto del mes, o None."""
    reparto = servicios.reparto_del_mes(mes)
    return reparto.asignacion if reparto else None


def _url_mes(mes):
    return f"{reverse('centro:comedor')}?mes={mes:%Y-%m}"


@admin_requerido
@require_http_methods(["GET", "POST"])
def comedor(request):
    """HU-05-03 (PA1 a PA5). Solo el administrador."""
    datos = request.POST if request.method == "POST" else request.GET
    mes = _mes_pedido(datos.get("mes"))
    usuario = request.user
    accion = request.POST.get("accion", "")
    abierto = ""  # qué formulario se enseña abierto (el que tiene errores)
    error = None
    comedor_abierto = None  # «Cambiar» en un día con estudiante: su ComedorDelDia

    form_comedor = FormComedor(usuario=usuario, mes=mes)
    form_reparto = FormReparto(usuario=usuario)
    form_menu = FormMenu()

    # «Asignar», «Cambiar» o «Subir»: la pantalla enseña solo ese formulario (sin
    # desplazamiento, decisión 0005). En un día de la lista, el formulario trae ese día.
    if request.method == "GET":
        abierto = request.GET.get("abrir", "")
        if abierto not in ("comedor", "reparto", "menu"):
            abierto = ""
        if abierto == "comedor" and request.GET.get("dia"):
            inicial = {"dia": request.GET["dia"]}
            comedor_abierto = ComedorDelDia.objects.filter(fecha=_fecha(request.GET["dia"])).first()
            if comedor_abierto:  # «Cambiar»: con su estudiante y sus horas
                a = comedor_abierto.asignacion
                inicial.update(
                    estudiante=a.estudiante_id, hora_inicio=a.hora_inicio, hora_fin=a.hora_fin
                )
            form_comedor = FormComedor(usuario=usuario, mes=mes, initial=inicial)
        a = reparto_actual(mes) if abierto == "reparto" else None
        if a:
            form_reparto = FormReparto(
                usuario=usuario,
                initial={
                    "estudiante": a.estudiante_id,
                    "dias": a.dias_semana,
                    "hora_inicio": a.hora_inicio,
                    "hora_fin": a.hora_fin,
                },
            )

    if request.method == "POST":
        try:
            if accion == "comedor":
                form_comedor = FormComedor(request.POST, usuario=usuario, mes=mes)
                abierto = "comedor"
                if form_comedor.is_valid():
                    d = form_comedor.cleaned_data
                    resultado = servicios.asignar_comedor(
                        d["dia"], d["estudiante"], d["hora_inicio"], d["hora_fin"], usuario
                    )
                    messages.success(request, resultado.texto)
                    return redirect(_url_mes(mes))
            elif accion == "quitar_comedor":
                fecha = date.fromisoformat(request.POST.get("dia", ""))
                estudiante = servicios.quitar_comedor(fecha)
                if estudiante:
                    messages.success(
                        request,
                        f"Comedor del {servicios.texto_fecha(fecha)}: pendiente de asignar "
                        f"(quitado {estudiante.usuario.get_full_name()}).",
                    )
                return redirect(_url_mes(mes))
            elif accion == "reparto":
                form_reparto = FormReparto(request.POST, usuario=usuario)
                abierto = "reparto"
                if form_reparto.is_valid():
                    d = form_reparto.cleaned_data
                    resultado = servicios.asignar_reparto(
                        mes, d["estudiante"], d["hora_inicio"], d["hora_fin"], d["dias"], usuario
                    )
                    messages.success(request, resultado.texto)
                    return redirect(_url_mes(mes))
            elif accion == "quitar_reparto":
                estudiante = servicios.quitar_reparto(mes)
                if estudiante:
                    messages.success(
                        request,
                        f"Reparto del menú de {servicios.nombre_mes(mes)}: pendiente de asignar "
                        f"(quitado {estudiante.usuario.get_full_name()}).",
                    )
                return redirect(_url_mes(mes))
            elif accion == "menu":
                form_menu = FormMenu(request.POST, request.FILES)
                abierto = "menu"
                if form_menu.is_valid():
                    servicios.subir_menu(mes, form_menu.cleaned_data["archivo"])
                    messages.success(request, f"Guardado el menú de {servicios.nombre_mes(mes)}.")
                    return redirect(_url_mes(mes))
            elif accion == "quitar_menu":
                servicios.quitar_menu(mes)
                messages.success(request, f"Quitado el menú de {servicios.nombre_mes(mes)}.")
                return redirect(_url_mes(mes))
        except servicios.ErrorDeCentro as e:
            error = str(e)
        except ValueError:
            error = "No se ha guardado: el día no es válido."

    mes_pasado = servicios.ultimo_dia(mes) < servicios.hoy()
    if mes_pasado:
        abierto = ""  # un mes que ya ha pasado solo se consulta
    hay_errores = bool(error or form_comedor.errors or form_reparto.errors or form_menu.errors)
    reparto = servicios.reparto_del_mes(mes)
    menu = reparto.menu if reparto and reparto.menu else None
    return render(
        request,
        "centro/comedor.html",
        {
            "mes": mes,
            "nombre_mes": servicios.nombre_mes(mes),
            "mes_anterior": servicios.mes_anterior(mes),
            "mes_siguiente": servicios.mes_siguiente(mes),
            "mes_param": f"{mes:%Y-%m}",
            "url_mes": _url_mes(mes),
            "nombre_mes_anterior": servicios.nombre_mes(servicios.mes_anterior(mes)),
            "nombre_mes_siguiente": servicios.nombre_mes(servicios.mes_siguiente(mes)),
            "corto_anterior": servicios.MESES[servicios.mes_anterior(mes).month - 1],
            "corto_siguiente": servicios.MESES[servicios.mes_siguiente(mes).month - 1],
            "mes_pasado": mes_pasado,
            "mes_empezado": mes < servicios.hoy(),
            "dias": servicios.comedor_del_mes(mes),
            "reparto": reparto,
            "texto_dias_reparto": (
                servicios.texto_dias(reparto.asignacion.dias_semana)
                if reparto and reparto.asignacion
                else ""
            ),
            "menu": menu,
            "menu_es_imagen": bool(menu) and servicios.menu_es_imagen(menu),
            "form_comedor": form_comedor,
            "form_reparto": form_reparto,
            "form_menu": form_menu,
            "abierto": abierto,
            "comedor_abierto": comedor_abierto,
            "texto_dia_abierto": (
                servicios.texto_fecha(comedor_abierto.fecha) if comedor_abierto else ""
            ),
            "error": error,
        },
        status=400 if hay_errores else 200,
    )


# --- HU-05-04 · Anotar quién come (el estudiante encargado del comedor de hoy) -----------


def _encargado(vista):
    """Solo entra el estudiante que hoy tiene el comedor (HU-05-03). Deja su ComedorDelDia
    en `request.encargo`."""

    @estudiante_requerido
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        request.encargo = quien_come.encargo_de_hoy(request.estudiante)
        if request.encargo is None:
            raise PermissionDenied  # hoy no le toca: la tarea no está en su agenda
        return vista(request, *args, **kwargs)

    return envoltura


def _volver_a_la_tarea(request):
    return reverse("agenda:detalle", args=[request.encargo.asignacion_id])


@_encargado
@require_GET
def comedor_hoy(request):
    """B60 · Las clases del centro: cuántos lleva marcados de cada una, cuáles ha terminado y
    cuántos comen hoy en todo el centro (PA1, PA4, RF5.2.7)."""
    return render(
        request,
        "centro/comedor_hoy.html",
        {"resumen": quien_come.resumen(servicios.hoy()), "volver": _volver_a_la_tarea(request)},
    )


def _clase(pk):
    """La clase, si es del centro (tiene algún estudiante activo). Si no, 404."""
    return get_object_or_404(
        Clase.objects.filter(estudiantes__usuario__is_active=True).distinct(), pk=pk
    )


def _es_htmx(request):
    return request.headers.get("HX-Request") == "true"


def _url_clase(clase, ultimo=""):
    url = reverse("centro:comedor_clase", args=[clase.pk])
    return f"{url}?ultimo={ultimo}" if ultimo else url


def _pantalla_clase(request, clase, tocado=None):
    """B61. `tocado`: el compañero que se acaba de marcar, para anunciarlo al lector."""
    hoy = servicios.hoy()
    dia = quien_come.clase_del_dia(clase, hoy)
    anuncio = next(
        (
            f"{c.nombre}: {'come' if c.come else 'no come'}."
            for c in dia.companeros
            if c.estudiante.pk == tocado and c.marcado
        ),
        "",
    )
    return render(
        request,
        "centro/comedor_clase.html",
        {
            "dia": dia,
            "comen_hoy": quien_come.comen_hoy(hoy),
            "anuncio": anuncio,
            "ultimo": request.GET.get("ultimo", ""),
        },
    )


@_encargado
@require_GET
def comedor_clase(request, pk):
    """B61 · Los compañeros de una clase con su avatar y su marca (PA1, PA2, PA3)."""
    return _pantalla_clase(request, _clase(pk))


@_encargado
@require_POST
def comedor_marcar(request, pk, codigo):
    """PA2 y PA3: un toque en el compañero cambia su marca (come / no come).

    El formulario envía la marca que tiene que quedar (`come=1` o `0`), así que si el mismo
    toque llega dos veces (doble pulsación sin JavaScript, reintento) no se deshace. Con HTMX
    solo cambia su marca, el recuento y los mensajes; sin JavaScript, vuelve a la clase.
    """
    clase = _clase(pk)
    companero = get_object_or_404(
        Estudiante.objects.select_related("usuario", "clase"),
        codigo_estudiante=codigo,
        clase=clase,
        usuario__is_active=True,
    )
    htmx = _es_htmx(request)
    come = request.POST.get("come")
    try:
        if come in ("0", "1"):
            quien_come.marcar(request.estudiante, companero, come == "1")
        else:
            quien_come.cambiar(request.estudiante, companero)
    except servicios.ErrorDeCentro as e:
        messages.error(request, str(e))
        if htmx:
            # La pantalla ya no vale (p. ej. la clase se ha terminado en otra pestaña):
            # se carga entera, con el mensaje.
            respuesta = HttpResponse(status=204)
            respuesta["HX-Redirect"] = _url_clase(clase, codigo)
            return respuesta
        return redirect(_url_clase(clase, codigo))
    if htmx:
        return _pantalla_clase(request, clase, tocado=companero.pk)
    return redirect(_url_clase(clase, codigo))


@_encargado
@require_POST
def comedor_terminar(request, pk):
    """PA4 y PA5: «Clase terminada» si todos tienen marca. Vuelve a las clases."""
    clase = _clase(pk)
    try:
        quien_come.terminar_clase(request.estudiante, clase)
    except servicios.ErrorDeCentro as e:
        messages.error(request, str(e))
        return redirect(_url_clase(clase))
    faltan = quien_come.resumen(servicios.hoy()).texto_faltan
    messages.success(request, f"{clase.nombre} terminada. {faltan}")
    return redirect("centro:comedor_hoy")


# --- HU-05-01 · Reprografía (tutor y administrador) ------------------------------------


def _tutor_o_admin(vista):
    """Solo el tutor y el administrador. Sin sesión, a la portada; con otro rol, 403."""

    @login_required
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not reprografia.puede_crear(request.user):
            raise PermissionDenied
        return vista(request, *args, **kwargs)

    return envoltura


# «Tareas del centro»: lo que sale dentro de esa opción del menú lateral, con el mismo
# aspecto que las tarjetas del panel (B13). De momento solo la reprografía; las tareas del
# centro que se hagan más adelante se añaden aquí: (texto, descripción, nombre de la URL,
# icono de templates/_icono.html).
TAREAS_DEL_CENTRO = [
    (
        "Reprografía",
        "Poner a un estudiante a imprimir, fotocopiar o plastificar un trabajo.",
        "centro:reprografia",
        "impresora",
    ),
]


@_tutor_o_admin
@require_GET
def tareas_del_centro(request):
    """La página de «Tareas del centro»: una tarjeta por cada tarea del centro."""
    opciones = [
        {"texto": texto, "descripcion": descripcion, "url": reverse(url), "icono": icono}
        for texto, descripcion, url, icono in TAREAS_DEL_CENTRO
    ]
    return render(request, "centro/tareas.html", {"opciones": opciones})


def _fila(request, pk):
    """El trabajo, si es de un estudiante que ve el usuario (si no, 404), con su día."""
    trabajo = get_object_or_404(
        reprografia.visibles(request.user).select_related(
            "asignacion__estudiante__usuario", "asignacion__estudiante__clase"
        ),
        pk=pk,
    )
    return reprografia.Fila(trabajo, *reprografia.como_queda(trabajo))


def _texto_guardado(trabajo, verbo):
    a = trabajo.asignacion
    return (
        f"Reprografía {verbo} en la agenda de {a.estudiante.usuario.get_full_name()}: "
        f"{servicios.texto_fecha(a.vigencia_desde)}, de {a.hora_inicio:%H:%M} a "
        f"{a.hora_fin:%H:%M}."
    )


@_tutor_o_admin
@require_GET
def reprografia_lista(request):
    """PA1: los trabajos de reprografía de hoy en adelante y «Nueva tarea de reprografía»."""
    return render(
        request,
        "centro/reprografia.html",
        {"filas": reprografia.lista(request.user)},
    )


def _formulario(request, fila=None):
    """«Nueva» (sin fila) o «Cambiar» (con la fila del trabajo)."""
    usuario = request.user
    error = None
    if request.method == "POST" and request.POST.get("accion") == "quitar" and fila:
        try:
            reprografia.quitar(fila.trabajo)
        except servicios.ErrorDeCentro as e:
            messages.error(request, str(e))
            return redirect("centro:reprografia_cambiar", pk=fila.trabajo.pk)
        messages.success(
            request,
            f"Quitada la reprografía de la agenda de {fila.estudiante.usuario.get_full_name()}.",
        )
        return redirect("centro:reprografia")
    if request.method == "POST":
        form = FormReprografia(request.POST, usuario=usuario)
        if form.is_valid():
            try:
                if fila:
                    trabajo = reprografia.cambiar(fila.trabajo, form.datos(), usuario)
                    texto = _texto_guardado(trabajo, "cambiada")
                else:
                    trabajo = reprografia.crear(form.datos(), usuario)
                    texto = _texto_guardado(trabajo, "creada")
            except servicios.ErrorDeCentro as e:
                error = str(e)
            else:
                messages.success(request, texto)
                return redirect("centro:reprografia")
    elif fila:
        form = FormReprografia.de_un_trabajo(fila, usuario=usuario)
    else:
        form = FormReprografia(usuario=usuario)
    return render(
        request,
        "centro/reprografia_form.html",
        {"form": form, "fila": fila, "error": error},
        status=400 if (error or form.errors) else 200,
    )


@_tutor_o_admin
@require_http_methods(["GET", "POST"])
def reprografia_nueva(request):
    """PA1 y PA2: crear la tarea de reprografía en la agenda de un estudiante."""
    return _formulario(request)


@_tutor_o_admin
@require_http_methods(["GET", "POST"])
def reprografia_cambiar(request, pk):
    """Cambiar (o quitar) un trabajo. PA4: si ya no está pendiente (la ha empezado, ya
    pasó su hora o está cancelada), solo se ven sus datos."""
    fila = _fila(request, pk)
    if not fila.se_puede_cambiar:
        if request.method == "POST":
            # Lo ha empezado mientras se rellenaba el formulario: no se guarda nada.
            messages.error(request, reprografia.por_que_no_se_cambia(fila.trabajo, fila.estado))
            return redirect("centro:reprografia_cambiar", pk=pk)
        return render(request, "centro/reprografia_ver.html", {"fila": fila})
    return _formulario(request, fila)


@_tutor_o_admin
@require_GET
def reprografia_fases(request):
    """PA3: las fases con las que viene la tarea. El tutor las cambia en «Pasos de la
    tarea» (HU-03-02, Úrsula); el administrador no entra ahí (no gestiona tareas)."""
    tarea, pasos = reprografia.fases(request.user)
    return render(
        request,
        "centro/reprografia_fases.html",
        {
            "tarea": tarea,
            "pasos": pasos,
            "puede_cambiar": request.user.rol == Rol.TUTOR,
        },
    )
