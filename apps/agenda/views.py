"""Pantallas de la agenda del estudiante (Tomás): HU-02-01 a HU-02-04.

Bocetos: docs/iteracion-1/bocetos/despega_mockup_v3.html, pantallas B06 (Tareas de hoy),
B07 (Tarea) y B08 (¿Has terminado?).
"""

from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.tareas.models import Asignacion

from . import servicios
from .acceso import estudiante_requerido


def _usa_lector(estudiante):
    perfil = getattr(estudiante, "perfil", None)
    return bool(perfil and perfil.usa_lector_pantalla)


@estudiante_requerido
@require_GET
def dia(request):
    """HU-02-01. Ver mi agenda del día (B06)."""
    ahora = servicios.ahora()
    return render(
        request,
        "agenda/dia.html",
        {
            "estudiante": request.estudiante,
            "agenda": servicios.agenda_del_dia(request.estudiante, ahora),
            "ahora": ahora,
            "titulo": servicios.titulo_de_hoy(ahora),
        },
    )


@estudiante_requerido
@require_GET
def detalle(request, pk):
    """HU-02-02. Una tarea con su descripción, sus pasos, «Antes» y «Después» (B07)."""
    ahora = servicios.ahora()
    agenda = servicios.agenda_del_dia(request.estudiante, ahora)
    try:
        t, antes, despues = servicios.con_contexto(agenda, pk)
    except Asignacion.DoesNotExist:
        raise Http404 from None
    return render(
        request,
        "agenda/tarea.html",
        {
            "t": t,
            "antes": antes,
            "despues": despues,
            "agenda": agenda,
            "ahora": ahora,
            "estudiante": request.estudiante,
            "perfil": getattr(request.estudiante, "perfil", None),
            # Con lector de pantalla la app no pone su propia voz (para no solaparse).
            "ofrecer_voz": not _usa_lector(request.estudiante),
        },
    )


@estudiante_requerido
@require_GET
def aviso(request):
    """Aviso de la siguiente tarea al pie (RF2.10.1). Lo pide HTMX cada 30 s.

    `mostrado` es la asignación que ya se ve (0 = ninguna). Si no ha cambiado responde
    204 y HTMX no toca nada: así el lector de pantalla no repite el aviso.
    """
    agenda = servicios.agenda_del_dia(request.estudiante)
    actual = agenda.aviso.asignacion.pk if agenda.aviso else 0
    if request.GET.get("mostrado") == str(actual):
        return HttpResponse(status=204)
    return render(request, "agenda/_aviso_siguiente.html", {"agenda": agenda})


@estudiante_requerido
@require_POST
def empezar(request, pk):
    """HU-02-03. Confirmar el inicio de una tarea."""
    try:
        servicios.empezar(request.estudiante, pk)
    except Asignacion.DoesNotExist:
        raise Http404 from None
    except servicios.ErrorDeAgenda as error:
        messages.error(request, str(error))
    return redirect("agenda:detalle", pk=pk)


@estudiante_requerido
@require_http_methods(["GET", "POST"])
def terminar(request, pk):
    """HU-02-04. POST registra el fin.

    La confirmación (B08) es un <dialog> en la pantalla de la tarea (RF2.5.1). Este GET
    es la misma pregunta en una página, para cuando el navegador no tiene JavaScript.
    """
    try:
        t = servicios.tarea_del_dia(request.estudiante, pk)
    except Asignacion.DoesNotExist:
        raise Http404 from None
    if request.method == "POST":
        try:
            servicios.terminar(request.estudiante, pk)
        except servicios.ErrorDeAgenda as error:
            messages.error(request, str(error))
        return redirect("agenda:detalle", pk=pk)
    if not t.puede_terminar:
        if t.en_curso:
            messages.error(request, "Todavía te faltan pasos por hacer.")
        return redirect("agenda:detalle", pk=pk)
    return render(request, "agenda/confirmar_fin.html", {"t": t, "estudiante": request.estudiante})
