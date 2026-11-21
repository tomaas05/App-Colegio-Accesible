"""Crear tareas, verlas y asignarlas (Úrsula): HU-03-01, HU-03-03 y HU-03-08.

Permisos: solo tutor, profesional o familiar (permisos.py). Los estudiantes a los que
se puede asignar salen de `estudiantes_de(request.user)`, la única regla de visibilidad.
Pictogramas: el servidor los trae de ARASAAC y guarda una copia (decisión 0004).
"""

from datetime import date, timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import PermissionDenied
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
    NoSePuedeForm,
    PasoFormSet,
    TareaForm,
)
from .models import Ambito, Asignacion, ExcepcionAsignacion, PlanB, Tarea, TipoExcepcion
from .permisos import gestiona_tareas

MAX_PASOS = 30
SIN_PICTOGRAMA = (
    "No se ha podido traer el pictograma de ARASAAC. "
    "Vuelve a intentarlo o sube una imagen de tu equipo."
)


@gestiona_tareas
@require_GET
def catalogo_tareas(request):
    """Biblioteca de tareas (HU-03-01), con buscador por nombre y filtro por ámbito.

    Retrospectiva del 19/11: el tutor busca una tarea en lugar de pasar páginas. Los filtros
    van por GET y se aplican al pulsar «Buscar» (nada cambia solo al escribir, WCAG 3.2.2).
    """
    texto = (request.GET.get("q") or "").strip()[:80]
    ambito = request.GET.get("ambito") or ""
    if ambito not in Ambito.values:
        ambito = ""
    tareas = Tarea.objects.annotate(
        n_pasos=Count("pasos", distinct=True), n_planes_b=Count("planes_b", distinct=True)
    ).order_by("-id")
    if texto:
        tareas = tareas.filter(Q(nombre__icontains=texto) | Q(descripcion__icontains=texto))
    if ambito:
        tareas = tareas.filter(ambito=ambito)
    return render(
        request,
        "tareas/catalogo.html",
        {
            "tareas": tareas,
            "texto": texto,
            "ambito": ambito,
            "ambitos": Ambito.choices,
            "con_filtros": bool(texto or ambito),
        },
    )


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
        # RESTRICCIÓN PROFESIONAL (HU-03-08): solo tareas de ámbito escolar
        if form.is_valid() and request.user.rol == Rol.PROFESIONAL:
            ambito = form.cleaned_data.get("ambito")
            if ambito != Ambito.ESCOLAR:
                form.add_error(
                    "ambito", "Los profesionales solo pueden crear tareas de ámbito escolar."
                )
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
        if request.user.rol == Rol.PROFESIONAL:
            form.initial["ambito"] = Ambito.ESCOLAR
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
    """B43 · Asignar una tarea a uno o varios de mis estudiantes, con solapes y restricciones."""
    tarea_inicial = get_object_or_404(Tarea, id=tarea_id) if tarea_id else None

    if request.method == "POST":
        form = AsignacionForm(request.POST, usuario=request.user)

        # Restricción de familiar: tareas para casa fuera del horario escolar
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

        # Restricción de profesional (HU-03-08): estrictamente dentro del horario escolar
        if (
            form.is_valid()
            and request.user.rol == Rol.PROFESIONAL
            and not choca_con_horario_escolar(
                form.cleaned_data["dias_semana"],
                form.cleaned_data["hora_inicio"],
                form.cleaned_data["hora_fin"],
            )
        ):
            form.add_error(
                None,
                "Las actividades de los profesionales "
                "deben programarse estrictamente dentro del horario escolar.",
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
        # Retrospectiva del 19/11: «Desde» sale con la fecha de hoy (se puede cambiar).
        inicial = {"vigencia_desde": timezone.localdate()}
        if tarea_inicial:
            inicial["tarea"] = tarea_inicial
        form = AsignacionForm(initial=inicial, usuario=request.user)

    return render(request, "tareas/asignar_tarea.html", {"form": form, "tarea": tarea_inicial})


# --- Tareas planificadas (B44): HU-03-04 modificar y HU-03-05 cancelar ---


def _fecha_de(request):
    try:
        return date.fromisoformat(request.GET.get("fecha") or request.POST.get("fecha") or "")
    except ValueError:
        return None


def _alcance_de(request):
    alcance = request.POST.get("alcance") or request.GET.get("alcance")
    return "dia" if alcance == "dia" else "serie"


def _filtros_de(request):
    return {
        clave: request.GET.get(clave) or request.POST.get(clave) or ""
        for clave in ("f_estudiante", "f_fecha")
    }


def _volver_a_planificadas(request):
    filtros = {clave[2:]: valor for clave, valor in _filtros_de(request).items() if valor}
    url = reverse("tareas:tareas_planificadas")
    return f"{url}?{urlencode(filtros)}" if filtros else url


def _asignacion_que_puede_cambiar(request, asignacion_id):
    asignacion = get_object_or_404(
        Asignacion.objects.select_related("tarea", "estudiante__usuario", "asignado_por"),
        id=asignacion_id,
    )
    # RESTRICCIÓN PROFESIONAL (HU-03-08): No puede modificar/cancelar tareas creadas por otros
    if request.user.rol == Rol.PROFESIONAL and asignacion.asignado_por != request.user:
        raise Http404
    if not planificacion.puede_cambiar(request.user, asignacion):
        raise Http404
    return asignacion


def _empezada(asignacion, fecha):
    from apps.agenda.models import Ejecucion

    return Ejecucion.objects.filter(
        asignacion=asignacion, fecha=fecha, inicio_real__isnull=False
    ).exists()


def _dia_valido(asignacion, fecha, hoy):
    if fecha is None or fecha < hoy or not asignacion.aplica_el(fecha):
        return False
    excepcion = asignacion.excepciones.filter(fecha=fecha).first()
    return not planificacion.ocurrencia(asignacion, fecha, excepcion).cancelada


@gestiona_tareas
@require_GET
def tareas_planificadas(request):
    hoy = timezone.localdate()
    filtro = FiltroPlanificadasForm(request.GET or None, usuario=request.user, hoy=hoy)
    estudiante = fecha = None
    if filtro.is_valid():
        estudiante = filtro.cleaned_data["estudiante"]
        fecha = filtro.cleaned_data["fecha"]

    asignaciones = (
        planificacion.que_puede_cambiar(request.user)
        .select_related("tarea", "estudiante__usuario")
        .filter(cancelada=False)
        .filter(Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=fecha or hoy))
        .order_by("estudiante__usuario__first_name", "hora_inicio", "pk")
    )
    # RESTRICCIÓN PROFESIONAL: filtrar solo las suyas en la lista de planificadas si procede
    if request.user.rol == Rol.PROFESIONAL:
        asignaciones = asignaciones.filter(asignado_por=request.user)

    if estudiante:
        asignaciones = asignaciones.filter(estudiante=estudiante)

    filas = []
    marcables = set()
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
        if fecha == hoy:
            marcables = {o.asignacion.pk for o in filas if _hoy_se_puede_marcar(o.asignacion)}
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
            "marcables": marcables,
        },
    )


