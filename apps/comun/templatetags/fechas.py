"""Fecha de hoy en español para la barra de título (decisión 0005).

Con nombres fijos: {% now %} usa el idioma activo y LocaleMiddleware lo toma del navegador,
así que con el navegador en inglés salía «Sunday, 15 de November».

    {% load fechas %}
    {% fecha_larga %}   →  Domingo, 15 de noviembre
    {% fecha_corta %}   →  Dom 15 nov
    {% fecha_iso %}     →  2026-11-15 (para <time datetime>)
"""

from django import template
from django.utils import timezone

register = template.Library()

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
DIAS_CORTOS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]  # fmt: skip


def _hoy(fecha=None):
    return fecha or timezone.localdate()


@register.simple_tag
def fecha_larga(fecha=None):
    f = _hoy(fecha)
    return f"{DIAS[f.weekday()].capitalize()}, {f.day} de {MESES[f.month - 1]}"


@register.simple_tag
def fecha_corta(fecha=None):
    f = _hoy(fecha)
    return f"{DIAS_CORTOS[f.weekday()].capitalize()} {f.day} {MESES[f.month - 1][:3]}"


@register.simple_tag
def fecha_iso(fecha=None):
    return _hoy(fecha).isoformat()
