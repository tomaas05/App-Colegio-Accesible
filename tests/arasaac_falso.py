"""ARASAAC de mentira para las pruebas: nunca se sale a Internet.

`arasaac` (fixture de tests/conftest.py) sustituye `requests.get` dentro de
apps/comun/pictogramas.py y apunta cada petición en `arasaac.pedidas`.
"""

import io

import requests
from PIL import Image


def png(lado=300, color=(11, 60, 73)):
    """Un PNG válido de lado × lado píxeles."""
    salida = io.BytesIO()
    Image.new("RGB", (lado, lado), color).save(salida, "PNG")
    return salida.getvalue()


class Respuesta:
    def __init__(self, status_code=200, contenido=b"", datos=None, cabeceras=None):
        self.status_code = status_code
        self.content = contenido
        self._datos = datos
        self.headers = cabeceras or {}

    def json(self):
        if self._datos is None:
            raise ValueError("no es JSON")
        return self._datos

    def iter_content(self, tamano):
        for inicio in range(0, len(self.content), tamano):
            yield self.content[inicio : inicio + tamano]

    def close(self):
        pass


class ArasaacFalso:
    """Responde a la búsqueda con `resultados` y a las imágenes con `imagen`."""

    def __init__(self):
        self.pedidas = []
        self.resultados = [
            {"_id": 2349, "keywords": [{"keyword": "perro"}]},
            {"_id": 7202, "keywords": [{"keyword": "perro guía"}]},
        ]
        self.imagen = Respuesta(contenido=png())
        self.error = None  # una excepción de requests para simular que no responde

    def get(self, url, timeout=None, **opciones):
        self.pedidas.append({"url": url, "timeout": timeout})
        if self.error:
            raise self.error
        if "/search/" in url:
            if self.resultados is None:
                return Respuesta(status_code=404)
            return Respuesta(datos=self.resultados)
        return self.imagen

    def lento(self):
        self.error = requests.Timeout("tarda demasiado")
