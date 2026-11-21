"""Pantallas de la agenda del estudiante (Tomás): HU-02-01 a HU-02-04, HU-02-06, HU-02-07
y HU-07-04. HU-02-05: Javi.

Bocetos: docs/iteracion-1/bocetos/despega_mockup_v3.html, pantallas B06 (Tareas de hoy),
B07 (Tarea, también los pasos), B08 (¿Has terminado? / ¿No puedes hacerla?), B11 (plan B)
y B30 (semana).
"""

from datetime import date

from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.comun.models import Notificacion, TipoAviso, avisar, pendientes
from apps.tareas import planificacion
from apps.tareas.models import Asignacion, Paso, Tarea

from . import servicios
from .acceso import estudiante_requerido


def _usa_lector(estudiante):
    perfil = getattr(estudiante, "perfil", None)
    return bool(perfil and perfil.usa_lector_pantalla)


def _puede_ver_semana(estudiante):
    perfil = getattr(estudiante, "perfil", None)
    alcance = getattr(perfil, "alcance_agenda", "semana") if perfil else "semana"
    return alcance == "semana"


@estudiante_requerido
@require_GET
def dia(request):
    """HU-02-01. Ver mi agenda del día (B06).

    Si le han cambiado o cancelado una tarea (HU-03-04 y HU-03-05), antes ve el aviso: uno
    por pantalla, con el pictograma de la tarea y «Entendido» (ver `aviso_visto`).
    """
    ahora = servicios.ahora()
    aviso_pendiente = pendientes(request.user).first()
    if aviso_pendiente:
        return render(
            request,
            "agenda/aviso_cambio.html",
            {
                "aviso": aviso_pendiente,
                "quedan": pendientes(request.user).count() - 1,
                "estudiante": request.estudiante,
            },
        )
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
@require_POST
def aviso_visto(request, pk):
    """«Entendido» en un aviso de cambio: queda registrado que lo ha visto y vuelve a la
    agenda (que enseña el siguiente aviso, si hay más)."""
    aviso = get_object_or_404(Notificacion, pk=pk, destinatario=request.user)
    aviso.marcar_vista()
    # HU-07-04: si un adulto ha dicho que hoy no se puede hacer una tarea con plan B, de
    # aquí se va directo a elegir otra cosa.
    if aviso.tipo == TipoAviso.NO_SE_PUEDE and aviso.tarea_id:
        agenda = servicios.agenda_del_dia(request.estudiante)
        for t in agenda.tareas:
            if t.tarea_original.pk == aviso.tarea_id and t.debe_elegir_plan_b:
                return redirect("agenda:plan_b", pk=t.asignacion.pk)
    return redirect("agenda:dia")


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

    Si mientras tanto un adulto le ha cambiado o cancelado una tarea (HU-03-04, HU-03-05),
    se vuelve a cargar la agenda, que enseña primero ese aviso.
    """
    if pendientes(request.user).exists():
        respuesta = HttpResponse(status=200)
        respuesta["HX-Redirect"] = reverse("agenda:dia")
        return respuesta
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
        # Retrospectiva del 19/11: al terminarla bien, una pantalla de «¡Bravo!».
        return redirect("agenda:bravo", pk=pk)
    if not t.puede_terminar:
        if t.en_curso:
            messages.error(request, "Todavía te faltan pasos por hacer.")
        return redirect("agenda:detalle", pk=pk)
    return _confirmar(request, t, "¿Has terminado?", reverse("agenda:terminar", args=[pk]))


@estudiante_requerido
@require_GET
def bravo(request, pk):
    """«¡Bravo!» tras terminar una tarea (retrospectiva del 19/11).

    Una pantalla de enhorabuena con el pictograma de la tarea, sin sonido ni animación que no
    pueda pararse (baja sobrecarga, prefers-reduced-motion), y dos salidas: la siguiente tarea
    de hoy, si la hay, y «Mis tareas». Si la tarea no está hecha, vuelve a la tarea.
    """
    ahora = servicios.ahora()
    agenda = servicios.agenda_del_dia(request.estudiante, ahora)
    try:
        t, _, _ = servicios.con_contexto(agenda, pk)
    except Asignacion.DoesNotExist:
        raise Http404 from None
    if t.estado != "hecha":
        return redirect("agenda:detalle", pk=pk)
    siguiente = next(
        (
            o
            for o in agenda.tareas
            if o is not t and o.estado == "pendiente" and o.fin > ahora and o.inicio >= t.inicio
        ),
        None,
    )
    hechas = sum(1 for o in agenda.tareas if o.estado == "hecha")
    return render(
        request,
        "agenda/bravo.html",
        {
            "t": t,
            "siguiente": siguiente,
            "hechas": hechas,
            "total": sum(1 for o in agenda.tareas if o.estado != "cancelada"),
            "estudiante": request.estudiante,
        },
    )


def _confirmar(request, t, pregunta, accion):
    """HU-02-07 · La confirmación en una página, para cuando no se abre el <dialog>."""
    return render(
        request,
        "agenda/confirmar.html",
        {"t": t, "pregunta": pregunta, "accion": accion, "estudiante": request.estudiante},
    )


def avisar_al_tutor(t):
    """HU-07-04 (PA5): el tutor sabe qué tarea no se ha podido hacer y qué ha elegido."""
    avisar(
        t.asignacion.estudiante.tutor,
        servicios.texto_para_el_tutor(t),
        tipo=TipoAviso.PLAN_B,
        tarea=t.tarea,
    )


@estudiante_requerido
@require_http_methods(["GET", "POST"])
def no_puedo(request, pk):
    """HU-07-04 · «No puedo hacerla» (B07), después de confirmarlo (HU-02-07).

    Con plan B, pasa a elegir otra cosa (B11). Sin plan B, se queda como «No se ha podido»
    y se avisa al tutor.
    """
    try:
        t = servicios.tarea_del_dia(request.estudiante, pk)
    except Asignacion.DoesNotExist:
        raise Http404 from None
    if request.method == "GET":
        if not t.puede_decir_no_puedo:
            return redirect("agenda:detalle", pk=pk)
        return _confirmar(request, t, "¿No puedes hacerla?", reverse("agenda:no_puedo", args=[pk]))
    try:
        t = servicios.no_puedo(request.estudiante, pk, por=request.user)
    except servicios.ErrorDeAgenda as error:
        messages.error(request, str(error))
        return redirect("agenda:detalle", pk=pk)
    if t.debe_elegir_plan_b:
        return redirect("agenda:plan_b", pk=pk)
    avisar_al_tutor(t)
    return redirect("agenda:detalle", pk=pk)


@estudiante_requerido
@require_http_methods(["GET", "POST"])
def plan_b(request, pk):
    """HU-07-04 · B11 «Puedes hacer esto»: las actividades del plan B, por su orden. La
    que elige sustituye a la tarea en la agenda y se avisa al tutor."""
    try:
        t = servicios.tarea_del_dia(request.estudiante, pk)
    except Asignacion.DoesNotExist:
        raise Http404 from None
    if request.method == "POST":
        try:
            alternativa = int(request.POST.get("alternativa", ""))
            t = servicios.elegir_plan_b(request.estudiante, pk, alternativa)
        except (ValueError, Tarea.DoesNotExist):
            raise Http404 from None
        except servicios.ErrorDeAgenda as error:
            messages.error(request, str(error))
            return redirect("agenda:detalle", pk=pk)
        avisar_al_tutor(t)
        return redirect("agenda:dia")
    if not t.debe_elegir_plan_b:
        return redirect("agenda:detalle", pk=pk)
    return render(
        request,
        "agenda/plan_b.html",
        {"t": t, "estudiante": request.estudiante},
    )


@estudiante_requerido
@require_POST
def paso_hecho(request, pk, paso_pk):
    """HU-02-05. «Hecho» en el paso que toca. Vuelve a la pantalla de la tarea.

    Sin JavaScript se recarga la página y baja hasta los pasos (#pasos). Con HTMX el
    navegador sigue la redirección y solo se cambian los pasos, el botón principal, los
    mensajes y la confirmación de «Terminar» (ver tarea.html).
    """
    try:
        servicios.marcar_paso_hecho(request.estudiante, pk, paso_pk)
    except (Asignacion.DoesNotExist, Paso.DoesNotExist):
        raise Http404 from None
    except servicios.ErrorDeAgenda as error:
        # Sin bajar a los pasos: el aviso sale arriba y tiene que verse.
        messages.error(request, str(error))
        return redirect("agenda:detalle", pk=pk)
    return redirect(reverse("agenda:detalle", args=[pk]) + "#pasos")


# --- HU-02-06 · Ver mi semana y mi horario de clases (B30) ----------------------------


@estudiante_requerido
@require_GET
def semana(request):
    """B30 · Los 7 días de esta semana con su nombre, su letra, su forma y su color, y en
    cada uno la hora y el pictograma de sus tareas (PA1 y PA2). Al tocar un día se abre
    entero (PA3). El horario de la clase está en «Mi horario de clase» (PA4 y PA5)."""
    if not _puede_ver_semana(request.estudiante):
        return redirect("agenda:dia")
    ahora = servicios.ahora()
    dias = servicios.semana(request.estudiante, ahora)
    return render(
        request,
        "agenda/semana.html",
        {
            "estudiante": request.estudiante,
            "laborables": dias[:5],
            "fin_de_semana": dias[5:],
            "hoy": next(d for d in dias if d.es_hoy),
            "hoy_fecha": f"{ahora.day} de {planificacion.MESES[ahora.month - 1]}",
        },
    )


@estudiante_requerido
@require_GET
def otro_dia(request, fecha):
    """HU-02-06, PA3 · Un día de esta semana, entero: sus tareas en la línea de tiempo, solo
    para ver (no se empiezan antes de su día). Hoy es la agenda de siempre."""
    if not _puede_ver_semana(request.estudiante):
        return redirect("agenda:dia")
    try:
        dia = date.fromisoformat(fecha)
    except ValueError:
        raise Http404 from None
    ahora = servicios.ahora()
    if dia == ahora.date():
        return redirect("agenda:dia")
    if servicios.lunes_de(dia) != servicios.lunes_de(ahora.date()):
        raise Http404  # solo los días de esta semana
    tareas = servicios.tareas_del_dia(request.estudiante, dia, ahora)
    return render(
        request,
        "agenda/otro_dia.html",
        {
            "estudiante": request.estudiante,
            "tareas": tareas,
            "fecha": dia,
            "fecha_texto": planificacion.fecha_en_texto(dia),
            "dia_nombre": planificacion.DIAS[dia.weekday()],
            "pasado": dia < ahora.date(),
        },
    )
