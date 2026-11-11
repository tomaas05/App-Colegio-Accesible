"""Descarga una sola vez los pictogramas de ARASAAC que usa la interfaz (decisión 0004).

Lee `static/img/pictogramas/listado.csv` (id;nombre) y guarda cada uno como
`static/img/pictogramas/<nombre>.png`. Los que ya están no se vuelven a pedir.
Hacia ARASAAC solo sale el número del pictograma.
"""

import csv
import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.comun import pictogramas

CARPETA = settings.BASE_DIR / "static" / "img" / "pictogramas"
NOMBRE = re.compile(r"[a-z0-9][a-z0-9_-]{0,39}")


class Command(BaseCommand):
    help = "Descarga los pictogramas de ARASAAC de static/img/pictogramas/listado.csv."

    def add_arguments(self, parser):
        parser.add_argument("--listado", default=str(CARPETA / "listado.csv"))
        parser.add_argument("--destino", default=str(CARPETA))

    def handle(self, *args, listado, destino, **opciones):
        from pathlib import Path

        destino = Path(destino)
        destino.mkdir(parents=True, exist_ok=True)
        try:
            with open(listado, encoding="utf-8", newline="") as archivo:
                filas = list(csv.DictReader(archivo, delimiter=";"))
        except OSError as error:
            raise CommandError(f"No se puede leer {listado}.") from error

        nuevos = ya_estaban = fallos = 0
        for numero, fila in enumerate(filas, start=2):
            nombre = (fila.get("nombre") or "").strip()
            try:
                identificador = pictogramas.id_valido(fila.get("id") or "")
            except pictogramas.IdentificadorNoValido:
                raise CommandError(f"Línea {numero}: el id no es un número.") from None
            if not NOMBRE.fullmatch(nombre):
                raise CommandError(f"Línea {numero}: nombre no válido «{nombre}».")
            archivo = destino / f"{nombre}.png"
            if archivo.exists():
                ya_estaban += 1
                continue
            try:
                archivo.write_bytes(pictogramas.descargar(identificador))
                nuevos += 1
            except pictogramas.ErrorArasaac as error:
                fallos += 1
                self.stderr.write(f"{nombre} ({identificador}): {error}")
        self.stdout.write(f"{nuevos} descargados, {ya_estaban} ya estaban, {fallos} con fallo.")
        self.stdout.write(pictogramas.ATRIBUCION)
        if fallos:
            raise CommandError("Algún pictograma no se ha podido descargar.")