def _hoy(asignacion):
    from apps.agenda import servicios

    try:
        return servicios.tarea_del_dia(asignacion.estudiante, asignacion.pk)
    except Asignacion.DoesNotExist:
        return None


def _hoy_se_puede_marcar(asignacion):
    t = _hoy(asignacion)
    return bool(t and t.puede_decir_no_puedo)


@gestiona_tareas
@require_http_methods(["GET", "POST"])
def no_se_puede(request, asignacion_id):
    from apps.agenda import servicios

    asignacion = _asignacion_que_puede_cambiar(request, asignacion_id)
    volver = _volver_a_planificadas(request)
    estudiante, tarea = asignacion.estudiante, asignacion.tarea
    hoy = _hoy(asignacion)
    if not (hoy and hoy.puede_decir_no_puedo):
        messages.error(request, f"«{tarea.nombre}» ya no se puede marcar hoy.")
        return redirect(volver)
    form = NoSePuedeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        motivo = form.cleaned_data["motivo"].strip().rstrip(".")
        la_de_hoy = hoy.tarea
        t = servicios.no_puedo(estudiante, asignacion.pk, por=request.user, motivo=motivo)
        texto = f"Hoy no se puede hacer «{la_de_hoy.nombre}»: {motivo}."
        if t.debe_elegir_plan_b:
            texto += " Elige otra cosa."
        avisar(estudiante.usuario, texto, tipo=TipoAviso.NO_SE_PUEDE, tarea=la_de_hoy)
        if estudiante.tutor_id and estudiante.tutor_id != request.user.pk:
            avisar(
                estudiante.tutor,
                f"{request.user.get_full_name()} ha marcado que {estudiante.usuario.first_name} "
                f"no puede hacer «{la_de_hoy.nombre}» hoy: {motivo}.",
                tipo=TipoAviso.PLAN_B,
                tarea=la_de_hoy,
            )
        messages.success(
            request,
            f"Hecho. {estudiante.usuario.first_name} recibe un aviso"
            + (" y elige otra cosa de su plan B." if t.debe_elegir_plan_b else "."),
        )
        return redirect(volver)
    return render(
        request,
        "tareas/no_se_puede.html",
        {
            "form": form,
            "tarea": tarea,
            "estudiante": estudiante,
            "asignacion": asignacion,
            "hoy": hoy,
            "tiene_plan_b": bool(hoy.alternativas) and not hoy.es_plan_b,
            "volver": volver,
            "filtros": _filtros_de(request),
        },
    )


