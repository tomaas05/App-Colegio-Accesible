"""Cálculo del temporizador y avisos de una tarea en curso (HU-07-01, HU-07-02)."""

import math

from django import template

from apps.agenda import servicios
from apps.perfil.models import Paleta, TipoTemporizador

register = template.Library()

CIRCUNFERENCIA_RADIAL = 226.19  # 2 * pi * r (con r = 36)
UMBRAL_AVISO_5_SEG = 300  # 5 minutos (RF4.3.2)
UMBRAL_AVISO_1_SEG = 60  # 1 minuto (RF4.3.2)

# Sonido suave local en WAV base64 (sin peticiones externas, RNF1.1.2).
SONIDO_AVISO_WAV = (
    "data:audio/wav;base64,UklGRkQDAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YSADAACA"
    "gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICA"
    "gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICA"
)


def _resolver_siguiente_tarea(context, t):
    """Obtiene la siguiente tarea activa del día después de `t` (PA3, PA4)."""
    siguiente = context.get("despues")
    if siguiente is not None and not getattr(siguiente, "cancelada", False):
        return siguiente
    agenda = context.get("agenda")
    tareas = getattr(agenda, "tareas", None) if agenda is not None else None
    if not tareas or t is None:
        return None
    encontrada = False
    for candidata in tareas:
        if candidata == t or getattr(candidata, "asignacion", None) == getattr(
            t, "asignacion", None
        ):
            encontrada = True
        elif encontrada and not getattr(candidata, "cancelada", False):
            return candidata
    return None


@register.simple_tag(takes_context=True)
def datos_temporizador(context, fin=None, perfil=None, inicio=None, ahora=None):
    """Calcula el tiempo restante hasta `fin` y el aviso de poco tiempo (HU-07-01, HU-07-02)."""
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

    # HU-07-02 · Avisos de poco tiempo (5 min y 1 min) y sonido según sobrecarga sensorial.
    aviso_5_min = getattr(perfil, "aviso_5_min", True) if perfil is not None else True
    aviso_1_min = getattr(perfil, "aviso_1_min", True) if perfil is not None else True
    sonidos_activos = getattr(perfil, "sonidos_activos", True) if perfil is not None else True
    baja_sobrecarga = (
        bool(
            getattr(perfil, "baja_sobrecarga_sensorial", False)
            or getattr(perfil, "paleta", "") == Paleta.SUAVE
        )
        if perfil is not None
        else False
    )
    sonido_activo = bool(sonidos_activos and not baja_sobrecarga)

    mostrar_aviso = False
    texto_aviso = "¡Quedan 5 minutos!" if aviso_5_min else "¡Queda 1 minuto!"
    if 0 < segundos_restantes <= UMBRAL_AVISO_1_SEG and (aviso_1_min or aviso_5_min):
        mostrar_aviso = True
        texto_aviso = "¡Queda 1 minuto!"
    elif 0 < segundos_restantes <= UMBRAL_AVISO_5_SEG and aviso_5_min:
        mostrar_aviso = True
        if minutos_restantes > 1:
            texto_aviso = f"¡Quedan {minutos_restantes} minutos!"
        else:
            texto_aviso = "¡Queda 1 minuto!"

    siguiente_tarea = _resolver_siguiente_tarea(context, t)
    offset_radial = round(CIRCUNFERENCIA_RADIAL * (100 - porcentaje) / 100, 2)

    tiempo_agotado = segundos_restantes == 0
    tarea_actual = getattr(t, "tarea", None) if t is not None else None
    asignacion_obj = getattr(t, "asignacion", None) if t is not None else None
    asignacion_pk = getattr(asignacion_obj, "pk", None) if asignacion_obj is not None else None
    puede_no_puedo = bool(getattr(t, "puede_decir_no_puedo", False)) if t is not None else False
    tiene_plan_b = bool(getattr(t, "alternativas", None)) if t is not None else False

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
        "aviso_5_min": bool(aviso_5_min),
        "aviso_1_min": bool(aviso_1_min),
        "baja_sobrecarga": baja_sobrecarga,
        "sonido_activo": sonido_activo,
        "sonido_data_uri": SONIDO_AVISO_WAV,
        "mostrar_aviso": mostrar_aviso,
        "texto_aviso": texto_aviso,
        "siguiente_tarea": siguiente_tarea,
        "tiempo_agotado": tiempo_agotado,
        "tarea_actual": tarea_actual,
        "asignacion_pk": asignacion_pk,
        "puede_no_puedo": puede_no_puedo,
        "tiene_plan_b": tiene_plan_b,
    }
