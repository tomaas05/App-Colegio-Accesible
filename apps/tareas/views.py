"""Crear tareas, verlas y asignarlas (Úrsula): HU-03-01 y HU-03-03.

Permisos: solo tutor, profesional o familiar (permisos.py). Los estudiantes a los que
se puede asignar salen de `estudiantes_de(request.user)`, la única regla de visibilidad.
Pictogramas: el servidor los trae de ARASAAC y guarda una copia (decisión 0004).
"""

from datetime import date, timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from apps.comun import pictogramas
from apps.comun.models import TipoAviso, avisar
from apps.horario.servicios import choca_con_horario_escolar
from apps.usuarios.models import Rol

from . import planificacion
from .forms import (
    AnadirPlanBForm,
    AsignacionForm,
    CrearAlternativaForm,
    EditarAsignacionForm,
    FiltroPlanificadasForm,
    HorasForm,
    PasoFormSet,
    TareaForm,
)
from .models import Asignacion, ExcepcionAsignacion, PlanB, Tarea, TipoExcepcion
from .permisos import gestiona_tareas

MAX_PASOS = 30
SIN_PICTOGRAMA = (
    "No se ha podido traer el pictograma de ARASAAC. "
    "Vuelve a intentarlo o sube una imagen de tu equipo."
)


@gestiona_tareas
@require_GET
def catalogo_tareas(request):
    tareas = Tarea.objects.annotate(
        n_pasos=Count("pasos", distinct=True), n_planes_b=Count("planes_b", distinct=True)
    ).order_by("-id")
    return render(request, "tareas/catalogo.html", {"tareas": tareas})


def _poner_pictograma(objeto, identificador):
    """Si no se ha subido un archivo, la imagen es la copia local del pictograma elegido."""
    if identificador and not objeto.imagen:
        objeto.imagen = pictogramas.obtener(identificador)


def _guardar(form, formset, usuario):
    """Guarda la tarea y sus pasos, numerados del 1 en adelante en el orden enviado."""
    tarea = form.save(commit=False)
    tarea.creador = usuario
    _poner_pictograma(tarea, form.cleaned_data.get("arasaac_id_tarea"))
    tarea.save()

    validos = [
        paso_form
        for paso_form in formset.forms
        if paso_form.cleaned_data and not paso_form.cleaned_data.get("DELETE")
    ]
    validos.sort(key=lambda paso_form: paso_form.cleaned_data.get("orden") or 0)
    for orden, paso_form in enumerate(validos, start=1):
        paso = paso_form.save(commit=False)
        paso.tarea = tarea
        paso.orden = orden
        _poner_pictograma(paso, paso_form.cleaned_data.get("arasaac_id_paso"))
        paso.save()
    return tarea


@gestiona_tareas
@require_http_methods(["GET", "POST"])
def crear_tarea(request):
    """B40 y B41 · Crear tarea con su imagen y sus pasos."""
    if request.method == "POST":
        form = TareaForm(request.POST, request.FILES)
        formset = PasoFormSet(request.POST, request.FILES, prefix="pasos")
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    tarea = _guardar(form, formset, request.user)
            except pictogramas.ErrorArasaac:
                form.add_error(None, SIN_PICTOGRAMA)
            else:
                messages.success(request, f"La tarea «{tarea.nombre}» se ha creado.")
                return redirect("tareas:catalogo")
    else:
        form = TareaForm()
        formset = PasoFormSet(prefix="pasos")
    return render(request, "tareas/crear_tarea.html", {"form": form, "formset": formset})


@gestiona_tareas
@require_GET
def anadir_paso(request):
    """Un paso nuevo y vacío para el formulario de crear tarea. Lo pide HTMX."""
    try:
        numero = int(request.GET.get("total_forms", 0))
    except ValueError:
        return HttpResponseBadRequest("total_forms no es un número.")
    if not 0 <= numero < MAX_PASOS:
        return HttpResponseBadRequest("Demasiados pasos.")
    formset = PasoFormSet(prefix="pasos")
    paso_form = formset.empty_form
    paso_form.prefix = f"pasos-{numero}"
    return render(request, "tareas/_paso.html", {"paso_form": paso_form, "numero": numero + 1})


