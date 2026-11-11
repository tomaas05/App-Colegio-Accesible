"""Fuente para las imágenes que dibuja Pillow (avatares con inicial y marcadores de prueba).

La fuente por defecto de Pillow no tiene vocales con tilde ni «Ñ»: dibuja un cuadro.
Se usa Nunito, la misma de los títulos, que ya servimos desde static/fonts/.
"""

from functools import lru_cache

from django.conf import settings
from PIL import ImageFont

NUNITO = settings.BASE_DIR / "static" / "fonts" / "nunito-latin-800-normal.woff2"


@lru_cache(maxsize=8)
def fuente_titulos(tamano):
    """Nunito 800 del tamaño pedido; si no se puede leer, la de Pillow (sin tildes)."""
    try:
        return ImageFont.truetype(str(NUNITO), tamano)
    except OSError:
        return ImageFont.load_default(size=tamano)
