"""Crear tareas, verlas y asignarlas (Úrsula): HU-03-01 y HU-03-03.

Permisos: solo tutor, profesional o familiar (permisos.py). Los estudiantes a los que
se puede asignar salen de `estudiantes_de(request.user)`, la única regla de visibilidad.
Pictogramas: el servidor los trae de ARASAAC y guarda una copia (decisión 0004).
"""

from django.contrib import messages
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from apps.comun import pictogramas
from apps.horario.servicios import choca_con_horario_escolar
from apps.usuarios.models import Estudiante, Rol

from .forms import AsignacionForm, EditarAsignacionForm, PasoFormSet, TareaForm
from .models import Asignacion, Tarea
from .permisos import gestiona_tareas

MAX_PASOS = 30
SIN_PICTOGRAMA = (
    "No se ha podido traer el pictograma de ARASAAC. "
    "Vuelve a intentarlo o sube una imagen de tu equipo."
)


@gestiona_tareas
@require_GET
def catalogo_tareas(request):
    tareas = (
        Tarea.objects.annotate(n_pasos=Count("pasos")).prefetch_related("planes_b").order_by("-id")
    )
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

    form.save_m2m()

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


@gestiona_tareas
def tareas_planificadas(request):
    """Vista para listar y filtrar las tareas planificadas por estudiante y/o día."""
    asignaciones = Asignacion.objects.filter(cancelada=False)

    estudiante_seleccionado = request.GET.get("estudiante")
    dia_seleccionado = request.GET.get("dia")

    if estudiante_seleccionado:
        asignaciones = asignaciones.filter(estudiante_id=estudiante_seleccionado)

    if dia_seleccionado:
        try:
            dia_int = int(dia_seleccionado)
            # Filtramos las asignaciones cuyo array dias_semana contenga el día seleccionado
            asignaciones = [asig for asig in asignaciones if dia_int in asig.dias_semana]
        except ValueError:
            pass

    estudiantes = Estudiante.objects.all()

    return render(
        request,
        "tareas/tareas_planificadas.html",
        {
            "asignaciones": asignaciones,
            "estudiantes": estudiantes,
            "estudiante_seleccionado": estudiante_seleccionado or "",
            "dia_seleccionado": dia_seleccionado or "",
        },
    )


@gestiona_tareas
@require_http_methods(["GET", "POST"])
def editar_asignacion(request, asignacion_id):
    """HU-03-04 · Modificar la hora, el día o la vigencia de una tarea con control de solapes."""
    asignacion = get_object_or_404(Asignacion, id=asignacion_id)

    if request.method == "POST":
        form = EditarAsignacionForm(request.POST, instance=asignacion)

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

            # --- VALIDACIÓN DE SOLAPES ---
            dias_nuevos = datos["dias_semana"]
            hora_ini = datos["hora_inicio"]
            hora_fin = datos["hora_fin"]

            solapa = False
            otras_asignaciones = Asignacion.objects.filter(
                estudiante=asignacion.estudiante, cancelada=False
            ).exclude(id=asignacion.id)
            for otra in otras_asignaciones:
                if any(d in otra.dias_semana for d in dias_nuevos):
                    if hora_ini < otra.hora_fin and hora_fin > otra.hora_inicio:
                        solapa = True
                        break

            if solapa:
                form.add_error(
                    None,
                    "El cambio genera un solapamiento con otra tarea existente del estudiante.",
                )
            else:
                with transaction.atomic():
                    form.save()
                    try:
                        from apps.comun.models import Notificacion

                        Notificacion.objects.create(
                            destinatario=asignacion.estudiante.usuario,
                            mensaje=(
                                f"Se ha actualizado la planificación "
                                f"de la tarea «{asignacion.tarea.nombre}»."
                            ),
                        )
                    except Exception:
                        pass

                messages.success(
                    request,
                    f"La planificación de la tarea «{asignacion.tarea.nombre}» "
                    f"se ha actualizado correctamente y se ha avisado al estudiante.",
                )
                return redirect("tareas:tareas_planificadas")
    else:
        form = EditarAsignacionForm(instance=asignacion)

    return render(
        request,
        "tareas/editar_asignacion.html",
        {
            "form": form,
            "asignacion": asignacion,
            "tarea": asignacion.tarea,
            "estudiante": asignacion.estudiante,
        },
    )


@gestiona_tareas
@require_http_methods(["GET", "POST"])
def cancelar_asignacion(request, asignacion_id):
    """HU-03-05 · Cancelar una tarea planificada (o un día específico de la serie)."""
    asignacion = get_object_or_404(Asignacion, id=asignacion_id)

    # Recogemos el día que venía filtrado (si lo hay)
    dia_filtro = request.GET.get("dia") or request.POST.get("dia")

    if request.method == "POST":
        alcance = request.POST.get("alcance", "serie")  # 'dia' o 'serie'

        if alcance == "dia" and dia_filtro:
            try:
                dia_int = int(dia_filtro)
                if len(asignacion.dias_semana) <= 1 and dia_int in asignacion.dias_semana:
                    asignacion.cancelada = True
                elif dia_int in asignacion.dias_semana:
                    asignacion.dias_semana = [d for d in asignacion.dias_semana if d != dia_int]

                asignacion.save()
            except ValueError:
                pass
        else:
            asignacion.cancelada = True
            asignacion.save()

        try:
            from apps.comun.models import Notificacion

            Notificacion.objects.create(
                destinatario=asignacion.estudiante.usuario,
                mensaje=(
                    f"Se ha cancelado la planificación de la tarea «{asignacion.tarea.nombre}»."
                ),
            )
        except Exception:
            pass

        messages.success(
            request,
            f"La planificación de la tarea «{asignacion.tarea.nombre}» "
            f"se ha actualizado correctamente.",
        )
        return redirect("tareas:tareas_planificadas")

    return render(
        request,
        "tareas/confirmar_cancelacion.html",
        {
            "asignacion": asignacion,
            "tarea": asignacion.tarea,
            "estudiante": asignacion.estudiante,
            "dia_filtro": dia_filtro,
        },
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