@gestiona_tareas
@require_http_methods(["GET", "POST"])
def asignar_tarea(request, tarea_id=None):
    """B43 · Asignar una tarea a uno o varios de mis estudiantes, sin solapes de horario."""
    tarea_inicial = get_object_or_404(Tarea, id=tarea_id) if tarea_id else None

    if request.method == "POST":
        form = AsignacionForm(request.POST, usuario=request.user)
        # HU-03-11, PA5 (Javi): el familiar solo pone tareas para casa fuera del horario escolar.
        if (
            form.is_valid()
            and request.user.rol == Rol.FAMILIAR
            and choca_con_horario_escolar(
                form.cleaned_data["dias_semana"],
                form.cleaned_data["hora_inicio"],
                form.cleaned_data["hora_fin"],
            )
        ):
            form.add_error(
                None,
                "Esas horas son de horario escolar. Las tareas para casa se ponen fuera "
                "de las horas de clase.",
            )
        if form.is_valid():
            datos = form.cleaned_data
            with transaction.atomic():
                for estudiante in datos["estudiantes"]:
                    Asignacion.objects.create(
                        tarea=datos["tarea"],
                        estudiante=estudiante,
                        asignado_por=request.user,
                        hora_inicio=datos["hora_inicio"],
                        hora_fin=datos["hora_fin"],
                        dias_semana=datos["dias_semana"],
                        vigencia_desde=datos.get("vigencia_desde"),
                        vigencia_hasta=datos.get("vigencia_hasta"),
                    )
            messages.success(request, f"La tarea «{datos['tarea'].nombre}» se ha asignado.")
            return redirect("tareas:catalogo")
    else:
        inicial = {"tarea": tarea_inicial} if tarea_inicial else {}
        form = AsignacionForm(initial=inicial, usuario=request.user)

    return render(request, "tareas/asignar_tarea.html", {"form": form, "tarea": tarea_inicial})


# --- Tareas planificadas (B44): HU-03-04 modificar y HU-03-05 cancelar ---


def _fecha_de(request):
    """La fecha de «Solo este día» (?fecha=AAAA-MM-DD), o None si no hay o no es válida."""
    try:
        return date.fromisoformat(request.GET.get("fecha") or request.POST.get("fecha") or "")
    except ValueError:
        return None


def _alcance_de(request):
    alcance = request.POST.get("alcance") or request.GET.get("alcance")
    return "dia" if alcance == "dia" else "serie"


def _filtros_de(request):
    """Los filtros con los que se salió de la lista (f_estudiante y f_fecha): se guardan en
    campos ocultos para volver a ella igual después de guardar o cancelar."""
    return {
        clave: request.GET.get(clave) or request.POST.get(clave) or ""
        for clave in ("f_estudiante", "f_fecha")
    }


def _volver_a_planificadas(request):
    """La lista con los mismos filtros con los que se salió de ella."""
    filtros = {clave[2:]: valor for clave, valor in _filtros_de(request).items() if valor}
    url = reverse("tareas:tareas_planificadas")
    return f"{url}?{urlencode(filtros)}" if filtros else url


def _asignacion_que_puede_cambiar(request, asignacion_id):
    """La asignación, si quien entra la puede cambiar. Si no, 404: ni se dice que existe."""
    asignacion = get_object_or_404(
        Asignacion.objects.select_related("tarea", "estudiante__usuario", "asignado_por"),
        id=asignacion_id,
    )
    if not planificacion.puede_cambiar(request.user, asignacion):
        raise Http404
    return asignacion


def _empezada(asignacion, fecha):
    """Si el estudiante ya ha empezado (o hecho) la tarea ese día: entonces no se toca."""
    from apps.agenda.models import Ejecucion

    return Ejecucion.objects.filter(
        asignacion=asignacion, fecha=fecha, inicio_real__isnull=False
    ).exists()


def _dia_valido(asignacion, fecha, hoy):
    """«Solo este día»: una fecha de hoy en adelante en la que la tarea toca y no está
    cancelada."""
    if fecha is None or fecha < hoy or not asignacion.aplica_el(fecha):
        return False
    excepcion = asignacion.excepciones.filter(fecha=fecha).first()
    return not planificacion.ocurrencia(asignacion, fecha, excepcion).cancelada


