"""{% pictograma "mochila" "🎒" %}: el pictograma de ARASAAC local o, si falta, el emoji."""

from django import template
from django.templatetags.static import static
from django.utils.html import format_html

from apps.comun import pictos_interfaz

register = template.Library()


@register.simple_tag
def pictograma(palabra, reserva=""):
    """Siempre decorativo (alt=""): el texto de al lado ya dice lo mismo."""
    ruta = pictos_interfaz.archivo(palabra)
    if ruta:
        return format_html(
            '<img class="loseta__imagen" src="{}" alt="" width="300" height="300">',
            static(f"img/pictogramas/{ruta.name}"),
        )
    return format_html('<span class="loseta__dibujo" aria-hidden="true">{}</span>', reserva)