@gestiona_tareas
@require_http_methods(["GET", "POST"])
def editar_asignacion(request, asignacion_id):
    """HU-03-04 · Cambiar las horas de un solo día, o las horas y los días de toda la serie."""
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
        # RESTRICCIÓN PROFESIONAL (HU-03-08):
        # las actividades modificadas deben estar en horario escolar
        elif request.user.rol == Rol.PROFESIONAL and not choca_con_horario_escolar(
            dias, inicio, fin
        ):
            form.add_error(
                None,
                "Las actividades de los profesionales "
                "deben programarse estrictamente dentro del horario escolar.",
            )
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
    from apps.agenda.models import Ejecucion, EstadoEjecucion

    return Ejecucion.objects.filter(
        asignacion=asignacion, fecha=fecha, estado=EstadoEjecucion.EN_CURSO
    ).exists()


def _guardar_dia(asignacion, fecha, inicio, fin, usuario):
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
    """HU-03-05 · Cancelar un solo día o toda la serie."""
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
    if usuario.rol in (Rol.TUTOR, Rol.PROFESIONAL):
        return True
    return usuario.rol == Rol.FAMILIAR and tarea.creador_id == usuario.pk


@gestiona_tareas
@require_http_methods(["GET", "POST"])
def plan_b(request, tarea_id):
    tarea = get_object_or_404(Tarea, id=tarea_id)
    if not puede_editar_plan_b(request.user, tarea):
        raise Http404
    anadir = AnadirPlanBForm(tarea=tarea)
    crear = CrearAlternativaForm()
    accion = request.POST.get("accion")
    foco = ""

    # Retrospectiva del 19/11 (opción A elegida por el equipo): se toca una tarjeta de la
    # biblioteca para añadirla al plan B o quitarla («alternar»), y «Primera» pone una
    # alternativa la primera. Las acciones de antes (subir, bajar, quitar, añadir) se
    # mantienen para quien no tenga la pantalla nueva y para las pruebas.
    texto_buscar = (request.GET.get("q") or request.POST.get("q") or "").strip()[:80]
    volver = reverse("tareas:plan_b", args=[tarea.pk])
    if texto_buscar:
        volver += "?" + urlencode({"q": texto_buscar})

    if request.method == "POST" and accion in ("alternar", "primera"):
        alternativa = get_object_or_404(
            Tarea.objects.exclude(pk=tarea.pk), pk=_numero_o_nada(request.POST.get("alternativa"))
        )
        with transaction.atomic():
            lista = list(tarea.planes_b.select_for_update().order_by("orden", "pk"))
            plan = next((p for p in lista if p.alternativa_id == alternativa.pk), None)
            if accion == "alternar" and plan:
                lista.remove(plan)
                plan.delete()
                texto = f"«{alternativa.nombre}» ya no está en el plan B."
            elif accion == "alternar":
                plan = PlanB.objects.create(
                    tarea=tarea, alternativa=alternativa, orden=len(lista) + 1
                )
                lista.append(plan)
                texto = f"«{alternativa.nombre}» se ha añadido al plan B (número {len(lista)})."
            elif plan:
                lista.remove(plan)
                lista.insert(0, plan)
                texto = f"«{alternativa.nombre}» es ahora la primera."
            else:
                raise Http404
            _renumerar(lista)
        messages.success(request, texto)
        return redirect(f"{volver}{'&' if '?' in volver else '?'}foco=t-{alternativa.pk}")

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

    planes = list(tarea.planes_b.select_related("alternativa").order_by("orden", "pk"))
    numero_de = {p.alternativa_id: i for i, p in enumerate(planes, start=1)}
    biblioteca = Tarea.objects.exclude(pk=tarea.pk).order_by("nombre")
    if texto_buscar:
        biblioteca = biblioteca.filter(
            Q(nombre__icontains=texto_buscar) | Q(descripcion__icontains=texto_buscar)
        )
    tarjetas = [(t, numero_de.get(t.pk)) for t in biblioteca]
    foco = request.GET.get("foco", "")
    return render(
        request,
        "tareas/plan_b.html",
        {
            "tarea": tarea,
            "planes": planes,
            "tarjetas": tarjetas,
            "texto_buscar": texto_buscar,
            "nueva": accion == "crear" or request.GET.get("nueva") == "1",
            "foco_tarjeta": int(foco[2:]) if foco.startswith("t-") and foco[2:].isdigit() else None,
            "anadir": anadir,
            "crear": crear,
            "accion": accion,
            **_foco(foco),
        },
    )