@gestiona_tareas
@require_GET
def tareas_planificadas(request):
    """B44 · Las tareas que puedo cambiar, por estudiante y por día.

    Con un día elegido, las que tocan ese día (con sus horas de ese día) y se puede
    cambiar solo ese día o toda la serie. Sin día, todas las series vigentes.
    """
    hoy = timezone.localdate()
    filtro = FiltroPlanificadasForm(request.GET or None, usuario=request.user, hoy=hoy)
    estudiante = fecha = None
    if filtro.is_valid():
        estudiante = filtro.cleaned_data["estudiante"]
        fecha = filtro.cleaned_data["fecha"]

    # Una serie cancelada ya no se planifica (sigue tachada en la agenda unos días).
    asignaciones = (
        planificacion.que_puede_cambiar(request.user)
        .select_related("tarea", "estudiante__usuario")
        .filter(cancelada=False)
        .filter(Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=fecha or hoy))
        .order_by("estudiante__usuario__first_name", "hora_inicio", "pk")
    )
    if estudiante:
        asignaciones = asignaciones.filter(estudiante=estudiante)

    filas = []
    if fecha:
        excepciones = {
            e.asignacion_id: e
            for e in ExcepcionAsignacion.objects.filter(asignacion__in=asignaciones, fecha=fecha)
        }
        for a in asignaciones.filter(dias_semana__contains=[fecha.isoweekday()]):
            if not a.aplica_el(fecha):
                continue
            filas.append(planificacion.ocurrencia(a, fecha, excepciones.get(a.pk)))
        filas.sort(key=lambda o: (o.asignacion.estudiante.usuario.first_name, o.hora_inicio))
    else:
        filas = [planificacion.ocurrencia(a, hoy) for a in asignaciones]

    return render(
        request,
        "tareas/tareas_planificadas.html",
        {
            "filtro": filtro,
            "filas": filas,
            "fecha": fecha,
            "fecha_texto": planificacion.fecha_en_texto(fecha) if fecha else "",
            "estudiante": estudiante,
            "filtros_url": request.GET.urlencode(),
        },
    )


@gestiona_tareas
@require_http_methods(["GET", "POST"])
def editar_asignacion(request, asignacion_id):
    """HU-03-04 · Cambiar las horas de un solo día, o las horas y los días de toda la serie.

    Un cambio que se solapa con otra tarea no se guarda y se dice con cuál (PA3). El
    estudiante recibe un aviso con una frase y el pictograma de la tarea (PA4).
    """
    asignacion = _asignacion_que_puede_cambiar(request, asignacion_id)
    hoy = timezone.localdate()
    alcance, fecha = _alcance_de(request), _fecha_de(request)
    volver = _volver_a_planificadas(request)
    estudiante, tarea = asignacion.estudiante, asignacion.tarea

    if asignacion.cancelada:
        messages.error(request, f"«{tarea.nombre}» está cancelada: ya no se puede cambiar.")
        return redirect(volver)
    if alcance == "dia" and not _dia_valido(asignacion, fecha, hoy):
        messages.error(request, "Ese día no se puede cambiar. Elige otro día en la lista.")
        return redirect(volver)
    # Lo que el estudiante ya ha empezado no se cambia: ese día, si es solo un día; hoy,
    # si es la serie y la está haciendo ahora (si ya la ha terminado, sí se puede).
    if (alcance == "dia" and _empezada(asignacion, fecha)) or (
        alcance == "serie" and _en_marcha(asignacion, hoy)
    ):
        messages.error(
            request,
            f"{estudiante.usuario.first_name} ya ha empezado «{tarea.nombre}» "
            f"{'ese día' if alcance == 'dia' else 'hoy'}: cámbiala cuando la termine.",
        )
        return redirect(volver)

    if alcance == "dia":
        actual = planificacion.ocurrencia(
            asignacion, fecha, asignacion.excepciones.filter(fecha=fecha).first()
        )
        form = HorasForm(
            request.POST or None,
            initial={"hora_inicio": actual.hora_inicio, "hora_fin": actual.hora_fin},
        )
    else:
        form = EditarAsignacionForm(request.POST or None, instance=asignacion)

    if request.method == "POST" and form.is_valid():
        datos = form.cleaned_data
        inicio, fin = datos["hora_inicio"], datos["hora_fin"]
        dias = [fecha.isoweekday()] if alcance == "dia" else datos["dias_semana"]
        choque = None
        if request.user.rol == Rol.FAMILIAR and choca_con_horario_escolar(dias, inicio, fin):
            form.add_error(None, HORARIO_ESCOLAR_FAMILIAR)
        elif alcance == "dia":
            choque = planificacion.choque_en_fecha(
                estudiante, fecha, inicio, fin, excluir=asignacion
            )
        else:
            choque = planificacion.choque_en_serie(
                estudiante,
                dias,
                inicio,
                fin,
                datos["vigencia_desde"],
                datos.get("vigencia_hasta"),
                excluir=asignacion,
                hoy=hoy,
            )
        if not form.errors and choque:
            form.add_error(None, f"Se solapa con {choque.texto}. Elige otras horas.")
        if not form.errors:
            with transaction.atomic():
                if alcance == "dia":
                    cambia = _guardar_dia(asignacion, fecha, inicio, fin, request.user)
                    texto = (
                        f"«{tarea.nombre}» cambia el {planificacion.fecha_en_texto(fecha)}: "
                        f"será {planificacion.horas_en_texto(inicio, fin)}."
                    )
                else:
                    cambia = form.has_changed()
                    form.save()
                    texto = (
                        f"«{tarea.nombre}» cambia: ahora es "
                        f"{planificacion.horas_en_texto(inicio, fin)}, "
                        f"{planificacion.dias_en_texto(dias)}."
                    )
                if cambia:
                    avisar(estudiante.usuario, texto, tipo=TipoAviso.CAMBIO, tarea=tarea)
            if cambia:
                messages.success(
                    request,
                    f"«{tarea.nombre}» de {estudiante.usuario.get_full_name()} ha cambiado. "
                    f"{estudiante.usuario.first_name} recibe un aviso.",
                )
            else:
                messages.success(request, "No has cambiado nada.")
            return redirect(volver)

    return render(
        request,
        "tareas/editar_asignacion.html",
        {
            "form": form,
            "asignacion": asignacion,
            "tarea": tarea,
            "estudiante": estudiante,
            "alcance": alcance,
            "fecha": fecha,
            "fecha_texto": planificacion.fecha_en_texto(fecha) if fecha else "",
            "volver": volver,
            "filtros": _filtros_de(request),
        },
    )


