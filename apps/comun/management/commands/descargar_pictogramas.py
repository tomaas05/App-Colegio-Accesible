"""Descarga una sola vez los pictogramas de ARASAAC que usa la interfaz (decisión 0004).

Lee `static/img/pictogramas/listado.csv` (nombre;palabra;id) y guarda cada uno como
`static/img/pictogramas/<nombre>.png`. Si la línea no trae id, busca la palabra y toma
el primer resultado (como hace el boceto v3), y apunta el id en el listado. Los que ya
están no se vuelven a pedir. Hacia ARASAAC solo sale la palabra o el número.
"""

import csv
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.comun import pictogramas
from apps.comun.pictos_interfaz import CARPETA

NOMBRE = re.compile(r"[a-z0-9][a-z0-9_-]{0,39}")
COLUMNAS = ["nombre", "palabra", "id"]


class Command(BaseCommand):
    help = "Descarga los pictogramas de ARASAAC de static/img/pictogramas/listado.csv."

    def add_arguments(self, parser):
        parser.add_argument("--listado", default=str(CARPETA / "listado.csv"))
        parser.add_argument("--destino", default=str(CARPETA))

    def handle(self, *args, listado, destino, **opciones):
        destino = Path(destino)
        destino.mkdir(parents=True, exist_ok=True)
        try:
            with open(listado, encoding="utf-8", newline="") as archivo:
                filas = list(csv.DictReader(archivo, delimiter=";"))
        except OSError as error:
            raise CommandError(f"No se puede leer {listado}.") from error

        # Primero se comprueba todo el listado: con una línea mal no se descarga nada.
        for numero, fila in enumerate(filas, start=2):
            fila["nombre"] = (fila.get("nombre") or "").strip()
            fila["palabra"] = (fila.get("palabra") or "").strip()
            fila["id"] = (fila.get("id") or "").strip()
            if not NOMBRE.fullmatch(fila["nombre"]):
                raise CommandError(f"Línea {numero}: nombre no válido «{fila['nombre']}».")
            if fila["id"]:
                try:
                    pictogramas.id_valido(fila["id"])
                except pictogramas.IdentificadorNoValido:
                    raise CommandError(f"Línea {numero}: el id no es un número.") from None
            elif not pictogramas.texto_valido(fila["palabra"]):
                raise CommandError(f"Línea {numero}: falta el id o una palabra que buscar.")

        nuevos = ya_estaban = fallos = 0
        for fila in filas:
            archivo = destino / f"{fila['nombre']}.png"
            if archivo.exists():
                ya_estaban += 1
                continue
            try:
                if not fila["id"]:
                    encontrados = pictogramas.buscar(fila["palabra"])
                    if not encontrados:
                        raise pictogramas.ErrorArasaac(f"no hay pictogramas de «{fila['palabra']}»")
                    fila["id"] = str(encontrados[0]["id"])
                archivo.write_bytes(pictogramas.descargar(fila["id"]))
                nuevos += 1
            except pictogramas.ErrorArasaac as error:
                fallos += 1
                self.stderr.write(f"{fila['nombre']}: {error}")

        # Se apuntan los id encontrados, para que la próxima descarga traiga los mismos.
        with open(listado, "w", encoding="utf-8", newline="") as archivo:
            escritor = csv.DictWriter(
                archivo, COLUMNAS, delimiter=";", lineterminator="\n", extrasaction="ignore"
            )
            escritor.writeheader()
            escritor.writerows(filas)

        self.stdout.write(f"{nuevos} descargados, {ya_estaban} ya estaban, {fallos} con fallo.")
        self.stdout.write(pictogramas.ATRIBUCION)
        if fallos:
            raise CommandError("Algún pictograma no se ha podido descargar. Vuelve a lanzarlo.")
