"""Pantallas de las tareas del centro (Objetivo 5, Javi).

HU-05-03 · Comedor y menú (administrador): de un mes, quién reparte el menú, el menú del
mes y quién se encarga del comedor cada día (boceto B67, «Tareas del centro»).
"""

import re
from datetime import date

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.usuarios.permisos import admin_requerido

from . import servicios
from .forms import FormComedor, FormMenu, FormReparto
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