HORARIO_ESCOLAR_FAMILIAR = (
    "Esas horas son de horario escolar. Las tareas para casa se ponen fuera de las horas de clase."
)


def _en_marcha(asignacion, fecha):
    """La está haciendo ahora: empezada y sin terminar."""
    from apps.agenda.models import Ejecucion, EstadoEjecucion

    return Ejecucion.objects.filter(
        asignacion=asignacion, fecha=fecha, estado=EstadoEjecucion.EN_CURSO
    ).exists()


def _guardar_dia(asignacion, fecha, inicio, fin, usuario):
    """Otras horas solo ese día. Si vuelven a ser las de siempre, se quita la excepción.
    Devuelve si algo ha cambiado."""
    actual = asignacion.excepciones.filter(fecha=fecha).first()
    antes = (
        (actual.hora_inicio, actual.hora_fin)
        if actual
        else (
            asignacion.hora_inicio,
            asignacion.hora_fin,
        )
    )
    if (inicio, fin) == antes:
        return False
    if (inicio, fin) == (asignacion.hora_inicio, asignacion.hora_fin):
        actual.delete()
        return True
    ExcepcionAsignacion.objects.update_or_create(
        asignacion=asignacion,
        fecha=fecha,
        defaults={
            "tipo": TipoExcepcion.MODIFICADA,
            "hora_inicio": inicio,
            "hora_fin": fin,
            "creada_por": usuario,
        },
    )
    return True


