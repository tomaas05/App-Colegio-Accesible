"""Pantallas del horario escolar (HU-03-11, Javi).

B37 · Horario escolar (administrador): elegir clase, ver su horario en una tabla y
poner o quitar asignaturas por día y franja.
Mi horario (estudiante): el horario de su clase día a día, con imagen y nombre.
Boceto: docs/iteracion-1/bocetos/despega_mockup_v3.html.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from apps.agenda.acceso import estudiante_requerido
from apps.usuarios.models import Clase, Rol

from . import servicios
from .models import Asignatura, DiaLectivo, Franja


def _numero(valor):
    return int(valor) if valor and str(valor).isdigit() else None


@login_required
@require_http_methods(["GET", "POST"])
def cargar_horario(request):
    """B37 · Horario escolar de una clase (PA1, PA2, PA3 y PA4). Solo el administrador."""
    if request.user.rol != Rol.ADMINISTRADOR:
        raise PermissionDenied("Solo el administrador carga el horario escolar.")

    clases = Clase.objects.order_by("nombre")
    datos = request.POST if request.method == "POST" else request.GET
    clase = clases.filter(pk=_numero(datos.get("clase"))).first() or clases.first()
    error = None
    elegido = {}

    if request.method == "POST" and clase:
        dia = _numero(request.POST.get("dia"))
        franja = Franja.objects.filter(pk=_numero(request.POST.get("franja"))).first()
        if dia not in DiaLectivo.values or franja is None:
            error = "Elige un día de lunes a viernes y una franja."
        elif "quitar" in request.POST:
            asignatura = servicios.quitar(clase, dia, franja)
            if asignatura:
                messages.success(request, f"Quitada «{asignatura.nombre}».")
            return redirect(f"{reverse('horario:cargar')}?clase={clase.pk}")
        else:
            asignatura = Asignatura.objects.filter(
                pk=_numero(request.POST.get("asignatura"))
            ).first()
            elegido = {"dia": dia, "franja": franja.pk, "asignatura": asignatura and asignatura.pk}
            if asignatura is None:
                error = "Elige una asignatura o un taller."
            else:
                try:
                    casilla = servicios.poner(clase, dia, franja, asignatura)
                except servicios.ErrorDeHorario as e:
                    error = str(e)
                else:
                    messages.success(request, f"Guardado: {servicios.texto_de(casilla)}.")
                    return redirect(f"{reverse('horario:cargar')}?clase={clase.pk}")

    return render(
        request,
        "horario/cargar.html",
        {
            "clases": clases,
            "clase": clase,
            "filas": servicios.rejilla(clase) if clase else [],
            "dias": servicios.dias(),
            "franjas": Franja.objects.order_by("orden"),
            "asignaturas": Asignatura.objects.order_by("nombre"),
            "error": error,
            "elegido": elegido,
        },
        status=400 if error else 200,
    )


@estudiante_requerido
@require_GET
def mi_horario(request):
    """El estudiante ve el horario de su clase (PA1 y PA4), un día cada vez.

    Por defecto, hoy (o el lunes si es fin de semana); ?dia=1…5 para otro día.
    """
    hoy = timezone.localdate().isoweekday()
    dia = _numero(request.GET.get("dia"))
    if dia not in DiaLectivo.values:
        dia = hoy if hoy in DiaLectivo.values else DiaLectivo.LUNES
    clase = request.estudiante.clase
    return render(
        request,
        "horario/mi_horario.html",
        {
            "clase": clase,
            "dia": DiaLectivo(dia),
            "es_hoy": dia == hoy,
            "dias": servicios.dias(),
            "casillas": servicios.del_dia(clase, dia),
        },
    )
