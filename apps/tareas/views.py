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
from apps.usuarios.models import Rol

from .forms import AsignacionForm, PasoFormSet, TareaForm
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
    tareas = Tarea.objects.annotate(n_pasos=Count("pasos")).order_by("-id")
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