@gestiona_tareas
@require_http_methods(["GET", "POST"])
def cancelar_asignacion(request, asignacion_id):
    """HU-03-05 · Cancelar un solo día o toda la serie, después de confirmar (PA3).

    No se cancela lo que el estudiante ya ha empezado (PA2). La tarea sale como
    «Cancelada» en su agenda (PA1) y recibe un aviso (PA4).
    """
    asignacion = _asignacion_que_puede_cambiar(request, asignacion_id)
    hoy = timezone.localdate()
    alcance, fecha = _alcance_de(request), _fecha_de(request)
    volver = _volver_a_planificadas(request)
    estudiante, tarea = asignacion.estudiante, asignacion.tarea

    if asignacion.cancelada:
        messages.error(request, f"«{tarea.nombre}» ya estaba cancelada.")
        return redirect(volver)
    if alcance == "dia":
        if not _dia_valido(asignacion, fecha, hoy):
            messages.error(request, "Ese día no se puede cancelar. Elige otro día en la lista.")
            return redirect(volver)
        if _empezada(asignacion, fecha):
            messages.error(
                request,
                f"{estudiante.usuario.first_name} ya ha empezado «{tarea.nombre}» ese día: "
                "ya no se puede cancelar.",
            )
            return redirect(volver)

    if request.method == "POST":
        with transaction.atomic():
            if alcance == "dia":
                ExcepcionAsignacion.objects.update_or_create(
                    asignacion=asignacion,
                    fecha=fecha,
                    defaults={
                        "tipo": TipoExcepcion.CANCELADA,
                        "hora_inicio": None,
                        "hora_fin": None,
                        "creada_por": request.user,
                    },
                )
                texto = (
                    f"«{tarea.nombre}» del {planificacion.fecha_en_texto(fecha)} se ha cancelado."
                )
            else:
                # Si hoy ya la ha empezado, lo de hoy sigue: se cancela desde mañana.
                desde = hoy + timedelta(days=1) if _empezada(asignacion, hoy) else hoy
                asignacion.cancelada = True
                asignacion.cancelada_el = desde
                asignacion.save(update_fields=["cancelada", "cancelada_el"])
                texto = f"«{tarea.nombre}» se ha cancelado. Ya no la tienes que hacer."
            avisar(estudiante.usuario, texto, tipo=TipoAviso.CANCELACION, tarea=tarea)
        messages.success(
            request,
            f"«{tarea.nombre}» de {estudiante.usuario.get_full_name()} se ha cancelado"
            f"{' el ' + planificacion.fecha_en_texto(fecha) if alcance == 'dia' else ''}. "
            f"{estudiante.usuario.first_name} recibe un aviso.",
        )
        return redirect(volver)

    actual = planificacion.ocurrencia(
        asignacion, fecha or hoy, asignacion.excepciones.filter(fecha=fecha).first()
    )
    return render(
        request,
        "tareas/confirmar_cancelacion.html",
        {
            "asignacion": asignacion,
            "tarea": tarea,
            "estudiante": estudiante,
            "alcance": alcance,
            "fecha": fecha,
            "fecha_texto": planificacion.fecha_en_texto(fecha) if fecha else "",
            "dias_texto": planificacion.dias_en_texto(asignacion.dias_semana),
            "horas_texto": planificacion.horas_en_texto(actual.hora_inicio, actual.hora_fin),
            "volver": volver,
            "filtros": _filtros_de(request),
        },
    )


# --- Plan B de una tarea (HU-03-06, boceto B42) ---


def puede_editar_plan_b(usuario, tarea):
    """El tutor y el profesional, en cualquier tarea del catálogo del centro; el familiar,
    solo en las suyas."""
    if usuario.rol in (Rol.TUTOR, Rol.PROFESIONAL):
        return True
    return usuario.rol == Rol.FAMILIAR and tarea.creador_id == usuario.pk


@gestiona_tareas
@require_http_methods(["GET", "POST"])
def plan_b(request, tarea_id):
    """B42 · Las alternativas de una tarea, en el orden en que se ofrecen al estudiante.

    Se añaden del catálogo o se crean nuevas (nombre y pictograma), se suben, se bajan y
    se quitan. Todo funciona sin JavaScript: cada botón es un formulario.
    """
    tarea = get_object_or_404(Tarea, id=tarea_id)
    if not puede_editar_plan_b(request.user, tarea):
        raise Http404
    anadir = AnadirPlanBForm(tarea=tarea)
    crear = CrearAlternativaForm()
    accion = request.POST.get("accion")
    foco = ""

    if request.method == "POST" and accion in ("subir", "bajar", "quitar"):
        plan = get_object_or_404(PlanB, tarea=tarea, alternativa_id=request.POST.get("alternativa"))
        nombre = plan.alternativa.nombre
        with transaction.atomic():
            lista = list(tarea.planes_b.select_for_update().order_by("orden", "pk"))
            i = lista.index(plan)
            if accion == "quitar":
                lista.pop(i)
                plan.delete()
                texto = f"«{nombre}» ya no está en el plan B."
            else:
                j = i - 1 if accion == "subir" else i + 1
                if 0 <= j < len(lista):
                    lista[i], lista[j] = lista[j], lista[i]
                    texto = f"«{nombre}» es ahora la número {j + 1}."
                elif accion == "subir":
                    texto = f"«{nombre}» ya es la primera."
                else:
                    texto = f"«{nombre}» ya es la última."
                foco = f"{accion}-{plan.alternativa_id}"
            _renumerar(lista)
        messages.success(request, texto)
        destino = reverse("tareas:plan_b", args=[tarea.pk])
        return redirect(f"{destino}?foco={foco}" if foco else destino)

    if request.method == "POST" and accion == "anadir":
        anadir = AnadirPlanBForm(request.POST, tarea=tarea)
        if anadir.is_valid():
            alternativa = anadir.cleaned_data["alternativa"]
            _anadir_al_plan_b(tarea, alternativa)
            messages.success(request, f"«{alternativa.nombre}» se ha añadido al plan B.")
            return redirect("tareas:plan_b", tarea_id=tarea.pk)

    if request.method == "POST" and accion == "crear":
        crear = CrearAlternativaForm(request.POST)
        if crear.is_valid():
            nombre = crear.cleaned_data["nombre"].strip()
            try:
                with transaction.atomic():
                    alternativa = Tarea(
                        nombre=nombre,
                        descripcion_imagen=nombre,
                        ambito=tarea.ambito,
                        creador=request.user,
                    )
                    _poner_pictograma(alternativa, crear.cleaned_data["arasaac_id_alternativa"])
                    alternativa.save()
                    _anadir_al_plan_b(tarea, alternativa)
            except pictogramas.ErrorArasaac:
                crear.add_error(None, SIN_PICTOGRAMA)
            else:
                messages.success(request, f"«{nombre}» se ha creado y se ha añadido al plan B.")
                return redirect("tareas:plan_b", tarea_id=tarea.pk)

    return render(
        request,
        "tareas/plan_b.html",
        {
            "tarea": tarea,
            "planes": tarea.planes_b.select_related("alternativa").order_by("orden", "pk"),
            "anadir": anadir,
            "crear": crear,
            "accion": accion,
            **_foco(request.GET.get("foco", "")),
        },
    )