def _numero_o_nada(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _foco(valor):
    accion, _, numero = valor.partition("-")
    if accion in ("subir", "bajar") and numero.isdigit():
        return {"foco_accion": accion, "foco_id": int(numero)}
    return {"foco_accion": "", "foco_id": None}


def _renumerar(lista):
    for orden, plan in enumerate(lista, start=1):
        if plan.orden != orden:
            plan.orden = orden
            plan.save(update_fields=["orden"])


def _anadir_al_plan_b(tarea, alternativa):
    ultimo = tarea.planes_b.order_by("-orden").values_list("orden", flat=True).first() or 0
    PlanB.objects.get_or_create(
        tarea=tarea, alternativa=alternativa, defaults={"orden": ultimo + 1}
    )


@gestiona_tareas
@require_http_methods(["GET", "POST"])
def editar_pasos_tarea(request, tarea_id):
    """HU-03-02 · Añadir, ordenar y modificar los pasos de una tarea existente."""
    tarea = get_object_or_404(Tarea, id=tarea_id)

    # RESTRICCIÓN PROFESIONAL (HU-03-08): El profesional solo puede editar los pasos de sus tareas
    if request.user.rol == Rol.PROFESIONAL and tarea.creador != request.user:
        raise PermissionDenied("No puedes modificar tareas creadas por otros usuarios.")

    if request.method == "POST":
        formset = PasoFormSet(request.POST, request.FILES, prefix="pasos", instance=tarea)
        if formset.is_valid():
            try:
                with transaction.atomic():
                    for p_form in formset.deleted_forms:
                        if p_form.instance.pk:
                            p_form.instance.delete()

                    validos = [
                        p_form
                        for p_form in formset.forms
                        if p_form.cleaned_data and not p_form.cleaned_data.get("DELETE")
                    ]
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
