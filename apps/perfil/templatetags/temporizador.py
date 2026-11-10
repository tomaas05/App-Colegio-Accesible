"""Cálculo del estado inicial del temporizador de una tarea en curso (HU-07-01)."""

import math

from django import template

from apps.agenda import servicios
from apps.perfil.models import TipoTemporizador

register = template.Library()

CIRCUNFERENCIA_RADIAL = 226.19  # 2 * pi * r (con r = 36)


@register.simple_tag(takes_context=True)
def datos_temporizador(context, fin=None, perfil=None, inicio=None, ahora=None):
    """Calcula el tiempo restante hasta `fin` (PA1, PA5, PA6)."""
    t = context.get("t")
    if fin is None and t is not None:
        fin = getattr(t, "fin", None)
    if inicio is None and t is not None:
        inicio = getattr(t, "inicio", None)
    if ahora is None:
        ahora = context.get("ahora") or servicios.ahora()
    if perfil is None:
        perfil = context.get("perfil")

    if fin is not None and ahora is not None:
        segundos_restantes = max(0, int((fin - ahora).total_seconds()))
    else:
        segundos_restantes = 0

    if fin is not None and inicio is not None and fin > inicio:
        duracion_total = max(1, int((fin - inicio).total_seconds()))
    else:
        duracion_total = max(1, segundos_restantes)

    porcentaje = max(0, min(100, round(segundos_restantes * 100 / duracion_total)))
    minutos_restantes = math.ceil(segundos_restantes / 60) if segundos_restantes > 0 else 0
    minutos_mm = segundos_restantes // 60
    segundos_ss = segundos_restantes % 60
    mm_ss = f"{minutos_mm:02d}:{segundos_ss:02d}"

    if segundos_restantes > 0:
        texto_restante = f"Quedan {minutos_restantes} min"
        texto_corto = f"{minutos_restantes} min"
    else:
        texto_restante = "Se acabó el tiempo"
        texto_corto = "0 min"

    tipo = getattr(perfil, "tipo_temporizador", None) or TipoTemporizador.LINEAL
    if tipo not in TipoTemporizador.values:
        tipo = TipoTemporizador.LINEAL

    visible = getattr(perfil, "temporizador_visible", True) if perfil is not None else True
    puede_ocultar = (
        getattr(perfil, "puede_ocultar_temporizador", False) if perfil is not None else False
    )

    offset_radial = round(CIRCUNFERENCIA_RADIAL * (100 - porcentaje) / 100, 2)

    return {
        "segundos_restantes": segundos_restantes,
        "duracion_total": duracion_total,
        "porcentaje": porcentaje,
        "minutos_restantes": minutos_restantes,
        "mm_ss": mm_ss,
        "texto_restante": texto_restante,
        "texto_corto": texto_corto,
        "tipo": tipo,
        "visible": bool(visible),
        "puede_ocultar": bool(puede_ocultar),
        "circunferencia": CIRCUNFERENCIA_RADIAL,
        "offset_radial": offset_radial,
    }