def _foco(valor):
    """«subir-12» → el botón que tenía el foco antes de recargar (para devolvérselo)."""
    accion, _, numero = valor.partition("-")
    if accion in ("subir", "bajar") and numero.isdigit():
        return {"foco_accion": accion, "foco_id": int(numero)}
    return {"foco_accion": "", "foco_id": None}


def _renumerar(lista):
    """Prioridades 1, 2, 3… en el orden de la lista."""
    for orden, plan in enumerate(lista, start=1):
        if plan.orden != orden:
            plan.orden = orden
            plan.save(update_fields=["orden"])


def _anadir_al_plan_b(tarea, alternativa):
    """La alternativa nueva va la última (la menos preferida); se sube si hace falta."""
    ultimo = tarea.planes_b.order_by("-orden").values_list("orden", flat=True).first() or 0
    PlanB.objects.get_or_create(
        tarea=tarea, alternativa=alternativa, defaults={"orden": ultimo + 1}
    )


@gestiona_tareas
@require_http_methods(["GET", "POST"])
def editar_pasos_tarea(request, tarea_id):
    """HU-03-02 · Añadir, ordenar y modificar los pasos de una tarea existente."""
    tarea = get_object_or_404(Tarea, id=tarea_id)

    if request.method == "POST":
        formset = PasoFormSet(request.POST, request.FILES, prefix="pasos", instance=tarea)
        if formset.is_valid():
            try:
                with transaction.atomic():
                    # Eliminamos primero los marcados para borrado
                    for p_form in formset.deleted_forms:
                        if p_form.instance.pk:
                            p_form.instance.delete()

                    # Obtenemos los formularios válidos que no están marcados para borrar
                    validos = [
                        p_form
                        for p_form in formset.forms
                        if p_form.cleaned_data and not p_form.cleaned_data.get("DELETE")
                    ]
                    # Ordenamos según el campo orden indicado
                    validos.sort(key=lambda pf: pf.cleaned_data.get("orden") or 0)

                    for orden, p_form in enumerate(validos, start=1):
                        paso = p_form.save(commit=False)
                        paso.tarea = tarea
                        paso.orden = orden
                        _poner_pictograma(paso, p_form.cleaned_data.get("arasaac_id_paso"))
                        paso.save()

            except pictogramas.ErrorArasaac:
                messages.error(request, SIN_PICTOGRAMA)
            else:
                messages.success(
                    request, f"Se han actualizado los pasos de la tarea «{tarea.nombre}»."
                )
                return redirect("tareas:catalogo")
    else:
        formset = PasoFormSet(prefix="pasos", instance=tarea)

    return render(request, "tareas/editar_pasos.html", {"tarea": tarea, "formset": formset})
